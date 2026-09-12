"""Batched MuJoCo Warp physics, with GPU-resident mixed actuator control."""
from pathlib import Path
import time

import mujoco
import mujoco_warp as mjw
import numpy as np
import torch
import warp as wp


@wp.kernel
def apply_pd(qpos: wp.array2d(dtype=float), qvel: wp.array2d(dtype=float),
             target: wp.array2d(dtype=float), ctrl: wp.array2d(dtype=float)):
    world, joint = wp.tid()
    if joint % 4 == 3:
        ctrl[world, joint] = wp.clamp(0.4 * (target[world, joint] - qvel[world, joint + 6]), -1.3, 1.3)
    else:
        ctrl[world, joint] = wp.clamp(80.0 * (target[world, joint] - qpos[world, joint + 7])
                                    - 2.0 * qvel[world, joint + 6], -8.0, 8.0)


class WarpBackend:
    def __init__(self, model_path: Path, worlds: int = 64, control_dt: float = .02):
        torch.set_num_threads(2)
        if not torch.cuda.is_available():
            raise RuntimeError('GPU training requires CUDA PyTorch; CPU fallback is not automatic')
        self.device = 'cuda:0'
        wp.init()
        self.cpu_model = mujoco.MjModel.from_xml_path(str(model_path))
        self.worlds = worlds
        self.substeps = round(control_dt / self.cpu_model.opt.timestep)
        assert abs(self.substeps * self.cpu_model.opt.timestep - control_dt) < 1e-8
        with wp.ScopedDevice(self.device):
            self.model = mjw.put_model(self.cpu_model)
            self.data = mjw.make_data(self.cpu_model, nworld=worlds, nconmax=96, njmax=384)
            self.targets_wp = wp.zeros((worlds, 16), dtype=float)
        self.q = wp.to_torch(self.data.qpos)
        self.v = wp.to_torch(self.data.qvel)
        self.target = wp.to_torch(self.targets_wp)
        self.ctrl = wp.to_torch(self.data.ctrl)
        self.xpos = wp.to_torch(self.data.xpos)
        self.xmat = wp.to_torch(self.data.xmat)
        self.initial_q = torch.tensor(self.cpu_model.qpos0.copy(), device=self.device, dtype=torch.float32)
        self.reset()
        started = time.monotonic()
        with wp.ScopedDevice(self.device):
            # Warm-up compilation precedes timing/capture and is never included
            # in the fixed training experiment budget.
            self._step()
            wp.synchronize()
            with wp.ScopedCapture() as capture:
                self._step()
            self.graph = capture.graph
        self.compile_seconds = time.monotonic() - started
        self.reset()

    def _step(self):
        for _ in range(self.substeps):
            wp.launch(apply_pd, dim=(self.worlds, 16),
                      inputs=[self.data.qpos, self.data.qvel, self.targets_wp, self.data.ctrl])
            mjw.step(self.model, self.data)

    def reset(self, mask=None):
        if mask is None:
            self.q[:] = self.initial_q
            self.v.zero_()
            self.target.zero_()
            wp.to_torch(self.data.qacc_warmstart).zero_()
            wp.to_torch(self.data.time).zero_()
        else:
            self.q[mask] = self.initial_q
            self.v[mask] = 0
            self.target[mask] = 0
            wp.to_torch(self.data.qacc_warmstart)[mask] = 0
            wp.to_torch(self.data.time)[mask] = 0

    def step(self, target):
        self.target.copy_(target)
        # All PyTorch interop writes must finish before the Warp graph reads.
        with wp.ScopedDevice(self.device), wp.ScopedStream(wp.stream_from_torch(torch.cuda.current_stream())):
            wp.capture_launch(self.graph)

    def sync(self):
        torch.cuda.synchronize()


def benchmark(model_path, worlds=64, steps=150):
    start = time.monotonic()
    backend = WarpBackend(model_path, worlds)
    print('GPU_PHYSICS_READY', backend.compile_seconds, 'compile seconds', flush=True)
    target = torch.zeros((worlds, 16), device='cuda')
    backend.sync()
    begin = time.monotonic()
    for _ in range(steps):
        backend.step(target)
    backend.sync()
    duration = time.monotonic() - begin
    q = backend.q.cpu().numpy()
    # Quaternion projected-up cosine; a fallen robot cannot pass just by
    # resting at a plausible height.
    upright = 1 - 2 * (q[:, 4] ** 2 + q[:, 5] ** 2)
    result = dict(device=torch.cuda.get_device_name(), worlds=worlds, steps=steps,
        control_samples_per_second=worlds * steps / duration,
        simulated_seconds=steps * .02, physics_wall_seconds=duration,
        total_wall_seconds=time.monotonic() - start,
        compile_seconds=backend.compile_seconds, finite=bool(np.isfinite(q).all()),
        min_upright=float(upright.min()), z_range=[float(q[:, 2].min()), float(q[:, 2].max())],
        torch_cpu_threads=torch.get_num_threads(), peak_torch_gpu_bytes=torch.cuda.max_memory_allocated())
    assert result['finite'] and result['min_upright'] > .95 and result['z_range'][0] > .16, result
    return result
