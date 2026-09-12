"""Export the exact actor including observation normalization; check ONNX parity."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import onnx
import onnxruntime as ort
import torch
from tensordict import TensorDict
from rsl_rl.models import MLPModel

p = argparse.ArgumentParser()
p.add_argument('checkpoint', type=Path)
args = p.parse_args()
torch.set_num_threads(2)
saved = torch.load(args.checkpoint, map_location='cpu', weights_only=True)
cfg = saved['metadata']['cfg']
actor_cfg = dict(cfg['actor']); actor_cfg.pop('class_name')
dummy = TensorDict({'policy': torch.zeros(1, 82)}, batch_size=[1])
actor = MLPModel(dummy, cfg['obs_groups'], 'actor', 16, **actor_cfg)
actor.load_state_dict(saved['actor_state_dict'])
actor.eval()
export = actor.as_onnx(verbose=False).cpu().eval()
path = args.checkpoint.with_suffix('.onnx')
torch.onnx.export(export, export.get_dummy_inputs(), str(path), export_params=True,
    opset_version=17, input_names=export.input_names, output_names=export.output_names,
    dynamic_axes={'obs': {0: 'batch'}, 'actions': {0: 'batch'}}, dynamo=False)
onnx.checker.check_model(onnx.load(path))
options = ort.SessionOptions(); options.intra_op_num_threads=2; options.inter_op_num_threads=1
session = ort.InferenceSession(str(path), options, providers=['CPUExecutionProvider'])
rng = np.random.default_rng(109)
errors = []
for batch in [1, 17, 256]:
    # Check both physical-scale and wide-tail inputs against PyTorch.
    x = rng.normal(0, .3, size=(batch,82)).astype(np.float32)
    with torch.no_grad():
        expected = export(torch.from_numpy(x)).numpy()
    got = session.run(None, {'obs': x})[0]
    errors.append(float(np.max(np.abs(expected-got))))
assert max(errors)<1e-4, errors
result = {'checkpoint_sha256': hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
          'onnx_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
          'onnx_opset':17, 'normalization_included':True,
          'batch_sizes':[1,17,256], 'max_absolute_errors':errors,
          'passed': True, 'training': saved['metadata']}
path.with_suffix('.export.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='training'}, indent=2))
