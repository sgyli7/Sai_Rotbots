"""Check actual sample/robot native distances on the finite IK poses."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

from sai_agent.goose.task_samples import sample_body

ROOT=Path(__file__).resolve().parents[2]
ROBOT=ROOT/'robots/Goose_V0.1'


def scene(item):
    source=ROBOT/'models/task_proxy_11_v1/robot.xml'
    tree=ET.parse(source).getroot()
    for mesh in tree.findall('asset/mesh'):
        mesh.set('file',str((source.parent/mesh.get('file')).resolve()))
    body,_,_=sample_body(item['object_id'],item['family'],item['SI']['mass_kg'])
    tree.find('worldbody').append(body)
    text=ET.tostring(tree,encoding='unicode')
    m=mujoco.MjModel.from_xml_string(text)
    original=mujoco.MjModel.from_xml_path(str(source.resolve()))
    for name in ('body_mass','body_ipos','body_inertia','body_iquat'):
        np.testing.assert_array_equal(getattr(m,name)[:original.nbody],getattr(original,name))
    for name in ('geom_type','geom_size','geom_friction','geom_solref','geom_solimp','geom_margin'):
        np.testing.assert_array_equal(getattr(m,name)[:original.ngeom],getattr(original,name))
    return m,text,original.nq,original.ngeom


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--poses',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    poses=json.loads(args.poses.read_text());catalog_path=ROBOT/'models/task_samples_v1/object_catalog.json'
    catalog=json.loads(catalog_path.read_text());samples={}
    for family in ['cylinder_weight','handle_weight']:
        item=next(x for x in catalog['objects'] if x['family']==family and not x['development_only'])
        m,text,nq,ngeom=scene(item);samples[family]=(item,m,nq,ngeom)
        (args.out/f'{family}_scene.xml').write_text(text+'\n')
    results=[]
    for row in poses:
        if not row['geometry_possible']:
            continue
        item,m,nq,ngeom=samples[row['family']];d=mujoco.MjData(m)
        d.qpos[:nq]=row['qpos'];qa=int(m.joint(f'{item["object_id"]}_free').qposadr[0])
        d.qpos[qa:qa+7]=[*row['object_grip_origin_world_m'],1,0,0,0]
        mujoco.mj_forward(m,d)
        distances=[]
        for g in range(ngeom):
            if m.geom(g).name=='ground':continue
            for objg in range(ngeom,m.ngeom):
                value=float(mujoco.mj_geomDistance(m,d,g,objg,1,None))
                distances.append({'robot_geom':m.geom(g).name,'object_geom':m.geom(objg).name,'signed_distance_m':value})
        penetrations=[x for x in distances if x['signed_distance_m']<-.0002]
        closure=[]
        if not penetrations:
            # Finite kinematic admission only: the object remains at its floor
            # pose. Stop at first jaw contact or another collision, never drive
            # through the specimen to manufacture a completed grasp.
            lower=m.geom('lower_bill_envelope').id
            bar=m.geom(item['object_id']+'_grip').id
            ground=m.geom('ground').id
            for angle in np.arange(.22,-.001,-.02):
                for name,multiplier in [('beak_hinge',1),('beak_input_rotor',1),('beak_coupler_link',-1)]:
                    d.qpos[int(m.joint(name).qposadr[0])]=float(angle)*multiplier
                mujoco.mj_forward(m,d)
                other=[]
                for g in range(ngeom):
                    if g==ground:continue
                    for objg in range(ngeom,m.ngeom):
                        if objg==bar and g in (lower,m.geom('head_upper_bill_envelope').id):continue
                        value=float(mujoco.mj_geomDistance(m,d,g,objg,1,None))
                        if value<-.0002:other.append([m.geom(g).name,m.geom(objg).name,value])
                for contact in d.contact:
                    if all(int(g)<ngeom for g in contact.geom) and contact.dist<-.0002:
                        other.append([*[m.geom(int(g)).name for g in contact.geom],float(contact.dist)])
                bar_gap=float(mujoco.mj_geomDistance(m,d,lower,bar,1,None))
                closure.append({'jaw_rad':float(angle),'lower_bar_gap_m':bar_gap,'other_penetrations':other})
                if other or bar_gap<=0:break
        results.append({**row,'sample_object_id':item['object_id'],'actual_sample_robot_distances':distances,
            'sample_robot_penetrations':penetrations,'actual_sample_robot_clear':not penetrations,
            'finite_closure_probe':closure,
            'finite_closure_reaches_bar_before_other_collision':bool(closure and closure[-1]['lower_bar_gap_m']<=0 and not closure[-1]['other_penetrations'])})
    report={'schema':'goose_sample_ground_native_contact_v1','source_robot_model_sha256':catalog['robot_model_sha256'],
        'object_catalog_sha256':hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
        'input_pose_record_sha256':hashlib.sha256(args.poses.read_bytes()).hexdigest(),
        'evaluator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'sample_geometries_identical_across_masses':True,'native_robot_mass_geometry_preserved':True,
        'initial_pose_robot_floor_self_clear_cases':len(results),
        'actual_sample_robot_clear_cases':sum(x['actual_sample_robot_clear'] for x in results),
        'results':results,'dynamics_integrations':0,'full_ground_pickup_qualification':False,
        'scope':'Finite endpoints and sampled jaw closure only. Query all 11 robot hulls against every sample leaf; actual robot SI/geoms preserved. Closure stops at first lower-bar contact or other collision. No continuous approach/sweep, grasp dynamics, compliance or material qualification.'}
    (args.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'pose_cases':len(results),'actual_sample_robot_clear_cases':report['actual_sample_robot_clear_cases'],
        'family_clear_counts':{f:sum(x['actual_sample_robot_clear'] for x in results if x['family']==f) for f in samples},
        'full_ground_pickup_qualification':False}))


if __name__=='__main__':main()
