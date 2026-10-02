"""Independent equal-crank sweep, packaging and conditional load-path sizing."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/models'))
from build_goose_stage_two import candidate,transmission_parts,MOTOR,JAW,RADIUS,PHASE,LINK_Y,R,mesh


def main():
    s=candidate();c=json.loads((R/'configs/stage_two_contract.json').read_text());shell=mesh(s.parts['goose_head_shell']);parts0={p['name']:p for p in transmission_parts()}
    length=np.linalg.norm((JAW-MOTOR)[[0,2]]);direction_angle=np.arctan2(JAW[2]-MOTOR[2],JAW[0]-MOTOR[0]);cases=[];gaps={};quad=[];volume_hits=[]
    nominal={i['name']:i for i in c['items']};head_mass=next(b['mass_kg'] for b in c['bodies'] if b['name']=='head_roll');max_com_error=0.;extra_armature=0.
    for p in c['items']:
        if p['name'] in ('beak_coupler','beak_input_pin'):
            extra_armature+=p['mass_kg']*RADIUS**2
    for p in transmission_parts():
        mm=mesh(p);quad.append(dict(part=p['name'],all_quads=all(len(f)==4 for f in p['faces']),watertight=bool(mm.is_watertight),winding_consistent=bool(mm.is_winding_consistent),positive_volume=bool(mm.volume>0)))
    for q in np.linspace(0,.55,61):
        theta=PHASE-q;v=RADIUS*np.array([np.cos(theta),0,np.sin(theta)]);pa=MOTOR+v;pb=JAW+v;pa[1]=pb[1]=LINK_Y
        sine=abs(np.sin(theta-direction_angle));output_torque=c['joints'][5]['torque_peak_limit_nm'];force=output_torque/(RADIUS*sine)*1.10
        cases.append(dict(jaw_angle_rad=float(q),closure_error_m=float(abs(np.linalg.norm(pb-pa)-length)),transmission_angle_sine=float(sine),coupler_force_n_with_10pct_allowance=float(force)))
        delta_moment=np.zeros(3)
        for p in transmission_parts(q):
            mm=mesh(p)
            if p['name'] in ('beak_coupler','beak_input_pin'):
                delta_moment+=nominal[p['name']]['mass_kg']*(mm.center_mass-mesh(parts0[p['name']]).center_mass)
            distance=trimesh.proximity.signed_distance(shell,mm.vertices)
            gaps[p['name']]=min(gaps.get(p['name'],1.),float(distance.min()))
        # Worst case all10g fasteners move through the maximum crank displacement.
        max_com_error=max(max_com_error,(np.linalg.norm(delta_moment)+.010*2*RADIUS*np.sin(q/2))/head_mass)
    peak=max(row['coupler_force_n_with_10pct_allowance'] for row in cases)
    bearing_front=peak*(.029+.0265)/.050+50*(.0265/.050)
    bending=peak*.0055;shaft_d=.008
    shaft_vm=np.sqrt((32*bending/(np.pi*shaft_d**3))**2+3*(16*c['joints'][5]['torque_peak_limit_nm']/(np.pi*shaft_d**3))**2)*1.5
    plate_stress=6*c['joints'][5]['torque_peak_limit_nm']/(.004*.014**2)*2
    bush_pressure=peak/(.005*.0045);bush_pv=bush_pressure/1e6*(.005/2*1.)
    # Check candidate motor independently of same-body and adjacent exclusions.
    motor=mesh(s.parts['beak_rated_motor_case']);obstacles=[]
    camera=trimesh.creation.box([.013,.030,.030]);camera.apply_translation([.166,0,.606]);obstacles.append(('camera_module',camera))
    obstacles.append(('head_roll_case',mesh(s.parts['head_roll_case'])))
    for n in ('jaw_bearing_reserve_right','jaw_bearing_reserve_left'):obstacles.append((n,mesh(s.parts[n])))
    for name,obstacle in obstacles:
        inter=trimesh.boolean.intersection([motor,obstacle],engine='manifold');vol=0. if inter.is_empty else abs(float(inter.volume))
        if vol>1e-10:volume_hits.append(dict(part=name,intersection_mm3=vol*1e9))
    # Repeat all actuator cases across the static poses after the neck upgrade.
    motor_parts=[]
    for n,key in s.selected.items():
        cat=s.catalog[key];mm=trimesh.creation.cylinder(cat['diameter']/2,cat['length'],sections=64);T=trimesh.geometry.align_vectors([0,0,1],s.axes[n]);T[:3,3]=s.pivots[n];mm.apply_transform(T);motor_parts.append((n,s.parents[n],mm))
    motor_parts.extend([('head_roll','head_pitch',mesh(s.parts['head_roll_case'])),('beak_drive','head_roll',motor)])
    g=json.loads((R/'evidence/stage_two_system_gate.json').read_text());motor_cases=[];s.pivots['torso']=np.zeros(3)
    for pose in g['pose_geometry']:
        rr=Rotation.from_quat(np.array(pose['root_qpos'][3:])[[1,2,3,0]]).as_matrix();root=np.array(pose['root_qpos'][:3])-rr@np.array([0,0,.29]);poses,_=s.fk(pose['joint_q_rad'],root,rr);world=[];hits=[]
        for n,b,mm in motor_parts:
            mm=mm.copy();position,rot=poses[b];mm.vertices=position+(mm.vertices-s.pivots[b])@rot.T;world.append((n,mm))
        for k,(a,ma) in enumerate(world):
            for b,mb in world[k+1:]:
                if np.any(np.minimum(ma.bounds[1],mb.bounds[1])-np.maximum(ma.bounds[0],mb.bounds[0])<=0):continue
                inter=trimesh.boolean.intersection([ma,mb],engine='manifold');vol=0 if inter.is_empty else abs(float(inter.volume))
                if vol>1e-10:hits.append(dict(a=a,b=b,intersection_mm3=vol*1e9))
        motor_cases.append(dict(pose=pose['name'],count=len(motor_parts),intersections=hits,passed=not hits))
    capacity=.8*8*.85
    checks=dict(closure=max(x['closure_error_m'] for x in cases)<1e-10,away_from_toggle=min(x['transmission_angle_sine'] for x in cases)>.7,motor_conditional_output_capacity=capacity>=c['joints'][5]['torque_peak_limit_nm'],force_50n_with_gravity_reserve=c['joints'][5]['continuous_design_limit_nm']>=4.05,bearing_static_factor_ge_1_5=910/bearing_front>=1.5,shaft_conditional_stress=shaft_vm<160e6,crank_conditional_stress=plate_stress<80e6,bush_20c_pressure_and_pv=bush_pressure<80e6 and bush_pv<.42,source_quads=all(all(row[k] for k in ('all_quads','watertight','winding_consistent','positive_volume')) for row in quad),sampled_outer_shell_clearance=min(gaps.values())>=.0025,no_motor_camera_or_bearing_intersection=not volume_hits,all_motor_case_poses=all(p['passed'] for p in motor_cases),moving_mass_com_error_below_1mm=max_com_error<.001)
    checks={key:bool(value) for key,value in checks.items()}
    report=dict(status='CONDITIONAL_LINKAGE_AND_ENVELOPE_SCREEN_NOT_MANUFACTURING_RELEASE',model_sha256=c['model_sha256'],contract_sha256=hashlib.sha256((R/'configs/stage_two_contract.json').read_bytes()).hexdigest(),source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'scripts/models/build_goose_stage_two.py']},checks=checks,all_checks_passed=all(checks.values()),crank_radius_m=RADIUS,coupler_pin_spacing_m=float(length),sweep=cases,minimum_source_outer_shell_distances_m=gaps,minimum_net_clearance_after_2mm_wall_m=min(gaps.values())-.002,motor_intersections=volume_hits,motor_cases=motor_cases,quad_parts=quad,force_path=dict(conditional_output_capacity_nm=capacity,nominal_80mm_contact_force_at_continuous_limit_n=c['joints'][5]['continuous_design_limit_nm']/.08,peak_coupler_force_n=peak,front_bearing_design_load_n=bearing_front,bearing_sku='JTEKT698;8x19x6mm;7.2g',bearing_static_rating_n=910,bearing_static_safety_factor=910/bearing_front,shaft_nominal_diameter_m=shaft_d,shaft_stress_with_1_5_notch_factor_pa=float(shaft_vm),shaft_material_requirement='machined steel; certified yield>=480MPa; design stress limit160MPa; D-flat/clamp-interface FEA remains',output_crank_stress_with_2x_local_factor_pa=plate_stress,crank_material_requirement='6061-T6 Al candidate; declared80MPa allowable; net-hole/clamp bearing checks remain',bush_sku='igus GFM-0506-05',bush_projected_pressure_pa=bush_pressure,bush_pv_mpa_m_s=bush_pv,bush_max_pressure_at_20c_pa=80e6,bush_catalog_pv_mpa_m_s=.42),reduced_model=dict(max_head_com_error_bound_m=max_com_error,coupler_and_pin_omitted_armature_bound_kg_m2=extra_armature,declared_rotor_armature_kg_m2=c['joints'][5]['armature_kg_m2']),sources=['https://www.cubemars.com/product/ak45-36-v3-0-kv80-robotic-actuator.html','https://www.cubemars.com/data/cms/202607/ak45-36-v3-0-kv80-2d-drawing.pdf','https://koyo.jtekt.co.jp/en/products/detail/?pno=698','https://www.igus.com/ContentData/Products/Downloads/iglide_G300_FM_USen.pdf','https://www.igus.co.uk/plain-bearing/materials/universal-use'],limits=['No measured stationary thermal rating inside the head; catalog rated point is8Nm/40rpm','Parallel-crank equal-length model assumes a rigid, correctly clocked uncrossed linkage; assembly tolerance and wear unvalidated','Sampled outer-envelope signed distances, not an offset-shell fabrication proof; head wall2mm and connector exits must be designed','Axle flats/clamps, mounting screws, bearing seats and fatigue are not released; solidity blanks include intentional joint overlaps','Source motor mass is a cylindrical estimate; exact manufacturer CAD mass distribution unknown','Small mechanism masses are lumped; output crank/shaft rotate correctly but input crank/coupler visuals are closed-pose proxies in the reduced MJCF'])
    (R/'evidence/stage_two_mechanism_gate.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(checks=checks,force_path=report['force_path'],clearance=report['minimum_net_clearance_after_2mm_wall_m'],reduced_model=report['reduced_model']),indent=2))
if __name__=='__main__':main()
