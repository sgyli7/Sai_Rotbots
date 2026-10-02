"""Final source/display/runtime identity audit for the detached candidate."""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths = [R/'configs/tip_grip_physics_contract.json', R/'models/tip_grip_physics/robot.xml',
             R/'cad/source/tip_grip_candidate/assembly_scene.json',
             R/'cad/source/mechanical_preview/scene.json', R/'cad/exports/tip_grip_candidate/manifest.json',
             R/'evidence/tip_grip_finite_reach.json', R/'evidence/tip_grip_floor_object_geometry.json',
             R/'evidence/tip_grip_floor_pickup_80mm_contact_probe.json',
             R/'evidence/tip_grip_dynamic_native_floor.json']
    c = json.loads(paths[0].read_text())
    scene, base, kit = [json.loads(paths[i].read_text()) for i in [2, 3, 4]]
    for record in [c]+[json.loads(p.read_text()) for p in paths[5:]]:
        for relative, expected in record['source_hashes'].items():
            if sha(ROOT/relative) != expected:
                raise ValueError(('stale candidate input', relative))
    if sha(paths[1]) != c['model_sha256'] or sha(paths[2]) != c['candidate_scene_sha256']:
        raise ValueError('XML or scene identity')
    for relative, expected in c['asset_sha256'].items():
        if sha(paths[1].parent/relative) != expected:
            raise ValueError(('runtime asset identity', relative))
    old = {p['name']: p for p in base['parts']}
    new = {p['name']: p for p in scene['parts']}
    replaced = set(kit['replaces_existing_parts'])
    assert len(new) == len(old) == len(c['visual_sources']) == 344
    assert set(new) == set(old)
    assert all(new[n] == old[n] for n in new if n not in replaced)
    assert np.array_equal(scene['assembly_translation_m'], base['assembly_translation_m'])
    native = {p['name']: p for p in kit['parts']}
    visuals = {p['name']: p for p in c['visual_sources']}
    sources = []
    for name in replaced:
        part, item, visual = new[name], native[name], visuals[name]
        assert part['body'] == item['body'] == visual['body']
        assert part['source_sha256'] == item['files']['npz']['sha256'] == visual['source_sha256']
        file = R/part['geometry_npz']
        assert sha(file) == part['source_sha256']
        with np.load(file, allow_pickle=False) as mesh:
            assert mesh['faces'].shape == (item['quad_faces'], 4)
            assert len(mesh['vertices']) == visual['vertices']
            assert len(mesh['faces']) == visual['quad_faces']
        sources.append(dict(name=name, body=item['body'], quad_faces=visual['quad_faces'],
                            vertices=visual['vertices'], geometry_npz=part['geometry_npz'],
                            source_sha256=part['source_sha256']))
    tree = ET.parse(paths[1]).getroot()
    geom_names = {g.get('name') for g in tree.findall('.//geom')}
    assert not geom_names & set(c['removed_old_merged_visual_names'])
    coverage = [n for g in c['visual_geometries'] for n in g.get('part_names', [])]
    assert len(coverage) == len(set(coverage))
    assert set(coverage) == set(c['rebuilt_visual_part_names'])
    assert replaced <= set(coverage)
    model = mujoco.MjModel.from_xml_path(str(paths[1]))
    assert (model.nq, model.nv, model.nu) == (39, 38, 18)
    np.testing.assert_allclose(model.body_mass.sum(), c['nominal_robot_mass_kg'], rtol=0, atol=1e-12)
    errors = []
    for body in c['bodies']:
        index = model.body(body['name']).id
        q = model.body_iquat[index]
        rotation = Rotation.from_quat(q[[1, 2, 3, 0]]).as_matrix()
        tensor = rotation@np.diag(model.body_inertia[index])@rotation.T
        np.testing.assert_allclose(model.body_mass[index], body['mass_kg'], rtol=0, atol=1e-12)
        np.testing.assert_allclose(model.body_ipos[index], body['com_local_m'], rtol=0, atol=1e-12)
        np.testing.assert_allclose(tensor, body['inertia_at_com_body_kg_m2'], rtol=0, atol=1e-12)
        errors.append(float(np.max(np.abs(tensor-body['inertia_at_com_body_kg_m2']))))
    report = dict(schema='goose_tip_grip_identity_v1', identity_pass=True, parts=344,
        replaced_parts=len(replaced), retained_parts_unchanged=338,
        conditional_bare_mass_kg=float(model.body_mass.sum()), active_axes=18, runtime_bodies=len(c['bodies']),
        nq=model.nq, nv=model.nv, nu=model.nu, actual_quad_sources=sources,
        removed_old_merged_visual_groups=len(c['removed_old_merged_visual_names']),
        rebuilt_visual_source_parts=len(coverage), duplicate_rebuilt_visual_source_parts=0,
        max_full_inertia_error_kg_m2=max(errors), own_runtime_assets_checked=len(c['asset_sha256']),
        floor_pickup_release=False, manufacturing_release=False, training_release=False,
        source_hashes={str(p.relative_to(ROOT)): sha(p) for p in paths+[Path(__file__)]})
    (R/'evidence/tip_grip_geometry_identity.json').write_text(json.dumps(report, indent=2)+'\n')
    print('TIP IDENTITY', report['parts'], 'parts', report['runtime_bodies'], 'bodies',
          'max inertia error', report['max_full_inertia_error_kg_m2'], flush=True)


if __name__ == '__main__':
    main()
