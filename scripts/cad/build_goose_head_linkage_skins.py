"""Local cheek and underside clearance; accepted exterior sources unchanged."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path.insert(0,str(ROOT/'scripts/cad'))
import build_goose_manufacturing_skins as base


def main():
    original=base.head_grid
    def grid(scene):
        out,inner=original(scene)
        # A broad, symmetric local relief over the lower cheek maintains the
        # existing brow, camera face and bill silhouette. Both surfaces shift
        # together; minimum normal wall remains a manufacturing gate.
        for points in (out,inner):
            x,z=points[:,:,0],points[:,:,2]
            rise=np.clip((x-110)/8,0,1);rise=rise*rise*(3-2*rise)
            fall=np.clip((174-x)/16,0,1);fall=fall*fall*(3-2*fall)
            low=np.clip((605-z)/20,0,1);low=low*low*(3-2*low)
            points[:,:,1]+=np.sign(points[:,:,1])*3*rise*fall*low
            # The240deg output crank passes below the cheek floor. A lateral
            # expansion alone left actual solids intersecting atZ560..563mm.
            # Lower both native skin surfaces together over a broad smooth
            # chin patch; retain the efficient transmission phase and radius.
            chin_rise=np.clip((x-135)/10,0,1);chin_rise=chin_rise*chin_rise*(3-2*chin_rise)
            chin_fall=np.clip((176-x)/10,0,1);chin_fall=chin_fall*chin_fall*(3-2*chin_fall)
            chin_low=np.clip((580-z)/15,0,1);chin_low=chin_low*chin_low*(3-2*chin_low)
            points[:,:,2]-=4*chin_rise*chin_fall*chin_low
        return out,inner
    base.head_grid=grid
    base.SOURCE=R/'cad/source/head_linkage_clearance_skins';base.EXPORT=R/'cad/exports/head_linkage_clearance_skins'
    base.SOURCE.mkdir(exist_ok=True);base.EXPORT.mkdir(exist_ok=True)
    if not (base.EXPORT/'manifest.json').exists():
        (base.EXPORT/'manifest.json').write_text('{"parts":[]}\n')
        (base.SOURCE/'quad_scene.json').write_text('{"parts":[]}\n')
    sys.argv=[str(Path(__file__)),'--only-heads'];base.main()
    m=json.loads((base.EXPORT/'manifest.json').read_text())
    m['status']='LOCAL_CHEEK_CLEARANCE_CANDIDATE_NOT_INTEGRATED'
    m['replaces_existing_parts']=['goose_head_shell_left','goose_head_shell_right']
    m['source_hashes'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    m['maximum_cheek_shift_mm']=3;m['maximum_chin_lowering_mm']=4
    m['manufacturing_pass']=False;m['final_appearance_pass']=False
    (base.EXPORT/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    q=json.loads((base.SOURCE/'quad_scene.json').read_text())
    for p in q['parts']:p['body']='head_roll'
    (base.SOURCE/'quad_scene.json').write_text(json.dumps(q,separators=(',',':'))+'\n')


if __name__=='__main__':main()
