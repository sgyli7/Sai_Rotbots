"""Strict native-only merger of intact022 and explicitly frozen A/E replacements.

No physics, synthesized parts, inferred retirement, or inferred motion. A merge plan
normalizes the two authoritative handoffs; every pose must provide an explicit
rigid transform for each moving body. The original sources remain untouched.
"""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import math

W = Path(__file__).resolve().parents[2]
BASE = W / 'experiments/goose_v0_2/intact_bill_rebaseline_022/full_native_manifest.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve(value):
    p = Path(value)
    return p if p.is_absolute() else W / p


def checked(ref):
    p = resolve(ref['path'])
    if not p.is_file() or sha(p) != ref['sha256']:
        raise ValueError(f'Missing or changed frozen input: {p}')
    return p


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(plan):
    require(plan['schema'] == 'intact_head_native_merge_026_v1', 'Unknown schema')
    require(plan['interface_id'], 'Explicit shared interface identity required')
    require(plan['frame'] == '08zero_mm', 'Normalize source transforms explicitly')
    basepath = checked(plan['baseline'])
    require(basepath.resolve() == BASE.resolve(), 'Must reuse intact022 baseline')
    base = json.loads(basepath.read_text())
    old = {p['name']: p for p in base['parts']}
    require(len(old) == len(base['parts']), 'Duplicate baseline occurrence')
    require(set(plan['handoffs']) == {'drive', 'support_carrier'}, 'Both final handoffs required')
    for ref in plan['handoffs'].values():
        checked(ref)
    require(plan['source_interface_confirmation']['drive'] == plan['interface_id'] and
            plan['source_interface_confirmation']['support_carrier'] == plan['interface_id'],
            'Drive/support interface mismatch')
    retired = plan['retired']
    require(len(retired) == len(set(retired)), 'Duplicate retirement')
    require(set(retired) <= set(old), 'Retired occurrence absent from intact022')
    names = set(old) - set(retired)
    for part in plan['new_parts']:
        require(part['name'] not in names, f'Duplicate retained/new occurrence: {part["name"]}')
        names.add(part['name'])
        checked(part['source'])
        require(part['handoff_owner'] in plan['handoffs'], 'Unknown part authority')
        require(part['body'] and part['material'], 'Body/material identity missing')
        require(len(part['translation_to_zero_mm']) == 3, 'Explicit frame transform missing')
        require(part['rotation_xyz_deg'] == [0, 0, 0], 'Rotated source needs explicit normalization upstream')
        mci = part['mci']
        if mci.get('inertia_com_kg_m2') is None:
            require(part.get('catalogue_envelope_only') and mci.get('inertia_status') == 'UNKNOWN_NOT_FABRICATED', 'Only declared catalogue bearing may omit detailed inertia')
            require(mci['mass_kg'] > 0 and len(mci['com_zero_mm']) == 3, 'Bearing mass/location missing')
            continue
        require(mci['mass_kg'] > 0 and len(mci['com_zero_mm']) == 3 and
                len(mci['inertia_com_kg_m2']) == 6, 'True full part MCI required')
        require(all(math.isfinite(x) for x in [mci['mass_kg'], *mci['com_zero_mm'], *mci['inertia_com_kg_m2']]), 'Nonfinite MCI')
    require(set(plan['retired_mci']) == set(retired), 'Retired MCI reconciliation must be occurrence-complete')
    for name, mci in plan['retired_mci'].items():
        require(mci['mass_kg'] > 0 and mci['authority'], f'Retired MCI authority missing: {name}')
    require(plan['kinematics']['input_sign'] in [-1, 1], 'Explicit encoder sign required')
    for key in ['input_axis_zero_mm', 'output_axis_zero_mm', 'input_range_rad',
                'output_range_rad', 'closure_equations', 'same_branch_evidence']:
        require(plan['kinematics'][key], f'Kinematics missing: {key}')
    require({'closed', 'open'} <= set(plan['poses']), 'Both actual closed/open poses required')
    bodies = {p['body'] for p in base['parts'] if p['name'] not in retired} | {p['body'] for p in plan['new_parts']}
    for pose, transforms in plan['poses'].items():
        require(set(transforms) == bodies, f'{pose}: explicit transforms required for every body')
        for tf in transforms.values():
            require(len(tf['axis_zero_mm']) == 3 and len(tf['translation_mm']) == 3 and
                    math.isfinite(tf['rotation_y_deg']), 'Invalid body transform')
    return base


def build(plan, base, output):
    from cadgen import build123d as b, read_step
    require(not output.exists(), 'Refuse overwrite of prior native output')
    output.mkdir(parents=True)
    cache = {}
    parts = []
    for row in base['parts']:
        if row['name'] in plan['retired']:
            continue
        src = checked(row['source'])
        if 'native_part_index' in row:
            if src not in cache:
                tmp = output / 'baseline_authority.brep'
                tmp.write_bytes(gzip.decompress(src.read_bytes()))
                cache[src] = list(b.import_brep(str(tmp)))
            shape = cache[src][row['native_part_index']]
        else:
            shape = read_step(str(src)).translate((-13.55, 0, 32.305))
        parts.append((shape, row['name'], row['body']))
    for row in plan['new_parts']:
        shape = read_step(str(checked(row['source']))).translate(tuple(row['translation_to_zero_mm']))
        parts.append((shape, row['name'], row['body']))
    outputs = {}
    for pose, transforms in plan['poses'].items():
        shapes = []
        for source, name, body in parts:
            tf = transforms[body]
            shape = source.rotate(b.Axis(tuple(tf['axis_zero_mm']), (0, 1, 0)), tf['rotation_y_deg'])
            shape = shape.translate(tuple(tf['translation_mm']))
            shape.label = name
            if 'shell' in name and ('bill' in name or 'grip' in name):
                shape.color = b.Color(1.0, .46, .045)
            elif any(k in name for k in ['shell','hood']):
                shape.color = b.Color(.94, .95, .96)
            elif 'pad' in name:
                shape.color = b.Color(.26, .29, .32)
            else:
                shape.color = b.Color(.64, .68, .73)
            shapes.append(shape)
        dest = output / f'full_head_{pose}.step'
        b.export_step(b.Compound(children=shapes), str(dest))
        outputs[pose] = {'path': str(dest), 'sha256': sha(dest)}
        inside = [s for s, (_, name, _) in zip(shapes, parts) if not any(k in name for k in ['shell', 'hood'])]
        b.export_step(b.Compound(children=inside), str(output / f'internal_{pose}.step'))
    result = dict(schema=plan['schema'], candidate_id=plan['candidate_id'],
                  interface_id=plan['interface_id'], outputs=outputs,
                  retained_names=[r['name'] for r in base['parts'] if r['name'] not in plan['retired']],
                  retained_parts=[r for r in base['parts'] if r['name'] not in plan['retired']],
                  baseline=plan['baseline'], source=dict(path=str(Path(__file__)),sha256=sha(Path(__file__))),
                  poses=plan['poses'], unresolved=plan['unresolved'],
                  source_interface_comparison=plan.get('interface_comparison'),
                  retired=plan['retired'], new_parts=plan['new_parts'],
                  missing_native=base['missing'], handoffs=plan['handoffs'],
                  kinematics=plan['kinematics'], physics_steps=0,
                  mass_delta_kg=sum(p['mci']['mass_kg'] for p in plan['new_parts']) -
                  sum(v['mass_kg'] for v in plan['retired_mci'].values()),
                  limits=['Native source bench handoff only; not physical or manufacturing qualification',
                          'Missing baseline allocations remain missing; no proxy invented',
                          '04/08 and public defaults unchanged; fit/strength requires independent review'])
    (output / 'merged_native_manifest.json').write_text(json.dumps(result, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    base = validate(plan)
    if args.build:
        require(args.out is not None, 'Explicit new export directory required')
        build(plan, base, args.out)
    print(json.dumps({'validation': 'PASS', 'geometry_built': args.build,
                      'source_sha256': sha(Path(__file__)), 'physics_steps': 0}))


if __name__ == '__main__':
    main()
