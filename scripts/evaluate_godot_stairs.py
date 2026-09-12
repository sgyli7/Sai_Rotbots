"""Independent continuous-flight checks from actual Godot/Jolt telemetry."""
import argparse,json
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,default=Path('artifacts'));p.add_argument('--prefix',default='godot-stairs-');p.add_argument('--out',type=Path,required=True);p.add_argument('--require-pass',action='store_true');a=p.parse_args()
rows=[]
for f in sorted(a.directory.glob(a.prefix+'*.json')):
 raw=json.loads(f.read_text());ss=raw['samples'];last=ss[-1]
 xyz=np.array([s['base_position'] for s in ss]);up=np.array([s['upright'] for s in ss]);wheel=np.array(last['wheel_positions'])
 settled=[s for s in ss if s['time']>last['time']-1]
 final_ground=0 if raw['descending'] else 4*raw['riser']
 checks=dict(all_wheels_cleared=wheel[:,0].min()>1.04,three_second_stop=raw['cleared_at']>=0 and last['time']-raw['cleared_at']>=2.999,
    upright_on_final_level=up[-1]>.9,remained_in_lane=abs(xyz[:,1]).max()<.3,
    height_on_final_level=abs(xyz[-1,2]-(final_ground+.2192))<.02,
    four_wheels_supported=np.mean([s['wheels_supported']==4 for s in settled])>.7,no_fall=up.min()>.6,
    real_forward_key=any(e['key']==87 and e['pressed'] for e in raw['input_events']),
    automatic_stair_selection=any(s['controller_stage']=='stairs' for s in ss))
 rows.append(dict(riser=raw['riser'],descending=raw['descending'],duration=last['time'],final_xyz=xyz[-1].tolist(),min_upright=float(up.min()),
    maximum_lateral_m=float(abs(xyz[:,1]).max()),checks={k:bool(v) for k,v in checks.items()},passed=bool(all(checks.values()))))
result=dict(suite='godot-continuous-stairs-v1',engine=raw['engine'],physics_hz=2000,controller_hz=50,
    sensor='Ground-only raycasts, not camera-based VLA',cases=rows,passed=bool(rows) and all(r['passed'] for r in rows))
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if a.require_pass and not result['passed']:raise SystemExit(1)
