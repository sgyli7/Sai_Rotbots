"""Preview real native skins on the preserved stage-two candidate assembly.

Explicitly mixed maturity: the rest of the robot still has unmanufactured
architecture parts. This scene can never be called final appearance.
"""
from pathlib import Path
import hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parents[2]

def main():
    r=ROOT/'robots/Goose_V0.1'
    old=r/'cad/source/stage_two_architecture/scene.json';native=r/'cad/source/manufacturing_skins/quad_scene.json';layout=r/'configs/manufacturing_head_layout.json'
    s=json.loads(old.read_text());n=json.loads(native.read_text());l=json.loads(layout.read_text());names={p['name'] for p in n['parts']}
    parts=[p for p in s['parts'] if p['name'] not in names and p['name']!='goose_head_shell']
    for p in parts:
        if p['name'] in l['translation_applies_to']:
            p['vertices']=(np.array(p['vertices'])+np.array(l['optical_module_translation_from_stage_two_m'])).tolist()
            p['source_sha256']=hashlib.sha256(json.dumps(p['vertices'],separators=(',',':')).encode()).hexdigest()
    parts+=n['parts'];out=r/'cad/source/manufacturing_preview';out.mkdir(exist_ok=True)
    inputs=[old,native,layout,Path(__file__)]
    payload=dict(unit='m',status='NATIVE_SKIN_INSTALLATION_PREVIEW_OTHER_STRUCTURE_STILL_STAGE_TWO_CANDIDATE',manufacturing_pass=False,parts=parts,source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},scope='Native skins and coherent optical offset; old candidate forks, motors, feet and jaw remain unreleased. No final assembly or training model change.')
    (out/'scene.json').write_text(json.dumps(payload,separators=(',',':'))+'\n')
    print(len(parts),'parts; skins native, remaining structure not released')
if __name__=='__main__':main()
