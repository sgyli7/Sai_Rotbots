"""Nominal static support torques from the neutral SI body/joint contract.

Inputs are encoders, an IMU quaternion, declared fixed foot anchors and an
optional known carried load. No simulator root translation, contact-force
truth or randomized mass is used. Valid only for assumed double support.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import ConvexHull

from .stage_one_gravity import quat_matrix


def _rotation(axis, angle):
    x, y, z = axis
    skew = np.array([[0., -z, y], [z, 0., -x], [-y, x, 0.]])
    return np.eye(3)+np.sin(angle)*skew+(1-np.cos(angle))*(skew@skew)


class NominalDoubleSupport:
    def __init__(self, contract, support_centers_y_m, support_hulls_xy_m, ground_z_m=.0005):
        self.names = list(contract['joint_order'])
        self.joints = list(contract['joints'])
        if self.names != [j['name'] for j in self.joints] or len(set(self.names)) != len(self.names):
            raise ValueError('unique ordered neutral joints required')
        self.bodies = {b['name']: b for b in contract['bodies']}
        self.pivots = {'torso':np.array(contract['root_origin_at_zero_m'], dtype=float)}
        self.pivots.update({j['name']:np.array(j['pivot_world_at_zero_m'], dtype=float) for j in self.joints})
        self.parents = {j['name']:j['parent'] for j in self.joints}
        self.axes = {j['name']:np.array(j['axis_parent'], dtype=float) for j in self.joints}
        self.passive = list(contract.get('passive_linkage_joints', []))
        for j in self.passive:
            self.pivots[j['name']] = np.array(j['pivot_world_at_zero_m'], dtype=float)
            self.parents[j['name']] = j['parent']
            self.axes[j['name']] = np.array(j['axis_parent'], dtype=float)
        self.pads = list(contract.get('passive_contacts', []))
        for pad in self.pads:
            self.pivots[pad['name']] = np.array(pad['world_at_zero_m'], dtype=float)
            self.parents[pad['name']] = pad['body']
        self.tree = self.names+[j['name'] for j in self.passive]+[p['name'] for p in self.pads]
        if set(self.bodies) != set(self.tree) | {'torso'}:
            raise ValueError('complete nominal body tree required')
        self.descendants = {n:{n} for n in ['torso']+self.tree}
        for name in reversed(self.tree):
            self.descendants[self.parents[name]] |= self.descendants[name]
        self.feet = {'right':'right_ankle_roll', 'left':'left_ankle_roll'}
        self.anchors = {side:self.pivots[name].copy() for side, name in self.feet.items()}
        self.center_y = dict(support_centers_y_m)
        self.hulls = {side:ConvexHull(np.asarray(points, dtype=float)) for side, points in support_hulls_xy_m.items()}
        if set(self.hulls) != set(self.feet) or self.center_y['left'] <= self.center_y['right']:
            raise ValueError('two ordered support footprints required')
        self.ground_z = float(ground_z_m)

    def forward(self, q, imu_wxyz):
        q = np.asarray(q, dtype=float)
        imu = np.asarray(imu_wxyz, dtype=float)
        if q.shape != (len(self.names),) or not np.isfinite(q).all():
            raise ValueError('finite named encoder vector required')
        if imu.shape != (4,) or not np.isfinite(imu).all() or np.linalg.norm(imu) < 1e-12:
            raise ValueError('finite nonzero IMU quaternion required')
        angles = dict(zip(self.names, q))
        for j in self.passive:
            angles[j['name']] = j['mimic_multiplier']*angles[j['mimic_joint']]+j['mimic_offset_rad']
        positions = {'torso':np.zeros(3)}
        rotations = {'torso':quat_matrix(imu)}
        axes = {}
        for name in self.tree:
            parent = self.parents[name]
            parent_r = rotations[parent]
            positions[name] = positions[parent]+parent_r@(self.pivots[name]-self.pivots[parent])
            if name in self.axes:
                axes[name] = parent_r@self.axes[name]
                rotations[name] = parent_r@_rotation(self.axes[name], angles[name])
            else:
                # Sole deflection is uninstrumented here; nominal zero
                # compression retains actual pad mass and frame ownership.
                rotations[name] = parent_r
        return positions, rotations, axes

    def root_from_supported_feet(self, q, imu_wxyz):
        positions, _, _ = self.forward(q, imu_wxyz)
        return np.mean([self.anchors[side]-positions[name] for side, name in self.feet.items()], axis=0)

    def estimate(self, q, imu_wxyz, payload_mass_kg=0., payload_head_point_m=None):
        mass = float(payload_mass_kg)
        if not np.isfinite(mass) or mass < 0:
            raise ValueError('nonnegative known payload mass required')
        positions, rotations, axes = self.forward(q, imu_wxyz)
        root = np.mean([self.anchors[side]-positions[name] for side, name in self.feet.items()], axis=0)
        components = []
        for name, body in self.bodies.items():
            center = positions[name]+rotations[name]@np.asarray(body['com_local_m'])
            components.append((name, float(body['mass_kg']), center))
        if mass:
            point = np.asarray(payload_head_point_m, dtype=float)
            if point.shape != (3,) or not np.isfinite(point).all():
                raise ValueError('declared head-owned payload point required')
            center = positions['head_roll']+rotations['head_roll']@(point-self.pivots['head_roll'])
            components.append(('head_roll', mass, center))
        total_mass = sum(m for n, m, c in components)
        com = sum(m*c for n, m, c in components)/total_mass+root
        span = self.center_y['left']-self.center_y['right']
        share_right = (self.center_y['left']-com[1])/span
        contacts = []
        for side, share in [('right', share_right), ('left', 1-share_right)]:
            cop = np.array([com[0], self.center_y[side], self.ground_z])
            hull = self.hulls[side]
            margin = float(np.min(-(hull.equations[:, :2]@cop[:2]+hull.equations[:, 2])))
            contacts.append(dict(side=side, body=self.feet[side], point_world_m=cop,
                force_world_n=np.array([0., 0., total_mass*9.81*share]),
                edge_margin_m=margin, positive_normal=bool(share>0)))
        moments = {}
        for name, axis in axes.items():
            moment = np.zeros(3)
            for owner, component_mass, center in components:
                if owner in self.descendants[name]:
                    moment += np.cross(center-positions[name], [0., 0., -component_mass*9.81])
            for contact in contacts:
                if contact['body'] in self.descendants[name]:
                    moment += np.cross(contact['point_world_m']-root-positions[name], contact['force_world_n'])
            moments[name] = -float(axis@moment)
        torque = np.array([moments[n] for n in self.names])
        for j in self.passive:
            # Virtual work folds passive mimic coordinates into the sole
            # active jaw coordinate; same rule applies across backends.
            torque[self.names.index(j['mimic_joint'])] += j['mimic_multiplier']*moments[j['name']]
        return dict(torque_nm=torque, estimated_root_position_m=root,
                    nominal_com_world_m=com, contacts=contacts,
                    nominal_support_feasible=all(c['positive_normal'] and c['edge_margin_m'] >= 0 for c in contacts),
                    mass_kg=total_mass)
