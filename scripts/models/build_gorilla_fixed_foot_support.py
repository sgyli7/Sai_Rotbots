#!/usr/bin/env python3
"""Rebuild the Gorilla fixed-side foot support B candidate into local artifacts.

The frozen B candidate is an input to the separate whole-frame builder. This
portable entry does not replace or re-sign that published candidate. Its local
force report retains the original Internal A sensitivity assumptions, and is
not the current whole-robot B statics report.

Runtime extras: numpy, trimesh, shapely, mapbox-earcut and Pillow. CLI help needs
only Python's standard library. Example:
  uv run --no-project --with numpy --with trimesh --with shapely \
    --with mapbox-earcut --with pillow python scripts/models/build_gorilla_fixed_foot_support.py
"""
from __future__ import annotations

import argparse
import copy
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / 'artifacts/gorilla_v0_1/fixed_foot_support_b'
OUT = DEFAULT_OUTPUT
BASE_SHA = '7a1e49f45838303ca5fd86265dc9980c10cde85ed7626424136afd3863aa5886'
ORIGINAL_PRODUCER_SHA256 = '0a586959b701c84648b18d06a2189978dd0d5f8b6e3b2c130795f5157a357238'
FROZEN_B_CANDIDATE_SHA256 = '064b2e178343a49ed80e64351c054e5e319c5fa03919824759b649bb816351bd'
RHO = 7850.0


def reference_path(path):
    """Repository-relative inside the checkout; absolute for external outputs."""
    path = Path(path).resolve()
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def load_runtime():
    """Keep optional geometry dependencies out of the CLI/help import path."""
    global np, trimesh, Polygon, Image, ImageDraw, relation, transformed, triangles, mesh
    try:
        import numpy as np
        import trimesh
        from shapely.geometry import Polygon
        from PIL import Image, ImageDraw
        sys.path.insert(0, str(ROOT / 'scripts/evaluation'))
        from check_gorilla_composite_foot import relation, transformed, triangles, mesh
    except ImportError as exc:
        raise RuntimeError('Geometry runtime requires numpy, trimesh, shapely, '
                           'mapbox-earcut and Pillow; see the command in --help.') from exc


def validate_output_directory(path, parser):
    """Generated products cannot overwrite source, controlled inputs or snapshots."""
    path = Path(path).resolve()
    if path.is_relative_to(ROOT) and not any(
        path.is_relative_to(ROOT / parent) for parent in ('artifacts', '.scratch')
    ):
        parser.error('--output-dir inside this repository must be under artifacts/ or .scratch/')
    for name in ('native_screen.json', 'local_free_body.json', 'material_mass.json',
                 'candidate_scene.json', 'neutral_left_native.png',
                 'folded_left_native.png', 'mechanism_left_native.png', 'foot_candidate.json'):
        output = path / name
        if output.is_symlink():
            parser.error('Refusing symlink output: ' + str(output))
    return path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False)+'\n')


def volume_com(part):
    m = mesh(part)
    return float(m.volume), m.center_mass.tolist()


def bounds(part):
    v = np.asarray(part['vertices_world_m'])
    return [v.min(0).tolist(), v.max(0).tolist()]


def new_part(template, name, vertices, faces, side, note, component):
    part = copy.deepcopy(template)
    for key in ('structural_member', 'face_rgba', 'ring_vertex_count',
                'longitudinal_sharp_ring_indices', 'sharp_surface_edge_pairs'):
        part.pop(key, None)
    part.update({'name': name, 'body': side+'_foot', 'role': 'primary_structure_candidate',
                 'vertices_world_m': np.asarray(vertices).tolist(), 'faces': [list(map(int,f)) for f in faces],
                 'rgba': [.22,.24,.25,1.0], 'edge_bevel_m': 0, 'structure_view_visible': True,
                 'surface_shading': 'mechanical_smooth', 'hardware': True, 'note': note,
                 'physical_mass_assigned': False, 'geometry_accepted': False, 'physics_accepted': False,
                 'composite_foot_group': 'arch', 'display_only_body': False,
                 'internal_b_foot_component': component,
                 'material_candidate': {'family': 'steel_candidate_not_selected_grade',
                                        'density_kg_m3': RHO, 'density_basis': 'Internal A stock density assumption',
                                        'yield_strength_Pa': None, 'material_qualified': False},
                 'physical_parent_body': side+'_foot',
                 'composite_foot_interface_candidate': 'Real face/bores candidate only; machining, weld/bolt, bearing fit and lock force not approved'})
    return part


def box_member(template, name, side, a, b, width, depth, wall):
    """Actual rectangular hollow material; width X, depth Z, axis Y."""
    a, b = np.array(a), np.array(b)
    length = np.linalg.norm(b-a)
    tangent = (b-a)/length
    u = np.array([1.,0,0]); v = np.cross(tangent, u)
    outer = np.array([[-width/2,-depth/2],[width/2,-depth/2],[width/2,depth/2],[-width/2,depth/2]])
    inner = np.array([[-width/2+wall,-depth/2+wall],[width/2-wall,-depth/2+wall],
                      [width/2-wall,depth/2-wall],[-width/2+wall,depth/2-wall]])
    vertices = [p+q[0]*u+q[1]*v for p in (a,b) for profile in (outer,inner) for q in profile]
    faces=[]
    for i in range(4):
        j=(i+1)%4
        faces.extend([[i,j,8+j,8+i],[4+j,4+i,12+i,12+j],
                      [i,4+i,4+j,j],[8+j,12+j,12+i,8+i]])
    area = width*depth-(width-2*wall)*(depth-2*wall)
    inertia_u = (width*depth**3-(width-2*wall)*(depth-2*wall)**3)/12
    inertia_v = (depth*width**3-(depth-2*wall)*(width-2*wall)**3)/12
    p = new_part(template,name,vertices,faces,side,'Finite-wall fixed short box; stops are separate supported contact blocks, not a full sole.', 'closed_short_box')
    p['structural_member']={'id':name,'body':side+'_foot','distal_body':side+'_foot',
        'centerline_world_m':[a.tolist(),b.tolist()], 'body_load_path_world_m':[a.tolist(),b.tolist()],
        'station_basis_axis_u_v':[[tangent.tolist(),u.tolist(),v.tolist()]]*2,
        'outer_polygon_uv_m':outer.tolist(),'inner_polygon_uv_m':inner.tolist(),
        'wall_m':wall,'perforations':False,
        'section':{'area_m2':area,'Iu_m4':inertia_u,'Iv_m4':inertia_v,'Iuv_m4':0.0},
        'connections_status':'Flush end plate / stop underside contacts declared; joints unqualified',
        'screen_scope':'Material geometry/volume only; no section/assembly capacity acceptance'}
    p['analytic_material_volume_m3']=area*length
    return p


def yoke(template, name, side, direction, pivot):
    # X,Z contour includes the true crossmember end, the old arch-boss region,
    # and both separate stop bracket ends. It stays above the split sole skins.
    px = pivot[0]
    outer = np.array([[-.050,.035],[-.098,.035],[-.105,.045],[-.137,.045],[-.137,.132],
                      [-.137,.177],[-.106,.198],[-.036,.198],[-.036,.174],
                      [-.050,.157],[-.052,.099],[-.050,.064]])
    # Values are world X in the frozen C15 source; shift by actual pivot X.
    outer[:,0] += px-(-.106)
    circle = np.array([[px+.023*math.cos(t),.124+.023*math.sin(t)]
                       for t in np.arange(64)*2*math.pi/64])
    guide_x = px+.033
    slot = np.array([[guide_x-.012,.072],[guide_x+.012,.072],
                     [guide_x+.012,.088],[guide_x-.012,.088]])
    polygon = Polygon(outer, holes=[circle,slot])
    if not polygon.is_valid:
        raise ValueError('Invalid yoke profile')
    local = trimesh.creation.extrude_polygon(polygon, height=.014, engine='earcut')
    v = np.c_[local.vertices[:,0], pivot[1]+direction*(.180+local.vertices[:,2]), local.vertices[:,1]]
    f = local.faces[:,::-1] if direction>0 else local.faces
    p = new_part(template,name,v,f,side,'14mm finite steel cheek with a real 46mm axle bore and 24x16mm lock withdrawal through-slot. Not a filled sole or monolithic foot.', 'pierced_side_yoke')
    p['plate_geometry']={'outer_profile_xz_m':outer.tolist(),'holes_xz_m':[circle.tolist(),slot.tolist()],
                         'thickness_m':.014,'net_profile_area_m2':float(polygon.area),
                         'analytic_material_volume_m3':float(polygon.area*.014),
                         'density_kg_m3':RHO,'axis_bore_diameter_m':.046,
                         'variable_ligament_and_holes_require_local_analysis':True}
    p['analytic_material_volume_m3']=float(polygon.area*.014)
    p['integrated_heel_guide_candidate']={'center_xz_m':[guide_x,.080], 'slot_width_height_m':[.024,.016],
                                        'tongue_edge_layout_clearance_m':.002,'actuator_or_retainer_selected':False}
    return p


def liner(template,name,side,direction,pivot):
    n=64;vertices=[]
    for r in (.023,.0218):
        for q in (.180,.194):
            vertices.extend(pivot+[r*math.cos(t),direction*q,r*math.sin(t)] for t in np.arange(n)*2*math.pi/n)
    faces=[]
    for i in range(n):
        j=(i+1)%n
        faces.extend([[i,j,n+j,n+i],[3*n+i,3*n+j,2*n+j,2*n+i],
                      [j,i,2*n+i,2*n+j],[n+i,n+j,3*n+j,3*n+i]])
    if direction<0:faces=[f[::-1] for f in faces]
    faces=[f[::-1] for f in faces]
    p=new_part(template,name,vertices,faces,side,'14mm-long finite liner: same polygonal OD as cheek bore, pin radial layout clearance 0.3mm. Fit/material/lubrication/retention unselected.', 'axle_liner')
    p['analytic_material_volume_m3']=n/2*math.sin(2*math.pi/n)*(.023**2-.0218**2)*.014
    p['bearing_candidate']={'outer_radius_m':.023,'inner_radius_m':.0218,'length_m':.014,
                            'pin_outer_radius_m':.0215,'radial_layout_gap_m':.0003,
                            'outer_interface':'Coincident OD/hole surface, candidate fitted interface; not a certified interference fit',
                            'shaft_retention_unverified':True}
    return p


def apply_fixed_support_candidate(scene):
    result=copy.deepcopy(scene);byname={p['name']:p for p in scene['parts']}
    new,removed,interfaces=[],[],[]
    for side in ('left','right'):
        template=byname[side+'_composite_arch_crossbeam']
        pivot=np.array(template['composite_foot_pivot_world_m']);y=pivot[1]
        name=side+'_composite_arch_crossbeam';removed.append(name)
        p=box_member(template,name,side,[pivot[0]+.035,y-.180,.190],[pivot[0]+.035,y+.180,.190],.070,.040,.005)
        new.append(p)
        for direction,label in ((-1,'negative_y'),(1,'positive_y')):
            base=side+'_composite_'+label
            for ending in ('_arch_boss','_arch_support','_heel_lock_guide'):
                removed.append(base+ending)
            plate=yoke(template,side+'_b_'+label+'_fixed_arch_yoke',side,direction,pivot);new.append(plate)
            journal=liner(template,side+'_b_'+label+'_fixed_axis_liner',side,direction,pivot);new.append(journal)
            interfaces.append({'id':side+'_'+label+'_beam_yoke','parts':[name,plate['name']],
                               'kind':'flush planar end / cheek inner face',
                               'plane_axis':'Y','plane_world_m':float(y+direction*.180),
                               'joining_process':'Unqualified bolted/welded end attachment; no material penetration used as proof'})
            interfaces.append({'id':side+'_'+label+'_liner_bore','parts':[plate['name'],journal['name']],
                               'kind':'coincident polygonal cylinder liner OD / cheek bore',
                               'joining_process':'Fitted liner attachment unknown; no preload/holding/friction model'})
            for group,stop_x,stop_bottom,inner_offset in (('forefoot',pivot[0]+.030,.051,.097),
                                                         ('heel',pivot[0]-.025,.053,.135)):
                bracket_name=base+'_'+group+'_stop_bracket'
                center_z=stop_bottom-.009
                if group=='forefoot':
                    removed.append(bracket_name)
                    member=box_member(template,bracket_name,side,[stop_x,y+direction*.180,center_z],
                                      [stop_x,y+direction*inner_offset,center_z],.044,.018,.006)
                    new.append(member)
                stop_name=base+'_'+group+'_neutral_stop';removed.append(stop_name)
                stop=copy.deepcopy(byname[stop_name]);stop.update({'role':'primary_structure_candidate',
                    'material_candidate':copy.deepcopy(plate['material_candidate']), 'structure_view_visible':True,
                    'internal_b_foot_component':'unchanged_geometry_neutral_stop', 'physical_mass_assigned':False})
                new.append(stop)
                interfaces.extend([{'id':side+'_'+label+'_'+group+'_yoke_bracket','parts':[plate['name'],bracket_name],
                                    'kind':'flush planar bracket end / cheek inner face','plane_axis':'Y',
                                    'plane_world_m':float(y+direction*.180),'joining_process':'End attachment unresolved'},
                                   {'id':side+'_'+label+'_'+group+'_bracket_stop','parts':[bracket_name,stop_name],
                                    'kind':'flat short-box upper face / exact stop underside' if group=='forefoot' else 'Inherited C15 fixed material overlap; not a certified join','plane_axis':'Z',
                                    'plane_world_m':stop_bottom,'joining_process':'Weld/bolt/supported contact undefined'}])
    if any(name not in byname for name in removed):raise ValueError('Stale C15 source parts')
    result['parts']=[p for p in result['parts'] if p['name'] not in set(removed)]+new
    result['checkpoint_id']='gorilla_internal_b_foot_fixed_support_scratch'
    result['geometry_accepted']=False;result['physics_accepted']=False
    return result,new,removed,interfaces


def native_screen(scene,new_parts,interfaces):
    added={p['name'] for p in new_parts};parts=[p for p in scene['parts'] if 'composite_foot_group' in p]
    same_group_allowed={frozenset(q['parts']) for q in interfaces}
    topology=[]
    for p in new_parts:
        m=mesh(p);analytic=p.get('analytic_material_volume_m3')
        topology.append({'name':p['name'],'closed':bool(m.is_watertight),'consistent_winding':bool(m.is_winding_consistent),
                         'positive_material_volume':bool(m.volume>0),'volume_m3':float(m.volume),
                         'analytic_volume_m3':analytic,'volume_delta_m3':None if analytic is None else float(m.volume-analytic)})
    poses=[]
    for side in ('left','right'):
        for folded in (False,True):
            posed=transformed(parts,side,folded);contacts=[];fixed=[];allowed=[];joint=[]
            expected_stops={frozenset((side+'_composite_'+flank+'_'+segment+'_rotor',
                                      side+'_composite_'+flank+'_'+group+'_neutral_stop'))
                            for flank in ('negative_y','positive_y') for segment,group in (('fore','forefoot'),('heel','heel'))}
            for i,a in enumerate(posed):
                av=np.array(a['vertices_world_m'])
                for b in posed[i+1:]:
                    if not (a['name'] in added or b['name'] in added):continue
                    bv=np.array(b['vertices_world_m'])
                    if np.any(av.max(0)<bv.min(0)-1e-8) or np.any(bv.max(0)<av.min(0)-1e-8):continue
                    rel=relation(a,b)
                    if not (rel['surface_touch_or_crossing_triangle_pairs'] or rel['strict_material_vertex_containment_count']):continue
                    key=frozenset(rel['parts'])
                    if not folded and key in expected_stops and rel['strict_material_vertex_containment_count']==0:allowed.append(rel)
                    elif key in same_group_allowed and rel['strict_material_vertex_containment_count']==0:joint.append(rel)
                    elif a['composite_foot_group']!=b['composite_foot_group']:contacts.append(rel)
                    else:fixed.append(rel)
            poses.append({'id':side+('_unloaded_fold' if folded else '_neutral'),
                          'angles_deg':{'forefoot':-15 if folded else 0,'heel':10 if folded else 0},
                          'locks_withdrawn':folded,'new_vs_native_unexpected_cross_group_contacts':contacts,
                          'unclassified_new_vs_fixed_contacts':fixed,'declared_flush_candidate_interfaces':joint,
                          'expected_stop_contacts':allowed,
                          'scope':'Actual native triangles and material-vertex containment for new/replaced vs all C15 foot parts; inherited unrelated contacts are not rerun.'})
            print(poses[-1]['id'],'cross',len(contacts),'fixed',len(fixed),flush=True)
    return {'robot_id':'gorilla_v0_1','topology':topology,'poses':poses,
            'continuous_sweep_checked':False,'physics_accepted':False}


def local_forces(scene,budget):
    byname={p['name']:p for p in scene['parts']};output=[]
    pivot=np.array(byname['left_composite_arch_pin']['composite_foot_pivot_world_m'])
    fore_poly=np.array(byname['left_composite_forepad']['vertices_world_m'])
    heel_poly=np.array(byname['left_composite_heel_pad']['vertices_world_m'])
    # CoP choices are sensitivities, not validated support states. Each segment
    # has its own lower stop; do not apply the total ground force to both.
    cops={'forefoot_rear':.025,'forefoot_mid':.20,'forefoot_front':float(fore_poly[:,0].max()),
          'heel_mid':-.27,'heel_rear':float(heel_poly[:,0].min())}
    for route,data in budget['routes'].items():
        force_range=data['separate_3000kg_pressure_demand_static_normal_load_N']
        for split in (.5,1.0):
            for case,cop in cops.items():
                group='forefoot' if case.startswith('forefoot') else 'heel'
                offset=.030 if group=='forefoot' else -.025
                source_load=np.array(force_range)*split
                lever=cop-pivot[0]
                stop_force=source_load*abs(lever/offset)
                pin_force=stop_force-source_load
                output.append({'route':route,'foot_fraction_of_total_static_demand':split,'CoP_world_x_m':cop,
                    'segment_load_case':case,'force_range_low_nominal_high_N':source_load.tolist(),
                    'pitch_moment_about_low_foot_axis_Nm':(source_load*lever).tolist(),
                    'assumed_compressive_stop_lever_m':abs(offset),
                    'stop_force_on_rotating_segment_N':(stop_force*(-1)).tolist(),
                    'pin_vertical_force_on_rotating_segment_N':pin_force.tolist(),
                    'equal_paired_stop_reaction_per_side_N':(stop_force/2).tolist(),
                    'paired_yoke_stop_vertical_input_N':(stop_force/2).tolist(),
                    'paired_yoke_pin_vertical_input_N':(-pin_force/2).tolist(),
                    'paired_yoke_upper_mount_vertical_reaction_N':(-source_load/2).tolist(),
                    'paired_yoke_force_balance_residual_N':((stop_force-pin_force-source_load)/2).tolist(),
                    'low_axis_ground_torque_world_Nm':[[0,float(-q*lever),0] for q in source_load],
                    'upper_mount_world_x_m':float(pivot[0]+.035),
                    'paired_yoke_upper_mount_required_pitch_couple_world_Y_Nm':(source_load*(cop-(pivot[0]+.035))/2).tolist(),
                    'mount_couple_scope':'Required ideal mount couple to close local free-body balance, not an ankle drive/brake rating.',
                    'pin_span_load_distribution':'Unsolved: actual rotor/liner Y positions need multi-support shaft bending/contact model',
                    'lock_load_role':'No primary compressive load credit assigned; lock/guide must resist reverse/unseating torque and fault cases independently',
                    'force_balance_residual_N':(source_load-stop_force+pin_force).tolist(),
                    'moment_balance_residual_Nm':(source_load*lever-stop_force*abs(offset)*(1 if lever>0 else -1)).tolist()})
    return {'robot_id':'gorilla_v0_1','gravity_m_s2':9.80665,'pressure_request_kg':3000,
        'pressure_scope':'A original static demand includes gross robot stock+module mass plus 3000kg external pressure, not 3t payload or certified support.',
        'cases':output,'equations':'R_stop = F_segment * abs((CoP_x-pivot_x)/r_stop); R_pin = R_stop-F_segment. Pair split 50/50 assumed only.',
        'assumptions':['Ground reaction vertical only; no full robot contact feasibility or horizontal/inertial load.',
                       'All load assigned to one selected segment as a local worst-case sensitivity; actual fore/heel force split unresolved.',
                       'Stop lever uses current block center; actual positive contact centroid and pressure distribution unassigned.',
                       'Reaction equal between side cheeks assumed; transverse CoP and torsion require independent checks.',
                       'Welds, bolted faces, bush contact/fits, pin retention and brace/bore stress concentrations unverified.'],
        'not_a_strength_screen':True,'physics_accepted':False}


def native_image(parts,path,folded=False,mechanism=False):
    posed=transformed(parts,'left',folded)
    hidden=[]
    if mechanism:
        hidden=[p['name'] for p in posed if p['role'] in ('armor_cover','armor_surface','contact_surface_candidate')]
        posed=[p for p in posed if p['name'] not in hidden]
    size=(1100,620);margin=55;scale=970;center_x=.035;center_z=.16
    image=Image.new('RGB',size,'white');draw=ImageDraw.Draw(image)
    screen=lambda v:(size[0]/2-(v[0]-center_x)*scale,size[1]/2-(v[2]-center_z)*scale)
    faces=[]
    for p in posed:
        v=np.array(p['vertices_world_m']);color=p['rgba'][:3]
        if p.get('internal_b_foot_component') in ('pierced_side_yoke','closed_short_box','axle_liner'):color=[.80,.45,.14]
        for f in p['faces']:
            q=v[f];faces.append((q[:,1].mean(),q,tuple(int(c*255) for c in color)))
    for depth,q,color in sorted(faces,key=lambda x:x[0]):draw.polygon([screen(v) for v in q],fill=color,outline=(40,45,50))
    title='GORILLA internal B fixed-side foot | '+('unloaded -15/+10' if folded else 'neutral')+(' | mechanism isolation' if mechanism else ' | all foot parts')
    draw.text((18,16),title,fill=(25,38,49));draw.text((18,38),'Actual native mesh projection; candidate in amber. No smoothing, no geometry/strength acceptance.',fill=(25,38,49))
    draw.line([screen(np.array([-.47,0,0])),screen(np.array([.55,0,0]))],fill=(70,75,80),width=2)
    image.save(path)
    return {'path':reference_path(path),'sha256':sha(path),'camera':'orthographic +Y, fixed scale 970px/m',
            'hidden_part_names':hidden,'palette_note':'Amber diagnostic color for new support parts only; no source material/shape change'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    global OUT
    parser.add_argument('--scene', type=Path,
                        default=ROOT/'experiments/gorilla_v0_1/appearance_c_round_fifteen/appearance_c_scene.json',
                        help='Frozen C15 native scene; its hash is required.')
    parser.add_argument('--budget', type=Path,
                        default=ROOT/'robots/gorilla_v0_1/evidence/internal_architecture_a_budget.json',
                        help='Original A sensitivity budget, not whole-robot B statics.')
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT,
                        help='Generated local products; defaults to ignored artifacts/gorilla_v0_1/fixed_foot_support_b.')
    args=parser.parse_args()
    OUT=validate_output_directory(args.output_dir, parser)
    args.scene=args.scene.resolve()
    load_runtime()
    if sha(args.scene)!=BASE_SHA:raise ValueError('Unexpected C15 input version')
    scene=json.loads(args.scene.read_text());candidate,new,removed,interfaces=apply_fixed_support_candidate(scene)
    OUT.mkdir(parents=True, exist_ok=True)
    checks=native_screen(candidate,new,interfaces)
    budget_path=args.budget.resolve()
    forces=local_forces(candidate,json.loads(budget_path.read_text()))
    original={p['name']:p for p in scene['parts']};rows=[]
    for p in new:
        volume,com=volume_com(p);rows.append({'name':p['name'],'volume_m3':volume,'mass_kg_at_7850':volume*RHO,
                                            'COM_world_m':com,'bounds_world_m':bounds(p),'role':p['role']})
    removed_rows=[]
    for name in removed:
        volume,com=volume_com(original[name]);removed_rows.append({'name':name,'volume_m3':volume,
            'counterfactual_mass_kg_if_steel':volume*RHO,'original_role':original[name]['role']})
    mass={'robot_id':'gorilla_v0_1','density_kg_m3':RHO,'new_parts':rows,'removed_parts':removed_rows,
          'new_material_net_volume_m3':sum(r['volume_m3'] for r in rows),
          'new_material_mass_kg':sum(r['mass_kg_at_7850'] for r in rows),
          'removed_material_volume_m3':sum(r['volume_m3'] for r in removed_rows),
          'geometric_delta_mass_kg_all_removed_assumed_steel':sum(r['mass_kg_at_7850'] for r in rows)-sum(r['counterfactual_mass_kg_if_steel'] for r in removed_rows),
          'baseline_A_stock_delta_mass_kg':sum(r['mass_kg_at_7850'] for r in rows)-sum(r['counterfactual_mass_kg_if_steel'] for r in removed_rows if r['original_role'].startswith('primary_structure')),
          'scope':'Each candidate part is a true material mesh, including real bores and slots. No unproved mass credit for old excluded visible-mechanism proxies. Union of remaining C15 stock/contacts must be performed by root; this is not final assembly net mass.'}
    write(OUT/'native_screen.json',checks);write(OUT/'local_free_body.json',forces);write(OUT/'material_mass.json',mass)
    write(OUT/'candidate_scene.json',candidate)
    images=[native_image(candidate['parts'],OUT/'neutral_left_native.png'),
            native_image(candidate['parts'],OUT/'folded_left_native.png',True),
            native_image(candidate['parts'],OUT/'mechanism_left_native.png',False,True)]
    unchanged=[p['name'] for p in scene['parts'] if p['name'] not in set(removed)]
    candidate_byname={p['name']:p for p in candidate['parts']}
    exact=all(original[name]==candidate_byname[name] for name in unchanged)
    manifest={'schema':'gorilla_internal_b_foot_candidate_v1','robot_id':'gorilla_v0_1','base_commit':'16b3813fcc286c3662134399b4ff10bc18ffb690',
        'base_scene_path':reference_path(args.scene),'base_scene_sha256':BASE_SHA,
        'builder_path':reference_path(Path(__file__)),'builder_sha256':sha(Path(__file__)),
        'original_producer_sha256':ORIGINAL_PRODUCER_SHA256,
        'frozen_b_candidate_sha256':FROZEN_B_CANDIDATE_SHA256,
        'migration_scope':'Portable own-source entry; local outputs are newly generated products, not a re-signature or replacement of the frozen B candidate.',
        'reissues_frozen_candidate':False,
        'original_A_sensitivity_budget_path':reference_path(budget_path),
        'original_A_sensitivity_budget_sha256':sha(budget_path),
        'new_parts':new,'removed_part_names':removed,'declared_interfaces':interfaces,
        'replaced_part_names':[p['name'] for p in new if p['name'] in set(removed)],
        'unmodified_original_parts_exact':exact,'upper_ankle_socket_geometry_not_modified':True,
        'foot_axis_world':[0,1,0],'foot_axis_pivot_world_m_by_side':{side:original[side+'_composite_arch_pin']['composite_foot_pivot_world_m'] for side in ('left','right')},
        'endpoint_check_report_path':reference_path(OUT/'native_screen.json'),
        'material_report_path':reference_path(OUT/'material_mass.json'),
        'free_body_report_path':reference_path(OUT/'local_free_body.json'),
        'source_reports_sha256':{p.name:sha(p) for p in (OUT/'native_screen.json',OUT/'material_mass.json',OUT/'local_free_body.json')},
        'images':images,'geometry_accepted':False,'physics_accepted':False,
        'remaining_unknowns':['Selected steel grade/material fatigue/buckling/bore and slot stress concentrations.',
                              'Declared contact faces are geometric mating candidates; weld/bolt method/fasteners/preload are not defined.',
                              'C15 socket/stem/crossbeam central joint and residual within-group stock overlaps remain unqualified. Old heel short brackets are preserved to retain endpoint clearance; their existing stop overlaps are not proof of a joint.',
                              'Current fixed hollow pin retention and per-bearing shaft bending/contact are unresolved.',
                              'Forefoot tongue guide mounting/actuator/reversal-lock load path remains incomplete; heel guide is integrated but actuator/retention unassigned.',
                              'Stops have a short 25/30mm torque arm: local FBD amplification is substantial and requires root architecture/capacity decision.',
                              'The 0.285m leg ankle output shaft/bearings are separate from this 0.124m low folding foot axis.',
                              'Neutral and unloaded endpoints only; no continuous sweep, actual contacts, engine or 3t strength validation.']}
    write(OUT/'foot_candidate.json',manifest)
    print(json.dumps({'candidate':str(OUT/'foot_candidate.json'),'new_parts':len(new),'removed':len(removed),
                      'new_mass_kg':mass['new_material_mass_kg'],'geometric_mass_delta_kg':mass['geometric_delta_mass_kg_all_removed_assumed_steel'],
                      'unmodified_exact':exact,'all_new_closed_positive':all(t['closed'] and t['consistent_winding'] and t['positive_material_volume'] for t in checks['topology'])}))


if __name__=='__main__':main()
