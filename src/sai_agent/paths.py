from pathlib import Path
import json
import os


def resource_root():
    checkout=Path(__file__).resolve().parents[2]
    if (checkout/'models/robot_manifest.json').is_file():return checkout
    bundled=Path(__file__).resolve().parent/'bundle'
    if (bundled/'models/robot_manifest.json').is_file():return bundled
    raise FileNotFoundError('Sai model bundle is missing; install the full distribution')


def robot_catalog(root=None):
    root = root or resource_root()
    return json.loads((root / 'robots/catalog.json').read_text())['robots']


def model_root(robot_id=None, root=None):
    root = root or resource_root()
    robot_id = robot_id or os.environ.get('SAI_ROBOT_ID', 'Sai_Agent_001')
    entry = robot_catalog(root).get(robot_id)
    if entry is None:
        raise ValueError(f'Unknown robot: {robot_id}')
    return root / entry['models']
