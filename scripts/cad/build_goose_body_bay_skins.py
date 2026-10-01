"""Native module-bay torso skin with structured editable quad surface.

Original accepted skins stay immutable. The rear shoulder is shaped for the
actual battery allowance and the high hip cluster, without a giant side arch.
This is a same-version candidate; attachments and full sweep remain gates.
"""
from pathlib import Path
import hashlib, json, sys
import numpy as np
import trimesh
from build123d import export_brep, export_step, import_step

ROOT = Path(__file__).resolve().parents[2]; R = ROOT/'robots/Goose_V0.1'
sys.path.insert(0, str(ROOT/'scripts/cad'))
from goose_nurbs_skin import skin, surface, native_properties
from sai_agent.goose.morphology import body_grids
from sai_agent.native_cad import sampled_skin_quads


def main():
    layout_path = R/'configs/body_bay_layout_candidate.json'; layout = json.loads(layout_path.read_text())
    source = R/'cad/source/body_bay_skins'; exports = R/'cad/exports/body_bay_skins'
    source.mkdir(exist_ok=True); exports.mkdir(exist_ok=True)
    records = []; scene = []
    for side, label in [(-1, 'right'), (1, 'left')]:
        out, inside = body_grids(layout['body_profile_x_cz_ry_rz_mm'], side, layout['body_wall_mm'],layout['lower_limb_exit_boundary_u_v'])
        aft = np.zeros((64,48), dtype=bool); fore = aft.copy(); door = aft.copy()
        for i in range(64):
            for j in range(48):
                if 39 <= i < 49 and j >= 42: continue
                if 10 <= i < 48 and 14 <= j < 36: door[i,j] = True
                elif i < 30: aft[i,j] = True
                else: fore[i,j] = True
        for suffix, mask in [('aft', aft), ('fore', fore), ('door', door)]:
            name = 'wing_access_cover_'+label if suffix == 'door' else 'torso_shell_'+label+'_'+suffix
            outer = out.copy(); inner = inside.copy()
            if suffix == 'door':
                for array in (outer, inner):
                    for i in range(65):
                        for j in range(49):
                            u = np.clip((i-10)/38, 0, 1); v = np.clip((j-14)/22, 0, 1)
                            array[i,j,1] += side*1.2*np.sin(np.pi*u)*np.sin(np.pi*v)
                    array[:,:,0] = -32+(array[:,:,0]+32)*.988
                    array[:,:,2] = 293+(array[:,:,2]-293)*.974
                    array[:,:,1] += side*.25
            else:
                outer[:,:,0] += -.08 if suffix == 'aft' else .08
                inner[:,:,0] += -.08 if suffix == 'aft' else .08
            shape = skin(outer, inner, mask)
            if not shape.is_valid or len(shape.solids()) != 1: raise ValueError((name,'native skin invalid'))
            volume, com, inertia, integration = native_properties(shape)
            vertices, faces = sampled_skin_quads(surface(outer), surface(inner), mask, factor=5)
            triangles = np.concatenate([faces[:,[0,1,2]], faces[:,[0,2,3]]])
            mesh = trimesh.Trimesh(vertices, triangles, process=False)
            error = abs(mesh.volume/volume-1)
            if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0 or error > .005:
                raise ValueError((name,'structured mesh gate',error))
            paths = {'brep':source/(name+'.brep'), 'step':exports/(name+'.step'),
                'stl':exports/(name+'.stl'), 'npz':source/(name+'_quad.npz')}
            export_brep(shape, paths['brep']); export_step(shape, paths['step'])
            exchange = import_step(paths['step']); ev, *_ = native_properties(exchange)
            if not exchange.is_valid or len(exchange.solids()) != 1 or abs(ev/volume-1) > 1e-5:
                raise ValueError((name,'native STEP exchange'))
            # Native authoring topology has exact shared parametric boundaries;
            # ASCII retains double coordinates without binary32 collapse.
            paths['stl'].write_text(trimesh.exchange.stl.export_stl_ascii(mesh))
            back = trimesh.load(paths['stl'], force='mesh', process=True)
            if not back.is_watertight or not back.is_winding_consistent or abs(back.volume/volume-1) > .005:
                raise ValueError((name,'STL exchange'))
            np.savez_compressed(paths['npz'], vertices=vertices/1000, faces=faces)
            files = {k:dict(path=str(p.relative_to(R)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for k,p in paths.items()}
            records.append(dict(name=name, body='torso', material='PETG', unit='mm', density_kg_m3=1270,
                volume_mm3=volume, mass_kg=volume*1270e-9, full_density_mass_kg=volume*1270e-9,
                center_of_mass_world_m=(com/1000).tolist(), inertia_at_com_world_kg_m2=(inertia*1270e-15).tolist(),
                files=files, quad_faces=len(faces), quad_closed=True, native_valid=True,
                stl_method='shared structured CAD surface sampling5x; ASCII full precision; no mesh repair',
                quad_vs_native_volume_relative=error, adaptive_integration_error=integration,
                manufacturing_released=False, remaining=['frame mounting/hinge/latch', 'continuous full assembly/connector clearance', 'print fit and orientation']))
            scene.append(dict(name=name,body='torso',material='ivory',group='body_bay_skins',role='native_body_bay_candidate',
                geometry_npz=files['npz']['path'],source_sha256=files['npz']['sha256']))
            print(name, 'native/quad/STL pass', len(faces), 'mass_g', volume*1270e-6, flush=True)
    inputs = [layout_path, Path(__file__), ROOT/'src/sai_agent/goose/morphology.py', ROOT/'src/sai_agent/native_cad.py', ROOT/'scripts/cad/goose_nurbs_skin.py']
    report = dict(schema='goose_body_bay_skins_v1', parts=records, manufacturing_pass=False, final_appearance_pass=False,
        total_skin_mass_kg=sum(p['mass_kg'] for p in records),
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    (exports/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    (source/'quad_scene.json').write_text(json.dumps(dict(unit='m',status='BODY_BAY_NATIVE_CANDIDATE_UNRELEASED',parts=scene),separators=(',',':'))+'\n')


if __name__ == '__main__': main()
