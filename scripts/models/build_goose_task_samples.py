"""Generate external sample includes without changing the frozen robot."""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

from sai_agent.goose.task_samples import sample_body, rotation

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/Goose_V0.1'


def main():
    out = ROBOT / 'models/task_samples_v1'; out.mkdir(parents=True, exist_ok=True)
    source = ROBOT / 'models/task_proxy_11_v1/robot.xml'
    contract = ROBOT / 'configs/task_proxy_11_v1_contract.json'
    catalog = {'schema': 'goose_task_samples_v1', 'candidate_id': 'goose_task_samples_v1',
        'robot_model_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'robot_contract_sha256': hashlib.sha256(contract.read_bytes()).hexdigest(),
        'formal_masses_kg': [.1, .2, .3], 'development_masses_kg': [.05],
        'robot_modified': False, 'robot_collision_leaves': 11, 'objects': [],
        'object_frame': 'Graspable cylindrical crossbar centre; inertial COM is separate. TaskGoal position/rotation are this named body frame.',
        'friction': {'coefficient': .65, 'status': 'declared virtual assumption, not measured',
            'priority': 2, 'rule': 'Object priority selects .65 for object/robot and object/floor pairs; zero-friction negative test is separately named.'},
        'material_status': 'Virtual primitive mass distribution; no measured material/printing or purchased sample identity.',
        'scope': 'Object inputs and bounded contact/geometry/static diagnostics; task training and scene scheduling remain with Lab.'}
    for family in ['cylinder_weight', 'handle_weight']:
        for mass in [.05, .1, .2, .3]:
            name = f'{family}_{round(mass*1000)}g_v1'
            body, parts, si = sample_body(name, family, mass)
            tree = ET.Element('mujoco', model=name); world = ET.SubElement(tree, 'worldbody'); world.append(body)
            ET.indent(tree); path = out / f'{name}.xml'; ET.ElementTree(tree).write(path, encoding='unicode')
            # Compile the actual serialized include, not only the in-memory body.
            loaded = mujoco.MjModel.from_xml_path(str(path.resolve())); bid = loaded.body(name).id
            actualI = rotation(loaded.body_iquat[bid]) @ np.diag(loaded.body_inertia[bid]) @ rotation(loaded.body_iquat[bid]).T
            if (abs(loaded.body_mass[bid]-mass)>1e-12 or
                not np.allclose(loaded.body_ipos[bid], si['com_body_m'], rtol=0, atol=1e-12) or
                not np.allclose(actualI, si['inertia_at_com_body_kg_m2'], rtol=1e-10, atol=1e-14)):
                raise ValueError(f'Serialized sample SI differs: {name}')
            catalog['objects'].append({'object_id': name, 'family': family,
                'development_only': mass==.05, 'model': path.name,
                'model_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'native_dynamic_bodies': 1, 'collision_leaves': len(parts),
                'geometry': parts, 'SI': si, 'grip_diameter_m': .012,
                'ground_grip_height_m': -si['bounds_body_m'][0][2],
                'floor_birth_origin_m': list(map(float, body.get('pos').split())),
                'native_serialized_si_verified': True, 'full_task_qualification': False})
    (out / 'object_catalog.json').write_text(json.dumps(catalog, indent=2)+'\n')
    print(json.dumps({'objects': len(catalog['objects']), 'robot_modified': False, 'formal_masses_kg': catalog['formal_masses_kg']}))


if __name__ == '__main__':
    main()
