"""Nominal shell support increment and same-source SI body parameters.

The kit includes four replacement skins. Its gross mass is not an addition to
the robot BOM. Purchased insert revision and all generic screws remain gates.
"""
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
    paths = [ROBOT / relative for relative in [
        'cad/exports/torso_shell_mounts/manifest.json',
        'evidence/torso_shell_mount_parameters.json',
        'configs/torso_shell_mounts.json']]
    kit, parameters, config = [json.loads(path.read_text()) for path in paths]
    rows = []
    for part in kit['parts']:
        name = part['name']
        sku, url = '', ''
        if name.startswith('torso_mounted_shell_'):
            kind, material = 'own_replacement_shell_candidate', 'PETG density1270 candidate'
            description = 'Existing exterior; inside9.2OD blind boss,4.0mm pilot; insert fit and strength unqualified'
        elif name.startswith('torso_roof_frame_carrier_'):
            kind, material = 'own_cnc_carrier_candidate', '6061 density2700 candidate'
            description = 'Monolithic frame flange,8x3mm brace and roof pad; machining, fillets, preload and strength unqualified'
        elif name.startswith('torso_roof_m3_insert_'):
            kind, material = 'selected_insert_envelope_not_purchase_released', 'brass density8500 conservative envelope'
            sku, url = config['insert']['sku'], config['insert']['manufacturer_product_url']
            description = 'M3x5.7,maxOD4.6; envelope not printable; purchased revision and PETG heat-set qualification pending'
        else:
            kind, material = 'nominal_hardware_not_purchase_released', 'steel density'+str(part['density_kg_m3'])+' candidate'
            if '_m3x8_' in name:
                description = 'M3x8 nominal screw,head5.5ODx3; insert engagement5.0mm'
            elif name.endswith('_m3x16'):
                description = 'M3x16 nominal screw replaces shared compute M3x12'
            elif name.endswith('_m3x20'):
                description = 'M3x20 nominal screw replaces shared neck power M3x18'
            elif 'raised_m3_nut' in name:
                description = 'M3 nominal nut,AF5.5,height2.4; raised2mm from previous stack'
            elif name.startswith('torso_roof_washer_') or name.startswith('compute_'):
                description = 'Nominal steel washer7ODx3.2IDx0.5mm'
            else:
                description = 'Nominal steel washer6ODx3.2IDx0.5mm'
        rows.append(dict(id=name, quantity=1, kind=kind, nominal_description=description,
            material=material, mass_each_kg=part['mass_kg'], sku=sku, manufacturer_url=url,
            source_step=part['files']['step']['path'], purchase_released=False,
            remaining='Material/grade, purchased tolerances, tool and service paths, preload, full assembly and strength'))
    if len(rows) != 30 or parameters['parts'] != 462:
        raise ValueError('Unexpected candidate scope')
    csv_path = ROBOT / 'hardware/torso_shell_mount_bom.csv'
    fields = list(rows[0])
    with csv_path.open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fields, lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
    xlsx_path = ROBOT / 'hardware/torso_shell_mount_bom.xlsx'
    book = Workbook(); sheet = book.active; sheet.title = 'shell_support_candidate'
    sheet.append(fields)
    for row in rows:
        sheet.append([row[key] for key in fields])
    sheet.freeze_panes = 'A2'; sheet.auto_filter.ref = sheet.dimensions
    for column in sheet.columns:
        sheet.column_dimensions[column[0].column_letter].width = min(
            65, max(14, max(len(str(cell.value)) for cell in column)+2))
    body_fields = ['body','mass_kg','com_x_m','com_y_m','com_z_m',
                   'ixx_kg_m2','iyy_kg_m2','izz_kg_m2','ixy_kg_m2','ixz_kg_m2','iyz_kg_m2']
    body_rows = []
    for body in parameters['bodies']:
        tensor = body['inertia_at_com_body_kg_m2']
        body_rows.append(dict(zip(body_fields, [body['name'],body['mass_kg'],*body['com_local_m'],
            tensor[0][0],tensor[1][1],tensor[2][2],tensor[0][1],tensor[0][2],tensor[1][2]])))
    body_path = ROBOT / 'hardware/torso_shell_mount_body_parameters.csv'
    with body_path.open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=body_fields, lineterminator='\n')
        writer.writeheader(); writer.writerows(body_rows)
    body_sheet = book.create_sheet('neutral_si_bodies'); body_sheet.append(body_fields)
    for row in body_rows:
        body_sheet.append([row[key] for key in body_fields])
    body_sheet.freeze_panes = 'A2'
    book.save(xlsx_path)
    output = dict(schema='goose_torso_shell_mount_nominal_bom_v1',
        status='NOMINAL_REPLACEMENT_INCREMENT_NOT_PURCHASE_OR_TRAINING_RELEASE', rows=rows,
        parts=len(rows), body_rows=body_rows, active_axes=18,
        nominal_conditional_robot_mass_kg=parameters['nominal_conditional_mass_kg'],
        robot_delta_from446_kg=parameters['delta_from446_kg'],
        gross_kit_mass_kg=kit['native_mass_kg'], gross_kit_mass_is_not_robot_increment=True,
        original30g_unclosed_shell_hardware_reserve_retained=True,
        source_hashes={str(path.relative_to(ROOT)):sha(path) for path in paths+[Path(__file__)]},
        outputs={str(path.relative_to(ROBOT)):sha(path) for path in [csv_path,xlsx_path,body_path]})
    (ROBOT / 'hardware/torso_shell_mount_bom.json').write_text(json.dumps(output,indent=2)+'\n')
    print('SHELL MOUNT BOM',len(rows),'nominal pieces,',len(body_rows),'SI bodies; delta',parameters['delta_from446_kg'])


if __name__ == '__main__':
    main()
