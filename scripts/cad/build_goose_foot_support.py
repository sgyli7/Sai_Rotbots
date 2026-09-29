"""Preserve accepted foot surfaces while separating rubber, trim and metal plate.

This is a structural candidate, not a release: ankle fastening, shell fixing,
material certificates, contact tests and the full roll sweep remain open.
Quad source geometry is retained; STEP is an exact faceted plate blank, not a
claim that the smooth source rubber surface is a machined BREP.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from scipy.integrate import trapezoid
from shapely.geometry import Polygon, LineString
from build_goose_fuller_exterior import closed_skin
from build_goose_r2_reference_rebuild import QuadMesh, section_solid

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/Goose_V0.1'


def volume(mesh):
    return float(trimesh.Trimesh(mesh.vertices, mesh.triangles(), process=False).volume)


def boundary_loops(faces):
    edges = defaultdict(list)
    for face in faces:
        for a, b in zip(face, np.roll(face, -1)):
            edges[tuple(sorted((int(a), int(b))))].append((int(a), int(b)))
    boundary = [v[0] for v in edges.values() if len(v) == 1]
    adjacent = defaultdict(list)
    for a, b in boundary:
        adjacent[a].append(b); adjacent[b].append(a)
    if not all(len(v) == 2 for v in adjacent.values()):
        raise ValueError('invalid plate boundary')
    unused = set(adjacent); loops = []
    while unused:
        start = min(unused); loop = [start]; previous = None; current = start
        while True:
            nxt = next(k for k in adjacent[current] if k != previous)
            if nxt == start:
                break
            loop.append(nxt); previous, current = current, nxt
        unused.difference_update(loop); loops.append(loop)
    return loops


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, default=ROBOT/'cad/source/fuller_exterior_candidate/closed/scene.json')
    ap.add_argument('--output', type=Path, default=ROBOT/'cad/source/foot_support_candidate')
    ap.add_argument('--exports', type=Path, default=ROBOT/'cad/exports/foot_support_candidate')
    ap.add_argument('--preview', type=Path, default=ROOT/'artifacts/Goose_V0.1/foot_support_candidate')
    args = ap.parse_args()
    source = json.loads(args.source.read_text())
    parts = {p['name']: p for p in source['parts']}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'quad_source').mkdir(exist_ok=True)
    args.exports.mkdir(parents=True, exist_ok=True)
    args.preview.mkdir(parents=True, exist_ok=True)
    changes = {}; reports = []; polygons = {}

    def save(name, material, mesh, group, role, density):
        mesh.orient_outward()
        obj = args.output/'quad_source'/f'{name}.obj'
        mesh.write_obj(obj)
        mesh.write_stl(args.exports/f'{name}.stl')
        changes[name] = dict(name=name, material=material, group=group, role=role,
            vertices=(mesh.vertices*.001).tolist(), faces=mesh.faces.tolist(),
            source_sha256=hashlib.sha256(obj.read_bytes()).hexdigest())
        q = trimesh.Trimesh(mesh.vertices, mesh.triangles(), process=False)
        if not q.is_watertight or not q.is_winding_consistent or q.volume <= 0:
            raise ValueError(f'invalid solid {name}')
        reports.append(dict(name=name, density_kg_m3=density, volume_mm3=volume(mesh),
            mass_kg=volume(mesh)*density*1e-9, quads=len(mesh.faces),
            watertight=bool(q.is_watertight), winding_consistent=bool(q.is_winding_consistent)))

    for side, label in [(-1, 'right'), (1, 'left')]:
        center = np.array([10., side*89.])
        for suffix, material, density in [('sole','rubber',1200), ('trim','orange',1250)]:
            name = f'{label}_foot_{suffix}'
            src = parts[name]; v = np.asarray(src['vertices'])*1000; f = np.asarray(src['faces'])
            original_v = v.copy()
            if suffix == 'trim':
                # Original visual band overlaps the rubber in z=10.5..12 mm.
                # Trim away only that buried band, retaining the original loft.
                bottom = np.isclose(v[:,2],10.5)
                next_ring = v[np.isclose(v[:,2],14.0)]
                # section_solid puts the matching perimeter rings first.
                count = len(next_ring)
                v[:count] += (next_ring-v[:count])*((12.-10.5)/(14.-10.5))
                # Bottom cap interior vertices will be removed with that cap.
                v[bottom,2] = 12.0
            zlo, zhi = v[:,2].min(), v[:,2].max()
            cap_top = np.all(np.isclose(v[f,2], zhi), axis=1)
            cap_bottom = np.all(np.isclose(v[f,2], zlo), axis=1)
            retained = f[~cap_top] if suffix == 'sole' else f[~(cap_top|cap_bottom)]
            inner = v.copy()
            # Axis offsets are explicit parameters, not asserted constant normals.
            inset = 2.5 if suffix == 'sole' else 2.0
            inner[:,:2] = center + (inner[:,:2]-center)*np.array([(89-inset)/89, (46-inset)/46])
            if suffix == 'sole':
                inner[:,2] = 3.5+(v[:,2]-zlo)*(zhi-3.5)/(zhi-zlo)
            mesh = closed_skin(v,inner,retained)
            save(name,material,mesh,label+'_foot','hollow_sole_candidate' if suffix=='sole' else 'hollow_trim_candidate',density)
            reports[-1].update(previous_mass_kg=volume(QuadMesh(original_v,f))*density*1e-9,
                bottom_thickness_mm=3.0 if suffix=='sole' else None,
                outer_retained_face_count=len(retained),
                exterior_change="none" if suffix == "sole" else "trim buried overlap below z=12 mm; remaining loft unchanged",
                nominal_axis_inset_mm=inset)

        # Four mm aluminium plate: same swept forefoot rule as approved mesh.
        # Six mm outline inset fits above the inner rubber floor, with clearance.
        plate = section_solid([(3.5,10,side*89,83,40),(7.5,10,side*89,83,40)],2,3.1,24)
        vv = plate.vertices
        u = np.clip((vv[:,0]+30)/110,0,1); u=u*u*(3-2*u)
        vv[:,1] = side*89+(vv[:,1]-side*89)*(1+.24*u)
        vv[:,0] += np.maximum(vv[:,0]-20,0)*.32
        ff = plate.faces[np.all(np.isclose(vv[plate.faces,2],7.5),axis=1)]
        # Paired lightening windows, clear of a central full-width ankle land.
        centers = vv[ff].mean(axis=1)
        x,y = centers[:,0], centers[:,1]-side*89
        cut = (x > -42)&(x < 3)&(np.abs(y)>10)&(np.abs(y)<26)
        ff = ff[~cut]
        lower = vv.copy(); lower[:,2] = 3.5
        mesh = closed_skin(vv,lower,ff)
        name = f'{label}_foot_load_plate'
        save(name,'titanium',mesh,label+'_foot','aluminium_plate_blank_no_ankle_holes',2700)
        loops = boundary_loops(ff)
        rings = [vv[k,:2] for k in loops]
        outer_index = max(range(len(rings)),key=lambda k:Polygon(rings[k]).area)
        outer = rings.pop(outer_index)
        poly = Polygon(outer, rings)
        if not poly.is_valid: raise ValueError('plate polygon invalid')
        polygons[label] = poly
        # The STEP solid exactly represents this polygonal blank and its windows.
        from build123d import Wire, Face, Vector, Solid, export_step
        ow = Wire.make_polygon([Vector(float(x),float(y),3.5) for x,y in outer], close=True)
        holes = [Wire.make_polygon([Vector(float(x),float(y),3.5) for x,y in ring],close=True) for ring in rings]
        face = Face(ow, holes)
        solid = Solid.extrude(face, Vector(0,0,4))
        if not solid.is_valid: raise ValueError('STEP plate invalid')
        export_step(solid, args.exports/f'{name}.step')
        relative_error = abs(solid.volume-volume(mesh))/volume(mesh)
        if relative_error > 1e-8: raise ValueError('quad/STEP volume mismatch')
        reports[-1].update(step_quad_volume_relative_error=relative_error, window_count=len(rings),
            thickness_mm=4, mounting_status='blank; ankle bearing/frame fastening not designed')

    # Honest small beam screen: plate is NOT accepted from this approximation.
    poly = polygons['right']
    trials = []
    for point, anchor in [(-55.,31.), (105.,75.)]:
        xx = np.linspace(min(point,anchor)+.01,max(point,anchor)-.01,801)
        width = np.array([poly.intersection(LineString([(t,-200),(t,0)])).length for t in xx])
        force=125.; t=4.; E=69000.; arm=np.abs(xx-point)
        moment=force*arm
        sigma=6*moment/(width*t*t)
        deflection=force*trapezoid(arm*arm/(E*width*t**3/12),xx)
        trials.append(dict(load_n=force,point_x_mm=point,assumed_fixed_edge_x_mm=anchor,
            max_nominal_beam_stress_mpa=float(sigma.max()),beam_deflection_mm=float(deflection),
            minimum_net_section_width_mm=float(width.min())))

    old_mass=sum(r.get('previous_mass_kg',0) for r in reports)
    new_mass=sum(r['mass_kg'] for r in reports)
    digest=hashlib.sha256(args.source.read_bytes()).hexdigest()
    report=dict(status='CONDITIONAL_FOOT_STRUCTURE_CANDIDATE_NOT_MANUFACTURING_RELEASE',
        approved_scene_sha256=digest, appearance_status="sole contact and outer sole preserved; trim buried overlap removed",
        original_sole_contact_vertices_preserved=True, parts=reports,
        replaced_solid_sole_and_trim_mass_kg=old_mass,
        hollow_sole_trim_and_aluminium_plates_mass_kg=new_mass,
        conditional_mass_reduction_kg=old_mass-new_mass,
        densities_are_assumed_not_weighed=True, plate_beam_screen=trials,
        beam_material_assumptions=dict(youngs_modulus_mpa=69000,design_yield_floor_mpa=200,
            nominal_stress_limit_mpa=100,material='6061-T6 candidate; certificate required'),
        limitations=['Plate is an unmounted blank: no released motor/axis interface or shell fasteners',
            'Beam assumes fixed edges at x=31 and 75 mm; actual frame stiffness, window corner concentrations and 3D FEA unresolved',
            '125 N load is a design screen, not validated walking impact or contact pressure',
            'Shell above sole/trim remains the earlier solid exterior; this is not a complete printable foot',
            'Axis-scaled inset is not a constant-normal wall-thickness certificate',
            'Rubber modulus, traction, bonding, wear, dimensional tolerances and print process not selected',
            'No gain in stability or walking is inferred from mass reduction; inertia/contact model must be regenerated'])
    (args.output/'foot_parts.json').write_text(json.dumps(dict(status=report['status'],approved_scene_sha256=digest,parts=list(changes.values())),indent=2)+'\n')
    (ROBOT/'evidence/foot_support_candidate.json').write_text(json.dumps(report,indent=2)+'\n')
    # Full scene is a reproducible local preview, not a second approved baseline.
    merged=[]
    for p in source['parts']: merged.append(changes.get(p['name'],p))
    merged.extend(p for n,p in changes.items() if n not in parts)
    scene=dict(source,parts=merged,status=report['status'])
    (args.preview/'scene.json').write_text(json.dumps(scene))
    # A real cutaway of these meshes, separated vertically for inspectability.
    exploded=[]
    for p in changes.values():
        p=json.loads(json.dumps(p)); offset=.020 if p['name'].endswith('trim') else .010 if p['name'].endswith('plate') else 0
        for v in p['vertices']:v[2]+=offset
        exploded.append(p)
    cutaway=args.preview/'exploded';cutaway.mkdir(exist_ok=True)
    (cutaway/'scene.json').write_text(json.dumps(dict(status=report['status'],parts=exploded)))
    print(json.dumps({k:report[k] for k in ('replaced_solid_sole_and_trim_mass_kg','hollow_sole_trim_and_aluminium_plates_mass_kg','conditional_mass_reduction_kg','plate_beam_screen')},indent=2))

if __name__=='__main__':main()
