"""Same-candidate hardware delta and neutral SI table; no procurement release."""
from pathlib import Path
import csv, hashlib, json
from openpyxl import Workbook
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 paths=[R/'configs/manual_wing_service.json',R/'cad/exports/manual_wing_service/manifest.json',R/'evidence/manual_wing_service_parameters.json'];cfg,kit,params=[json.loads(p.read_text()) for p in paths]
 rows=[]
 for p in kit['parts']:
  name=p['name'];source='';sku='Self-designed PETG print candidate';basis='Full-density native CAD estimate, print unqualified';material='PETG'
  if name.endswith('_shoulder_screw'):rec=cfg['shoulder_screw'];sku=rec['sku'];source=rec['current_product'];material='SCM435';basis='Own nominal purchased envelope, tolerances/price/delivery unqualified'
  elif name.endswith('_retention_nut'):rec=cfg['retention_nut'];sku=rec['sku'];source=rec['primary_drawing'];material='Steel+nylon';basis=rec['model_basis']
  elif name.endswith('_thumb_screw'):rec=cfg['thumb_screw'];sku=rec['sku'];source=rec['primary_drawing'];material='Steel';basis=rec['mass_basis']
  elif name.endswith('_m3_insert'):sku='Ruthex RX-M3x5.7';source='https://www.ruthex.de/products/ruthex-gewindeeinsatz-m3-100-stuck-rx-m3x5-7';material='Brass';basis='Own nominal maximum-OD envelope; heat setting unqualified'
  elif name.endswith('_m3_washer'):sku='M3 plain washer OD7 ID3.2 t0.5mm';material='Steel';basis='Nominal purchased envelope; confirm actual selected lot dimensions'
  rows.append(dict(part=name,quantity=1,sku=sku,material=material,mass_kg=p['mass_kg'],basis=basis,primary_source=source,step=p['files']['step']['path'],stl=p['files']['stl']['path'],manufacturing_release=False))
 fields=['body','mass_kg','com_x_m','com_y_m','com_z_m','ixx_kg_m2','iyy_kg_m2','izz_kg_m2','ixy_kg_m2','ixz_kg_m2','iyz_kg_m2'];body_rows=[]
 for b in params['bodies']:
  i=b['inertia_at_com_body_kg_m2'];body_rows.append(dict(zip(fields,[b['name'],b['mass_kg'],*b['com_local_m'],i[0][0],i[1][1],i[2][2],i[0][1],i[0][2],i[1][2]])))
 outputs=[]
 for filename,data in [('manual_wing_service_bom.csv',rows),('manual_wing_service_body_parameters.csv',body_rows)]:
  path=R/'hardware'/filename
  with path.open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(data[0]),lineterminator='\n');w.writeheader();w.writerows(data)
  outputs.append(path)
 book=Workbook();sheet=book.active;sheet.title='hardware_delta';sheet.append(list(rows[0]))
 for row in rows:sheet.append(list(row.values()))
 sheet.freeze_panes='A2';sheet=book.create_sheet('neutral_si');sheet.append(fields)
 for row in body_rows:sheet.append([row[f] for f in fields])
 sheet.freeze_panes='A2';xp=R/'hardware/manual_wing_service_bom.xlsx';book.save(xp);outputs.append(xp)
 report=dict(schema='goose_manual_wing_service_bom_v1',scope='Six printed skin replacements plus eighteen nominal purchased fasteners; delta only, retain existing other hardware BOM.',rows=rows,body_rows=body_rows,replaced_parts=kit['replaces_existing_parts'],active_axes=18,source_objects=params['parts'],nominal_conditional_mass_kg=params['nominal_conditional_mass_kg'],delta_from460_kg=params['delta_from460_kg'],other_hardware_reserves_retained=True,manufacturing_release=False,source_hashes={str(p.relative_to(ROOT)):sha(p) for p in paths+[Path(__file__)]},outputs={str(p.relative_to(R)):sha(p) for p in outputs})
 (R/'hardware/manual_wing_service_bom.json').write_text(json.dumps(report,indent=2)+'\n');print('BOM',len(rows),'rows',len(body_rows),'SI bodies',params['nominal_conditional_mass_kg'],'kg')
if __name__=='__main__':main()
