import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from sai_agent.gpu_backend import benchmark

p = argparse.ArgumentParser()
p.add_argument('--worlds', type=int, default=64)
p.add_argument('--steps', type=int, default=150)
args = p.parse_args()
result = benchmark(ROOT / 'models/locomotion.xml', args.worlds, args.steps)
(ROOT / 'artifacts').mkdir(exist_ok=True)
(ROOT / 'artifacts/gpu-benchmark.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
