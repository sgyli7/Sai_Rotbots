#!/usr/bin/env python3
"""Check sampled native intake armor obstruction, never airflow or heat capacity.

The supplied complete scene is evaluated without mesh hiding. This diagnostic
uses the registered left artwork opening and the model's mirrored right opening.
"""
from pathlib import Path
import argparse
import json,hashlib
from collections import defaultdict
import numpy as np
from PIL import Image,ImageDraw


def main():
    root=Path(__file__).resolve().parents[2]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene',type=Path,default=root/'robots/gorilla_v0_1/cad/source/appearance_c_scene.json')
    parser.add_argument('--output',type=Path,default=root/'robots/gorilla_v0_1/evidence/appearance_c_intake_clearance.json')
    parser.add_argument('--artifact-dir',type=Path,default=root/'artifacts/gorilla_v0_1/appearance_c_intake_check')
    args=parser.parse_args()
    args.artifact_dir.mkdir(parents=True,exist_ok=True)
    ROOT=Path(__file__).resolve().parents[2]
    SCENE=args.scene.resolve()
    scene=json.loads(SCENE.read_text());parts=scene['parts']
    LANDMARKS=ROOT/'robots/gorilla_v0_1/source/appearance_c_reference_landmarks.json'
    landmark_bytes=LANDMARKS.read_bytes();landmarks=json.loads(landmark_bytes)
    SCALE=2.65/516;CX=325.5;GROUND=603
    profiles={v:{p['id']:p['global_uv_px'] for p in data['profiles']} for v,data in landmarks['views'].items()}
    opening=np.array(profiles['front']['left_vent_black_opening'],float)
    side_profile=np.array(profiles['left']['side_vent_ivory_mount'],float)

    def span(poly,v):
        xs=[]
        for a,b in zip(poly,np.roll(poly,-1,axis=0)):
            if abs(b[1]-a[1])<1e-10:
                if abs(v-a[1])<1e-9:xs.extend((a[0],b[0]))
            elif min(a[1],b[1])-1e-10<=v<=max(a[1],b[1])+1e-10:
                xs.append(a[0]+(v-a[1])*(b[0]-a[0])/(b[1]-a[1]))
        return min(xs),max(xs)

    def surface(v):
        return (971-span(side_profile,float(np.clip(v,161.15,222.85)))[0])*SCALE-.009

    def category(p):
        name=p['name']
        if 'radiator_louver' in name:return 'grille'
        if 'radiator_black_well' in name:return 'candidate_throat_wall'
        if 'radiator_turning_plenum' in name:return 'candidate_turning_plenum_wall'
        if 'radiator_ivory_socket' in name or 'radiator_gold_trim' in name or 'vent_fastener' in name:return 'intake_frame_or_fastener'
        c=np.array(p['rgba'])[:3]
        if c[2]>.50 and c[0]<.1:return 'blue_armor'
        if c[0]>.7 and c[1]>.7 and c[2]>.5:return 'ivory_armor'
        return 'other_geometry_not_classified_as_duct'

    def ray_part(part,y,z):
        v=np.array(part['vertices_world_m']);lo=v.min(0);hi=v.max(0)
        hits=defaultdict(list)
        ids=np.flatnonzero((y>=lo[1]-1e-10)&(y<=hi[1]+1e-10)&(z>=lo[2]-1e-10)&(z<=hi[2]+1e-10))
        if not len(ids):return hits
        yy,zz=y[ids],z[ids]
        # Exact -X intersections of every fan-triangulated native face. Both
        # orientations accepted; all hits are retained and depth sorted later.
        for fi,f in enumerate(part['faces']):
            for ti in range(1,len(f)-1):
                t=v[[f[0],f[ti],f[ti+1]]];q=t[:,1:3]
                den=(q[1,1]-q[2,1])*(q[0,0]-q[2,0])+(q[2,0]-q[1,0])*(q[0,1]-q[2,1])
                if abs(den)<1e-12:continue
                a=((q[1,1]-q[2,1])*(yy-q[2,0])+(q[2,0]-q[1,0])*(zz-q[2,1]))/den
                b=((q[2,1]-q[0,1])*(yy-q[2,0])+(q[0,0]-q[2,0])*(zz-q[2,1]))/den;c=1-a-b
                good=(a>=-1e-9)&(b>=-1e-9)&(c>=-1e-9)
                xx=a*t[0,0]+b*t[1,0]+c*t[2,0]
                for rid,x in zip(ids[good],xx[good]):hits[int(rid)].append({'x_m':float(x),'face_index':fi,'fan_triangle_index':ti-1})
        for rid in hits:
            ordered=sorted(hits[rid],key=lambda h:-h['x_m']);unique=[]
            for h in ordered:
                if not unique or abs(h['x_m']-unique[-1]['x_m'])>1e-7:unique.append(h)
            hits[rid]=unique
        return hits

    samples=[]
    for vv in np.arange(163.5,205,.5):
        left,right=span(opening,float(vv))
        for uu in np.arange(253.5,272,.5):
            # Margin avoids conflating an edge/frame ray with a central gap.
            if left+.70<=uu<=right-.70:
                samples.append((float(uu),float(vv)))
    uv=np.array(samples);base_y=(CX-uv[:,0])*SCALE;z=(GROUND-uv[:,1])*SCALE
    entry=np.array([surface(v)+.012 for v in uv[:,1]])
    report={'scene_sha256':hashlib.sha256(SCENE.read_bytes()).hexdigest(),'native_part_count':len(parts),'frozen_scene_path':str(SCENE.relative_to(ROOT)),
        'scene_build_inputs':scene['build_inputs'],'authority_sha256':scene['image_sha256'],'landmarks_sha256':hashlib.sha256(landmark_bytes).hexdigest(),
        'method':'All supplied native parts, every face fan triangle, exact -X ray. Complete-scene intersections retained, no visual mesh exclusions. Native cage only; Cycles-applied bevel tessellation not evaluated.',
        'front_source_mapping':{'scale_m_per_px':SCALE,'center_u_px':CX,'ground_v_px':GROUND},
        'entry_definition':'Original black-opening FRONT polygon, 0.70px edge margin, 0.50px raster. Entry X is the fitted source-side surface +12mm; well rear mouth is entry-72mm. Grille-gap rays exclude any sample intersecting an actual louver ahead of the entry.',
        'axial_depth_m':{'entry':0,'well_rear_mouth':.072,'analysis_window':[-.05,.220]},'appearance_or_thermal_accepted':False,'sides':{}}
    traces={};heat=[]
    for side,sign in [('left',1),('right',-1)]:
        all_hits=[[] for _ in samples]
        for p in parts:
            hit=ray_part(p,sign*base_y,z)
            for rid,values in hit.items():
                for h in values:
                    depth=float(entry[rid]-h['x_m'])
                    if -.05<=depth<=.220:
                        all_hits[rid].append({**h,'depth_from_entry_m':depth,'part':p['name'],'category':category(p)})
        gap=[];trace=[];grid=[]
        for rid,hits in enumerate(all_hits):
            hits.sort(key=lambda h:h['depth_from_entry_m'])
            blocked_grille=any(h['category']=='grille' and h['depth_from_entry_m']<.01 for h in hits)
            armor=[h for h in hits if h['category'] in ('blue_armor','ivory_armor') and h['depth_from_entry_m']<=.072+1e-6]
            inner_armor=[h for h in armor if h['depth_from_entry_m']>=-1e-6]
            legal=[h for h in hits if h['category'] in ('candidate_throat_wall','candidate_turning_plenum_wall')]
            record={'sample_id':rid,'source_uv_px':[uv[rid,0] if side=='left' else 2*CX-uv[rid,0],uv[rid,1]],'local_left_uv_px':uv[rid].tolist(),'world_yz_m':[float(sign*base_y[rid]),float(z[rid])],'entry_x_m':float(entry[rid]),'is_actual_grille_gap':not blocked_grille,'hits':hits}
            trace.append(record)
            if not blocked_grille:gap.append(rid)
            grid.append((rid,blocked_grille,bool(armor),bool(inner_armor),bool(legal)))
        by_part={}
        for rid in gap:
            for hit in all_hits[rid]:
                name=hit['part'];d=by_part.setdefault(name,{'category':hit['category'],'sample_ids':set(),'depths':[],'xs':[],'us':[],'vs':[]})
                d['sample_ids'].add(rid);d['depths'].append(hit['depth_from_entry_m']);d['xs'].append(hit['x_m']);d['us'].append(float(uv[rid,0]));d['vs'].append(float(uv[rid,1]))
        summary={}
        for name,d in by_part.items():
            summary[name]={'category':d['category'],'gap_ray_hit_count':len(d['sample_ids']),'depth_range_from_entry_m':[min(d['depths']),max(d['depths'])],'world_x_range_m':[min(d['xs']),max(d['xs'])],
                'local_left_uv_bbox_px':[min(d['us']),max(d['us']),min(d['vs']),max(d['vs'])]}
        bad=[rid for rid,g,a,i,l in grid if not g and a];inner_bad=[rid for rid,g,a,i,l in grid if not g and i]
        clear=[rid for rid,g,a,i,l in grid if not g and not a]
        examples=[]
        for ids,label in [(bad,'armor_hit'),(clear,'no_armor_in_throat_window')]:
            if ids:
                # Different vertical locations, to avoid six identical line hits.
                choose=sorted(ids,key=lambda rid:uv[rid,1]);selection=[choose[int(t*(len(choose)-1))] for t in (0,.25,.5,.75,1)]
                examples.extend({'label':label,**trace[i]} for i in sorted(set(selection)))
        report['sides'][side]={'polygon_sample_count':len(samples),'actual_grille_gap_ray_count':len(gap),'grille_ray_count':len(samples)-len(gap),'gap_rays_with_armor_ahead_or_within_throat':len(bad),'gap_rays_with_armor_strictly_inside_0_to_72mm':len(inner_bad),'gap_rays_without_armor_ahead_or_within_throat':len(clear),'part_hit_summary':summary,'examples':examples}
        traces[side]=trace;heat.append(grid)
    # Source-registered classification of all samples, not a replacement render.
    canvas=Image.new('RGB',(680,610),'white');draw=ImageDraw.Draw(canvas)
    for si,(side,sign) in enumerate([('left',1),('right',-1)]):
        xbase=si*340;draw.text((xbase+12,8),side.upper()+' -X NATIVE ENTRY RAYS',(0,0,0))
        for rid,g,a,i,l in heat[si]:
            u,v=uv[rid];x=xbase+30+int((u-248)*10);yy=35+int((v-161)*11)
            color=(100,100,100) if g else ((215,45,45) if a else (30,100,190))
            draw.rectangle((x-2,yy-2,x+2,yy+2),fill=color)
        draw.text((xbase+12,540),'gray=louver; red=armor <=72mm',(0,0,0));draw.text((xbase+12,560),'blue=gap with no armor <=72mm',(0,0,0));draw.text((xbase+12,580),'Blue still may hit candidate chamber wall',(0,0,0))
    image_path=args.artifact_dir/"intake_ray_map.png";canvas.save(image_path)
    trace_path=args.artifact_dir/"intake_ray_traces.json";trace_path.write_text(json.dumps({'scene_sha256':report['scene_sha256'],'sides':traces},indent=2))
    report['trace_file_sha256']=hashlib.sha256(trace_path.read_bytes()).hexdigest();report['ray_map_sha256']=hashlib.sha256(image_path.read_bytes()).hexdigest()
    report['limitation']='Geometric source cage check only. Candidate duct walls are distinguished by actual part names and construction, not proven airflow. A rear chamber wall is a legitimate geometric turn surface, not an open axial exhaust. Side outlet continuity and heat transfer are not evaluated.'
    report['schema']='gorilla_sampled_intake_armor_clearance_v1'
    report['checker_path']=str(Path(__file__).resolve().relative_to(ROOT))
    report['checker_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report['sampling_scope']='Right uses the mirrored registered left opening, matching current model symmetry; it is not an independently traced original-right contour. No sub-grid or bevel guarantee.'
    report['sampled_intake_armor_clearance_pass']=all(d['gap_rays_with_armor_ahead_or_within_throat']==0 for d in report['sides'].values())
    report['physics_accepted']=False
    report['thermal_accepted']=False
    report['artifact_files']={'traces':str(trace_path.resolve()),'ray_map':str(image_path.resolve())}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'report':str(args.output.resolve()),'scene_sha256':report['scene_sha256'],'native_part_count':len(parts),'sampled_intake_armor_clearance_pass':report['sampled_intake_armor_clearance_pass'],'gap_samples_per_side':{s:d['actual_grille_gap_ray_count'] for s,d in report['sides'].items()},'armor_hit_samples_per_side':{s:d['gap_rays_with_armor_ahead_or_within_throat'] for s,d in report['sides'].items()},'physics_accepted':False,'thermal_accepted':False}))
    raise SystemExit(0 if report['sampled_intake_armor_clearance_pass'] else 1)


if __name__=='__main__':main()
