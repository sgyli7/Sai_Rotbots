import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from sai_agent.gpu_backend import benchmark

p = argparse.ArgumentParser()
p.add_argument('--worlds', type=int, default=64)
p.add_argument('--steps', type=int, default=150)
args = p.parse_args()
result = benchmark(ROOT/'robots/Sai_Agent_001/models/locomotion.xml', args.worlds, args.steps)
out = ROOT / 'artifacts/Sai_Agent_001/gpu_benchmark'
out.mkdir(parents=True, exist_ok=True)
(out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
