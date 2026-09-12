"""Re-run the preserved 100 g free-contact cargo task using public package assets."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from sai_agent.cargo_task import CargoTask
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--height',type=float,default=.018);p.add_argument('--no-clamp',action='store_true');p.add_argument('--require-pass',action='store_true');a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=True)
result=CargoTask(a.height,a.no_clamp).run()
(a.out/'trace.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
summary={k:v for k,v in result.items() if k not in ['samples','limitations']}
(a.out/'result.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if a.require_pass:
 if a.no_clamp:assert not result['success'] and result['placed_in_cargo'] and result['physics_cargo_checks']==0
 else:assert result['success']
