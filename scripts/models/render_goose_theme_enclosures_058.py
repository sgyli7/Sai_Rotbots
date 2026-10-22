"""Render the requested theme-coloured exterior without editing the 056 renderer."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'robots/goose_v0_2/configs/enclosure_theme_finish_058.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    argv = sys.argv[sys.argv.index('--') + 1:]

    def option(name, default=None):
        return argv[argv.index(name) + 1] if name in argv else default

    output = option('--output')
    if output is None:
        raise SystemExit('An explicit --output directory is required.')
    config_sha = sha(CONFIG)
    config = json.loads(CONFIG.read_text())
    baseline = ROOT / config['base_renderer']['path']
    assert sha(baseline) == config['base_renderer']['sha256']
    assembly = ROOT / config['assembly_manifest']['path']
    assert sha(assembly) == config['assembly_manifest']['sha256']
    spec = importlib.util.spec_from_file_location('goose056_render_baseline', baseline)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original_role = module.colour_role
    overrides = config['whole_part_role_overrides']
    module.colour_role = lambda row: overrides.get(row['name'], original_role(row))
    extension_sha = sha(Path(__file__))
    module.main()
    name = option('--receipt-name', option('--colorway', 'clay') + '_render_receipt.json')
    receipt_path = Path(output) / name
    receipt = json.loads(receipt_path.read_text())
    assert sha(CONFIG) == config_sha and sha(Path(__file__)) == extension_sha
    for part, role in overrides.items():
        matches = [r for r in receipt['whole_part_finish_bindings'] if r['part'] == part]
        assert len(matches) == 1 and matches[0]['finish'] == role, part
    receipt['finish_variant'] = 'theme_coloured_exterior_covers'
    receipt['renderer_extension'] = {
        'path': str(Path(__file__).relative_to(ROOT)), 'sha256': extension_sha,
        'config': {'path': str(CONFIG.relative_to(ROOT)), 'sha256': config_sha},
        'base_renderer': config['base_renderer'],
        'whole_part_role_overrides': overrides,
        'scope': config['scope'],
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
