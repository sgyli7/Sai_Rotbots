"""ECAD-derived package envelopes in the existing raw-mm PCB reserve.

Purchased packages are dimension envelopes, never printable replacement parts.
No board/protection mass is invented or written into the frozen hardware SI.
"""
from pathlib import Path
import hashlib
import itertools
import json
import sys

import numpy as np
import trimesh
from build123d import Compound, export_brep, export_step, import_brep, import_step

ROOT=Path(__file__).resolve().parents[2]
R=ROOT/'robots/Goose_V0.1'
sys.path.insert(0,str(ROOT/'scripts/cad'))
from build_goose_cad import box,cylinder,transform
from build_goose_actuator_interfaces import quad_sampling
from sai_agent.native_cad_query import native_solid_integrity


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    config=R/'configs/brake_pcb_candidate.json';cfg=json.loads(config.read_text())
    directory=R/'cad/source/brake_pcb_candidate';directory.mkdir(parents=True,exist_ok=True)
    out=R/'cad/exports/brake_pcb_candidate';out.mkdir(parents=True,exist_ok=True)
    rot=np.array([[0,0,1],[1,0,0],[0,1,0]],float)
    origin=np.array([101.4,-40,265.])
    board=box([80,50,1.6],[40,25,.8])
    for x,y in cfg['mounting_holes_mm'].values():board-=cylinder(1.6,3,[x,y,.8])
    solids={'pcb_finished_board_envelope':board};roles={'pcb_finished_board_envelope':'pcb_reference'}
    for p in cfg['components']:
        if p['kind']=='external_resistor':continue
        f=cfg['footprints'][p['footprint']];x,y=cfg['placements_mm'][p['ref']]
        x0,y0,x1,y1=f['body_bounds_mm'];h=f['max_height_mm']
        shape=box([x1-x0,y1-y0,h],[x+(x0+x1)/2,y+(y0+y1)/2,1.6+h/2])
        role='graphite'
        if p['footprint']=='f12':
            # Maximum base width and cylinder diameter, not just nominal D10.
            shape=box([10.5,10.5,1.0],[x,y,2.1])+cylinder(5.25,h-1,[x,y,2.6+(h-1)/2])
            role='titanium'
        if p['kind']=='connector':role='orange'
        key='pcb_'+p['ref'].lower();solids[key]=shape;roles[key]=role
    parts=[];native=[];world={};reserve_min=np.array([97.4,-40,265.]);reserve_max=np.array([116.6,40,315.])
    for name,shape in solids.items():
        shape=transform(shape,rot,origin);world[name]=shape
        filename=directory/(name+'.brep');export_brep(shape,filename)
        check=native_solid_integrity(import_brep(filename))
        if not check['boolean_input_integrity_pass']:raise ValueError((name,check))
        points,triangles=shape.tessellate(.05,.08)
        mesh=trimesh.Trimesh(vertices=np.array([tuple(p) for p in points]),faces=np.array(triangles),process=True)
        if not mesh.is_watertight or not mesh.is_winding_consistent:raise ValueError((name,'mesh integrity'))
        v,q=quad_sampling(mesh);npz=directory/(name+'_quad.npz');np.savez_compressed(npz,vertices=v,faces=q)
        bb=shape.bounding_box(optimal=True);lo=np.array(tuple(bb.min));hi=np.array(tuple(bb.max))
        contained=bool(np.all(lo>=reserve_min-1e-5) and np.all(hi<=reserve_max+1e-5))
        if not contained:raise ValueError((name,'outside preceding PCB reserve',lo,hi))
        parts.append({'name':name,'body':'torso','group':'brake_pcb_candidate','material':roles[name],
            'role':'ecad_package_envelope_not_printable','geometry_npz':str(npz.relative_to(R)),
            'source_sha256':sha(npz)})
        native.append({'name':name,'brep':str(filename.relative_to(R)),'sha256':sha(filename),
            'bounds_mm':[lo.tolist(),hi.tolist()],'reserve_subset':contained,'integrity':check,
            'mass_kg':None,'mass_basis':'Unknown package mass; existing protection reserve is unchanged'})
    overlaps=[];minimum_gap=float('inf')
    for (a,A),(b,B) in itertools.combinations(world.items(),2):
        if a=='pcb_finished_board_envelope' or b=='pcb_finished_board_envelope':
            # Shared component seating plane is intentional. No positive volume.
            common=A.intersect(B);vol=0. if common is None else abs(common.volume)
            if vol>1e-5:overlaps.append({'a':a,'b':b,'volume_mm3':vol})
        else:
            gap=A.distance_to(B);minimum_gap=min(minimum_gap,gap)
            if gap<1e-5:
                common=A.intersect(B);vol=0. if common is None else abs(common.volume)
                if vol>1e-5:overlaps.append({'a':a,'b':b,'volume_mm3':vol})
    if overlaps:raise ValueError(('package interference',overlaps))
    assembly=Compound(children=list(world.values()));step=out/'package_layout.step';export_step(assembly,step)
    back=import_step(step)
    if len(back.solids())!=len(solids):raise ValueError('STEP lost package bodies')
    scene={'unit':'m','status':'PCB PACKAGE GEOMETRY ONLY - NOT MOUNT/MASS/THERMAL RELEASE','parts':parts,
        'review_views':{'pcb_packages':[[.30,-.20,.43],[.109,0,.290]]},'review_ortho_scale_m':{'pcb_packages':.13}}
    (directory/'quad_scene.json').write_text(json.dumps(scene,separators=(',',':'))+'\n')
    record={'schema':'goose_brake_pcb_envelope_v1','source_config_sha256':sha(config),
        'source_board_sha256':sha(R/'hardware/brake_pcb_candidate/brake_pcb_candidate.kicad_pcb'),
        'local_board_xy_to_raw_robot':{'rotation':rot.tolist(),'origin_mm':origin.tolist()},
        'reserve_bounds_mm':[reserve_min.tolist(),reserve_max.tolist()],
        'geometry_count':len(solids),'step_solid_count':len(back.solids()),'parts':native,
        'all_within_previous_reserved_volume':True,'package_positive_volume_overlap':False,
        'minimum_package_gap_mm':minimum_gap,'mass_or_si_updated':False,'hardware_mount_designed':False,
        'source_script_sha256':sha(Path(__file__)),'step':{'path':str(step.relative_to(R)),'sha256':sha(step)}}
    (out/'manifest.json').write_text(json.dumps(record,indent=2)+'\n')
    (R/'evidence/brake_pcb_envelope_check.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ['geometry_count','step_solid_count','all_within_previous_reserved_volume','minimum_package_gap_mm','mass_or_si_updated']}))


if __name__=='__main__':main()
