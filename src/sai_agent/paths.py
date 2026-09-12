from pathlib import Path


def resource_root():
    checkout=Path(__file__).resolve().parents[2]
    if (checkout/'models/robot_manifest.json').is_file():return checkout
    bundled=Path(__file__).resolve().parent/'bundle'
    if (bundled/'models/robot_manifest.json').is_file():return bundled
    raise FileNotFoundError('Sai model bundle is missing; install the full distribution')
