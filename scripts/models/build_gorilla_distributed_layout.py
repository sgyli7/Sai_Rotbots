#!/usr/bin/env python3
"""Compose D's finite leg, split foot and distributed system at C15 scale.

All historical candidates stay frozen. Unqualified modules remain visible and
mass accounted; this source is not a released SI contract or aesthetic baseline.
"""
from pathlib import Path
import argparse,copy,hashlib,json,importlib.util
import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[2]
ROBOT=ROOT/'robots/gorilla_v0_1'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--spec',type=Path,default=ROBOT/'configs/internal_structure_d_spec.json')
 parser.add_argument('--output',type=Path,default=ROBOT/'cad/source/internal_structure_d_scene.json')
 args=parser.parse_args();spec=json.loads(args.spec.read_text())
 inputs={k:ROOT/spec[k] for k in ('base_scene','geometry_spec','leg_scene','foot_scene','system_scene','system_spec','component_references')}
 for k,p in inputs.items():
  if sha(p)!=spec[k+'_sha256']:raise ValueError('Changed D input '+k)
 base=json.loads(inputs['base_scene'].read_text());leg=json.loads(inputs['leg_scene'].read_text());foot=json.loads(inputs['foot_scene'].read_text());system=json.loads(inputs['system_scene'].read_text());system_spec=json.loads(inputs['system_spec'].read_text())
 helper_path=ROOT/'scripts/models/build_gorilla_internal_structure.py'
 definition=importlib.util.spec_from_file_location('net_helpers',helper_path);h=importlib.util.module_from_spec(definition);definition.loader.exec_module(h)
 feet={side+'_'+body for side in ('left','right') for body in ('foot','forefoot_display','heel_display')}
 legs={side+'_'+body for side in ('left','right') for body in ('thigh','middle_shank','distal_shank')}
 prefixes=tuple(side+'_'+joint+'_' for side in ('left','right') for joint in ('hip','knee','fold','ankle'))
 parts=[];frames={};removed=[]
 for p in base['parts']:
  body=p['body'];role=p['role'];keep=role in ('armor_cover','armor_surface','ground_pad','contact_surface_candidate','control_display_ui','control_display_glass','display_module_envelope')
  if role.startswith('primary_structure'):
   if body not in legs|feet and role=='primary_structure_candidate':frames.setdefault(body,[]).append(h.native_mesh(p))
  elif role=='visible_mechanism' and body not in feet and not p['name'].startswith(prefixes):keep=True
  if keep:parts.append(copy.deepcopy(p))
  else:removed.append(p['name'])
 for body,meshes in frames.items():
  m=h.united(meshes)
  parts.append({'name':'isd_retained_path_'+body,'body':body,'role':'D_finite_primary_material','color_rgba':[.20,.24,.27,1.],'vertices_world_m':m.vertices.tolist(),'faces':m.faces.tolist(),'edge_bevel_m':0,'hardware':True,'D_metadata':{'density_kg_m3':spec['material']['density_kg_m3'],'scope':'Exact union of C15 original upper/pelvis members, not a qualified interface to D modules','connection_qualified':False}})
 leg_parts=leg.get('parts')
 if leg_parts is None:leg_parts=next(p for p in leg['pose_scenes'] if p['id']=='neutral')['parts']
 foot_neutral=next(p for p in foot['pose_scenes'] if p['id']=='neutral_locked')['parts']
 parts.extend(copy.deepcopy(leg_parts));parts.extend(copy.deepcopy(foot_neutral));parts.extend(copy.deepcopy(system['parts']))
 names=[p['name'] for p in parts]
 if len(names)!=len(set(names)):raise ValueError('Duplicate D native part names')
 for p in parts:
  if not p.get('vertices_world_m') or not p.get('faces'):raise ValueError('No native geometry '+p['name'])
  if p['name'].startswith('isd_') and not p.get('color_rgba') and p.get('rgba'):p['color_rgba']=p['rgba']
 armor={p['name']:p for p in base['parts'] if p['role'] in ('armor_cover','armor_surface')}
 lookup={p['name']:p for p in parts}
 assert all(lookup[k]==v for k,v in armor.items())
 source={'robot_id':'gorilla_v0_1','schema':'gorilla_internal_structure_candidate_v1','candidate':'internal_structure_d','coordinate_frame':base.get('coordinate_frame','SI m; X front, Y left, Z up'),'base_scene':spec['base_scene'],'base_scene_sha256':sha(inputs['base_scene']),'spec_path':str(args.spec.relative_to(ROOT)),'spec_sha256':sha(args.spec),'builder_path':str(Path(__file__).resolve().relative_to(ROOT)),'builder_sha256':sha(__file__),'input_hashes':{str(p.relative_to(ROOT)):sha(p) for p in [*inputs.values(),helper_path]},'parts':parts,'joint_supports':leg['joint_supports'],'system_module_rows':system_spec['modules'],'component_pose_sources':{'leg':spec['leg_scene'],'foot':spec['foot_scene']},'removed_C15_part_names':removed,'original_armor_preserved_count':len(armor),'mass_scope':'All D finite materials and distributed modules counted, original visible mechanisms retained as display only and replaced by explicit module/connection mass allowances. No inherited A989kg.','geometry_accepted':False,'physics_accepted':False,'stable_physical_contract':False,'aesthetic_baseline_approved':False,'scope':'D distributed full-body assembly diagnostic; eight sagittal leg axes plus partial additional-axis packages. Complete serial carriers and whole drive/thermal/connection qualifications remain open.'}
 write(args.output,source)
 print(json.dumps({'candidate':'internal_structure_d','native_parts':len(parts),'retained_armor':len(armor),'scene_sha256':sha(args.output),'geometry_accepted':False}))

if __name__=='__main__':main()
