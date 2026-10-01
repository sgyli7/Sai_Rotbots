"""Four actual upper-bill/frame M3 clamp stacks, independent native candidate.

Millimetres in the common head design datum. Nominal hardware envelopes are
ours, not supplied threaded CAD or a qualified preload/strength specification.
"""
from pathlib import Path
import json
import sys

import numpy as np
from build123d import Solid, Wire

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'
sys.path.insert(0, str(ROOT/'scripts/cad'))
from build_goose_cad import cylinder
from goose_candidate_export import CandidateExport


def hex_nut(x, y, z):
    radius=5.5/np.sqrt(3)
    polygon=[(x+radius*np.cos(a), z+radius*np.sin(a))
             for a in np.linspace(0, 2*np.pi, 6, endpoint=False)]
    nut=Solid.make_loft([Wire.make_polygon([(px, yy, pz) for px,pz in polygon], close=True)
                         for yy in [y-1.2, y+1.2]], ruled=True)
    return nut-cylinder(1.25, 4.4, [x,y,z], 'y')


def main():
    inputs=[R/'cad/exports'/folder/'manifest.json'
            for folder in ['jaw_retention', 'grip_cassettes']]
    # The four 3.2mm bores belong to fixed frame/tab material. None of these
    # fasteners fixes a rotating bearing race or the moving lower bill.
    export=CandidateExport(R, 'bill_mount_fasteners')
    stacks, contacts=[], []
    for side, direction, outer, inner in [('front',-1.,25.5,17.5),
                                          ('rear',1.,-25.,-17.)]:
        for index,x in enumerate([174.,182.]):
            name=f'upper_bill_{side}_mount_{index}'
            face=outer-direction*.5
            washer=cylinder(3.5,.5,[x,outer-direction*.25,566.],'y')
            washer-=cylinder(1.6,2.,[x,outer,566.],'y')
            screw=cylinder(1.5,12.,[x,face+direction*6.,566.],'y')
            screw+=cylinder(2.85,1.65,[x,face-direction*.825,566.],'y')
            nut_center=inner+direction*1.2
            export.emit(name+'_washer',washer,'head_roll',rho=7850.,material='titanium',notes=[
                'Own nominal M3 washer7OD/3.2ID/0.5mm; supports head against the outside frame face.',
                'Supplier dimensions,grade,preload,locking and surface treatment not released.',
            ])
            export.emit(name+'_screw',screw,'head_roll',rho=7850.,material='titanium',notes=[
                'Own nominal M3x12 button-head envelope5.7OD x1.65mm; actual socket/thread helices omitted.',
                '12mm under-head reach spans0.5mm washer,4mm frame,4mm fixed tab and2.4mm nut;1.1mm protrusion.',
            ])
            export.emit(name+'_nut',hex_nut(x,nut_center,566.),'head_roll',rho=7850.,material='titanium',notes=[
                'Own nominal M3 nut5.5AF x2.4mm,2.5mm thread-minor envelope;2.4mm full-height engagement.',
                'Fits inside the fixed tab; complete nut/driver approach and grade/preload remain gates.',
            ])
            contacts.append(dict(screw=name+'_screw',nut=name+'_nut',
                                 expected_thread_overlap_mm3=float(np.pi*(1.5**2-1.25**2)*2.4)))
            stacks.append(dict(side=side,hole_axis_world_mm=[x,0.,566.],axis='y',
                               direction=direction,frame_outer_face_y_mm=outer,
                               tab_inner_face_y_mm=inner,washer_thickness_mm=.5,
                               frame_thickness_mm=4.,tab_thickness_mm=4.,
                               screw_under_head_face_y_mm=face,screw_length_mm=12.,
                               nut_engagement_mm=2.4,screw_protrusion_mm=1.1,
                               static_load_route='upper grip carrier -> upper backbone -> fixed tabs -> frame'))
    payload=export.save(ROOT,inputs+[Path(__file__),ROOT/'scripts/cad/goose_candidate_export.py'],extra=dict(
        status='BILL_FRAME_M3_CLAMP_STACK_CANDIDATE_NOT_INSTALLED',installed=False,
        nominal_thread_contacts=contacts,mount_stacks=stacks,
        full_tool_access_pass=False,preload_release=False,structural_strength_pass=False))
    print('BILL FRAME STACKS',len(payload['parts']),'mass',payload['native_mass_kg'],flush=True)


if __name__=='__main__':
    main()
