"""Physical-input closeout drive on the unchanged native-discrete algorithm.

The sixth public coordinate is the real rotor. The two passive coordinates
are computed from the hash-bound 020 four-bar rather than a fixed mimic.
"""
import copy
import json
import math

import torch

from .batch_drive import BatchedNominalNeckGravity, BatchedRigidNativeDrive, _quat_matrix


def _fourbar_pose(output, mapping):
    phase = mapping.phase - output
    cx = mapping.o[0] + mapping.rout * torch.cos(phase)
    cy = mapping.o[1] + mapping.rout * torch.sin(phase)
    vx, vy = cx - mapping.a[0], cy - mapping.a[1]
    distance = torch.sqrt(vx.square() + vy.square())
    cosine = (mapping.rin**2 + distance.square() - mapping.length**2) / (2 * mapping.rin * distance)
    theta = torch.atan2(vy, vx) - torch.acos(cosine)
    dx = mapping.a[0] + mapping.rin * torch.cos(theta)
    dy = mapping.a[1] + mapping.rin * torch.sin(theta)
    angle = torch.atan2(cy - dy, cx - dx)
    return theta, angle


def passive_from_rotor(rotor, mapping):
    """Vectorized source 60-bisection map, retaining rotor as public axis."""
    if bool(((rotor < mapping.input_range[0] - 1e-10) | (rotor > mapping.input_range[1] + 1e-10)).any()):
        raise ValueError('Physical beak rotor outside source linkage range')
    zero = torch.zeros_like(rotor)
    theta0, angle0 = _fourbar_pose(zero, mapping)
    lo, hi = torch.zeros_like(rotor), torch.full_like(rotor, .55)
    for _ in range(60):
        mid = (lo + hi) / 2
        theta, _ = _fourbar_pose(mid, mapping)
        input_at_mid = -(theta - theta0)
        go_up = input_at_mid > rotor
        lo, hi = torch.where(go_up, mid, lo), torch.where(go_up, hi, mid)
    output = (lo + hi) / 2
    _, angle = _fourbar_pose(output, mapping)
    coupler = -(angle - angle0) - rotor
    return output, coupler


class CloseoutNominalNeckGravity(BatchedNominalNeckGravity):
    """Reuse nominal gravity arithmetic with actual nonlinear passive angles."""
    def __init__(self, contract, mapping, *, device='cpu'):
        proxy = copy.deepcopy(contract)
        if root := contract['closeout_native50'].get('_resolved_gravity_source_root'):
            proxy['source_checkpoint']['source_root'] = root
        # Structural indices only: real passive angles are substituted below.
        for joint in proxy['passive_linkage_joints']:
            joint.update(mimic_joint='beak_input_rotor', mimic_multiplier=0., mimic_offset_rad=0.)
        super().__init__(proxy, device=device)
        self.mapping = mapping
        self.evaluation_envelope_rad = float(contract['joints'][5]['speed_limit_rad_s']*contract['physics_dt_s'])
        if not math.isfinite(self.evaluation_envelope_rad) or self.evaluation_envelope_rad<=0:
            raise ValueError('Nominal FF evaluation requires a positive source speed and physical step')
        self.last_actual_rotor=torch.empty(0,dtype=torch.float64,device=self.device)
        self.last_evaluation_rotor=self.last_actual_rotor.clone()
        self.last_projection_rad=self.last_actual_rotor.clone()

    @torch.no_grad()
    def __call__(self, q, imu_wxyz):
        q = torch.as_tensor(q, dtype=torch.float64, device=self.device)
        imu_wxyz = torch.as_tensor(imu_wxyz, dtype=torch.float64, device=self.device)
        if (q.ndim != 2 or q.shape[1] != 6 or imu_wxyz.shape != (q.shape[0], 4)
                or not bool(torch.isfinite(q).all() & torch.isfinite(imu_wxyz).all())):
            raise ValueError('Closeout gravity requires finite encoder and IMU values')
        # Only the nominal gravity estimate projects numerical soft-stop states.
        # The public encoder/observation, physical state, target and hard limits
        # remain raw. One source-speed Tick bounds this estimate-only envelope.
        rotor=q[:,5]
        projected=rotor.clamp(self.mapping.input_range[0],self.mapping.input_range[1])
        delta=projected-rotor
        self.last_actual_rotor=rotor.detach().clone()
        self.last_evaluation_rotor=projected.detach().clone()
        self.last_projection_rad=delta.detach().clone()
        invalid=delta.abs()>self.evaluation_envelope_rad
        if bool(invalid.any()):
            worlds=invalid.nonzero(as_tuple=False).flatten().cpu().tolist()
            actual=rotor[invalid].cpu().tolist()
            raise ValueError(f'Nominal gravity rotor evaluation envelope exceeded: worlds={worlds}, actual_rad={actual}, design_range={self.mapping.input_range}, evaluation_envelope_rad={self.evaluation_envelope_rad}')
        q_eval=q.clone()
        q_eval[:,5]=projected
        return self._evaluate_configuration(q_eval,imu_wxyz)

    @torch.no_grad()
    def _evaluate_configuration(self,q,imu_wxyz):
        """Unchanged nominal gravity arithmetic on one consistent configuration."""
        jaw, coupler = passive_from_rotor(q[:, 5], self.mapping)
        positions = [torch.zeros((q.shape[0], 3), dtype=torch.float64, device=self.device)]
        rotations = [_quat_matrix(imu_wxyz)]
        axes, centers, forces = [], [], []
        for i, (parent, offset, axis, skew, skew2, com, force, _source, _multiplier, _bias) in enumerate(self.nodes):
            pr = rotations[parent]
            positions.append(positions[parent] + pr @ offset)
            if i < 6:
                axes.append(pr @ axis)
            angle = q[:, i] if i < 6 else (jaw if i == 6 else coupler)
            rotations.append(pr @ (self.identity + angle.sin()[:, None, None]*skew
                                     + (1-angle.cos())[:, None, None]*skew2))
            centers.append(positions[-1] + rotations[-1] @ com)
            forces.append(force)
        diff = torch.stack(centers, dim=1)[:, None] - torch.stack(positions[1:6], dim=1)[:, :, None]
        moment = torch.linalg.cross(diff, torch.stack(forces)[None, None].expand_as(diff), dim=-1)
        moment *= self.descendants[None, :, :, None]
        return -(moment.sum(dim=2)*torch.stack(axes[:5], dim=1)).sum(dim=-1)


class CloseoutRigidNativeDrive(BatchedRigidNativeDrive):
    """Original drive algorithm with source-bound physical 18-axis parameters."""
    def __init__(self, contract, num_envs, *, device='cpu'):
        from .closeout_native50 import load_beak_mapping
        baseline_path = contract['closeout_native50']['source_refs']['baseline_contract']['path']
        baseline = json.loads(open(baseline_path).read())
        if root := contract['closeout_native50'].get('_resolved_gravity_source_root'):
            baseline['source_checkpoint']['source_root'] = root
        super().__init__(baseline, num_envs, device=device)
        self.gravity = CloseoutNominalNeckGravity(contract, load_beak_mapping(contract), device=device)
        joints = contract['joints']
        for name, field in (('kp','kp_nm_rad'), ('kd','kd_nm_s_rad'),
                ('peak','torque_peak_limit_nm'), ('cont','continuous_design_limit_nm'),
                ('speed','speed_limit_rad_s'), ('scale','action_scale_rad'),
                ('neutral','q_neutral_rad'), ('ranges','range_rad')):
            setattr(self, name, torch.tensor([j[field] for j in joints], dtype=torch.float64, device=self.device))
        self.power_limit = contract['positive_mechanical_power_limit_w']
        self.target = self.neutral.repeat(num_envs, 1)
        self.contract_native = contract['rigid_native']


def gravity_estimator_readback(gravity):
    """Expose estimate-only projections without mutating physical drive state."""
    return {'policy':'source_speed_times_physics_dt_bounded_nominal_gravity_projection_v1',
            'evaluation_envelope_rad':gravity.evaluation_envelope_rad,
            'design_input_range_rad':list(gravity.mapping.input_range),
            'actual_input_rotor_rad':gravity.last_actual_rotor.cpu().tolist(),
            'evaluation_input_rotor_rad':gravity.last_evaluation_rotor.cpu().tolist(),
            'signed_evaluation_projection_rad':gravity.last_projection_rad.cpu().tolist(),
            'physical_state_or_target_projected':False}
