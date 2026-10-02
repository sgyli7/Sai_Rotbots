#!/usr/bin/env python3
"""Bind actual Gorilla box geometry to conditional mass and gravity wrenches.

This is a first quasistatic articulated load model, not fixed-foot FEA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import ConvexHull

from sai_agent.structural_statics import contact_extreme_allocations, hollow_section, normal_contacts, resultant, nominal_section_stress

ROOT=Path(__file__).resolve().parents[2]
ROBOT=ROOT/'robots/gorilla_v0_1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mesh(part):
    faces=[[f[0],f[k],f[k+1]] for f in part['faces'] for k in range(1,len(f)-1)]
    return trimesh.Trimesh(vertices=part['vertices_world_m'],faces=faces,process=False)


def topology(points):
    parents={'pelvis':None,'torso':'pelvis'}
    origins={'pelvis':[0,0,1.66],'torso':[0,0,1.74]}
    for side in ('left','right'):
        for group,parent,pivot in (
            ('upper_arm','torso','shoulder'),('forearm',side+'_upper_arm','elbow'),
            ('palm',side+'_forearm','wrist'),('thigh','pelvis','hip'),
            ('middle_shank',side+'_thigh','knee'),('distal_shank',side+'_middle_shank','fold'),
            ('foot',side+'_distal_shank','ankle')):
            body=side+'_'+group;parents[body]=parent;origins[body]=points[side+'_'+pivot]
    return parents,origins


def ledger(scene,settings,parents):
    rows=[];rho=settings['material']['density_kg_m3']
    for p in scene['parts']:
        if p['role'] not in ('primary_structure_candidate','primary_structure_socket_candidate','armor_cover','armor_surface'):
            continue
        # Tiny tags/seams included in colored covers do not gain a separate
        # drive/hardware steel density. Mechanism solids use explicit reserves.
        m=mesh(p)
        if not(m.is_watertight and m.is_winding_consistent and m.volume>0):
            raise ValueError('Invalid mass geometry: '+p['name'])
        body=p['body']
        if body not in parents:
            if any(k in body for k in ('finger','thumb')):body=body.split('_')[0]+'_palm'
            else:raise ValueError('Unknown load group: '+body)
        primary=p['role'] in ('primary_structure_candidate','primary_structure_socket_candidate')
        densities=[rho]*3 if primary else settings['armor_density_range_kg_m3']
        basis=('conditional_primary_socket_stock_volume' if p['role']=='primary_structure_socket_candidate'
               else 'conditional_primary_member_stock_volume' if primary else 'conditional_actual_armor_volume')
        rows.append({'id':p['name'],'body':body,'basis':basis,
            'volume_m3':float(m.volume),'mass_range_kg':[float(m.volume*r) for r in densities],
            'position_world_m':m.center_mass.tolist(),'nominal_inertia_at_COM_kg_m2':(m.moment_inertia*densities[1]).tolist(),
            'density_range_kg_m3':densities,'supply_verified':False})
    for item in settings['nonstructural_mass_candidates']:
        variants=(('left',1),('right',-1)) if item.get('symmetric') else ((None,1),)
        for side,s in variants:
            position=np.array(item['position_left_world_m'] if side else item['position_world_m']);position[1]*=s
            rows.append({'id':(side+'_' if side else '')+item['id'],
                'body':(side+'_' if side else '')+item['body'],
                'basis':'explicit_unverified_complete_component_reserve',
                'mass_range_kg':item['mass_range_kg'],'position_world_m':position.tolist(),
                'nominal_inertia_at_COM_kg_m2':None,'supply_verified':False})
    return rows


def projected_arc(point,path):
    path=np.asarray(path,float);point=np.asarray(point,float)
    offset=0;best=None
    for a,b in zip(path[:-1],path[1:]):
        d=b-a;length=np.linalg.norm(d);t=float(np.clip(np.dot(point-a,d)/np.dot(d,d),0,1))
        distance=np.linalg.norm(point-(a+t*d))
        candidate=(distance,offset+t*length)
        if best is None or candidate[0]<best[0]:best=candidate
        offset+=length
    return best[1]


def member_segments(part,density):
    """Exact volume/COM of the material between each pair of native rings."""
    data=part['structural_member'];n=len(data['outer_polygon_uv_m']);stride=2*n
    allv=np.asarray(part['vertices_world_m']);out=[]
    if data.get('native_vertex_layout','').startswith('outer_station_0, outer_station_1'):
        allv=allv[np.r_[0:n,2*n:3*n,n:2*n,3*n:4*n]]
    if len(allv)!=len(data['centerline_world_m'])*stride:
        raise ValueError('Unsupported station layout: '+part['name'])
    for k in range(len(data['centerline_world_m'])-1):
        v=allv[k*stride:(k+2)*stride];faces=[]
        for i in range(n):
            j=(i+1)%n
            faces.extend([[i,j,stride+j,stride+i],[n+j,n+i,stride+n+i,stride+n+j],
                          [i,n+i,n+j,j],[stride+j,stride+n+j,stride+n+i,stride+i]])
        triangles=[[f[0],f[j],f[j+1]] for f in faces for j in range(1,len(f)-1)]
        m=trimesh.Trimesh(vertices=v,faces=triangles,process=False)
        if m.volume<0:m.invert()
        if not(m.is_watertight and m.is_winding_consistent and m.volume>0):
            raise ValueError('Invalid member segment: '+part['name'])
        out.append({'index':k,'mass_kg':float(m.volume*density),'position_world_m':m.center_mass.tolist()})
    full=mesh(part)
    if abs(sum(r['mass_kg'] for r in out)-full.volume*density)>1e-5:
        raise ValueError('Segment/full mass mismatch: '+part['name'])
    return out


def validate_member(part):
    data=part['structural_member'];n=len(data['outer_polygon_uv_m'])
    expected=hollow_section(data['outer_polygon_uv_m'],data['inner_polygon_uv_m'])
    for key in ('area_m2','Iuu_m4','Ivv_m4','Iuv_m4','median_enclosed_area_m2'):
        if not np.isclose(expected[key],data['section'][key],rtol=1e-7,atol=1e-14):
            raise ValueError('Section metadata mismatch: '+part['name']+' '+key)
    vertices=np.asarray(part['vertices_world_m'])
    if data.get('native_vertex_layout','').startswith('outer_station_0, outer_station_1'):
        vertices=vertices[np.r_[0:n,2*n:3*n,n:2*n,3*n:4*n]]
    predicted=[]
    for p,basis in zip(data['centerline_world_m'],data['station_basis_axis_u_v']):
        basis=np.asarray(basis)
        if not np.allclose(basis@basis.T,np.eye(3),atol=1e-10) or np.linalg.det(basis)<.999999:
            raise ValueError('Invalid member basis: '+part['name'])
        for polygon in (data['outer_polygon_uv_m'],data['inner_polygon_uv_m']):
            predicted.extend(np.asarray(p)+uv[0]*basis[1]+uv[1]*basis[2] for uv in polygon)
    error=float(np.max(np.abs(np.asarray(predicted)-vertices)))
    if error>1e-7:raise ValueError('Member metadata/native mesh disagreement: '+part['name'])
    return error


def add_contact_wrenches(force,moment,vertices,allocations,mask,point):
    active=allocations*mask
    forces=np.tile(force,(len(active),1));forces[:,2]+=active.sum(1)
    lever=np.cross(vertices-np.asarray(point),[0,0,1])
    moments=np.asarray(moment)+active@lever
    return forces,moments


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene',type=Path,default=ROBOT/'cad/source/appearance_c_scene.json')
    parser.add_argument('--settings',type=Path,default=ROBOT/'configs/structure_c14_spec.json')
    parser.add_argument('--output',type=Path,default=ROBOT/'evidence/structure_c14_screen.json')
    args=parser.parse_args();scene=json.loads(args.scene.read_text());settings=json.loads(args.settings.read_text())
    for item in scene['build_inputs']:
        if sha(ROOT/item['path'])!=item['sha256']:raise ValueError('Stale source input: '+item['path'])
    if sha(ROOT/scene['spec_path'])!=scene['spec_sha256']:
        raise ValueError('Scene/spec identity mismatch')
    if settings['appearance_spec']!=scene['spec_path']:
        raise ValueError('Structure/appearance spec mismatch')
    if not any(item['path']==str(args.settings.relative_to(ROOT)) and item['sha256']==sha(args.settings)
               for item in scene['build_inputs']):
        raise ValueError('Structure settings not bound to scene')
    spec=json.loads((ROOT/scene['spec_path']).read_text());parents,origins=topology(spec['points_world_m'])
    rows=ledger(scene,settings,parents)
    descendants={body:{body} for body in parents}
    for body in parents:
        parent=parents[body]
        while parent:
            descendants[parent].add(body);parent=parents[parent]
    sole_vertices={}
    for side in ('left','right'):
        sole=next(p for p in scene['parts'] if p['name']==side+'_black_ground_sole')
        v=np.asarray(sole['vertices_world_m']);bottom=v[v[:,2]<=v[:,2].min()+1e-7]
        polygon=bottom[ConvexHull(bottom[:,:2]).vertices]
        sole_vertices[side]=polygon
    members=[p for p in scene['parts'] if p.get('structural_member')]
    metadata_errors={p['name']:validate_member(p) for p in members}
    segments={p['name']:member_segments(p,settings['material']['density_kg_m3']) for p in members}
    cases=[]
    for mass_index,label in enumerate(('low','nominal','high')):
        for pressure in (0,2000,3000):
            cases.append((label+'_double_'+str(pressure),mass_index,pressure,1.0,('left','right')))
    cases.extend([('nominal_double_3000_factor_1_5',1,3000,1.5,('left','right')),
                  ('nominal_single_left_empty',1,0,1.0,('left',)),
                  ('nominal_single_left_3000',1,3000,1.0,('left',))])
    results=[];g=settings['screen_policy']['gravity_m_s2'];fy=settings['material']['minimum_yield_Pa']
    for name,index,pressure,multiplier,sides in cases:
        loads=[{'id':r['id'],'body':r['body'],'position_world_m':r['position_world_m'],
                'force_world_N':[0,0,-r['mass_range_kg'][index]*g*multiplier],
                'source_basis':r['basis']} for r in rows]
        if pressure:
            loads.append({'id':'external_crown_compression','body':'torso','position_world_m':[0,0,2.45],
                          'force_world_N':[0,0,-pressure*g*multiplier],
                          'source_basis':'user_tonnes_pressure_design_test_not_rated_payload'})
        vertices=np.concatenate([sole_vertices[s] for s in sides]);contact=normal_contacts(vertices,loads)
        total=sum(r['mass_range_kg'][index] for r in rows)
        com=np.average(np.array([r['position_world_m'] for r in rows]),axis=0,
                       weights=[r['mass_range_kg'][index] for r in rows])
        result={'id':name,'mass_range_index':index,'robot_conditional_mass_kg':total,
            'robot_COM_world_m':com.tolist(),'external_pressure_equivalent_kg':pressure,
            'load_multiplier':multiplier,'support_sides':list(sides),'contact':contact,
            'overall_gate':'blocked','physics_accepted':False}
        if not contact['feasible']:
            result['rejection']='Neutral mass/pressure resultant lies outside the active sole support. No hidden root support or ground torque added.'
            results.append(result);continue
        gravity_loads=list(loads)
        allocations=contact_extreme_allocations(vertices,gravity_loads)
        if not len(allocations):raise ValueError('Feasible contact has no extreme allocation')
        contact_bodies=[side+'_foot' for side in sides for _ in sole_vertices[side]]
        contact['extreme_allocation_count']=len(allocations)
        contact['extreme_normal_forces_N']=allocations.tolist()
        residuals=allocations@np.vstack([np.ones(len(vertices)),vertices[:,1],-vertices[:,0]]).T
        f0,m0=resultant(gravity_loads,[0,0,0]);target=[-f0[2],-m0[0],-m0[1]]
        contact['extreme_balance_max_abs_residual_N_or_Nm']=float(np.max(abs(residuals-target)))
        cursor=0
        for side in sides:
            for c in contact['contacts'][cursor:cursor+len(sole_vertices[side])]:
                c.update({'id':side+'_sole_contact','body':side+'_foot','source_basis':'unilateral_static_contact'})
                loads.append(c)
            cursor+=len(sole_vertices[side])
        joint=[]
        for body,parent in parents.items():
            if not parent:continue
            f,m=resultant([r for r in loads if r['body'] in descendants[body]],origins[body])
            gf,gm=resultant([r for r in gravity_loads if r['body'] in descendants[body]],origins[body])
            mask=np.array([b in descendants[body] for b in contact_bodies],float)
            allf,allm=add_contact_wrenches(gf,gm,vertices,allocations,mask,origins[body])
            worst=int(np.argmax(np.linalg.norm(allm,axis=1)))
            joint.append({'body':body,'parent':parent,'origin_world_m':origins[body],
                'force_world_N':f.tolist(),'moment_world_Nm':m.tolist(),
                'required_reaction_force_N':(-f).tolist(),'required_holding_moment_Nm':(-m).tolist(),
                'contact_envelope_force_min_max_N':[allf.min(0).tolist(),allf.max(0).tolist()],
                'contact_envelope_moment_min_max_Nm':[allm.min(0).tolist(),allm.max(0).tolist()],
                'contact_envelope_max_moment_norm_Nm':float(np.linalg.norm(allm[worst])),
                'worst_contact_allocation_index':worst,
                'drive_capacity_status':'unknown_no_holding_torque_supplied_automatically'})
        stress=[]
        for part in members:
            data=part['structural_member'];body=data['body'];distal=data['distal_body']
            if data.get('load_role')=='cover_mount_only_connection_unverified':
                stress.append({'member':part['name'],'status':'not_analyzed_cover_mount_payload_and_connection_required'})
                continue
            if part['name'].endswith('_sole_rail') or part.get('c14_primary_structure_segment')=='foot_base':
                stress.append({'member':part['name'],'status':'not_analyzed_plantar_plate_and_reaction_distribution_required'})
                continue
            path=np.asarray(data['centerline_world_m']);arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
            body_path=np.asarray(data.get('body_load_path_world_m',path))
            stations=[]
            for k,(point,basis) in enumerate(zip(path,data['station_basis_axis_u_v'])):
                relevant=[]
                for load in gravity_loads:
                    if load['id']==part['name']:continue
                    if load['body'] not in descendants[distal]:continue
                    # Child groups transfer at the end joint. Components on
                    # this rigid body attach at the closest beam location.
                    if distal==body and load['body']==body:
                        if projected_arc(load['position_world_m'],body_path)<projected_arc(point,body_path)-1e-8:continue
                    relevant.append(load)
                for segment in segments[part['name']][k:]:
                    relevant.append({'position_world_m':segment['position_world_m'],
                                     'force_world_N':[0,0,-segment['mass_kg']*g*multiplier]})
                f,m=resultant(relevant,point)
                mask=np.array([b in descendants[distal] for b in contact_bodies],float)
                allf,allm=add_contact_wrenches(f,m,vertices,allocations,mask,point)
                values=[nominal_section_stress(data['section'],data['outer_polygon_uv_m'],basis,
                        af,am,data['wall_m'],data['inner_polygon_uv_m']) for af,am in zip(allf,allm)]
                worst_index=max(range(len(values)),key=lambda i:values[i]['equivalent_stress_envelope_Pa'])
                value=values[worst_index]
                value.update({'station':k,'position_world_m':point.tolist(),
                              'worst_contact_allocation_index':worst_index,
                              'yield_margin':fy/max(value['equivalent_stress_envelope_Pa'],1e-9)})
                stations.append(value)
            worst=max(stations,key=lambda x:x['equivalent_stress_envelope_Pa'])
            stress.append({'member':part['name'],'status':'limited_nominal_elastic_screen',
                'worst_station':worst,'stations':stations,
                'nominal_margin_target_met':worst['yield_margin']>=settings['screen_policy']['nominal_yield_margin_target'],
                'strength_approved':False})
        result.update({'joint_wrench_demands':joint,'member_section_screens':stress,
            'max_required_holding_moment_norm_Nm':max(x['contact_envelope_max_moment_norm_Nm'] for x in joint),
            'analyzed_sections_nominal_target_met':all(x['nominal_margin_target_met'] for x in stress if 'nominal_margin_target_met' in x),
            'unanalysed_member_ids':[x['member'] for x in stress if 'nominal_margin_target_met' not in x],
            'complete_structural_target_verified':False,
            'contact_allocation_note':'Every basic feasible extreme allocation of this finite flat-sole normal-contact model evaluated; no favorable prescribed split. Compliance/pressure, dynamics and actual actuator capacity remain unverified.'})
        results.append(result)
    groups={}
    for row in rows:
        group=groups.setdefault(row['basis'],np.zeros(3));group+=row['mass_range_kg']
    report={'schema':'gorilla_primary_structure_screen_v1','robot_id':'gorilla_v0_1',
        'scene_path':str(args.scene.relative_to(ROOT)),'scene_sha256':sha(args.scene),
        'settings_path':str(args.settings.relative_to(ROOT)),'settings_sha256':sha(args.settings),
        'appearance_spec_path':scene['spec_path'],'appearance_spec_sha256':scene['spec_sha256'],
        'script_sha256':sha(Path(__file__)),'statics_library_sha256':sha(ROOT/'src/sai_agent/structural_statics.py'),
        'method':'Actual finite-wall stock volumes/inertia and native-ring section polygons; SI point-mass/reserve gravity loads; articulated subtree wrenches; all basic feasible contact allocations on actual flat soles; nominal elastic bending, sampled VQ/Ib and Bredt torsion. No fixed-root/foot finite-element result.',
        'mass_ranges_by_basis_kg':{k:v.tolist() for k,v in groups.items()},
        'conditional_robot_mass_range_kg':np.sum([r['mass_range_kg'] for r in rows],axis=0).tolist(),
        'mass_ledger':rows,'sole_contact_polygons_world_m':{k:v.tolist() for k,v in sole_vertices.items()},
        'structural_member_count':len(members),'cases':results,
        'section_native_mesh_max_reconstruction_difference_m':max(metadata_errors.values()),
        'mass_basis_note':'Untrimmed part-stock sum plus explicit reserves and conditional armor. Bend/socket overlaps not boolean-trimmed; assembly net mass/inertia not approved. Frame-side sockets are separately counted; complete drive/internal-bearing reserves exclude these stock parts.',
        'limitations':['Native section stations, not continuous stress extrema or bend/weld/bolt/seat FEA.',
            'Candidate reserves and armor density/thickness are not supplier-validated.',
            'Body attachment points projected onto primary path; full mount load paths still need design.',
            'Joint axes/stiffness, bearing and actuator continuous torque unknown.',
            'Fatigue, global/local buckling, flange rigidity and pressure-contact load sharing unverified.',
            'Neutral gravity only; no motion/thermal/power or free-root dynamic acceptance.'],
        'open_red_items':settings['open_items'],'structural_strength_accepted':False,
        'stable_physical_contract':False,'physics_accepted':False,'appearance_accepted':False}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'report':str(args.output),'structural_members':len(members),
        'conditional_robot_mass_range_kg':report['conditional_robot_mass_range_kg'],
        'cases':[{'id':x['id'],'contact_feasible':x['contact']['feasible'],
            'analyzed_sections_nominal_target_met':x.get('analyzed_sections_nominal_target_met'),
            'max_holding_moment_norm_Nm':x.get('max_required_holding_moment_norm_Nm')} for x in results],
        'physics_accepted':False}))


if __name__=='__main__':main()
