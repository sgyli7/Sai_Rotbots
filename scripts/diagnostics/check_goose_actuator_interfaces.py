"""Re-import interface CAD and probe every documented hole, not render pixels."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
import trimesh
from build123d import import_step
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/cad'))
from build_goose_cad import cylinder
from goose_nurbs_skin import native_properties
ROBOT=ROOT/'robots/Goose_V0.1'

def main():
    manifest_path=ROBOT/'cad/exports/actuator_interfaces/manifest.json'
    manifest=json.loads(manifest_path.read_text());rows=[]
    for part in manifest['parts']:
        errors=[]
        for entry in part['files'].values():
            f=(ROBOT/entry['path']).resolve()
            if not f.is_relative_to(ROBOT.resolve()) or hashlib.sha256(f.read_bytes()).hexdigest()!=entry['sha256']:errors.append('file_hash_or_path')
        shape=import_step(ROBOT/part['files']['step']['path']);vol,com,I,_=native_properties(shape)
        if not shape.is_valid or len(shape.solids())!=1 or abs(vol-part['volume_mm3'])>vol*1e-7:errors.append('native_roundtrip')
        if np.linalg.norm(com/1000-np.array(part['center_of_mass_local_m']))>1e-7:errors.append('placement')
        for feature in part['features']:
            for center in feature['centers_mm']:
                probe=cylinder(feature['diameter_mm']*.499,part['thickness_mm']+10,center,'y')
                common=shape&probe
                if common is not None and sum(s.volume for s in common.solids())>1e-5:errors.append('missing_or_undersize_'+feature['type'])
        stack=part['selected_bolt'];depth=stack['length_mm']-part['thickness_mm']-stack['washer_thickness_mm']
        if abs(depth-stack['motor_penetration_mm'])>1e-8 or not 2<=depth<=stack['insertion_limit_mm']-.25:errors.append('screw_bottoming_or_short_engagement')
        with np.load(ROBOT/part['files']['npz']['path'],allow_pickle=False) as data:v,f=data['vertices'],data['faces']
        if f.shape[1]!=4 or not np.issubdtype(f.dtype,np.integer):errors.append('not_quads')
        else:
            tm=trimesh.Trimesh(v,np.concatenate([f[:,[0,1,2]],f[:,[0,2,3]]]),process=False)
            if not tm.is_watertight or not tm.is_winding_consistent or tm.volume<=0 or abs(tm.volume*1e9-vol)/vol>.01:errors.append('quad_topology_or_scale')
        rows.append(dict(name=part['name'],interface_geometry_pass=not errors,errors=errors,probed_holes=sum(len(f['centers_mm']) for f in part['features']),motor_insertion_mm=depth,mass_g=part['mass_kg']*1000,remaining_gates=part['remaining_gates']))
    facts=ROBOT/'hardware/stage_three_actuator_mounts.json';script=ROOT/'scripts/cad/build_goose_actuator_interfaces.py'
    inputs_pass=manifest['facts_sha256']==hashlib.sha256(facts.read_bytes()).hexdigest() and manifest['script_sha256']==hashlib.sha256(script.read_bytes()).hexdigest()
    report=dict(status='ACTUAL_PERFORATED_INTERFACES_PARTIAL_GATE',interface_geometry_pass=inputs_pass and all(r['interface_geometry_pass'] for r in rows),manufacturing_pass=False,assembled_joint_pass=False,input_hashes_pass=inputs_pass,manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),checks=rows,limitation='Part-level holes, screw insertion and exchange geometry only. No assembled fork/idler/preload, off-axis load or connector certification.')
    (ROBOT/'evidence/manufacturing_actuator_interfaces.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['interface_geometry_pass','assembled_joint_pass','manufacturing_pass']},indent=2))
    for r in rows:print(r['name'],r['interface_geometry_pass'],r['errors'])
    return 0 if report['interface_geometry_pass'] else 1
if __name__=='__main__':raise SystemExit(main())
