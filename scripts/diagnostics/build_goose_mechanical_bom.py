"""Extract the current Goose mechanical candidate BOM from scene, mass ledger, and CAD manifests.

This is a source extraction. Matching hashes or masses do not release manufacturing,
the whole robot, or stage three/four. The stage-two actuator table is a priced
architecture list, not this candidate's complete part list.
"""
from pathlib import Path
import csv, hashlib, json, re, time

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / 'robots/Goose_V0.1'
BOM_PATH = R / 'hardware/mechanical_candidate_bom.csv'
FASTENER_PATH = R / 'hardware/mechanical_candidate_fasteners.csv'
MANIFEST_PATH = R / 'hardware/mechanical_candidate_bom_manifest.json'

BOM_FIELDS = [
    'part_id', 'scene_part_id', 'rigid_body', 'rigid_body_status', 'scene_group', 'role', 'role_status',
    'scene_display_material', 'material', 'material_status', 'density_kg_m3', 'density_status',
    'mass_kg', 'mass_basis', 'mass_status', 'step_path', 'stl_path', 'npz_path', 'geometry_hash_status',
    'manufacturing_released', 'manufacturing_status', 'sku', 'sku_source', 'sku_status',
    'unit_usd_public_reference', 'price_status', 'quantity', 'quantity_status', 'process', 'process_status',
    'load_basis', 'load_basis_status', 'cad_manifest', 'notes',
]
FASTENER_FIELDS = [
    'fastener_id', 'ledger_mass_item', 'source', 'assembly', 'role', 'rigid_body', 'anchor_part',
    'thread', 'length_mm', 'count', 'clearance_stack_mm', 'washer_stack_mm', 'clamped_stack_mm',
    'engagement_mm', 'minimum_engagement_mm', 'maximum_insertion_mm', 'max_engagement_mm',
    'mass_upper_estimate_kg', 'mass_basis', 'length_geometry_screen', 'shared_case_bolt', 'released',
    'sku', 'sku_status', 'stack_status', 'engagement_status', 'price_status', 'process_status',
    'load_basis_status', 'notes',
]


def read_stable(path, attempts=8):
    previous = None
    for attempt in range(attempts):
        data = path.read_bytes()
        if previous is not None and data == previous:
            return data
        previous = data
        if attempt + 1 < attempts:
            time.sleep(0.05)
    raise RuntimeError(f'input changed during read: {path}')


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def cell(value):
    if value is None or value == '':
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, float):
        return json.dumps(value)
    if isinstance(value, list):
        return ';'.join(cell(item) for item in value)
    return str(value)


def blank_status(value, sourced):
    return sourced if value not in (None, '') else 'unresolved'


def load_json(path, store):
    data = read_stable(path)
    store[rel(path)] = sha256(data)
    return json.loads(data)


def load_text(path, store):
    data = read_stable(path)
    store[rel(path)] = sha256(data)
    return data.decode()


def actuator_bom_row(actuator_id, bom_rows):
    if actuator_id.startswith('xc330_m288'):
        hits = [row for row in bom_rows if row['model'].startswith('XC330-M288-T')]
    else:
        match = re.fullmatch(r'ak(\d+)_(\d+)_v(\d+)(?:_.+)?', actuator_id)
        if not match:
            return None
        prefix = f"AK{match.group(1)}-{match.group(2)} V{match.group(3)}.0"
        hits = [row for row in bom_rows if row['model'].startswith(prefix)]
    return hits[0] if len(hits) == 1 else None


def basis_bom_row(basis, bom_rows):
    hits = []
    for row in bom_rows:
        short = row['model'].split(' KV')[0]
        if short and short in basis:
            hits.append(row)
    return hits[0] if len(hits) == 1 else None


def explicit_sku(text):
    for token in ('JTEKT698', 'Pololu D24V90F5', 'Pololu D24V22F5', 'CNHL 220406BK', 'iglidur GFM0506-05'):
        if token in text:
            return token
    if 'Purchased SKF61800' in text:
        return 'SKF61800'
    return ''


def repo_path(path_text):
    path = Path(path_text)
    if path.is_absolute():
        return path
    if path_text.startswith('robots/'):
        return ROOT / path
    return R / path


def file_status(path_text, expected):
    if not path_text or not expected:
        return 'unresolved'
    path = repo_path(path_text)
    if not path.is_file():
        return 'missing'
    digest = sha256(read_stable(path))
    return 'verified' if digest == expected else 'mismatch'


def geometry_for(part, manifests_by_hash):
    hits = manifests_by_hash.get((part['name'], part.get('source_sha256')), [])
    manifests = sorted({hit['manifest'] for hit in hits})
    if len(manifests) > 1:
        return {'conflict': manifests}
    cad = hits[0]['part'] if len(manifests) == 1 else None
    files = (cad or {}).get('files') or {}
    chosen = {}
    for kind in ('step', 'stl', 'npz'):
        info = files.get(kind) or {}
        path_text = info.get('path') or ''
        expected = info.get('sha256') or ''
        if kind == 'npz' and not path_text:
            scene_path = part.get('geometry_npz') or ''
            if scene_path:
                path_text = scene_path
                expected = part.get('source_sha256') or ''
        if path_text:
            chosen[kind] = {'path': path_text, 'sha256': expected, 'status': file_status(path_text, expected)}
    if cad is None and part.get('geometry_npz'):
        status = file_status(part['geometry_npz'], part.get('source_sha256'))
        if status == 'mismatch':
            status = 'scene_hash_differs_from_file'
        chosen['npz'] = {'path': part['geometry_npz'], 'sha256': part.get('source_sha256') or '', 'status': status}
    statuses = [item['status'] for item in chosen.values()]
    if not statuses:
        overall = 'unresolved'
    elif 'mismatch' in statuses:
        overall = 'mismatch'
    elif 'missing' in statuses:
        overall = 'missing'
    elif 'scene_hash_differs_from_file' in statuses:
        overall = 'scene_hash_differs_from_file'
    elif any(status != 'verified' for status in statuses):
        overall = 'unresolved'
    else:
        overall = 'verified'
    return {'cad': cad, 'manifest': manifests[0] if len(manifests) == 1 else '', 'files': chosen, 'geometry_hash_status': overall}


def manufacturing_fields(part, cad, basis, name):
    released = None if cad is None else cad.get('manufacturing_released')
    named_allocation = any(token in name for token in ('allocation', 'allowance', 'reserve'))
    basis_allocation = 'allocation' in basis and 'remaining allowances' not in basis
    if 'specified held-object' in basis:
        status = 'not_a_hardware_part'
    elif named_allocation or basis_allocation:
        status = 'allocation_not_a_selected_part'
    elif released is False:
        status = 'unreleased'
    elif released is True:
        status = 'source_says_released'
    else:
        status = 'unresolved'
    return released, status


def sku_fields(name, basis, notes, joints, bom_rows):
    note_sku = explicit_sku(notes)
    basis_sku = explicit_sku(basis)
    basis_row = basis_bom_row(basis, bom_rows)
    contract_row = actuator_bom_row(joints[name], bom_rows) if name in joints else None
    if basis_row and contract_row and basis_row['model'] != contract_row['model']:
        return '', '', 'unresolved', '', 'unresolved'
    row = contract_row or basis_row
    if row:
        model = row['model']
        if model.startswith('XC330-M288-T'):
            model = 'XC330-M288-T'
        source = 'stage_two_contract_joint_and_stage_two_actuator_bom' if contract_row else 'mass_basis_and_stage_two_actuator_bom'
        return model, source, 'sourced', row['unit_usd_public_reference'], row['status']
    token = basis_sku or note_sku
    if token:
        source = 'mass_basis' if basis_sku else 'cad_note'
        return token, source, 'sourced', '', 'unresolved'
    return '', '', 'unresolved', '', 'unresolved'


def quantity_fields(basis):
    match = re.match(r'(\d+) iglidur\b', basis)
    if match:
        return match.group(1), 'stated_in_mass_basis_not_a_purchase_release'
    return '', 'unresolved'


def process_fields(notes):
    if 'CNC6061-T6' in notes:
        return 'CNC6061-T6', 'sourced_cad_note'
    return '', 'unresolved'


def load_fields(basis):
    match = re.search(r'C0r\d+N', basis)
    if match:
        return match.group(0), 'sourced_mass_basis'
    return '', 'unresolved'


def scene_row(part, item, geo, joints, bom_rows):
    cad = geo.get('cad') or {}
    basis = '' if item is None else item['basis']
    notes = ' | '.join(cad.get('notes') or [])
    material = cad.get('material') or ''
    density = cad.get('density_kg_m3')
    released, manufacturing_status = manufacturing_fields(part, cad if geo.get('cad') else None, basis, part['name'])
    sku, sku_source, sku_status, price, price_status = sku_fields(part['name'], basis, notes, joints, bom_rows)
    quantity, quantity_status = quantity_fields(basis)
    process, process_status = process_fields(notes)
    load_basis, load_status = load_fields(basis)
    body = part.get('body') or ('' if item is None else item['body'])
    files = geo.get('files') or {}
    if item is None:
        mass, mass_basis, mass_status = '', '', 'unresolved'
    else:
        mass, mass_basis, mass_status = item['mass_kg'], basis, 'ledger_item'
        if cad and abs(item['mass_kg'] - cad.get('mass_kg', item['mass_kg'])) > 1e-9:
            mass_status = 'ledger_cad_disagreement'
    return {
        'part_id': part['name'],
        'scene_part_id': '',
        'rigid_body': body,
        'rigid_body_status': blank_status(body, 'sourced'),
        'scene_group': part.get('group') or '',
        'role': part.get('role') or '',
        'role_status': blank_status(part.get('role'), 'sourced_scene'),
        'scene_display_material': part.get('material') or '',
        'material': material,
        'material_status': 'sourced_cad' if material else 'unresolved',
        'density_kg_m3': '' if density is None else density,
        'density_status': 'sourced_cad' if density is not None else 'unresolved',
        'mass_kg': mass,
        'mass_basis': mass_basis,
        'mass_status': mass_status,
        'step_path': (files.get('step') or {}).get('path', ''),
        'stl_path': (files.get('stl') or {}).get('path', ''),
        'npz_path': (files.get('npz') or {}).get('path', ''),
        'geometry_hash_status': geo.get('geometry_hash_status', 'unresolved'),
        'manufacturing_released': '' if released is None else released,
        'manufacturing_status': manufacturing_status,
        'sku': sku,
        'sku_source': sku_source,
        'sku_status': sku_status,
        'unit_usd_public_reference': price,
        'price_status': price_status,
        'quantity': quantity,
        'quantity_status': quantity_status,
        'process': process,
        'process_status': process_status,
        'load_basis': load_basis,
        'load_basis_status': load_status,
        'cad_manifest': geo.get('manifest') or '',
        'notes': notes,
    }


def ledger_row(item, scene_part, geo, joints, bom_rows):
    row = scene_row(scene_part, item, geo or {'files': {}, 'geometry_hash_status': 'unresolved'}, joints, bom_rows) if scene_part else None
    if row:
        row['part_id'] = item['name']
        row['scene_part_id'] = scene_part['name']
        row['mass_kg'] = item['mass_kg']
        row['mass_basis'] = item['basis']
        row['mass_status'] = 'ledger_item'
        row['rigid_body'] = item['body']
        row['rigid_body_status'] = 'sourced'
        sku, sku_source, sku_status, price, price_status = sku_fields(item['name'], item['basis'], row['notes'], joints, bom_rows)
        row.update(sku=sku, sku_source=sku_source, sku_status=sku_status, unit_usd_public_reference=price, price_status=price_status)
        return row
    basis = item['basis']
    released, manufacturing_status = manufacturing_fields({}, None, basis, item['name'])
    sku, sku_source, sku_status, price, price_status = sku_fields(item['name'], basis, '', joints, bom_rows)
    quantity, quantity_status = quantity_fields(basis)
    load_basis, load_status = load_fields(basis)
    return {
        'part_id': item['name'], 'scene_part_id': '', 'rigid_body': item['body'], 'rigid_body_status': 'sourced',
        'scene_group': '', 'role': '', 'role_status': 'unresolved', 'scene_display_material': '',
        'material': '', 'material_status': 'unresolved', 'density_kg_m3': '', 'density_status': 'unresolved',
        'mass_kg': item['mass_kg'], 'mass_basis': basis, 'mass_status': 'ledger_item',
        'step_path': '', 'stl_path': '', 'npz_path': '', 'geometry_hash_status': 'unresolved',
        'manufacturing_released': '', 'manufacturing_status': manufacturing_status,
        'sku': sku, 'sku_source': sku_source, 'sku_status': sku_status,
        'unit_usd_public_reference': price, 'price_status': price_status,
        'quantity': quantity, 'quantity_status': quantity_status, 'process': '', 'process_status': 'unresolved',
        'load_basis': load_basis, 'load_basis_status': load_status, 'cad_manifest': '', 'notes': '',
    }


def fastener_rows(pitch, hip, ledger, items):
    rows = []

    def add(source, record, ledger_name, stack_keys):
        item = items[ledger_name]
        clearance = record.get('clearance_stack_mm')
        washer = record.get('washer_stack_mm', record.get('washer_mm'))
        clamped = record.get('clamped_stack_mm')
        engagement = record.get('effective_engagement_mm', record.get('engagement_mm'))
        minimum = record.get('minimum_engagement_mm')
        maximum = record.get('maximum_insertion_mm')
        cap = record.get('max_engagement_mm')
        stack_sourced = any(value not in (None, '', []) for value in (clearance, washer, clamped))
        engagement_sourced = engagement not in (None, '')
        anchor = record.get('anchor_part') or record.get('anchor') or ''
        assembly = record.get('assembly') or ''
        role = record.get('role') or record.get('name') or ''
        rows.append({
            'fastener_id': f'{source}:{assembly or record.get("name")}:{role}:{anchor}',
            'ledger_mass_item': ledger_name,
            'source': source,
            'assembly': assembly,
            'role': role,
            'rigid_body': record.get('body') or item['body'],
            'anchor_part': anchor,
            'thread': record.get('thread'),
            'length_mm': record.get('length_mm'),
            'count': record.get('count'),
            'clearance_stack_mm': clearance,
            'washer_stack_mm': washer,
            'clamped_stack_mm': clamped,
            'engagement_mm': engagement,
            'minimum_engagement_mm': minimum,
            'maximum_insertion_mm': maximum,
            'max_engagement_mm': cap,
            'mass_upper_estimate_kg': record.get('mass_upper_estimate_kg'),
            'mass_basis': item['basis'],
            'length_geometry_screen': record.get('length_pass'),
            'shared_case_bolt': record.get('shared_case_bolt'),
            'released': record.get('released'),
            'sku': '',
            'sku_status': 'unresolved',
            'stack_status': 'sourced' if stack_sourced else 'unresolved',
            'engagement_status': 'sourced' if engagement_sourced else 'unresolved',
            'price_status': 'unresolved',
            'process_status': 'unresolved',
            'load_basis_status': 'unresolved',
            'notes': record.get('notes') or '',
            '_stack_keys': stack_keys,
        })

    for record in pitch['rows']:
        add('robots/Goose_V0.1/hardware/native_pitch_fastener_stacks.json', record, f"{record['assembly']}_{record['role']}_fastener_mass_bound", ('clearance_stack_mm',))
    for record in hip['rows']:
        add('robots/Goose_V0.1/hardware/hip_roll_carrier_fasteners.json', record, f"{record['assembly']}_{record['role']}_fastener_bound", ('clearance_stack_mm', 'washer_mm'))
    for record in ledger['ankle_fasteners']:
        add('robots/Goose_V0.1/evidence/body_bay_mechanical_parameters.json:ankle_fasteners', record, f"{record['assembly']}_ankle_{record['role']}_fastener_bound", ('washer_stack_mm', 'clamped_stack_mm'))
    for record in ledger['new_frame_fasteners']:
        add('robots/Goose_V0.1/evidence/body_bay_mechanical_parameters.json:new_frame_fasteners', record, record['name'], ())
    return rows


def write_csv(path, fields, rows):
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({field: cell(row.get(field)) for field in fields})


def main():
    hashes = {}
    scene = load_json(R / 'cad/source/mechanical_preview/scene.json', hashes)
    ledger = load_json(R / 'evidence/body_bay_mechanical_parameters.json', hashes)
    pitch = load_json(R / 'hardware/native_pitch_fastener_stacks.json', hashes)
    hip = load_json(R / 'hardware/hip_roll_carrier_fasteners.json', hashes)
    contract = load_json(R / 'configs/stage_two_contract.json', hashes)
    bom_text = load_text(R / 'hardware/stage_two_actuator_bom.csv', hashes)
    bom_rows = list(csv.DictReader(bom_text.splitlines()))
    joints = {joint['name']: joint['actuator'] for joint in contract['joints']}

    manifest_paths = sorted((R / 'cad/exports').glob('*/manifest.json'))
    manifests = []
    by_hash = {}
    export_names = {}
    for path in manifest_paths:
        manifest = load_json(path, hashes)
        manifests.append((rel(path), manifest))
        export_names[rel(path)] = []
        for part in manifest.get('parts') or []:
            if not isinstance(part, dict) or 'name' not in part:
                continue
            export_names[rel(path)].append(part['name'])
            for info in (part.get('files') or {}).values():
                if isinstance(info, dict) and info.get('sha256'):
                    by_hash.setdefault((part['name'], info['sha256']), []).append({'manifest': rel(path), 'part': part})

    items = {item['name']: item for item in ledger['items']}
    scene_parts = scene['parts']
    scene_by_name = {part['name']: part for part in scene_parts}
    if len(scene_by_name) != len(scene_parts):
        raise RuntimeError('scene part ids are not unique')
    fasteners = fastener_rows(pitch, hip, ledger, items)
    fastener_names = {row['ledger_mass_item'] for row in fasteners}
    if len(fastener_names) != len(fasteners):
        raise RuntimeError('fastener ledger ids are not unique')

    rows = {}
    catalog_for = {}
    for part in scene_parts:
        stem = part['name'].removesuffix('_catalog_case') if part['name'].endswith('_catalog_case') else ''
        if stem and stem in items and stem not in scene_by_name and part['name'] not in items:
            catalog_for[stem] = part
            continue
        geo = geometry_for(part, by_hash)
        rows[part['name']] = scene_row(part, items.get(part['name']), geo, joints, bom_rows)

    for name, item in items.items():
        if name in fastener_names or name in rows:
            continue
        scene_part = catalog_for.get(name)
        geo = geometry_for(scene_part, by_hash) if scene_part else None
        rows[name] = ledger_row(item, scene_part, geo, joints, bom_rows)

    bom = [rows[name] for name in sorted(rows)]
    fasteners = sorted(fasteners, key=lambda row: row['fastener_id'])
    write_csv(BOM_PATH, BOM_FIELDS, bom)
    write_csv(FASTENER_PATH, FASTENER_FIELDS, fasteners)

    current_names = set(scene_by_name)
    removed_not_reinstalled = sorted(set(scene['removed_parts']) - current_names)
    covered_scene = {row['part_id'] for row in bom if row['part_id'] in current_names}
    covered_scene |= {row['scene_part_id'] for row in bom if row['scene_part_id']}
    bom_mass = sum(float(row['mass_kg']) for row in bom if row['mass_kg'] != '')
    fastener_mass = sum(float(row['mass_upper_estimate_kg']) for row in fasteners)
    ledger_mass = sum(item['mass_kg'] for item in ledger['items'])
    payload = items['specified_payload_50g']['mass_kg']
    cad_disagreement = [row['part_id'] for row in bom if row['mass_status'] == 'ledger_cad_disagreement']
    hash_bad = [row['part_id'] for row in bom if row['geometry_hash_status'] in ('mismatch', 'missing')]
    scene_hash_differs = []
    for row in bom:
        if row['geometry_hash_status'] != 'scene_hash_differs_from_file':
            continue
        current = []
        for manifest, names in export_names.items():
            if row['part_id'] in names:
                current.append(manifest)
        scene_hash_differs.append({
            'part_id': row['part_id'],
            'scene_npz_path': row['npz_path'],
            'scene_source_sha256': scene_by_name[row['part_id']]['source_sha256'],
            'current_file_sha256': sha256(read_stable(repo_path(row['npz_path']))) if row['npz_path'] else '',
            'current_exports_with_same_name': current,
        })
    fastener_mass_bad = [
        row['fastener_id'] for row in fasteners
        if abs(float(row['mass_upper_estimate_kg']) - items[row['ledger_mass_item']]['mass_kg']) > 1e-9
        or row['rigid_body'] != items[row['ledger_mass_item']]['body']
    ]
    physical_keys = [
        (row['assembly'], row['role'], row['anchor_part'], row['thread'], cell(row['length_mm']), cell(row['count']))
        for row in fasteners
    ]
    export_not_in_scene = {
        manifest: sorted({name for name in names if name not in current_names})
        for manifest, names in export_names.items()
        if any(name not in current_names for name in names)
    }
    hash_matched = {}
    for part in scene_parts:
        hits = by_hash.get((part['name'], part.get('source_sha256')), [])
        if hits:
            hash_matched[part['name']] = hits[0]['manifest']
    superseded = {}
    for manifest, names in export_names.items():
        count = sum(1 for name in names if name in hash_matched and hash_matched[name] != manifest)
        if count:
            superseded[manifest] = count

    checks = {
        'part_ids_unique': len({row['part_id'] for row in bom}) == len(bom),
        'scene_part_ids_unique': len({row['scene_part_id'] for row in bom if row['scene_part_id']}) == sum(bool(row['scene_part_id']) for row in bom),
        'scene_parts_covered_once': covered_scene == current_names,
        'removed_parts_excluded': not (set(removed_not_reinstalled) & {row['part_id'] for row in bom}),
        'fastener_ids_unique': len({row['fastener_id'] for row in fasteners}) == len(fasteners),
        'fastener_physical_rows_unique': len(set(physical_keys)) == len(physical_keys),
        'fastener_ledger_mass_matches': not fastener_mass_bad,
        'ledger_mass_closed': abs(bom_mass + fastener_mass - ledger_mass) <= 1e-9,
        'nominal_mass_excludes_payload': abs(ledger['nominal_conditional_mass_kg'] - (ledger_mass - payload)) <= 1e-9,
        'scene_nominal_matches_ledger': scene['nominal_conditional_mass_kg'] == ledger['nominal_conditional_mass_kg'],
        'cad_mass_matches_ledger': not cad_disagreement,
        'cited_geometry_hashes_match': not hash_bad,
        'actuator_bom_quantity_not_copied': all(row['quantity'] not in {row_bom['quantity'] for row_bom in bom_rows} for row in bom),
        'manufacturing_pass_false': True,
        'whole_robot_release_false': True,
        'stage_three_complete_false': True,
        'stage_four_complete_false': True,
    }
    no_step = [row['part_id'] for row in bom if not row['step_path']]
    no_stl = [row['part_id'] for row in bom if not row['stl_path']]
    no_npz = [row['part_id'] for row in bom if not row['npz_path']]
    no_body = [row['part_id'] for row in bom if not row['rigid_body']]
    no_material = [row['part_id'] for row in bom if not row['material']]
    no_sku = [row['part_id'] for row in bom if not row['sku']]
    report = {
        'schema': 'goose_mechanical_candidate_bom_extract_v1',
        'manufacturing_pass': False,
        'whole_robot_release': False,
        'stage_three_complete': False,
        'stage_four_complete': False,
        'mass_or_hash_equality_is_not_an_engineering_release': True,
        'stage_two_actuator_bom_is_not_the_current_complete_bom': True,
        'bookkeeping_ok': all(checks.values()),
        'bookkeeping_checks': checks,
        'scene_status': scene['status'],
        'scene_scope': scene['scope'],
        'nominal_conditional_mass_kg': ledger['nominal_conditional_mass_kg'],
        'ledger_mass_including_payload_kg': ledger_mass,
        'bom_recorded_mass_kg': bom_mass,
        'fastener_upper_mass_kg': fastener_mass,
        'payload_mass_kg': payload,
        'bom_row_count': len(bom),
        'fastener_row_count': len(fasteners),
        'scene_part_count': len(scene_parts),
        'source_hashes': hashes,
        'outputs': [rel(BOM_PATH), rel(FASTENER_PATH), rel(MANIFEST_PATH)],
        'uncovered': {
            'scene_scope_not_released': scene['scope'],
            'removed_and_not_reinstalled': removed_not_reinstalled,
            'export_parts_not_in_current_scene': export_not_in_scene,
            'same_name_exports_whose_hash_is_not_current': superseded,
            'parts_without_step': no_step,
            'parts_without_stl': no_stl,
            'parts_without_npz': no_npz,
            'parts_without_rigid_body': no_body,
            'parts_without_engineering_material': no_material,
            'parts_without_sourced_sku': no_sku,
            'parts_with_unresolved_process': [row['part_id'] for row in bom if row['process_status'] == 'unresolved'],
            'parts_with_unresolved_quantity': [row['part_id'] for row in bom if row['quantity_status'] == 'unresolved'],
            'parts_with_unresolved_price': [row['part_id'] for row in bom if row['price_status'] == 'unresolved'],
            'parts_with_unresolved_load_basis': [row['part_id'] for row in bom if row['load_basis_status'] == 'unresolved'],
            'fasteners_without_vendor_sku': [row['fastener_id'] for row in fasteners],
            'fasteners_without_stack': [row['fastener_id'] for row in fasteners if row['stack_status'] == 'unresolved'],
            'fasteners_without_engagement': [row['fastener_id'] for row in fasteners if row['engagement_status'] == 'unresolved'],
            'scene_geometry_hash_differs_from_current_file': scene_hash_differs,
            'contract_joints_without_bom_part_id': sorted(set(joints) - {row['part_id'] for row in bom}),
            'stage_two_actuator_architecture_quantities_not_applied_per_part': bom_rows,
        },
        'source_limitations': {
            'mechanical_parameters': ledger.get('limitations') or [],
            'native_pitch_fastener_stacks': pitch.get('limitations') or [],
            'hip_roll_carrier_fasteners': hip.get('limitations') or [],
        },
        'extraction_notes': [
            'One row is one current scene part or one non-fastener mass-ledger item. Catalog-case meshes are aliases of the joint mass item and are not a second mass.',
            'STEP, STL, and NPZ paths are copied only from the export whose file hash equals the scene source hash, or from a scene NPZ whose bytes match that hash.',
            'Pitch, hip-roll, ankle, neck-root, and body-bay frame fastener rows come from the incremental lists already present in the mass ledger. Derived CSV copies and replaced parts are not added again.',
            'Public actuator prices remain the stage-two reference status. They are not quotations, and the architecture quantities are not purchase quantities.',
        ],
    }
    hashes[rel(Path(__file__))] = sha256(read_stable(Path(__file__)))
    report['source_hashes'] = hashes
    MANIFEST_PATH.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({
        'bookkeeping_ok': report['bookkeeping_ok'],
        'bom_rows': len(bom),
        'fastener_rows': len(fasteners),
        'failed_checks': [name for name, ok in checks.items() if not ok],
        'cad_disagreement': cad_disagreement,
        'hash_bad': hash_bad[:12],
        'fastener_mass_bad': fastener_mass_bad[:8],
    }, indent=2))
    return 0 if report['bookkeeping_ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
