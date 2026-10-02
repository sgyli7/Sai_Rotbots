"""Export SI rigid-body/constraint data without embedding backend units.

Bevy/Unity integrations consume this file, not a Godot scene. Unknown joint or
equality types fail explicitly instead of producing an incomplete conversion.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

from sai_agent.goose.control import JointMap, metadata
from sai_agent.goose.spec import load_spec
from sai_agent.paths import resource_root


def main():
    robot=resource_root()/'robots/Goose_V0.1';path=robot/'models/full/robot.xml'
    spec=load_spec();m=mujoco.MjModel.from_xml_path(str(path));d=mujoco.MjData(m)
    mujoco.mj_resetDataKeyframe(m,d,0);mujoco.mj_forward(m,d)
    mapping=JointMap(m,spec);tree=ET.parse(path)
    active_spec={j['name']:j for j in spec['joints']}
    types={int(mujoco.mjtGeom.mjGEOM_BOX):'box',int(mujoco.mjtGeom.mjGEOM_SPHERE):'sphere',
           int(mujoco.mjtGeom.mjGEOM_ELLIPSOID):'ellipsoid',int(mujoco.mjtGeom.mjGEOM_CAPSULE):'capsule',
           int(mujoco.mjtGeom.mjGEOM_CYLINDER):'cylinder',int(mujoco.mjtGeom.mjGEOM_PLANE):'plane',
           int(mujoco.mjtGeom.mjGEOM_MESH):'mesh'}
    bodies=[];joints=[]
    for i in range(1,m.nbody):
        bid=m.body(i);r=d.xmat[i].reshape(3,3)
        bodies.append({'name':bid.name,'parent':m.body(int(m.body_parentid[i])).name or 'world',
                       'mass_kg':float(m.body_mass[i]),'local_position_m':m.body_pos[i].tolist(),
                       'local_orientation_wxyz':m.body_quat[i].tolist(),
                       'com_local_m':m.body_ipos[i].tolist(),
                       'principal_inertia_kg_m2':m.body_inertia[i].tolist(),
                       'principal_frame_local_wxyz':m.body_iquat[i].tolist(),
                       'home_world_position_m':d.xpos[i].tolist(),
                       'home_world_orientation_wxyz':d.xquat[i].tolist(),
                       'home_com_world_m':d.xipos[i].tolist(),
                       'home_principal_rotation_world':d.ximat[i].reshape(3,3).tolist()})
    for i in range(m.njnt):
        jid=m.joint(i);kind=int(m.jnt_type[i]);body=int(m.jnt_bodyid[i])
        if kind==int(mujoco.mjtJoint.mjJNT_FREE):continue
        if kind not in (int(mujoco.mjtJoint.mjJNT_HINGE),int(mujoco.mjtJoint.mjJNT_SLIDE)):
            raise ValueError(f'Unsupported joint {jid.name}')
        addr=int(m.jnt_dofadr[i]);home=float(d.qpos[int(m.jnt_qposadr[i])])
        active=jid.name in mapping.names;idx=mapping.names.index(jid.name) if active else -1
        joints.append({'name':jid.name,'type':'hinge' if kind==3 else 'slide',
                       'parent':m.body(int(m.body_parentid[body])).name,'child':m.body(body).name,
                       'axis_local_child':m.jnt_axis[i].tolist(),'anchor_local_child_m':m.jnt_pos[i].tolist(),
                       'home_anchor_world_m':d.xanchor[i].tolist(),'home_axis_world':d.xaxis[i].tolist(),
                       'limited':bool(m.jnt_limited[i]),'range':m.jnt_range[i].tolist(),'home':home,
                       'damping_SI':float(m.dof_damping[addr]),'friction_loss_SI':float(m.dof_frictionloss[addr]),
                       'armature_kg_m2':float(m.dof_armature[addr]),'stiffness_SI':float(m.jnt_stiffness[i]),
                       'spring_reference':float(m.qpos_spring[int(m.jnt_qposadr[i])]),'actuated':active,
                       'kp':float(mapping.kp[idx]) if active else 0,'kd':float(mapping.kd[idx]) if active else 0,
                       'torque_limit_Nm':float(mapping.limits[idx]) if active else 0,
                       'speed_limit_rad_s':float(spec['servos'][active_spec[jid.name]['servo']]['speed_limit_rad_s']) if active else 0,
                       'home_gravity_torque_Nm':float(d.qfrc_bias[addr]) if active else 0})
    geoms=[]
    for i in range(m.ngeom):
        g=m.geom(i);kind=int(m.geom_type[i])
        if kind not in types:raise ValueError(f'Unsupported geometry {g.name}: {kind}')
        geoms.append({'name':g.name,'body':m.body(int(m.geom_bodyid[i])).name or 'world','type':types[kind],
                      'size_m':m.geom_size[i].tolist(),'local_position_m':m.geom_pos[i].tolist(),
                      'local_orientation_wxyz':m.geom_quat[i].tolist(),'rgba':m.geom_rgba[i].tolist(),
                      'contact':bool(m.geom_contype[i] or m.geom_conaffinity[i]),
                      'friction':m.geom_friction[i].tolist()})
        if types[kind]=='mesh':
            mesh=int(m.geom_dataid[i]);va=int(m.mesh_vertadr[mesh]);vn=int(m.mesh_vertnum[mesh])
            fa=int(m.mesh_faceadr[mesh]);fn=int(m.mesh_facenum[mesh])
            geoms[-1]['vertices_local_m']=m.mesh_vert[va:va+vn].tolist()
            geoms[-1]['triangles']=m.mesh_face[fa:fa+fn].tolist()
    sites=[]
    for i in range(m.nsite):
        site=m.site(i)
        sites.append({'name':site.name,
                      'body':m.body(int(m.site_bodyid[i])).name,
                      'local_position_m':m.site_pos[i].tolist(),
                      'local_orientation_wxyz':m.site_quat[i].tolist(),
                      'home_world_position_m':d.site_xpos[i].tolist()})
    cameras=[]
    for i in range(m.ncam):
        camera=m.camera(i)
        cameras.append({'name':camera.name,
                        'body':m.body(int(m.cam_bodyid[i])).name,
                        'local_position_m':m.cam_pos[i].tolist(),
                        'local_orientation_wxyz':m.cam_quat[i].tolist(),
                        'fovy_deg':float(m.cam_fovy[i]),
                        'intrinsics_status':'design FOV; physical K and distortion require calibration'})
    loops=[]
    for e in tree.findall('./equality/*'):
        if e.tag!='connect' or 'site1' not in e.attrib or 'site2' not in e.attrib:
            raise ValueError('Only explicit site-to-site translational closure is supported')
        loop_site_ids=[m.site(e.attrib[k]).id for k in ('site1','site2')]
        loops.append({'name':e.attrib['name'],'type':'point_closure',
                      'body_a':m.body(int(m.site_bodyid[loop_site_ids[0]])).name,'point_a_local_m':m.site_pos[loop_site_ids[0]].tolist(),
                      'body_b':m.body(int(m.site_bodyid[loop_site_ids[1]])).name,'point_b_local_m':m.site_pos[loop_site_ids[1]].tolist(),
                      'home_anchor_world_m':d.site_xpos[loop_site_ids[0]].tolist(),
                      'free_relative_rotation':True})
    exclusions=[dict(e.attrib) for e in tree.findall('./contact/exclude')]
    model_hash=hashlib.sha256(path.read_bytes()).hexdigest()
    ground_record=json.loads((robot/'evidence/ground_reach_check.json').read_text())
    if ground_record['model_sha256']!=model_hash:
        raise ValueError('Ground stance was solved for a different model')
    def describe_pose(qpos,scope):
        d.qpos[:]=qpos;mujoco.mj_forward(m,d)
        return {'scope':scope,'root_position_m':d.qpos[:3].tolist(),
                'root_orientation_wxyz':d.qpos[3:7].tolist(),
                'active_joint_positions_rad':{name:float(d.qpos[m.joint(name).qposadr[0]]) for name in mapping.names},
                'bodies':[{'name':m.body(i).name,'com_world_m':d.xipos[i].tolist(),
                           'principal_rotation_world':d.ximat[i].reshape(3,3).tolist()}
                          for i in range(1,m.nbody)]}
    ground_q=np.asarray(ground_record['qpos'])
    standing_q=m.key_qpos[0].copy();standing_q[:7]=ground_q[:7]
    for name in metadata(spec)['action_joint_names']:
        address=m.joint(name).qposadr[0];standing_q[address]=ground_q[address]
    standing=describe_pose(standing_q,'feet flat, head upright; dynamics require backend evaluation')
    ground_grasp=describe_pose(ground_q,'feet flat, beak at specified ground object; kinematic only')
    result={'schema':'sai_rigid_transfer_v1','robot_id':spec['robot_id'],'revision':spec['engineering_revision'],
            'units':spec['units'],'frame':spec['frame'],'quaternion_order':'wxyz',
            'model_sha256':model_hash,
            'source_spec_sha256':hashlib.sha256((robot/'configs/robot_spec.json').read_bytes()).hexdigest(),
            'gravity_m_s2':m.opt.gravity.tolist(),'physics_dt_s':float(m.opt.timestep),
            'bodies':bodies,'joints':joints,'geometries':geoms,
            'sites':sites,'cameras':cameras,'constraints':loops,
            'reference_poses':{'standing':standing,'ground_side_grasp':ground_grasp},
            'contact_exclusions':exclusions,'control':metadata(spec),
            'adapter_requirements':['COM/principal-frame transforms must preserve complete inertia tensor',
                                    'joint torques are equal/opposite on parent and child',
                                    'actuated joints must not add driving torque above their declared speed guard',
                                    'closed loops and passive compliance must not be dropped',
                                    'apply mass scaling to every mass/inertia/force/torque only inside adapter',
                                    'report unsupported constraint/geometry types explicitly']}
    out=robot/'models/full/rigid_transfer.json';out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'path':str(out),'bodies':len(bodies),'joints':len(joints),'loops':len(loops),
                      'all_principal_inertias_positive':all(np.min(b['principal_inertia_kg_m2'])>0 for b in bodies)},indent=2))


if __name__=='__main__':main()
