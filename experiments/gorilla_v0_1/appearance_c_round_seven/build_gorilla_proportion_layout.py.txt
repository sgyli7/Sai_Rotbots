#!/usr/bin/env python3
"""Build editable appearance geometry from the sole AA3 authority and layout B.

This is a reconstruction candidate, not manufacturing CAD or an appearance pass.
The closed panel meshes support conservative surface-area shell accounting.
Hardware visualization has zero shell thickness to avoid double-counting hardware.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / "robots/gorilla_v0_1"
IVORY = [0.88, 0.845, 0.735, 1]
BLUE = [0.008, 0.40, 0.76, 1]
GOLD = [1.0, 0.51, 0.025, 1]
DARK = [0.045, 0.052, 0.057, 1]
METAL = [0.17, 0.18, 0.18, 1]
BLACK = [0.009, 0.012, 0.015, 1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Geometry:
    def __init__(self, spec: dict):
        self.spec = spec
        self.parts: list[dict] = []
        self.bodies = {spec["root_body"], *(j["child"] for j in spec["joints"])}

    def part(self, name, body, vertices, faces, color, hardware=False, note=""):
        assert body in self.bodies, body
        vertices=np.asarray(vertices,float)
        assert np.isfinite(vertices).all(), name
        volume=sum(np.dot(vertices[f[0]],np.cross(vertices[f[i]],vertices[f[i+1]]))/6
                   for f in faces for i in range(1,len(f)-1))
        if volume < 0: faces=[list(reversed(f)) for f in faces]
        self.parts.append({
            "name": name, "body": body,
            "role": "decoration" if hardware else "armor",
            "vertices_world_m": np.round(vertices, 8).tolist(),
            "faces": [list(map(int, f)) for f in faces], "rgba": color,
            "shell_density_kg_m3": 2700, "shell_thickness_m": 0 if hardware else .003,
            "mass_basis_note": note or ("Visual representation of independently counted hardware/frame; no additional shell mass." if hardware else "Closed appearance panel; surface-area thin-shell estimate, not a solid billet."),
        })

    def loft(self, name, body, rings, color, hardware=False, n=16, square=False):
        """Rings are (world center, depth/2, width/2), stacked in local Z."""
        verts = []
        if square:
            # Chamfered rectangle, preserving an editable mostly-quad control cage.
            profile = [(1,.66),(.66,1),(-.66,1),(-1,.66),(-1,-.66),(-.66,-1),(.66,-1),(1,-.66)]
            n = len(profile)
        else:
            profile = [(math.cos(2*math.pi*i/n), math.sin(2*math.pi*i/n)) for i in range(n)]
        for center, rx, ry in rings:
            c = np.asarray(center)
            verts.extend([c + [rx*x, ry*y, 0] for x,y in profile])
        faces = [list(reversed(range(n)))]
        for k in range(len(rings)-1):
            for i in range(n):
                j = (i+1)%n
                faces.append([k*n+i, k*n+j, (k+1)*n+j, (k+1)*n+i])
        faces.append(list(range((len(rings)-1)*n, len(rings)*n)))
        self.part(name, body, np.asarray(verts), faces, color, hardware)

    def link(self, name, body, a, b, profiles, color, hardware=False, n=16):
        a,b = np.asarray(a,float), np.asarray(b,float)
        axis = (b-a)/np.linalg.norm(b-a)
        width = np.array([0.,1.,0.]) if abs(axis[1]) < .95 else np.array([0.,0.,1.])
        width -= axis*np.dot(axis,width)
        width /= np.linalg.norm(width)
        depth = np.cross(width,axis)
        # Positive depth aims forward wherever the limb is roughly vertical.
        if depth[0] < 0: depth *= -1
        verts = []
        for t, rx, ry in profiles:
            c = a+t*(b-a)
            for i in range(n):
                angle = 2*math.pi*i/n
                verts.append(c+rx*math.cos(angle)*depth+ry*math.sin(angle)*width)
        faces=[list(reversed(range(n)))]
        for k in range(len(profiles)-1):
            for i in range(n):
                j=(i+1)%n
                faces.append([k*n+i,k*n+j,(k+1)*n+j,(k+1)*n+i])
        faces.append(list(range((len(profiles)-1)*n,len(profiles)*n)))
        # The frame can have opposite orientation depending on link direction.
        va=np.asarray(verts)
        volume=sum(np.dot(va[f[0]],np.cross(va[f[i]],va[f[i+1]]))/6 for f in faces for i in range(1,len(f)-1))
        if volume < 0: faces=[list(reversed(f)) for f in faces]
        self.part(name,body,va,faces,color,hardware)

    def box(self, name, body, center, size, color, hardware=False):
        c=np.asarray(center,float); d=np.asarray(size,float)/2
        v=np.array([c+d*np.array([x,y,z]) for z in (-1,1) for y in (-1,1) for x in (-1,1)])
        faces=[[0,2,3,1],[4,5,7,6],[0,1,5,4],[2,6,7,3],[0,4,6,2],[1,3,7,5]]
        self.part(name,body,v,faces,color,hardware)

    def joint(self, name, body, pos, diameter, length):
        p=np.asarray(pos,float)
        self.link(name+"_housing",body,p+[0,-length/2,0],p+[0,length/2,0],
                  [(0,diameter*.42,diameter*.42),(.06,diameter/2,diameter/2),(.94,diameter/2,diameter/2),(1,diameter*.42,diameter*.42)],METAL,True,24)
        for s in (-1,1):
            center=p+[0,s*(length/2+.003),0]
            # Torus on the transverse output face; physical hardware is counted elsewhere.
            v=[]; faces=[]; n,m=24,6; r=diameter*.43; tube=.009
            for i in range(n):
                theta=2*math.pi*i/n
                for j in range(m):
                    phi=2*math.pi*j/m
                    rr=r+tube*math.cos(phi)
                    v.append(center+[rr*math.cos(theta),tube*math.sin(phi),rr*math.sin(theta)])
            for i in range(n):
                for j in range(m): faces.append([i*m+j,((i+1)%n)*m+j,((i+1)%n)*m+(j+1)%m,i*m+(j+1)%m])
            self.part(name+f"_rim_{'left' if s>0 else 'right'}",body,np.asarray(v),faces,GOLD,True)


def build(spec: dict) -> Geometry:
    g=Geometry(spec)
    # A curved, uninterrupted ivory chest wedge; not a humanoid head or a box.
    g.loft("ivory_chest_wedge","torso",[
        ([.40,0,1.77],.036,.07),([.49,0,1.93],.055,.145),
        ([.46,0,2.16],.067,.25),([.30,0,2.40],.075,.36),
        ([.095,0,2.58],.066,.41),([-.045,0,2.65],.042,.335)],IVORY,n=24)
    # AA3 has a gently crowned chest top, rather than a flat chopped rectangle.
    chest=g.parts[-1]
    for vertex in chest['vertices_world_m'][-24:]:
        vertex[2]=round(vertex[2]-.070*(abs(vertex[1])/.335)**2,8)
    g.loft("ivory_back_carapace","torso",[
        ([-.12,0,1.78],.055,.13),([-.29,0,1.94],.071,.31),
        ([-.37,0,2.22],.088,.43),([-.37,0,2.46],.084,.45),
        ([-.27,0,2.59],.065,.38),([-.085,0,2.642],.045,.32)],IVORY,n=24)
    g.loft("torso_internal_carrier_visual","torso",[
        ([.10,0,1.81],.19,.22),([.06,0,2.00],.29,.41),
        ([-.035,0,2.36],.29,.44),([-.04,0,2.50],.16,.39)],DARK,True)
    for side,s in (("left",1),("right",-1)):
        g.loft(side+"_blue_torso_side","torso",[
            ([.34,s*.18,1.87],.10,.077),([.34,s*.25,2.01],.13,.09),
            ([.27,s*.335,2.20],.19,.105),([.055,s*.41,2.40],.235,.105),
            ([-.075,s*.39,2.53],.17,.095)],BLUE,n=24)
        g.loft(side+"_blue_rear_side_transition","torso",[
            ([-.18,s*.25,1.90],.087,.08),([-.22,s*.38,2.15],.13,.082),
            ([-.24,s*.425,2.37],.135,.09),([-.15,s*.39,2.53],.088,.075)],BLUE,n=20)
        g.link(side+"_upper_blue_shoulder_bridge","torso",
            [-.04,s*.39,2.555],[-.12,s*.69,2.41],
            [(0,.090,.065),(.18,.175,.10),(.50,.21,.12),(.82,.17,.105),(1,.10,.08)],BLUE,n=24)
        # Front radiator cassette with a saffron surround and open black slats.
        yc=s*.335
        g.box(side+"_radiator_gold_frame","torso",[.486,yc,2.235],[.038,.145,.325],GOLD)
        g.box(side+"_radiator_dark_face","torso",[.512,yc,2.235],[.008,.105,.285],BLACK,True)
        for i in range(10):
            g.box(side+f"_radiator_louver_{i:02}","torso",[.519,yc,2.108+i*.028],[.009,.089,.009],METAL,True)
    g.box("central_amber_light_rim","torso",[.505,0,2.17],[.038,.060,.215],GOLD)
    g.box("central_amber_light","torso",[.528,0,2.17],[.012,.030,.165],[1,.76,.08,1],True)
    # Back service door lies on the rear carapace, not on a different design.
    g.loft("blue_back_service_panel","torso",[
        ([-.465,0,2.17],.020,.13),([-.471,0,2.20],.022,.155),
        ([-.471,0,2.50],.022,.155),([-.455,0,2.525],.018,.135)],BLUE,square=True)
    g.box("back_service_latch","torso",[-.497,0,2.468],[.012,.07,.025],DARK,True)
    for yy in (-.125,.125):
        for zz in (2.216,2.487):
            g.box(f"back_fastener_{yy}_{zz}".replace('-','n').replace('.','p'),"torso",[-.497,yy,zz],[.012,.018,.018],METAL,True)
    # Compact visible waist, with broad gold pelvis and ivory rear sacral cover.
    g.loft("pelvis_dark_carrier","pelvis",[
        ([.0,0,1.48],.16,.17),([.0,0,1.63],.20,.20),([.0,0,1.76],.18,.18)],DARK,True)
    g.loft("saffron_front_pelvis","pelvis",[
        ([.33,0,1.38],.049,.075),([.36,0,1.42],.057,.105),
        ([.38,0,1.66],.058,.16),([.34,0,1.74],.047,.135)],GOLD,square=True)
    g.box("pelvis_small_black_latch","pelvis",[.423,0,1.437],[.012,.050,.038],DARK,True)
    g.loft("rear_saffron_pelvis_band","pelvis",[
        ([-.20,0,1.56],.043,.29),([-.215,0,1.63],.049,.37),([-.19,0,1.69],.035,.32)],GOLD,square=True)
    g.loft("rear_ivory_sacral_guard","pelvis",[
        ([-.245,0,1.31],.032,.058),([-.25,0,1.37],.036,.085),
        ([-.26,0,1.58],.047,.12),([-.235,0,1.66],.043,.13)],IVORY,square=True)
    for side,s in (("left",1),("right",-1)):
        points={key.removeprefix('left_'): np.array([p[0],s*p[1],p[2]],float)
                for key,p in spec['points_world_m'].items() if key.startswith('left_')}
        sh,el,wr,pa=(points[k] for k in ('shoulder','elbow','wrist','palm'))
        hip,knee,fold,ankle,foot=(points[k] for k in ('hip','knee','fold','ankle','foot'))
        g.joint(side+"_shoulder",side+"_upper_arm",sh,.23,.19)
        g.link(side+"_ivory_upper_arm",side+"_upper_arm",sh,el,
               [(.045,.10,.11),(.18,.17,.145),(.48,.14,.135),(.77,.125,.115),(.88,.087,.093)],IVORY)
        g.loft(side+"_blue_outer_deltoid",side+"_upper_arm",[
            ([-.02,s*.735,2.12],.13,.09),([-.06,s*.755,2.23],.17,.135),
            ([-.12,s*.71,2.38],.155,.135),([-.13,s*.65,2.45],.095,.072)],BLUE)
        g.box(side+"_deltoid_gold_mark",side+"_upper_arm",[.077,s*.874,2.205],[.025,.017,.087],GOLD,True)
        g.joint(side+"_elbow",side+"_forearm",el,.22,.20)
        g.link(side+"_blue_forearm",side+"_forearm",el,wr,
               [(.105,.14,.145),(.20,.195,.167),(.42,.20,.175),(.69,.165,.14),(.91,.12,.098),(.98,.083,.079)],BLUE)
        g.box(side+"_forearm_small_gold_mark",side+"_forearm",[.21,s*.85,1.31],[.018,.04,.07],GOLD,True)
        g.joint(side+"_wrist",side+"_palm",wr,.135,.15)
        g.loft(side+"_ivory_palm",side+"_palm",[
            ([pa[0],pa[1]+s*.020,.975],.083,.12),([pa[0],pa[1]+s*.024,1.025],.099,.125),
            ([pa[0],pa[1]+s*.025,1.135],.089,.12),([pa[0],pa[1]+s*.022,1.174],.062,.095)],IVORY,square=True)
        for i in range(1,4):
            pj=next(j for j in spec['joints'] if j['name']==f'{side}_finger_{i}_proximal')
            dj=next(j for j in spec['joints'] if j['name']==f'{side}_finger_{i}_distal')
            p,d=np.array(pj['position_world_m']),np.array(dj['position_world_m'])
            g.link(f'{side}_finger_{i}_proximal',pj['child'],p,d,
                   [(0,.033,.031),(.18,.039,.034),(.83,.034,.03),(1,.026,.027)],DARK,n=12)
            g.box(f'{side}_finger_{i}_ivory_pad',pj['child'],p+[.036,0,-.043],[.018,.060,.061],IVORY)
            end=d+[.060,-s*.029,-.059]
            g.link(f'{side}_finger_{i}_distal',dj['child'],d,end,
                   [(0,.027,.028),(.18,.034,.032),(.58,.031,.029),(1,.023,.024)],DARK,n=12)
        pj=next(j for j in spec['joints'] if j['name']==side+'_thumb_proximal')
        dj=next(j for j in spec['joints'] if j['name']==side+'_thumb_distal')
        p,d=np.array(pj['position_world_m']),np.array(dj['position_world_m'])
        g.box(side+'_thumb_pivot_web',side+'_palm',[.07,s*.665,1.116],
              [.075,.13,.045],DARK,True)
        g.link(side+'_thumb_proximal',pj['child'],p,d,[(0,.035,.035),(.2,.045,.039),(.8,.038,.034),(1,.027,.027)],DARK,n=12)
        g.link(side+'_thumb_distal',dj['child'],d,d+[.063,-s*.038,-.058],[(0,.027,.027),(.2,.031,.028),(.85,.028,.025),(1,.021,.021)],DARK,n=12)
        g.joint(side+"_hip",side+"_thigh",hip,.29,.24)
        g.loft(side+"_ivory_hip_transition_cuff",side+"_thigh",[
            ([.018,s*.37,1.59],.042,.081),([.027,s*.365,1.65],.055,.095),
            ([.020,s*.34,1.72],.052,.085),([.01,s*.31,1.747],.034,.05)],IVORY,n=16)
        g.link(side+"_blue_thigh",side+"_thigh",hip+[.055,0,-.012],knee+[.035,0,.045],
               [(.09,.14,.145),(.26,.22,.205),(.52,.215,.20),(.78,.175,.163),(.94,.126,.12)],BLUE)
        g.loft(side+"_orange_knee_guard",side+"_thigh",[
            ([.39,s*.424,1.013],.049,.10),([.43,s*.418,1.075],.060,.145),
            ([.37,s*.41,1.245],.053,.155),([.33,s*.407,1.29],.042,.118)],GOLD,square=True)
        g.joint(side+"_knee",side+"_middle_shank",knee,.29,.245)
        g.link(side+"_blue_middle_shank",side+"_middle_shank",knee+[.05,0,-.01],fold+[.04,0,.028],
               [(.15,.155,.15),(.28,.19,.18),(.5,.175,.165),(.8,.125,.125),(.91,.09,.10)],BLUE)
        g.joint(side+"_fold",side+"_distal_shank",fold,.22,.215)
        g.link(side+"_gray_distal_carrier",side+"_distal_shank",fold,ankle,
               [(.11,.079,.089),(.28,.095,.10),(.74,.085,.09),(.89,.059,.071)],METAL,True)
        g.loft(side+"_blue_distal_front_guard",side+"_distal_shank",[
            ([.055,s*.52,.31],.026,.07),([.06,s*.515,.345],.032,.10),
            ([.045,s*.502,.45],.036,.102),([.023,s*.498,.476],.025,.071)],BLUE,square=True)
        g.joint(side+"_ankle",side+"_foot",ankle,.205,.205)
        fx,fy,fz=foot
        g.loft(side+"_dark_sole",side+"_foot",[
            ([fx,fy,0],.433,.288),([fx,fy,.021],.45,.305),
            ([fx,fy,.043],.447,.302),([fx,fy,.05],.42,.28)],DARK,square=True)
        g.loft(side+"_ivory_foot_upper",side+"_foot",[
            ([fx+.025,fy,.049],.417,.283),([fx+.01,fy,.084],.408,.274),
            ([fx-.055,fy,.15],.285,.205),([fx-.085,fy,.18],.21,.16)],IVORY,square=True)
        g.loft(side+"_dark_rear_heel",side+"_foot",[
            ([fx-.325,fy,.044],.121,.259),([fx-.31,fy,.075],.125,.255),
            ([fx-.285,fy,.167],.095,.209),([fx-.28,fy,.175],.087,.198)],DARK,square=True)
        g.loft(side+"_ivory_ankle_inst_ep",side+"_foot",[
            ([fx-.1,fy,.135],.12,.148),([fx-.14,fy,.22],.092,.129),
            ([fx-.18,fy,.244],.075,.10)],IVORY,square=True)
    return g


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec',type=Path,default=ROBOT/'configs/layout_b_spec.json')
    p.add_argument('--output',type=Path,default=ROBOT/'cad/source/layout_b_scene.json')
    args=p.parse_args()
    spec=json.loads(args.spec.read_text())
    image=ROBOT/spec['appearance_authority']['path']
    assert sha(image)==spec['appearance_authority']['sha256']
    g=build(spec)
    allv=np.concatenate([np.array(part['vertices_world_m']) for part in g.parts])
    scene={
        'schema':'gorilla_layout_scene_v1','robot_id':spec['robot_id'],
        'checkpoint_id':spec['checkpoint_id'],'spec_sha256':sha(args.spec),
        'image_sha256':sha(image),'spec_path':str(args.spec.relative_to(ROOT)),
        'appearance_authority_path':str(image.relative_to(ROOT)),
        'units':'m','coordinate_frame':spec['coordinate_frame'],
        'rgba_encoding':'sRGB colors; renderer converts to linear shader inputs',
        'parts':g.parts,'bounds_world_m':[allv.min(axis=0).tolist(),allv.max(axis=0).tolist()],
        'dimensions_xyz_m':np.ptp(allv,axis=0).tolist(),
        'appearance_status':'candidate_requires_actual_four_view_review',
        'source_uncertainties':['Artwork cameras are not calibrated orthographic views.',
            'Hidden joint axis depths and armor curvature are reconstructed estimates.',
            'Closed single-surface panels are not modeled inner/outer manufacturing walls.',
            'Decorative hardware repeats independently counted module/frame mass.'],
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(scene,indent=2)+'\n')
    export=ROBOT/'cad/exports/layout_b'; export.mkdir(parents=True,exist_ok=True)
    obj=[];mtl=[];offset=1
    for part in g.parts:
        obj.extend(['o '+part['name'],'usemtl '+part['name']])
        obj.extend('v '+' '.join(map(str,v)) for v in part['vertices_world_m'])
        obj.extend('f '+' '.join(str(i+offset) for i in face) for face in part['faces'])
        mtl.extend(['newmtl '+part['name'],'Kd '+' '.join(map(str,part['rgba'][:3])),'Ns 30'])
        offset+=len(part['vertices_world_m'])
    (export/'layout_b.obj').write_text('mtllib layout_b.mtl\n'+'\n'.join(obj)+'\n')
    (export/'layout_b.mtl').write_text('\n'.join(mtl)+'\n')
    print(json.dumps({'scene':str(args.output),'parts':len(g.parts),'dimensions_xyz_m':scene['dimensions_xyz_m']}))


if __name__=='__main__': main()
