"""Native open torso frame and high-hip yaw-to-roll load-path candidates.

CAD validity is not strength, OEM output-bearing capacity or release. Output
adapter loads MUST be checked against the actual actuator bearing ratings.
"""
from pathlib import Path
import hashlib, json, sys
import numpy as np
import trimesh
from build123d import export_brep, export_step, export_stl, import_step

ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path[:0]=[str(ROOT/'scripts/cad'),str(ROOT/'scripts/models')]
from build_goose_cad import cylinder,box,holes
from build_goose_actuator_interfaces import quad_sampling
from goose_nurbs_skin import native_properties
from build_goose_stage_two import candidate
from sai_agent.goose.morphology import apply_leg_layout


def main():
    layout_path=R/'configs/body_bay_layout_candidate.json';layout=json.loads(layout_path.read_text())
    facts_path=R/'hardware/stage_three_actuator_mounts.json';facts=json.loads(facts_path.read_text())['catalog']
    s=candidate();apply_leg_layout(s,layout)
    source=R/'cad/source/body_bay_frame';dest=R/'cad/exports/body_bay_frame'
    source.mkdir(exist_ok=True);dest.mkdir(exist_ok=True)
    records=[];scene=[];features=[]
    def emit(name,shape,body='torso',notes=None):
        if not shape.is_valid or len(shape.solids())!=1:raise ValueError((name,'invalid/disconnected native frame'))
        shape=shape.solids()[0];volume,com,I,_=native_properties(shape)
        paths={'brep':source/(name+'.brep'),'step':dest/(name+'.step'),'stl':dest/(name+'.stl'),'npz':source/(name+'_quad.npz')}
        export_brep(shape,paths['brep']);export_step(shape,paths['step']);export_stl(shape,paths['stl'],tolerance=.08,angular_tolerance=.18)
        rt=import_step(paths['step']);rv,*_=native_properties(rt);mesh=trimesh.load(paths['stl'],force='mesh',process=True)
        if not rt.is_valid or len(rt.solids())!=1 or abs(rv/volume-1)>1e-5 or not mesh.is_watertight or not mesh.is_winding_consistent or abs(mesh.volume/volume-1)>.005:
            raise ValueError((name,'native exchange'))
        vertices,faces=quad_sampling(mesh);np.savez_compressed(paths['npz'],vertices=vertices,faces=faces)
        files={k:dict(path=str(p.relative_to(R)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for k,p in paths.items()}
        records.append(dict(name=name,body=body,unit='mm',material='aluminium_6061_t6_candidate',density_kg_m3=2700,
            mass_kg=volume*2700e-9,volume_mm3=volume,center_of_mass_world_m=(com/1000).tolist(),inertia_at_com_world_kg_m2=(I*2700e-15).tolist(),
            files=files,quad_faces=len(faces),native_valid=True,manufacturing_released=False,notes=notes or []))
        scene.append(dict(name=name,body=body,material='graphite' if body=='torso' else 'ivory',group='body_bay_frame',
            role='native_load_path_candidate_OEM_bearing_capacity_pending',geometry_npz=files['npz']['path'],source_sha256=files['npz']['sha256']))
        print(name,'mass_g',volume*2700e-6,flush=True)
    def radial(center,radius,angles,plane='z'):
        c=np.array(center,float);a=np.deg2rad(angles)
        return [c+([radius*np.cos(t),radius*np.sin(t),0] if plane=='z' else [0,radius*np.cos(t),radius*np.sin(t)]) for t in a]
    chassis=None;seat_z=313.4
    for side in ['right','left']:
        yaw=s.pivots[side+'_hip_yaw']*1000;roll=s.pivots[side+'_hip_roll']*1000
        output_z=yaw[2]+20.1
        adapter=cylinder(22,4,[yaw[0],yaw[1],output_z+2])-cylinder(8,10,[yaw[0],yaw[1],output_z+2])
        motor=radial([yaw[0],yaw[1],output_z+2],13.5,facts['ak40_10_v3']['output_mount']['vendor_angles_xz_deg'])
        links=radial([yaw[0],yaw[1],output_z+2],17,[0,120,240])
        adapter=holes(adapter,motor,2.7,12,'z');adapter=holes(adapter,links,2.5,12,'z')
        emit(side+'_hip_yaw_output_adapter',adapter,side+'_hip_yaw',[
            'CNC6061-T6 4mm. ThreeM2.5x8 with1.5mm total washers:2.5mm insertion<=3mm; no centering pilot depth invented.',
            'ThreeM3 TAP through4mm atPCD34. U bracket M3x10 with1mm washer gives3.5mm thread engagement.',
            'Actuator output-bearing radial/axial/moment rating, clamp preload and fatigue not yet released.'])
        top_z=output_z+4+2.75;column_x=yaw[0]+36
        top=cylinder(23,5.5,[yaw[0],yaw[1],top_z])
        top+=box([column_x+2.75-yaw[0],24,5.5],[(yaw[0]+column_x+2.75)/2,yaw[1],top_z])
        top=holes(top,radial([yaw[0],yaw[1],top_z],17,[0,120,240]),3.2,14,'z')
        top=holes(top,radial([yaw[0],yaw[1],top_z],13.5,facts['ak40_10_v3']['output_mount']['vendor_angles_xz_deg']),5.2,14,'z')
        ring_x=roll[0]+25.25+2;beam_z=roll[2]+26.75
        bottom=cylinder(30,4,[ring_x,roll[1],roll[2]],'x')-cylinder(21,12,[ring_x,roll[1],roll[2]],'x')
        bottom=holes(bottom,radial([ring_x,roll[1],roll[2]],24,facts['ak45_36_v3']['case_front_mount']['vendor_angles_xz_deg'],'x'),3.2,14,'x')
        low=ring_x-2;high=column_x+2.75
        bottom+=box([high-low,24,5.5],[(low+high)/2,roll[1],beam_z])
        column_low=beam_z-2.75;column_high=top_z+2.75
        u=top+bottom+box([5.5,24,column_high-column_low],[column_x,roll[1],(column_low+column_high)/2])
        emit(side+'_hip_yaw_to_roll_u_carrier',u,side+'_hip_yaw',[
            'One CNC6061-T6 billet part; top5.5mm, vertical5.5x24mm, bottom5.5mm bridge and4mm stator front ring. No unsupported butt weld.',
            'SixM3x8 with1mm washer into roll stator front gives3mm insertion<=4mm.',
            'Output openingID42 clears rotating roll adapter radius20; actual all-pose assembly, connector and local stress gates remain.',
            'OEM yaw output-bearing capacity must support the overhung load or this carrier needs an independent bearing redesign.'])
        c=[yaw[0],yaw[1],seat_z]
        fixed=cylinder(32,3,c)-cylinder(18,10,c)
        fixed=holes(fixed,radial(c,23.5,[0,90,180,270]),2.7,10,'z')
        chassis=fixed if chassis is None else chassis+fixed
    chassis+=box([24,130,3],[-18,0,seat_z])
    for sign in [-1,1]:
        chassis+=box([75,12,3],[-77.5,sign*34,seat_z])
        chassis+=box([115,12,3],[17.5,sign*20,seat_z])
        chassis+=box([12,26,3],[-44,sign*27,seat_z])
        chassis+=box([10,20,3],[-6,sign*30,seat_z])
    chassis+=box([24,80,3],[43,0,seat_z])
    # Preserve rear driver access apertures after adding the central bridge.
    for side in ['right','left']:
        yaw=s.pivots[side+'_hip_yaw']*1000
        chassis-=cylinder(18,12,[yaw[0],yaw[1],seat_z])
        chassis=holes(chassis,radial([yaw[0],yaw[1],seat_z],23.5,[0,90,180,270]),2.7,12,'z')
    mounts=[[x,y,seat_z] for x in [-110,-6] for y in [-34,34]]+[[x,y,seat_z] for x in [34,52] for y in [-34,34]]
    chassis=holes(chassis,mounts,3.2,12,'z')
    emit('torso_open_chassis_plate',chassis,notes=['CNC3mm plate; driver rear4xM2.5 per hip, M2.5x8 +0.5mm washer gives4.5mm insertion<=5mm.',
        'Separate longitudinal rails keep the rear compute module open; no rear crossbar through electronics.',
        'M3 through stack to neck plate and battery posts. Neck/hip loads, local hole ligaments and stiffness remain verification gates.'])
    neck=s.pivots['neck_yaw']*1000;neck_z=neck[2]-20.1-1.5
    neck_mount=cylinder(32,3,[neck[0],neck[1],neck_z])+box([24,80,3],[neck[0],neck[1],neck_z])
    neck_mount-=cylinder(18,12,[neck[0],neck[1],neck_z])
    neck_mount=holes(neck_mount,radial([neck[0],neck[1],neck_z],23.5,[0,90,180,270]),2.7,12,'z')
    neck_points=[[x,y,neck_z] for x in [34,52] for y in [-34,34]]
    neck_mount=holes(neck_mount,neck_points,3.2,12,'z')
    emit('neck_yaw_rear_frame_plate',neck_mount,notes=['AK40 rear mounting through3mm plate, M2.5x8+0.5washer:4.5mm insertion<=5mm. Central36mm opening preserves driver access.'])
    gap=(neck_z-1.5)-(seat_z+1.5)
    if gap<=0:raise ValueError('neck frame spacing invalid')
    for k,(x,y,z) in enumerate(neck_points):
        spacer=cylinder(4,gap,[x,y,seat_z+1.5+gap/2])-cylinder(1.6,gap+4,[x,y,seat_z+1.5+gap/2])
        emit('neck_frame_spacer_'+str(k),spacer,notes=['Turned6061 throughM3 spacer; actual length '+str(gap)+'mm.'])
    battery_floor=329.
    gap=battery_floor-(seat_z+1.5)
    for side,sign in [('right',-1),('left',1)]:
        rail=box([120,6,2.5],[-55,sign*27,battery_floor+1.25])
        for x in [-110,-6]:rail+=box([10,14,2.5],[x,sign*31,battery_floor+1.25])
        rail=holes(rail,[[x,sign*34,battery_floor+1.25] for x in [-110,-6]],3.2,8,'z')
        emit(side+'_battery_support_rail',rail,notes=['2.5mm6061. Battery allowance bottom333mm; rail top331.5mm leaves1.5mm pad allocation, not measured foam compression.'])
        for k,x in enumerate([-110,-6]):
            post=cylinder(4,gap,[x,sign*34,seat_z+1.5+gap/2])-cylinder(1.6,gap+4,[x,sign*34,seat_z+1.5+gap/2])
            emit(side+'_battery_frame_post_'+str(k),post,notes=['Turned6061 throughM3 post, length '+str(gap)+'mm; end-to-end bolt and locknut stack pending complete release.'])
    inputs=[Path(__file__),layout_path,facts_path,ROOT/'src/sai_agent/goose/morphology.py']
    report=dict(schema='goose_body_bay_frame_candidate_v1',parts=records,native_mass_kg=sum(p['mass_kg'] for p in records),
        manufacturing_pass=False,whole_load_path_pass=False,hardware_freeze=False,source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        limitations=['OEM output-bearing moment/radial/axial limits absent: output-supported hip carrier is NOT released',
            'Frame is a native attachment candidate, not full local-stress/fatigue/fastener acceptance',
            'Head/neck cross-axis and ankle attachments remain separate critical gates',
            'No connectors, master protection/resistor mounts or shell hinges/latches released'])
    (dest/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    (source/'quad_scene.json').write_text(json.dumps(dict(unit='m',status='BODY_FRAME_LOAD_PATH_CANDIDATE_UNRELEASED',parts=scene),separators=(',',':'))+'\n')


if __name__=='__main__':main()
