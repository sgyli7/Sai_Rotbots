"""Framework-neutral I/O for a frozen Goose package; no task/reward or optimizer.

Actions retain the package's motor coordinates and immutable drive timing.
The optional RGB camera is a declared simulator debug camera, not calibration.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import zipfile
import numpy as np

INTERFACE_VERSION = 'goose_training_io_v1'

def verify_package(package: Path) -> dict:
    package = Path(package).resolve()
    manifest = json.loads((package / 'manifest.json').read_text())
    files = manifest['files']
    rows = [{'path': p, 'sha256': h} for p, h in files.items()] if isinstance(files, dict) else files
    for row in rows:
        p = (package / row['path']).resolve()
        if not p.is_relative_to(package) or not p.is_file():
            raise ValueError('Missing or unsafe package file: ' + row['path'])
        if hashlib.sha256(p.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Package hash mismatch: ' + row['path'])
        if 'bytes' in row and p.stat().st_size != row['bytes']:
            raise ValueError('Package size mismatch: ' + row['path'])
    return {'verified_files': len(rows), 'manifest_sha256': hashlib.sha256((package / 'manifest.json').read_bytes()).hexdigest(), 'release_id': manifest['release_id']}

class GooseTrainingIO:
    """NumPy reset/step/proprio/state/RGB interface, without inferred task success.

    Explicit reset is the only initialization path. Errors propagate and retain
    the actual terminal state; step never retries or automatically resets.
    """
    def __init__(self, package_zip: str | Path, *, expected_manifest_sha256: str):
        self._temp = tempfile.TemporaryDirectory(prefix='goose-training-io-')
        root = Path(self._temp.name)
        with zipfile.ZipFile(package_zip) as z:
            for name in z.namelist():
                if not (root / name).resolve().is_relative_to(root):
                    raise ValueError('Unsafe ZIP member')
            z.extractall(root)
        manifests = list(root.glob('*/manifest.json'))
        if len(manifests) != 1:
            raise ValueError('Expected one packaged model')
        self.package = manifests[0].parent
        self.verification = verify_package(self.package)
        if self.verification['manifest_sha256'] != expected_manifest_sha256:
            raise ValueError('Unexpected frozen model identity')
        spec = importlib.util.spec_from_file_location('frozen_goose_training_adapter', self.package / 'runtime_adapter.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.physics = module.FrozenPhysics(self.package)
        self.renderer = None
        self.failure = None
        self.last_commanded_action = np.zeros(18)

    def contract(self) -> dict:
        p = self.physics
        return {'interface_version': INTERFACE_VERSION, **self.verification,
                'action_shape': [18], 'action_dtype': 'float64', 'normalized_action_range': [-1, 1],
                'action_clipping': 'package clips to [-1,1], motor ROM, reference slew and source effort/power limits',
                'axis_order': p.names, 'axis5': 'physical beak input rotor; positive torque closes; not passive jaw',
                'legacy08_policy_compatible': False, 'proprio_shape': [65], 'proprio_dtype': 'float32',
                'physics_dt_s': p.dt, 'drive_dt_s': p.drive_dt, 'action_dt_s': p.policy_dt,
                'reward_done_and_task': 'intentionally outside this physical I/O interface',
                'rgb_camera': {'kind': 'explicit simulator free debug camera, not real camera calibration',
                               'world_lookat_m': [0, 0, .42], 'distance_m': 1.65, 'azimuth_deg': 135, 'elevation_deg': -18,
                               'projection': 'MuJoCo perspective free camera; vertical fovy from model.vis.global_.fovy'}}

    def reset(self, **kwargs):
        result = self.physics.reset(**kwargs)
        self.failure = None
        self.last_commanded_action[:] = 0
        return self.observe(), result

    def observe(self, commands=None, phase_rad=0.):
        return self.physics.observations(commands, phase_rad)

    def step(self, action):
        a = np.asarray(action, dtype=float)
        if a.shape != (18,) or not np.isfinite(a).all():
            raise ValueError('Action must be a finite shape(18,) vector')
        self.last_commanded_action = a.copy()
        try:
            state = self.physics.step(a)
        except Exception as error:
            self.failure = {'type': type(error).__name__, 'message': str(error), 'time_s': float(self.physics.data.time)}
            raise
        return self.observe(), state

    def rgb(self, width=320, height=240):
        import mujoco
        if self.renderer is None:
            self.renderer = mujoco.Renderer(self.physics.model, height=height, width=width)
        if (self.renderer.width, self.renderer.height) != (width, height):
            raise ValueError('RGB dimensions must remain constant for this renderer')
        camera = mujoco.MjvCamera()
        camera.lookat[:] = [0, 0, .42]
        camera.distance, camera.azimuth, camera.elevation = 1.65, 135, -18
        self.renderer.update_scene(self.physics.data, camera=camera)
        return self.renderer.render().copy()

    def write_sample(self, directory, *, language, action_chunk, sample_dt_s=None):
        """Record a proposed action chunk with SAME current-state image/proprio.

        This does not execute the chunk. Time and model/interface identities are
        attached so consumers cannot silently reinterpret legacy jaw actions.
        """
        out = Path(directory)
        out.mkdir(parents=True, exist_ok=False)
        chunk = np.asarray(action_chunk, dtype=np.float64)
        if chunk.ndim != 2 or chunk.shape[1] != 18 or not np.isfinite(chunk).all() or np.any(abs(chunk) > 1):
            raise ValueError('Action chunk must be normalized finite [T,18]')
        if not isinstance(language, str) or not language.strip():
            raise ValueError('A nonempty language instruction is required')
        dt = self.physics.policy_dt if sample_dt_s is None else float(sample_dt_s)
        if dt != self.physics.policy_dt:
            raise ValueError('Action chunk clock must match frozen policy clock')
        np.savez_compressed(out / 'sample.npz', rgb=self.rgb(), proprio=self.observe(), action_chunk=chunk,
                            qpos=self.physics.data.qpos.copy(), qvel=self.physics.data.qvel.copy(),
                            action_time_s=self.physics.data.time + dt * np.arange(len(chunk)))
        metadata = {'interface_version': INTERFACE_VERSION, 'model': self.verification, 'language': language,
                    'actual_state_time_s': float(self.physics.data.time), 'action_dt_s': dt,
                    'chunk_semantics': 'proposed normalized motor-target actions; not already executed',
                    'camera': self.contract()['rgb_camera']}
        (out / 'sample.json').write_text(json.dumps(metadata, indent=2) + '\n')
        return metadata

    def close(self):
        if self.renderer is not None:
            self.renderer.close()
        self._temp.cleanup()
