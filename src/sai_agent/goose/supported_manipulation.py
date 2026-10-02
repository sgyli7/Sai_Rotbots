"""Finite, nominal double-support manipulation reference in SI units.

This reference uses encoder angles and an IMU, plus declared fixed foot anchors.
It is a specified-object engineering maneuver, not perception or a walking policy.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import least_squares

from .low_reach import smooth5


class SupportedManipulation:
    def __init__(self, support, contract, crouch_q, reference_point_m, target_m, path_profile='initial'):
        self.support = support
        self.names = list(contract['joint_order'])
        self.neck = np.array([self.names.index(n) for n in
                              ['neck_pitch', 'neck_mid_pitch', 'head_pitch']])
        self.beak = self.names.index('beak_hinge')
        self.crouch = np.asarray(crouch_q, dtype=float).copy()
        self.crouch[self.neck] = 0.
        self.crouch[self.beak] = .30
        self.stand = np.zeros(len(self.names))
        self.stand[self.beak] = .30
        self.reference = np.asarray(reference_point_m, dtype=float)
        self.local = self.reference-support.pivots['head_roll']
        self.target = np.asarray(target_m, dtype=float)
        p, r, _ = support.forward(self.crouch, [1., 0., 0., 0.])
        root = support.root_from_supported_feet(self.crouch, [1., 0., 0., 0.])
        self.start = root+p['head_roll']+r['head_roll']@self.local
        self.bounds = np.array([contract['joints'][i]['range_rad'] for i in self.neck])
        self.q_neck = np.zeros(3)
        if path_profile not in ['initial', 'constant_pitch']:
            raise ValueError('explicit finite manipulation path profile required')
        self.place_pitch = 1.3 if path_profile == 'constant_pitch' else 1.
        self.place_offset = -.006 if path_profile == 'constant_pitch' else -.0025
        self.phases = [
            ('settle', .5), ('crouch', 1.2), ('approach', 2.5),
            ('clamp', .8), ('lift', 1.), ('carry_hold', .4),
            ('place', 1.), ('release', .7), ('retract', 2.5),
            ('rise', 1.2), ('final_settle', .5)]
        if path_profile == 'constant_pitch':
            # Finite slower traversal, chosen before dynamics. Bill pitch
            # stays at its screened 1.3rad value while carrying the object.
            self.phases = [('settle', .5), ('crouch', 3.), ('approach', 4.),
                ('clamp', .8), ('lift', 1.5), ('carry_hold', .4),
                ('place', 1.5), ('release', .7), ('retract', 4.),
                ('rise', 3.), ('final_settle', .5)]
        self.duration_s = sum(t for _, t in self.phases)

    def reference_at(self, time_s, encoder_q, imu_wxyz):
        begin = 0.
        phase, duration = self.phases[-1]
        for name, span in self.phases:
            phase, duration = name, span
            if time_s < begin+span:
                break
            begin += span
        blend = float(smooth5((time_s-begin)/duration))
        commanded = self.crouch.copy()
        desired, pitch = self.start.copy(), 0.
        solve_ik = True
        if phase in ['settle', 'final_settle']:
            commanded = self.stand.copy()
            solve_ik = False
        elif phase == 'crouch':
            commanded = self.stand*(1-blend)+self.crouch*blend
            solve_ik = False
        elif phase == 'rise':
            commanded = self.crouch*(1-blend)+self.stand*blend
            solve_ik = False
        elif phase == 'approach':
            desired = self.start*(1-blend)+self.target*blend
            desired[0] += .060*4*blend*(1-blend)
            pitch = 1.3*blend
        elif phase in ['clamp', 'lift', 'carry_hold']:
            fraction = blend if phase == 'lift' else 1. if phase == 'carry_hold' else 0.
            desired = self.target+[0., 0., .080*fraction]
            pitch = 1.3
        elif phase in ['place', 'release']:
            fraction = blend if phase == 'place' else 1.
            desired = self.target+[0., 0., .080*(1-fraction)+self.place_offset*fraction]
            pitch = 1.3+(self.place_pitch-1.3)*fraction
        elif phase == 'retract':
            placed = self.target+[0., 0., self.place_offset]
            desired = placed*(1-blend)+self.start*blend
            desired[0] += .060*4*blend*(1-blend)
            pitch = self.place_pitch*(1-blend)
        residual_m = 0.
        if solve_ik:
            q = np.asarray(encoder_q, dtype=float)
            root = self.support.root_from_supported_feet(q, imu_wxyz)
            def residual(angles):
                trial = q.copy()
                trial[self.neck] = angles
                p, r, _ = self.support.forward(trial, imu_wxyz)
                point = root+p['head_roll']+r['head_roll']@self.local
                forward = r['head_roll'][:, 0]
                actual_pitch = np.arctan2(-forward[2], forward[0])
                return np.r_[(point-desired)[[0, 2]], .08*(actual_pitch-pitch)]
            solution = least_squares(residual, self.q_neck,
                bounds=(self.bounds[:, 0], self.bounds[:, 1]), max_nfev=24,
                ftol=1e-7, xtol=1e-7, gtol=1e-7)
            self.q_neck = solution.x
            commanded[self.neck] = self.q_neck
            residual_m = float(np.linalg.norm(residual(solution.x)))
        grip = phase in ['clamp', 'lift', 'carry_hold', 'place']
        return commanded, dict(phase=phase, phase_blend=blend, grip_velocity_control=grip,
            declared_payload_kg=.050 if phase in ['lift', 'carry_hold', 'place'] else 0.,
            target_point_world_m=desired.tolist(), target_head_pitch_rad=pitch,
            ik_weighted_residual_m=residual_m)
