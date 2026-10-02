"""Build Goose's SI MJCF and engine-neutral rigid-body transfer description.

The motor internal inertia is an explicit envelope approximation. Printable
visuals and actual CAD mass properties can be substituted by the CAD manifest.
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

from sai_agent.goose.spec import load_spec, motor_envelope, quaternion_wxyz
from sai_agent.paths import resource_root


def values(v):
    return ' '.join(f'{float(x):.12g}' for x in v)


def build(root: Path | None = None) -> dict:
    root = root or resource_root()
    robot = root / 'robots/Goose_V0.1'
    out = robot / 'models/full'
    out.mkdir(parents=True, exist_ok=True)
    spec = load_spec(robot / 'configs/robot_spec.json')
    xml = ET.Element('mujoco', model='goose_v01_'+spec['engineering_revision'])
    ET.SubElement(xml, 'compiler', angle='radian', autolimits='true')
    ET.SubElement(xml, 'option', timestep='.001', gravity='0 0 -9.81',
                  iterations='100', tolerance='1e-10', integrator='implicitfast')
    default = ET.SubElement(xml, 'default')
    # Geartrain backdrive damping is an explicit design estimate; it also
    # dissipates the otherwise unphysical high-speed mode of light leg links.
    ET.SubElement(default, 'joint', damping='.03', armature='0', frictionloss='.001')
    ET.SubElement(default, 'geom', friction='.8 .005 .0001', condim='4',
                  solref='.006 1', solimp='.95 .99 .001')
    world = ET.SubElement(xml, 'worldbody')
    ET.SubElement(world, 'light', pos='0 -1 2', dir='0 0 -1')
    ET.SubElement(world, 'geom', name='floor', type='plane', size='3 3 .1',
                  rgba='.64 .69 .59 1', friction='.8 .005 .0001')
    torso = ET.SubElement(world, 'body', name='torso', pos=values(spec['root_home_position_m']))
    ET.SubElement(torso, 'freejoint', name='root')
    bodies = {'torso': torso}
    ledger = []
    white, orange, black = '.94 .94 .91 1', '.94 .43 .06 1', '.075 .08 .085 1'

    def geom(body, name, mass, **attrs):
        ET.SubElement(body, 'geom', name=name, mass=str(mass), **{k:values(v) if isinstance(v,(list,tuple,np.ndarray)) else str(v) for k,v in attrs.items()})
        ledger.append({'name':name,'body':body.get('name'),'mass_kg':mass,
                       'basis':'vendor_mass_envelope' if name.endswith('_motor') else 'initial_design_mass_estimate_pending_CAD'})

    geom(torso,'body_shell',.180,type='ellipsoid',size=np.array(spec['body_dimensions_m'])/2,rgba=white,contype='0',conaffinity='0')
    geom(torso,'torso_frame',.085,type='box',size=[.080,.046,.003],pos=[0,0,-.020],rgba=black,contype='0',conaffinity='0')
    layout_path=robot/'hardware/component_envelopes.json'
    layout=json.loads(layout_path.read_text())
    if layout['coordinate_frame']!='torso_x_forward_y_left_z_up' or layout['units']!='SI':
        raise ValueError('Component layout frame/unit mismatch')
    for item in layout['components']:
        geom(torso,item['name'],item['mass_reserve_kg'],type='box',
             size=np.asarray(item['reserved_xyz_m'])/2,pos=item['center_m'],
             rgba=black,contype='0',conaffinity='0')
    for j in spec['joints']:
        parent=bodies[j['parent']]
        center,size,rotation=motor_envelope(j,spec)
        servo=spec['servos'][j['servo']]
        geom(parent,j['name']+'_motor',servo['mass_kg'],type='box',pos=center,size=size/2,
             quat=quaternion_wxyz(rotation),rgba=black)
        body=ET.SubElement(parent,'body',name=j['name'],pos=values(j['position_m']))
        bodies[j['name']]=body
        ET.SubElement(body,'joint',name=j['name'],axis=values(j['axis']),range=values(j['range_rad']))
        if j['name']!='beak_drive':
            geom(body,j['name']+'_horn_frame',.014 if j['servo']!='xc330' else .007,
                 type='sphere',size='.012',rgba=white,contype='0',conaffinity='0')
        if j['name'].endswith('hip_pitch') or j['name'].endswith('knee_pitch'):
            geom(body,j['name']+'_link',.011,type='capsule',fromto=[0,0,-.017,0,0,-.060],size='.008',rgba=white)
        if j['name'].endswith('ankle_pitch'):
            geom(body,j['name']+'_foot',.065,type='box',size=[.060,.035,.015],pos=[.015,0,-.019],rgba=orange)
            ET.SubElement(body,'site',name=j['name'].replace('ankle_pitch','foot'),pos='.015 0 -.034',size='.004')
        if j['name'] in ('neck_pitch','neck_mid_pitch'):
            length=spec['neck_link_lengths_m'][0 if j['name']=='neck_pitch' else 1]
            geom(body,j['name']+'_beam',.026,type='box',size=[.005,.010,(length-.034)/2],pos=[0,0,length/2],rgba=white)
    head=bodies['head_roll']
    geom(head,'head_shell',.025,type='ellipsoid',size=[.041,.031,.038],pos=[.006,0,.020],rgba=white,contype='0',conaffinity='0')
    from scipy.spatial.transform import Rotation
    camera=spec['camera'];camera_r=Rotation.from_euler('y',camera['board_pitch_down_rad']).as_matrix()
    camera_p=np.asarray(camera['board_center_head_m'])
    geom(head,'camera_board',.0085,type='box',size=[.001,.009,.020],pos=camera_p,quat=quaternion_wxyz(camera_r),rgba=black,contype='0',conaffinity='0')
    lens_r=camera_r@Rotation.from_euler('y',np.pi/2).as_matrix()
    geom(head,'camera_lens',.0035,type='cylinder',size=[.009,camera['lens_depth_m']/2],pos=camera_p+camera_r@np.array([camera['lens_depth_m']/2,0,0]),quat=quaternion_wxyz(lens_r),rgba=black,contype='0',conaffinity='0')
    cvq=np.array(camera['orientation_head_from_cv_wxyz']);cv_r=Rotation.from_quat([*cvq[1:],cvq[0]]).as_matrix()
    mj_r=cv_r@np.diag([1,-1,-1])
    ET.SubElement(head,'camera',name='head_camera',pos=values(camera['position_head_m']),xyaxes=values(np.r_[mj_r[:,0],mj_r[:,1]]),fovy=str(camera['vertical_fov_deg']))
    ET.SubElement(head,'site',name='head_imu',pos='0 0 .02',size='.003')
    a=np.array(spec['joints'][-1]['position_m']);L=spec['beak']['crank_length_m'];H=spec['beak']['anchor_spacing_m']
    closed=spec['beak']['closed_rad'];pad_z=spec['beak']['pad_mount_z_relative_jaw_m'];top=L*math.sin(closed)+pad_z+.001
    for i,(x,width) in enumerate(zip((.029,.041,.053,.065),(.032,.027,.019,.013))):
        geom(head,f'upper_beak_shell_{i}',.002,type='box',size=[.006,width/2,.005],pos=a+[x,0,top+.007],rgba=orange)
    geom(head,'upper_pad',.0015,type='box',size=[.015,.011,.001],pos=a+[.051,0,top+.001],rgba=black)
    ET.SubElement(head,'site',name='task_center',pos=values(a+[.051,0,top-.012]),size='.003')
    lower=bodies['beak_drive']
    geom(lower,'lower_crank_pair',.004,type='capsule',fromto=[0,0,0,L,0,0],size='.0015',rgba=orange)
    jaw=ET.SubElement(lower,'body',name='lower_jaw',pos=values([L,0,0]))
    ET.SubElement(jaw,'joint',name='passive_jaw_pin',axis='0 -1 0',damping='.000001')
    for i,(x,width) in enumerate(zip((.012,.024,.036,.047),(.028,.024,.018,.012))):
        geom(jaw,f'lower_jaw_frame_{i}',.002,type='box',size=[.006,width/2,.002],pos=[x,0,pad_z-.008],rgba=orange)
    ET.SubElement(jaw,'site',name='jaw_loop',pos=values([0,0,H]),size='.001')
    follower=ET.SubElement(head,'body',name='upper_crank',pos=values(a+[0,0,H]))
    ET.SubElement(follower,'joint',name='passive_follower',axis='0 -1 0',damping='.000001')
    geom(follower,'upper_crank_pair',.004,type='capsule',fromto=[0,0,0,L,0,0],size='.0015',rgba=orange)
    ET.SubElement(follower,'site',name='follower_loop',pos=values([L,0,0]),size='.001')
    slide=ET.SubElement(jaw,'body',name='lower_pad_slide',pos=values([.025,0,pad_z]))
    ET.SubElement(slide,'joint',name='passive_pad_compression',type='slide',axis='0 0 -1',range='0 .0015',stiffness='2500',damping='1')
    geom(slide,'pad_retainer',.0015,type='box',size=[.005,.005,.0005],rgba=black,contype='0',conaffinity='0')
    tilt=ET.SubElement(slide,'body',name='lower_pad')
    ET.SubElement(tilt,'joint',name='passive_pad_pitch',axis='0 1 0',range=values([-math.radians(4),math.radians(4)]),stiffness='.015',damping='.001')
    geom(tilt,'lower_pad_contact',.002,type='box',size=[.0175,.011,.001],pos=[.0075,0,0],rgba=black)
    ET.SubElement(tilt,'site',name='grasp_center',pos='.0075 0 .001',size='.003')
    eq=ET.SubElement(xml,'equality')
    ET.SubElement(eq,'connect',name='beak_loop',site1='jaw_loop',site2='follower_loop',solref='.002 1',solimp='.999 .999 .001')
    contact=ET.SubElement(xml,'contact')
    for child,parent in [('upper_crank','head_roll'),('lower_jaw','head_roll'),('lower_pad','lower_jaw'),('upper_crank','lower_jaw'),('lower_pad','head_roll'),('beak_drive','upper_crank')]:
        ET.SubElement(contact,'exclude',body1=child,body2=parent)
    actuator=ET.SubElement(xml,'actuator')
    for j in spec['joints']:
        torque=spec['servos'][j['servo']]['torque_screening_Nm']
        ET.SubElement(actuator,'motor',name=j['name']+'_actuator',joint=j['name'],ctrlrange=values([-torque,torque]))
    ET.SubElement(torso,'site',name='torso_imu',pos='0 0 .035',size='.003')
    sensors=ET.SubElement(xml,'sensor')
    ET.SubElement(sensors,'gyro',name='imu_gyro',site='torso_imu')
    key=ET.SubElement(xml,'keyframe')
    q=[*spec['root_home_position_m'],1,0,0,0]
    # Tree order differs from actuator order: insert mouth follower/passive joints
    # after the main active chain by reading compiled joint names below.
    path=out/'robot.xml';ET.indent(xml);ET.ElementTree(xml).write(path,encoding='unicode')
    model=mujoco.MjModel.from_xml_path(str(path));data=mujoco.MjData(model)
    data.qpos[:7]=q
    homes={j['name']:j['home_rad'] for j in spec['joints']}
    homes.update(passive_jaw_pin=-closed,passive_follower=closed)
    for name,value in homes.items():data.qpos[model.joint(name).qposadr[0]]=value
    mujoco.mj_forward(model,data)
    soles=[data.site(name).xpos[2] for name in ('left_foot','right_foot')]
    data.qpos[2]-=min(soles)
    ET.SubElement(key,'key',name='home',qpos=values(data.qpos))
    cad_path=robot/'cad/exports/cad_manifest.json'
    if cad_path.exists():
        cad=json.loads(cad_path.read_text())
        if cad['spec_sha256']!=hashlib.sha256((robot/'configs/robot_spec.json').read_bytes()).hexdigest():
            raise ValueError('CAD/spec revision mismatch; finish CAD generation before model build')
        for part in cad['parts']:
            for entry in part['files'].values():
                if hashlib.sha256((robot/entry['path']).read_bytes()).hexdigest()!=entry['sha256']:
                    raise ValueError('CAD export changed without a matching manifest: '+part['name'])
        if cad['spec_sha256']!=hashlib.sha256((robot/'configs/robot_spec.json').read_bytes()).hexdigest():
            raise ValueError('Stale CAD manifest: regenerate for this specification')
        from scipy.spatial.transform import Rotation
        components={name:[] for name in bodies}
        components.update(lower_jaw=[],upper_crank=[],lower_pad_slide=[],lower_pad=[])
        geometry_model=mujoco.MjModel.from_xml_path(str(path))
        # Vendor masses and reserved electronics are retained. Printed mass
        # estimates are replaced by CAD volumes and specified bulk densities.
        retain={item['name'] for item in layout['components']}|{'camera_board','camera_lens','pad_retainer'}
        for entry in ledger:
            name=entry['name']
            if not (name.endswith('_motor') or name in retain):continue
            g=geometry_model.geom(name);typ=int(geometry_model.geom_type[g.id]);size=g.size
            mass=entry['mass_kg']
            if typ==6:inertia=mass/3*np.diag([size[1]**2+size[2]**2,size[0]**2+size[2]**2,size[0]**2+size[1]**2])
            elif typ==5:inertia=np.diag([mass*(3*size[0]**2+4*size[1]**2)/12]*2+[mass*size[0]**2/2])
            else:raise ValueError(f'Unexpected retained geometry {name}')
            rot=Rotation.from_quat([*g.quat[1:],g.quat[0]]).as_matrix()
            components[entry['body']].append((mass,np.asarray(g.pos),rot@inertia@rot.T))
        # Small fastener allowance at body origins is an explicit estimate.
        for name in components:components[name].append((.0015,np.zeros(3),np.eye(3)*1e-8))
        asset=ET.SubElement(xml,'asset');meshdir=out/'visuals';meshdir.mkdir(exist_ok=True)
        for part in cad['parts']:
            bodyname=part['body'];components[bodyname].append((part['mass_kg'],np.array(part['center_of_mass_body_m']),np.array(part['inertia_about_com_body_kg_m2'])))
            src=robot/part['files']['stl']['path'];dst=meshdir/src.name;shutil.copyfile(src,dst)
            ET.SubElement(asset,'mesh',name=part['name']+'_mesh',file='visuals/'+dst.name,scale='.001 .001 .001')
        all_bodies={b.get('name'):b for b in xml.findall('.//body')}
        for bodyname,body in all_bodies.items():
            for g in list(body.findall('geom')):
                name=g.get('name','')
                if name.endswith('_motor') or name in retain:g.set('mass','0')
                elif name.endswith('_foot') or 'pad_' in name or name.startswith(('upper_pad','lower_pad')):
                    g.set('mass','0');g.set('rgba','0 0 0 0')
                elif name=='body_shell':g.set('mass','0');g.set('rgba','0 0 0 0')
                else:body.remove(g)
            items=components[bodyname];mass=sum(x[0] for x in items)
            center=sum(m*p for m,p,_ in items)/mass
            inertia=sum(i+m*((p-center)@(p-center)*np.eye(3)-np.outer(p-center,p-center)) for m,p,i in items)
            ET.SubElement(body,'inertial',mass=str(mass),pos=values(center),
                          fullinertia=values([inertia[0,0],inertia[1,1],inertia[2,2],inertia[0,1],inertia[0,2],inertia[1,2]]))
        for part in cad['parts']:
            rgba=white if part['color']=='white' else orange if part['color']=='orange' else black
            ET.SubElement(all_bodies[part['body']],'geom',name=part['name']+'_cad',type='mesh',mesh=part['name']+'_mesh',
                          mass='0',contype='0',conaffinity='0',rgba=rgba)
        # Exterior torso shell is concave, with real service and leg ports.
        # It must not become one solid ellipsoid/convex hull around the motors.
        from sai_agent.goose.collision import surface_hulls
        collision_dir=out/'contacts';collision_dir.mkdir(exist_ok=True)
        for part in cad['parts']:
            if part['name'] not in ('body_shell_front','body_shell_rear','left_service_door','right_service_door'):continue
            for index,hull in enumerate(surface_hulls(robot/part['files']['stl']['path'])):
                name=f"collision_{part['name']}_{index}"
                file=collision_dir/(name+'.obj');hull.export(file)
                ET.SubElement(asset,'mesh',name=name,file='contacts/'+file.name)
                ET.SubElement(all_bodies[part['body']],'geom',name=name,type='mesh',mesh=name,
                              mass='0',rgba='0 0 0 0')
        ledger=[e for e in ledger if e['name'].endswith('_motor') or e['name'] in retain]
        ledger += [{'name':p['name'],'body':p['body'],'mass_kg':p['mass_kg'],'basis':'CAD solid volume x material bulk density'} for p in cad['parts']]
        ledger += [{'name':'fastener_allowance_'+name,'body':name,'mass_kg':.0015,'basis':'provisional fastener allowance, not weighed'} for name in components]
    ET.indent(xml);ET.ElementTree(xml).write(path,encoding='unicode')
    model=mujoco.MjModel.from_xml_path(str(path));data=mujoco.MjData(model);mujoco.mj_resetDataKeyframe(model,data,0);mujoco.mj_forward(model,data)
    manifest={'robot_id':spec['robot_id'],'revision':spec['engineering_revision'],'physical_units':'SI',
              'active_joint_names':[j['name'] for j in spec['joints']], 'nu':model.nu,'nq':model.nq,'nv':model.nv,
              'mass_kg':float(model.body_mass.sum()),'home_root_position_m':data.qpos[:3].tolist(),
              'home_center_of_mass_m':data.subtree_com[model.body('torso').id].tolist(),
              'loop_equality_count':model.neq,'motor_mass_kg':sum(spec['servos'][j['servo']]['mass_kg'] for j in spec['joints']),
              'source_spec_sha256':hashlib.sha256((robot/'configs/robot_spec.json').read_bytes()).hexdigest(),
              'model_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
              'mass_properties_status':'vendor motor mass/envelope inertia; CAD solid volume and bulk density for printed parts; reserved electronics/fasteners estimated' if cad_path.exists() else 'motor mass vendor; internal inertia envelope approximation; printed mass estimates pending CAD',
              'cad_manifest_sha256':hashlib.sha256(cad_path.read_bytes()).hexdigest() if cad_path.exists() else None,
              'component_layout_sha256':hashlib.sha256(layout_path.read_bytes()).hexdigest(),
              'collision_scope':'vendor motor envelopes, feet, CAD-matched grip pads, torso exterior surface convex clusters (20mm cells); exact BREP sweep remains assembly authority',
              'full_engineering_acceptance':False}
    (out/'robot_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (out/'mass_ledger.json').write_text(json.dumps(ledger,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))
    return manifest


if __name__=='__main__':build()
