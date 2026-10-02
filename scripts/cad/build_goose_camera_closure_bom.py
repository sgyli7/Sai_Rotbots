"""Export the camera/head closure's nominal increment, not a purchase release."""
from pathlib import Path
import csv
import hashlib
import json

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/Goose_V0.1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest_path = ROBOT / 'cad/exports/camera_head_closure/manifest.json'
    kit = json.loads(manifest_path.read_text())
    rows = []
    for part in kit['parts'][:5]:
        rows.append(dict(
            id=part['name'], quantity=1, kind='own_native_candidate',
            nominal_description=part['name'],
            material=('aluminium_density_2700_candidate' if part['name'].startswith('head_frame')
                      else 'petg_density_1270_candidate'),
            mass_each_kg=part['mass_kg'], source_step=part['files']['step']['path'],
            released=False,
            remaining='Exact material, support strength, bought tolerances and full head-shell/frame attachment pending'))
    screws = [part for part in kit['parts'] if '_m2x10' in part['name']]
    washers = [part for part in kit['parts'] if 'nylon_washer' in part['name']]
    for name, parts, description, material in [
        ('camera_m2x10_nominal', screws,
         'M2x10 thread envelope; shown head3.8OD/2.0height; exact boughtSKU/grade/preload unqualified',
         'steel_density_7850_candidate'),
        ('camera_m2_nylon_washer_nominal', washers,
         '4OD/2.2ID/0.5mm nylon insulation washer; exact boughtSKU/creep unqualified',
         'nylon_density_1150_candidate'),
    ]:
        masses = [part['mass_kg'] for part in parts]
        if max(masses) - min(masses) > 1e-10:
            raise ValueError('Unequal nominal hardware masses')
        rows.append(dict(
            id=name, quantity=len(parts), kind='nominal_bought_hardware_not_released',
            nominal_description=description, material=material,
            mass_each_kg=masses[0], source_step='', released=False,
            remaining='Match bought geometry, thread, grade and insulation durability before purchase release'))
    if sum(row['quantity'] for row in rows) != 29:
        raise ValueError('Incomplete nominal kit')
    fields = list(rows[0])
    csv_path = ROBOT / 'hardware/camera_head_closure_bom.csv'
    with csv_path.open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    xlsx_path = ROBOT / 'hardware/camera_head_closure_bom.xlsx'
    book = Workbook()
    sheet = book.active
    sheet.title = 'camera_head_closure'
    sheet.append(fields)
    for row in rows:
        sheet.append([row[key] for key in fields])
    sheet.freeze_panes = 'A2'
    sheet.auto_filter.ref = sheet.dimensions
    for column in sheet.columns:
        sheet.column_dimensions[column[0].column_letter].width = min(
            65, max(14, max(len(str(cell.value)) for cell in column) + 2))
    book.save(xlsx_path)
    payload = dict(
        schema='goose_camera_head_closure_nominal_bom_v1',
        status='NOMINAL_INCREMENT_NOT_PURCHASE_RELEASE', rows=rows, parts=29,
        outputs={str(path.relative_to(ROBOT)): sha(path) for path in [csv_path, xlsx_path]},
        adds_oem_corner_standoffs=False, oem_corner_standoff_thread_unqualified=True,
        camera_mass_allowance_consumed=False,
        source_hashes={str(path.relative_to(ROOT)): sha(path) for path in [manifest_path, Path(__file__)]})
    (ROBOT / 'hardware/camera_head_closure_bom.json').write_text(json.dumps(payload, indent=2) + '\n')
    print('CAMERA NOMINAL BOM', len(rows), 'rows,29pieces; OEM camera/standoffs retained')


if __name__ == '__main__':
    main()
