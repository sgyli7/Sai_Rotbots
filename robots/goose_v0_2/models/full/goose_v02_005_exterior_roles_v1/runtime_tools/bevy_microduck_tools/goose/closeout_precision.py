"""Same-clock observations and Owner-declared backend comparison, no integration."""
import json
from pathlib import Path
import mujoco
import numpy as np
from .artifacts import sha256
from .closeout_native50 import MOTOR_ORDER

ACCEPTANCE_SHA='c6a9b21f02b55b10298c922b7472a096130e97caf3f9ec4af3bf82cc3ac330f8'


def load_acceptance(path,digest,model_path):
    path=Path(path)
    if digest!=ACCEPTANCE_SHA or sha256(path)!=digest:
        raise ValueError('Unselected numerical acceptance identity')
    value=json.loads(path.read_text())
    if value['model']['sha256']!=sha256(Path(model_path)):
        raise ValueError('Numerical acceptance belongs to another plant')
    return {'path':str(path),'sha256':digest,'document':value}


def cpu_post_contacts(model,probe,qpos):
    probe.qpos[:]=qpos
    mujoco.mj_kinematics(model,probe);mujoco.mj_comPos(model,probe);mujoco.mj_collision(model,probe)
    ground=model.geom('ground').id;rows=[];depth=0.
    for i in range(probe.ncon):
        hit=probe.contact[i];a,b=int(hit.geom1),int(hit.geom2)
        if ground not in (a,b):continue
        depth=max(depth,-float(hit.dist))
        rows.append({'world':0,'geom_ids':[a,b],'geoms':[model.geom(a).name,model.geom(b).name],
                     'distance_m':float(hit.dist),'world_point_m':hit.pos.tolist()})
    return {'clock':'actual post-integration qpos; independent kinematics+collision, zero force solve/integrations',
            'ground_depth_m':[depth],'ground_contacts':rows}


def gpu_post_contacts(env):
    m=env.sim.mj_model;wp_data=env.sim.wp_data;contacts=wp_data.contact
    watched=('qpos','qvel','qacc_warmstart','time','ctrl')
    before={name:getattr(wp_data,name).numpy().copy()for name in watched}
    n=int(wp_data.nacon.numpy()[0]);ground=m.geom('ground').id
    geoms=contacts.geom.numpy()[:n];dist=contacts.dist.numpy()[:n]
    pos=contacts.pos.numpy()[:n];world=contacts.worldid.numpy()[:n]
    depths=np.zeros(env.num_envs);rows=[]
    for i in range(n):
        a,b=map(int,geoms[i]);w=int(world[i])
        if not 0<=w<env.num_envs:raise ValueError('Invalid actual contact world id')
        is_ground=ground in (a,b)
        if is_ground:depths[w]=max(depths[w],-float(dist[i]))
        rows.append({'world':w,'geom_ids':[a,b],'geoms':[m.geom(a).name,m.geom(b).name],
                     'ground_pair':is_ground,'distance_m':float(dist[i]),'world_point_m':pos[i].tolist()})
    if not all(np.array_equal(value,getattr(wp_data,name).numpy())for name,value in before.items()):
        raise RuntimeError('Read-only contact diagnostics changed physical solver state')
    return {'no_additional_forward':True,'watched_solver_fields_unchanged':list(watched),
            'clock':'actual GPU post-forward contact buffer at current integrated qpos',
            'ground_depth_m':depths.tolist(),'all_active_contacts':rows,'actual_nacon':n}


def compare_pass(model,cpu,gpu,bounds):
    cq=np.array([x['qpos']for x in cpu])[:,None,:];gq=np.array([x['qpos']for x in gpu])
    cv=np.array([x['qvel']for x in cpu])[:,None,:];gv=np.array([x['qvel']for x in gpu])
    qi=[int(model.joint(n).qposadr[0])for n in MOTOR_ORDER]
    vi=[int(model.joint(n).dofadr[0])for n in MOTOR_ORDER]
    passive=('beak_hinge','beak_coupler_link')
    pqi=[int(model.joint(n).qposadr[0])for n in passive];pvi=[int(model.joint(n).dofadr[0])for n in passive]
    ca=cq[:,:,3:7]/np.linalg.norm(cq[:,:,3:7],axis=-1,keepdims=True)
    ga=gq[:,:,3:7]/np.linalg.norm(gq[:,:,3:7],axis=-1,keepdims=True)
    angles=2*np.arccos(np.clip(np.abs(np.sum(ca*ga,axis=-1)),0,1))
    cf=np.array([x['motor_force_nm']for x in cpu])[:,None,:];gf=np.array([x['motor_force_nm']for x in gpu])
    cd=np.array([x['post_state_contacts']['ground_depth_m']for x in cpu])
    gd=np.array([x['post_state_contacts']['ground_depth_m']for x in gpu])
    values={'actuated_joint_position_rad':float(np.abs(gq[:,:,qi]-cq[:,:,qi]).max()),
            'actuated_joint_velocity_rad_s':float(np.abs(gv[:,:,vi]-cv[:,:,vi]).max()),
            'root_position_euclidean_m':float(np.linalg.norm(gq[:,:,:3]-cq[:,:,:3],axis=-1).max()),
            'root_orientation_geodesic_rad':float(angles.max()),
            'actual_motor_force_Nm':float(np.abs(gf-cf).max()),
            'ground_contact_depth_same_tick_m':float(np.abs(gd-cd).max())}
    return {'metrics':values,'bounds':{k:bounds[k]for k in values},
            'checks':{k:values[k]<=bounds[k]for k in values},
            'passed':all(np.isfinite(values[k])and values[k]<=bounds[k]for k in values),
            'actual_CPU_ground_depth_max_m':float(cd.max()),'actual_GPU_ground_depth_max_m':float(gd.max()),
            'active_order':list(MOTOR_ORDER),'actual_active_qpos_addresses':qi,'actual_active_dof_addresses':vi,
            'passive_position_max_abs_rad_by_coordinate':np.abs(gq[:,:,pqi]-cq[:,:,pqi]).max(axis=(0,1)).tolist(),
            'passive_velocity_max_abs_rad_s_by_coordinate':np.abs(gv[:,:,pvi]-cv[:,:,pvi]).max(axis=(0,1)).tolist(),
            'passive_order':list(passive)}


def evaluate_comparison(model,cpu,passes,acceptance):
    bounds=acceptance['document']['bounds']
    compared={('captured'if mode else'uncaptured'):compare_pass(model,cpu,rows,bounds)for mode,rows in passes.items()}
    graph={}
    for field,key in (('qpos','captured_uncaptured_qpos_component_max_abs'),('qvel','captured_uncaptured_qvel_component_max_abs')):
        direct=np.array([x[field]for x in passes[False]]);captured=np.array([x[field]for x in passes[True]])
        graph[key]=float(np.abs(captured-direct).max())
    graph_pass=all(graph[k]<=bounds[k]for k in graph)
    both=all(value['passed']for value in compared.values())
    selected=('captured'if graph_pass else'uncaptured')if both else None
    return {'acceptance_sha256':acceptance['sha256'],'by_execution_mode':compared,
            'graph_metrics':graph,'graph_bounds':{k:bounds[k]for k in graph},'graph_comparison_passed':graph_pass,
            'precision_passed':both,'selected_execution_mode':selected,
            'graph_qualified':both and graph_pass,'uncaptured_qualified':compared['uncaptured']['passed']}
