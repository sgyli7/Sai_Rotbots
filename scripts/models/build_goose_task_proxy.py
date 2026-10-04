"""Reproduce the frozen role-support proxy without changing manufacturing CAD."""
from pathlib import Path
import argparse,json,hashlib,xml.etree.ElementTree as ET
import numpy as np,trimesh
ROOT=Path(__file__).resolve().parents[2]

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
 src=ROOT/'robots/Goose_V0.1/source/task_proxy_11_v1';roles=json.loads((src/'role_supports.json').read_text());templates=json.loads((src/'geometry_templates.json').read_text());root=ET.parse(src/'mechanical_tree.xml').getroot();bodies={b.get('name'):b for b in root.iter('body')}
 for r in roles:
  mesh=trimesh.Trimesh(np.array(r['vertices']),np.array(r['triangles']),process=False);mesh.export(args.out/r['file'],include_normals=False,digits=12)
  ET.SubElement(bodies[r['body']],'geom',**templates['geometries'][r['name']])
 for name in templates['asset_order']:ET.SubElement(root.find('asset'),'mesh',name=name,file=name+'.obj',maxhullvert='-1')
 ET.indent(root);ET.ElementTree(root).write(args.out/'robot.xml',encoding='unicode')
 expected=json.loads((ROOT/'robots/Goose_V0.1/configs/task_proxy_11_v1_contract.json').read_text());outputs={'robot.xml':expected['model_sha256'],**expected['asset_sha256']}
 for name,digest in outputs.items():
  if hashlib.sha256((args.out/name).read_bytes()).hexdigest()!=digest:raise ValueError('Reproduction differs from frozen artifact: '+name)
 print('Reproduced byte-identical XML and all eleven collision assets.')
if __name__=='__main__':main()
