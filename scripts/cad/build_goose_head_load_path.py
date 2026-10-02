"""Native head load-path candidate using documented actuator mounting faces.

The beak motor retains its stage-two centre. Native mount faces and hollow
clearances replace earlier reserved masses only after integration checks.
"""
from pathlib import Path
import hashlib,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path.insert(0,str(ROOT/'scripts/cad'))
from build_goose_cad import box,cylinder,holes
from goose_candidate_export import CandidateExport
from build123d import Pos,Rot


def points(center,r,angles):
    return [[center[0]+r*np.cos(t),center[1],center[2]+r*np.sin(t)] for t in np.deg2rad(angles)]


def spider(center,r,angles,outer=23.,inner=21.,depth=4.,pad_radius=4.):
    shape=cylinder(outer,depth,center,'y')-cylinder(inner,depth+2,center,'y')
    for p in points(center,r,angles):
        shape+=cylinder(pad_radius,depth,p,'y')
    return holes(shape,points(center,r,angles),3.2,depth+4,'y')


def main():
    export=CandidateExport(R,'head_load_path');P=np.array([42.,0.,605.]);H=np.array([81.,0.,585.5]);M=np.array([129.,0.,601.]);J=np.array([160.,0.,576.])
    # AK45-10 head-pitch output atY22.6; integral bracket rear surface touches
    # only the stator's mounting ears atX69.5, not the case body.
    pitch=cylinder(20,3,[42,24.1,605],'y')-cylinder(7.6,8,[42,24.1,605],'y')
    pitch=holes(pitch,points([42,24.1,605],13.5,[30,150,270]),2.7,8,'y')
    rear=box([3,24,38],[68,0,578])
    rear=holes(rear,[[68,y,585.5+z] for y in [-8,8] for z in [7.5,-22.5]],2.2,10,'x')
    rear-=box([12,12,17],[68,0,574]) # rear centre and wire access
    base=box([28.5,37.6,3],[55.25,6.8,557.5])
    rise=box([10,3,31.5],[54,24.1,574.75])
    bracket=pitch+rear+base+rise
    bracket-=cylinder(27,46.2,[42,-.5,605],'y')
    export.emit('head_pitch_to_roll_stator_bracket',bracket,'head_pitch',notes=['AK45-10 output3M2.5PCD27 atY22.6,3mm adapter integral with CNC rear stator bracket.','ROBOTIS XC330 body23mm depth; rear faceX69.5; four ear holes16x30mm.','Rear case screw/plug access and complete swept head bracket fit are separate gates.'])
    # Correct23mm case,3mm output horn and16mm horn diameter, per official
    # XC330 drawing. Body mass remains catalog23g, not solid-aluminium mass.
    case=box([23,20,34],[81,0,578])+cylinder(8,3,[94,0,585.5],'x')
    export.emit('head_roll_catalog_case',case,'head_pitch',rho=1,material='graphite',catalog_mass=.023,
        notes=['Own nominal geometry reconstructed from ROBOTIS XL,XC-330.pdf; not redistributed vendor CAD.','Case X69.5..92.5; output horn faceX95.5,OD16mm. Connector shape and vendor internal inertia remain unknown.'])
    adapter=cylinder(14,2.5,[96.75,0,585.5],'x')-cylinder(2.1,8,[96.75,0,585.5],'x')
    adapter=holes(adapter,[[96.75,6*np.cos(a),585.5+6*np.sin(a)] for a in np.deg2rad([0,90,180,270])],2.2,8,'x')
    adapter=holes(adapter,[[96.75,11*np.cos(a),585.5+11*np.sin(a)] for a in np.deg2rad([0,120,240])],3.2,8,'x')
    export.emit('head_roll_horn_adapter',adapter,'head_roll',notes=['Four M2 tapping holes PCD12; motor penetration must not exceed3mm.','Three M3 through joints PCD22 attach native head frame; clamp nuts must clear the23mm servo.'])
    front=spider([129,27.25,601],24,[30,90,150,210,270,330],pad_radius=3.5)
    rear_frame=spider([129,-30,601],23.5,[45,135,225,315],outer=22,inner=10,depth=3.5)
    length=float(np.linalg.norm((J-M)[[0,2]]));angle=float(np.rad2deg(np.arctan2(25,31)))
    front+=Pos(144.5,27.25,588.5)*Rot(0,angle,0)*box([length,4,12])
    rear_frame+=Pos(144.5,-30,588.5)*Rot(0,angle,0)*box([length,3.5,12])
    for y in [23.5,-26.5]:
        housing=cylinder(12,8,[160,y,576],'y')-cylinder(9.5,12,[160,y,576],'y')
        housing-=cylinder(28.5,130,M,'y') #1mm motor keepout, minimum seat wall1.8246mm
        if y>0:front+=housing
        else:rear_frame+=housing+box([12,5,4],[154,-28,586])
    horn=cylinder(14,2.5,[99.25,0,585.5],'x')
    horn=holes(horn,[[99.25,11*np.cos(a),585.5+11*np.sin(a)] for a in np.deg2rad([0,120,240])],3.2,9,'x')
    bridge=horn
    for y in [27.25,-30]:
        bridge+=box([6,abs(y)+2,6],[101.5,y/2,585.5])
        bridge+=box([31,4 if y>0 else 3.5,10],[114.75,y,583.5])
    frame=front+rear_frame+bridge
    frame-=cylinder(28.5,53.5,[129,-1.5,601],'y')
    frame-=cylinder(21,4.2,[129,27.25,601],'y')
    frame=holes(frame,points([129,27.25,601],24,[30,90,150,210,270,330]),3.2,4.2,'y')
    frame=holes(frame,points([129,-30,601],23.5,[45,135,225,315]),3.2,4,'y')
    for y in [23.5,-26.5]:frame-=cylinder(9.5,9,[160,y,576],'y')
    frame-=cylinder(4.3,100,[160,0,576],'y')
    # The output arm is in front of the bearing seat. Relieve only its swept
    # front layer; the2.5mm rear part of the front arm remains connected.
    frame-=cylinder(19,4,[160,29.75,576],'y')
    print('head frame native validity',frame.is_valid,'connected solids',len(frame.solids()),flush=True)
    export.emit('head_motor_jaw_frame',frame,'head_roll',notes=['One CNC frame, front6M3PCD48 and rear4M3PCD47 for AK45-36.','Motor retainsX129/Y0/Z601. Seat19H7 journals atY23.5/-26.5,8mm housings for6mm-wide698 bearings.','Housing retains at least1.824mm radial material near motor keepout; structural/fatigue checks remain mandatory.','Upper jaw backbone, camera retention and full load-path connection remain separate candidates.'])
    for label,y in [('front',23.5),('rear',-26.5)]:
        bearing=cylinder(9.5,6,[160,y,576],'y')-cylinder(4,10,[160,y,576],'y')
        export.emit('jaw_'+label+'_bearing',bearing,'head_roll',rho=1,material='titanium',catalog_mass=.0072,
            notes=['JTEKT698,8x19x6mm,7.2g,static rating910N. Installation envelope; internal race geometry not reconstructed.'])
    motor=cylinder(27.5,53.5,[129,-1.5,601],'y')-cylinder(9,1.5,[129,25.5,601],'y')
    export.emit('beak_motor_catalog_case',motor,'head_roll',rho=1,material='graphite',catalog_mass=.349,
        notes=['AK45-36 nominal stator envelope excluding output rotation protrusions; output faceY26.25,front stator faceY25.25,rearY-28.25.'])
    replaces=['head_roll_case','head_roll_front_case','head_roll_horn','head_roll_idler','head_roll_output_ring','head_roll_shaft_bolt',
        *['head_roll_horn_fixing_'+str(k) for k in range(4)],'head_roll_connector',
        'head_roll_bridge_rear','head_roll_bridge_front','head_roll_bridge_bridge','head_roll_mount_reserve',
        'head_roll_catalog_envelope','head_roll',
        'beak_rated_motor_case','beak_drive','beak_drive_mount_reserve','jaw_bearing_reserve_right','jaw_bearing_reserve_left']
    value=export.save(ROOT,[Path(__file__),ROOT/'scripts/cad/goose_candidate_export.py',R/'hardware/stage_three_actuator_mounts.json'],replaces=replaces,
        extra=dict(status='NATIVE_HEAD_LOAD_PATH_CANDIDATE',beak_motor_world_mm=M.tolist(),head_roll_output_face_world_x_mm=95.5,
            source_urls=['https://www.robotis.com/service/download.php?no=1986','https://www.cubemars.com/data/cms/202607/ak45-36-v3-0-kv80-2d-drawing.pdf'],
            vendor_drawing_sha256=hashlib.sha256((ROOT/'artifacts/Goose_V0.1/vendor_interface_docs/xc330_drawing.pdf').read_bytes()).hexdigest(),
            transmission_installed=False,manufacturing_released=False))
    print('head native parts',len(value['parts']),'kg',value['native_mass_kg'],flush=True)

if __name__=='__main__':main()
