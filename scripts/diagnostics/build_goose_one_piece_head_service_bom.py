"""Publish the one-piece head replacement and matching19-body SI table."""
from pathlib import Path
import csv
import hashlib
import json
from openpyxl import Workbook

ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    paths=[R/'cad/exports/one_piece_head_service/manifest.json',R/'evidence/one_piece_head_service_parameters.json',R/'configs/one_piece_head_service.json']
    kit,params,cfg=[json.loads(p.read_text()) for p in paths]
    part=kit['parts'][0]
    row=dict(part=part['name'],quantity=1,material='PETG nominal1270kg/m3, printing unqualified',mass_kg=part['mass_kg'],
        replaces=';'.join(kit['replaces_existing_parts']),main_nominal_wall_mm=cfg['main_nominal_normal_wall_mm'],
        front_nominal_radial_wall_mm=cfg['front_nominal_radial_wall_mm'],step=part['files']['step']['path'],stl=part['files']['stl']['path'],
        manufacturing_release=False)
    csv_path=R/'hardware/one_piece_head_service_bom.csv'
    with csv_path.open('w',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=list(row),lineterminator='\n');writer.writeheader();writer.writerow(row)
    fields=['body','mass_kg','com_x_m','com_y_m','com_z_m','ixx_kg_m2','iyy_kg_m2','izz_kg_m2','ixy_kg_m2','ixz_kg_m2','iyz_kg_m2'];bodies=[]
    for b in params['bodies']:
        i=b['inertia_at_com_body_kg_m2'];bodies.append(dict(zip(fields,[b['name'],b['mass_kg'],*b['com_local_m'],i[0][0],i[1][1],i[2][2],i[0][1],i[0][2],i[1][2]])))
    body_path=R/'hardware/one_piece_head_service_body_parameters.csv'
    with body_path.open('w',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(bodies)
    book=Workbook();sheet=book.active;sheet.title='head_replacement';sheet.append(list(row));sheet.append(list(row.values()));sheet.freeze_panes='A2'
    sheet=book.create_sheet('neutral_si_bodies');sheet.append(fields)
    for b in bodies:sheet.append([b[f] for f in fields])
    sheet.freeze_panes='A2';xlsx_path=R/'hardware/one_piece_head_service_bom.xlsx';book.save(xlsx_path)
    result=dict(schema='goose_one_piece_head_nominal_bom_v1',status='ONE_PRINT_HEAD_REPLACEMENT_NOT_MANUFACTURING_RELEASE',
        rows=[row],body_rows=bodies,active_axes=18,source_objects=460,nominal_conditional_robot_mass_kg=params['nominal_conditional_mass_kg'],
        delta_from462_kg=params['delta_from462_kg'],original_other_hardware_reserves_unchanged=True,
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in paths+[Path(__file__)]},outputs={str(p.relative_to(R)):sha(p) for p in [csv_path,body_path,xlsx_path]})
    (R/'hardware/one_piece_head_service_bom.json').write_text(json.dumps(result,indent=2)+'\n');print('ONE PIECE HEAD BOM',row['mass_kg'],'kg; robot',params['nominal_conditional_mass_kg'],'kg;19SIbodies',flush=True)

if __name__=='__main__':main()
