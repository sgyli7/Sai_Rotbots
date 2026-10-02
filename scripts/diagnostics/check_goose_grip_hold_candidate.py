"""Bounded50g jaw-contact hold and2N pull on the current free-root robot.

Object starts between open pads; this is neither floor pickup nor autonomy.
Uses the native head mechanism with explicit passive crank/coupler coordinates.
"""
from pathlib import Path
import hashlib,json,time,xml.etree.ElementTree as ET
import mujoco
import numpy as np
from sai_agent.goose.native_linkage import set_passive_linkage
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'


def main():
    source=R/'models/mechanical_physics/robot.xml';contract_path=R/'configs/mechanical_physics_contract.json';c=json.loads(contract_path.read_text())
    for p,h in c['source_hashes'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    tree=ET.parse(source).getroot()
    for mesh in tree.find('asset').findall('mesh'):mesh.attrib['file']=str((source.parent/mesh.attrib['file']).resolve())
    scene_path=R/'cad/source/mechanical_preview/scene.json';scene=json.loads(scene_path.read_text())
    reference_path=R/'configs/mechanical_grip_reference.json';reference=json.loads(reference_path.read_text())
    upper=next(p for p in scene['parts'] if p['name']==reference['upper_pad_part'])
    pad_path=R/upper['geometry_npz']
    assert hashlib.sha256(pad_path.read_bytes()).hexdigest()==upper['source_sha256']
    with np.load(pad_path,allow_pickle=False) as pad:
        upper_bottom=float(pad['vertices'][:,2].min())+scene['assembly_translation_m'][2]
    grip=np.array(reference['reference_native_world_m'])+scene['assembly_translation_m']
    assert abs(grip[2]-upper_bottom)<1e-10
    world=tree.find('worldbody')
    # Grip site's source coordinate includes the rigid datum lift. Upper pad
    # bottom isZ553mm plus3.7mm; the10mm block starts immediately below it.
    center=[float(grip[0]),float(grip[1]),upper_bottom-.005];size=np.array([.020,.020,.010]);mass=.050
    obj=ET.SubElement(world,'body',name='specified_50g_object',pos=' '.join(map(str,center)));ET.SubElement(obj,'freejoint',name='object_root')
    diag=mass*(np.sum(size**2)-size**2)/12
    ET.SubElement(obj,'inertial',pos='0 0 0',mass=str(mass),diaginertia=' '.join(map(str,diag)))
    ET.SubElement(obj,'geom',name='specified_50g_object',type='box',size=' '.join(map(str,size/2)),contype='2',conaffinity='3',friction='.65 .01 .002',solref='.005 1',density='0')
    xml=ET.tostring(tree,encoding='unicode');out=ROOT/'artifacts/Goose_V0.1/grip_hold_candidate';out.mkdir(parents=True,exist_ok=True);(out/'task.xml').write_text(xml)
    m=mujoco.MjModel.from_xml_string(xml);d=mujoco.MjData(m);names=c['joint_order'];qadr=np.array([m.joint(n).qposadr[0] for n in names]);vadr=np.array([m.joint(n).dofadr[0] for n in names]);aid=np.array([m.actuator(n+'_motor').id for n in names]);lim=np.array([j['continuous_design_limit_nm'] for j in c['joints']]);beak=names.index('beak_hinge')
    d.qpos[qadr]=0;d.qpos[qadr[beak]]=.22;target=np.zeros(18);obj_id=m.body('specified_50g_object').id
    set_passive_linkage(m,d,c)
    mujoco.mj_forward(m,d)
    initial_object_contacts=[]
    for cc in d.contact:
        a,b=[m.geom(int(g)).name for g in cc.geom]
        if 'specified_50g_object' in (a,b):
            initial_object_contacts.append(dict(geom_a=a,geom_b=b,depth_m=max(0.,float(-cc.dist))))
    initial_penetration=max((x['depth_m'] for x in initial_object_contacts),default=0.)
    if initial_penetration>.0002:
        raise ValueError(('object initially penetrates the candidate jaw',initial_penetration))
    part={g['name']:g['part'] for g in c['collision_geometries']};start=time.monotonic();records=[];warnings=[];reason='FULL_DURATION';peak=np.zeros(18)
    for k in range(int(np.ceil(.75/m.opt.timestep))):
        mujoco.mj_forward(m,d)
        tau=80*(target-d.qpos[qadr])-4*d.qvel[vadr]+d.qfrc_bias[vadr]
        # Slow closing velocity avoids accelerating into the object while a
        # position controller remains saturated. This remains a draft
        # feedback controller, not firmware/hardware validation.
        tau[beak]=np.clip(2*(-.25-d.qvel[vadr[beak]]),-.4,.4)+d.qfrc_bias[vadr[beak]]
        tau=np.clip(tau,-lim,lim);peak=np.maximum(peak,abs(tau));d.ctrl[aid]=tau
        pull=2.0 if d.time>=.4 else 0.;d.xfrc_applied[obj_id,0]=pull
        mujoco.mj_step(m,d)
        if any(int(w.number) for w in d.warning) or not np.isfinite(d.qpos).all():reason='SOLVER_WARNING';break
        if k%100==0:
            contacts=[]
            for i,cc in enumerate(d.contact):
                a,b=[m.geom(int(g)).name for g in cc.geom]
                if 'specified_50g_object' not in [a,b]:continue
                other=b if a=='specified_50g_object' else a;force=np.zeros(6);mujoco.mj_contactForce(m,d,i,force)
                contacts.append(dict(part=part.get(other,other),normal_n=float(force[0])))
            grip_body=m.body('head_roll').id;root=m.body('torso').id
            tilt=float(np.arccos(np.clip(d.xmat[root].reshape(3,3)[2,2],-1,1)))
            hp=np.array(next(j for j in c['joints'] if j['name']=='head_roll')['pivot_world_at_zero_m'])
            local=d.xmat[grip_body].reshape(3,3).T@(d.xpos[obj_id]-d.xpos[grip_body])+hp
            records.append(dict(time_s=float(d.time),object_position_m=d.xpos[obj_id].tolist(),object_in_head_neutral_coordinates_m=local.tolist(),root_tilt_rad=tilt,jaw_q_rad=float(d.qpos[qadr[beak]]),pull_x_n=pull,contacts=contacts))
            if d.xpos[obj_id,2]<.40:reason='OBJECT_DROP';break
        if time.monotonic()-start>55:reason='WALL_TIME_BOUND';break
    warning_counts=[int(w.number) for w in d.warning];final=d.xpos[obj_id].copy()
    full=bool(reason=='FULL_DURATION' and d.time>=.749)
    end_contacts=records[-1]['contacts'] if records else [];pad_parts={x['part'] for x in end_contacts if x['normal_n']>.05}
    # A free robot can lean under the pull. Judge slip in its head frame,
    # together with both actual pad contacts; a fixed worldX assertion was
    # inappropriate for this experiment and rejected the first run.
    local=np.array(records[-1]['object_in_head_neutral_coordinates_m']) if records else np.full(3,np.inf)
    required_pads={reference['upper_pad_part'],reference['lower_pad_part']}
    passed=bool(full and not any(warning_counts) and final[2]>.5 and np.linalg.norm(local-np.array(center))<.02 and required_pads<=pad_parts and records[-1]['root_tilt_rad']<np.deg2rad(10))
    report=dict(schema='goose_50g_hold_pull_candidate_v1',status=reason,simulation_hold_pull_pass=passed,simulated_seconds=float(d.time),wall_seconds=time.monotonic()-start,
        object_mass_kg=.05,pull_x_n=2.,pull_start_s=.4,jaw_closing_feedback_cap_nm=.4,jaw_closing_velocity_target_rad_s=-.25,friction_assumption=.65,
        actual_pad_part_names=sorted(required_pads),grip_reference_world_m=grip.tolist(),
        initial_object_contacts=initial_object_contacts,initial_maximum_object_penetration_m=initial_penetration,
        peak_motor_torque_nm=dict(zip(names,peak.tolist())),final_object_position_m=final.tolist(),final_object_in_head_neutral_coordinates_m=local.tolist(),object_initial_center_m=center,
        slip_assertion_frame='head-owned neutral coordinates,not fixed worldX',records=records,solver_warning_counts=warning_counts,
        root_clamped=False,object_clamped=False,object_starts_in_open_beak=True,floor_pickup_pass=False,autonomy_pass=False,
        new_native_head_kit_validated=False,whole_manipulation_release=False,manufacturing_pass=False,
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,contract_path,scene_path,reference_path,pad_path,Path(__file__)]},
        task_xml_sha256=hashlib.sha256(xml.encode()).hexdigest(),
        limitations=['Object starts between open pads;no visual approach,pickup,release,walking or carried-object trajectory is demonstrated.',
            'Native240deg crank/coupler are explicit passive moving bodies; ideal joint constraints do not certify backlash, efficiency, pin wear or actual hardware.',
            'Friction,soft-tread stiffness,output torque calibration and stationary thermal capacity are assumptions,not measured hardware.',
            '2N object pull while standing is a grip rejection test,not dragging a floor-contact day item or moving cart.'])
    (R/'evidence/mechanical_50g_hold_pull.json').write_text(json.dumps(report,indent=2)+'\n')
    print('HOLD PULL',reason,'pass',passed,'seconds',d.time,'final',final,flush=True)
    return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
