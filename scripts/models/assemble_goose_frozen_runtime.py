"""Combine immutable design SI with source-owned collision leaves; no CAD/training."""
from __future__ import annotations
import argparse,copy,hashlib,json,shutil,sys,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import mujoco
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'scripts/models'),str(ROOT/'src')]
from sai_agent.goose.frozen_mjcf import write_model

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main(a):
 package=a.package.resolve();contract=json.loads((package/'physical_contract.json').read_text());mf=json.loads(a.collision_manifest.read_text());rows=mf if isinstance(mf,list)else mf.get('collision_geometries',mf.get('geometries',mf.get('collisions',mf.get('parts',mf.get('collision_leaves')))))
 if not isinstance(rows,list):raise ValueError('No collision geometry list')
 rows=copy.deepcopy(rows);assets=package/'meshes'
 if assets.exists():shutil.rmtree(assets)
 assets.mkdir(exist_ok=True)
 for r in rows:
  src=Path(r['asset']);src=src if src.is_absolute()else a.collision_root/src
  if not src.exists():raise FileNotFoundError(src)
  name=r['name']+src.suffix;dst=assets/name;shutil.copyfile(src,dst);r.update(asset='meshes/'+name,sha256=sha(dst),contact_policy_no_legacy_exclusions=True)
 # C's source-derived leaf coordinates are already in owning rigid body's frame.
 exclusions=write_model(contract,rows,package/'robot.xml',cold_root_z_m=a.cold_root_z_m,excludes=mf.get('explicit_exclusions',mf.get('explicit_body_pair_filters'))if isinstance(mf,dict)else None,contact_pairs=mf.get('explicit_contact_pairs')if isinstance(mf,dict)else None)
 p=package/'robot.xml'
 # Asset filenames can stay identical between two different convex proxies.
 # Bind their source digest in inert metadata so XML identity is unambiguous.
 tree=ET.parse(p);root=tree.getroot();custom=ET.SubElement(root,'custom')
 ET.SubElement(custom,'text',name='contact_source_sha256',data=sha(a.collision_manifest))
 ET.SubElement(custom,'text',name='physical_contract_sha256',data=sha(package/'physical_contract.json'))
 ET.SubElement(custom,'text',name='collision_package_id',data=package.name)
 ET.indent(tree);tree.write(p,encoding='utf-8',xml_declaration=True)
 receipt=dict(schema='goose_frozen_SI_and_source_contacts_runtime_composition_v1',physical_contract_sha256=sha(package/'physical_contract.json'),actuator_contract_sha256=sha(package/'actuator_contract.json'),collision_source_manifest=dict(sha256=sha(a.collision_manifest),provenance_path=str(a.collision_manifest),runtime_dependency=False),collision_geometries=rows,source_collision_metadata=mf if isinstance(mf,dict)else{},actuation=[dict(public_axis=j['name'],actuated_joint=j.get('actuation_joint',j['name']),mode='continuous_bounded_effort_200Hz_reference_adapter')for j in contract['joints']],explicit_exclusions=exclusions,robot_xml_sha256=sha(p),runtime_assets_all_relative=True,original_XML_native_position_actuators_not_used=True,training_tasks_or_policies_modified=False)
 receipt.update(active_physical_contract=dict(file='physical_contract.json',release_id=contract['release_id'],sha256=sha(package/'physical_contract.json')),contact_geometry_inherited_from_source_manifest=dict(sha256=sha(a.collision_manifest),provenance_path=str(a.collision_manifest)),historical_source_contact_metadata_does_not_override_active_SI=True,contact_assets_rescaled_for_material_change=False)
 (package/'collision_manifest.json').write_text(json.dumps(receipt,indent=2)+'\n')
 model=mujoco.MjModel.from_xml_path(str(p))
 mapping=dict(schema='goose_named_runtime_index_and_frame_mapping_v1',model_sha256=sha(p),public_joint_order=contract['joint_order'],public_axes=[dict(name=j['name'],logical_qpos_index=int(model.joint(j['name']).qposadr[0]),logical_qvel_index=int(model.joint(j['name']).dofadr[0]),actuator_index=i,actual_drive_joint=j.get('actuation_joint',j['name']),actual_drive_qvel_index=int(model.joint(j.get('actuation_joint',j['name'])).dofadr[0]))for i,j in enumerate(contract['joints'])],internal_joint_names=[j['name']for j in contract['passive_linkage_joints']],born_root_xyz_quat_wxyz=model.qpos0[:7].tolist(),root_frame='Worldzero CAD reference atgrounddatum; torso COM andvisual geometry are offset from the root origin. qpos[2] is not torsoCOMheight.',height_measurement='Use data.subtree_com[model.body("torso").id,2] for physical wholebodyCOM; taskdefinitions andterminations belong to training consumer.',handedness='Right handed; +X forward, +Y robotleft, +Z up; angle rad, lengthm, masskg, forceN, torqueNm.',backend='MuJoCo3.10.0; no V0.1 runtime identity compatibility is claimed')
 (package/'runtime_interface.json').write_text(json.dumps(mapping,indent=2)+'\n')
 print(json.dumps(dict(model=str(p),sha256=sha(p),leaves=len(rows),mass_kg=contract['nominal_robot_mass_kg'])),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);p.add_argument('--collision-manifest',type=Path,required=True);p.add_argument('--collision-root',type=Path,required=True);p.add_argument('--cold-root-z-m',type=float,default=.002206376);main(p.parse_args())
