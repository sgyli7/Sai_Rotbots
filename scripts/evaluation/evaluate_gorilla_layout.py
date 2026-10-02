"""Finite FK/contact-statics and free-root rejection checks for the layout.

Payloads are virtual hand wrenches, not grasped objects. Contact statics uses
nonnegative corner forces and an inscribed friction pyramid. This does not
prove structural strength, thermal capability, walking, or Bevy compatibility.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import mujoco
import numpy as np
from scipy.optimize import least_squares, linprog


ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Screen:
    def __init__(self, model_path, spec_path):
        self.model = mujoco.MjModel.from_xml_path(str(model_path))
        self.spec = json.loads(Path(spec_path).read_text())
        contract_path = Path(model_path).parent / 'robot.json'
        self.model_contract_sha256 = None
        if contract_path.is_file():
            contract = json.loads(contract_path.read_text())
            if contract['spec_sha256'] != digest(spec_path) or contract['model_sha256'] != digest(model_path):
                raise ValueError('Model, SI contract, and specification source identities differ')
            for relative, checksum in contract['asset_manifest'].items():
                asset = (contract_path.parent/relative).resolve()
                if not asset.is_relative_to(contract_path.parent.resolve()) or digest(asset) != checksum:
                    raise ValueError('Runtime asset identities differ from the bound SI contract')
            self.model_contract_sha256 = digest(contract_path)
        self.data = mujoco.MjData(self.model)
        self.neutral = self.model.qpos0.copy()
        self.joints = self.spec['joints']
        self.ids = [self.model.joint(j['name']).id for j in self.joints]
        self.qadr = np.array([self.model.jnt_qposadr[i] for i in self.ids])
        self.dadr = np.array([self.model.jnt_dofadr[i] for i in self.ids])
        free = np.flatnonzero(self.model.jnt_type == mujoco.mjtJoint.mjJNT_FREE)
        if (len(free) != 1 or self.model.jnt_dofadr[free[0]] != 0 or
                self.model.jnt_qposadr[free[0]] != 0 or
                self.model.jnt_bodyid[free[0]] != self.model.body('pelvis').id):
            raise ValueError('Screen requires an unconstrained pelvis free root at the first six DoF')
        if (set(self.dadr) != set(range(6, self.model.nv)) or
                any(self.model.jnt_type[i] != mujoco.mjtJoint.mjJNT_HINGE for i in self.ids)):
            raise ValueError('Every non-root DoF must be a declared scalar hinge')
        unsupported_flags = (int(mujoco.mjtDisableBit.mjDSBL_CONTACT) |
                             int(mujoco.mjtDisableBit.mjDSBL_CONSTRAINT) |
                             int(mujoco.mjtDisableBit.mjDSBL_GRAVITY))
        if not np.allclose(self.model.opt.gravity, [0, 0, -9.81], rtol=0, atol=1e-9):
            raise ValueError('Diagnostic requires enabled Earth gravity [0, 0, -9.81]')
        if (self.model.neq or self.model.ntendon or np.any(self.model.body_gravcomp) or
                self.model.opt.disableflags & unsupported_flags):
            raise ValueError('Hidden constraints, tendons, gravity compensation, or disabled contacts are unsupported')
        if (self.model.nu != len(self.ids) or
                set(self.model.actuator_trnid[:, 0]) != set(self.ids) or
                np.any(self.model.actuator_trntype != mujoco.mjtTrn.mjTRN_JOINT)):
            raise ValueError('Each declared hinge requires one explicit joint actuator')
        if not np.allclose(self.model.jnt_range[self.ids], [j['range_rad'] for j in self.joints],
                           rtol=0, atol=1e-7):
            raise ValueError('Model joint limits differ from the bound layout specification')
        if (not np.all(self.model.actuator_forcelimited) or
                not np.allclose(self.model.actuator_gear, [1, 0, 0, 0, 0, 0], rtol=0, atol=1e-9)):
            raise ValueError('Diagnostic requires explicit bounded output-torque actuators with unit gear')
        self.actuation_contract = []
        for a in range(self.model.nu):
            j = self.joints[self.ids.index(int(self.model.actuator_trnid[a, 0]))]
            drive = self.spec['drive_classes'][j['drive_class']]
            interval = self.model.actuator_forcerange[a]
            peak = drive.get('design_peak_nm', drive['design_torque_nm'])
            if (not np.isfinite(interval).all() or interval[0] >= 0 or interval[1] <= 0 or
                    max(abs(interval)) > peak + 1e-7):
                raise ValueError('Actuator torque interval exceeds the declared peak hypothesis')
            self.actuation_contract.append({'joint': j['name'], 'output_torque_range_nm': interval.tolist(),
                'design_torque_hypothesis_nm': drive['design_torque_nm'],
                'peak_torque_hypothesis_nm': peak, 'gear': 1,
                'continuous_thermal_capability_verified': False})
        self.root_contract = {'free_root_dof': 6, 'root_body': 'pelvis',
                              'all_nonroot_dof_declared': True,
                              'equality_constraint_count': int(self.model.neq),
                              'tendon_count': int(self.model.ntendon),
                              'gravity_compensation_used': False,
                              'contact_disabled': False, 'hidden_support': False}
        self.limits = np.array([self.spec['drive_classes'][j['drive_class']]['design_torque_nm']
                                for j in self.joints])
        self.speed_limits = np.array([self.spec['drive_classes'][j['drive_class']]['design_speed_rad_s']
                                      for j in self.joints])
        self.body_ids = {n: self.model.body(n).id for n in
                         ('left_foot', 'right_foot', 'left_palm', 'right_palm')}
        self.data.qpos[:] = self.neutral
        mujoco.mj_forward(self.model, self.data)
        planes = [g for g in range(self.model.ngeom)
                  if self.model.geom_type[g] == mujoco.mjtGeom.mjGEOM_PLANE
                  and self.model.geom_bodyid[g] == 0
                  and (self.model.geom_contype[g] or self.model.geom_conaffinity[g])
                  and np.allclose(self.data.geom_xmat[g].reshape(3, 3)[:, 2], [0, 0, 1])]
        if len(planes) != 1:
            raise ValueError('Static screen requires one active horizontal world ground plane')
        self.ground_geom = planes[0]
        self.ground_z = float(self.data.geom_xpos[self.ground_geom, 2])
        self.offsets = {}
        self.sole_corners_local = {}
        self.sole_geoms = {}
        self.sole_geom_ids = {}
        self.sole_friction = {}
        for side in ('left', 'right'):
            body = side + '_foot'
            bid = self.body_ids[body]
            boxes = []
            for gid in range(self.model.ngeom):
                if (self.model.geom_bodyid[gid] != bid or
                    self.model.geom_type[gid] != mujoco.mjtGeom.mjGEOM_BOX or
                    not (self.model.geom_contype[gid] or self.model.geom_conaffinity[gid])):
                    continue
                floor = self.ground_geom
                if not ((self.model.geom_contype[gid] & self.model.geom_conaffinity[floor]) or
                        (self.model.geom_contype[floor] & self.model.geom_conaffinity[gid])):
                    continue
                if bid in self.model.exclude_signature:
                    continue
                size = self.model.geom_size[gid]
                corners = np.array([[x, y, z] for x in (-size[0], size[0])
                                    for y in (-size[1], size[1]) for z in (-size[2], size[2])])
                world = self.data.geom_xpos[gid] + corners @ self.data.geom_xmat[gid].reshape(3, 3).T
                lower = world[np.argsort(world[:, 2])[:4]]
                boxes.append((gid, lower))
            if not boxes:
                raise ValueError(f'{body} has no active collision sole box; refusing fictitious support polygon')
            bottom = min(float(c[:, 2].min()) for _, c in boxes)
            selected = [(gid, c) for gid, c in boxes if float(c[:, 2].min()) <= bottom + .001]
            world = np.vstack([c for _, c in selected])
            rotation = self.data.xmat[bid].reshape(3, 3)
            self.sole_corners_local[side] = (world - self.data.xpos[bid]) @ rotation
            self.sole_geoms[side] = [self.model.geom(gid).name for gid, _ in selected]
            self.sole_geom_ids[side] = [gid for gid, _ in selected]
            coefficients = []
            for gid, _ in selected:
                floor = self.ground_geom
                pairs = [p for p in range(self.model.npair)
                         if {int(self.model.pair_geom1[p]), int(self.model.pair_geom2[p])} == {gid, floor}]
                if pairs:
                    mu = float(np.min(self.model.pair_friction[pairs[0], :2]))
                    dim = int(self.model.pair_dim[pairs[0]])
                elif self.model.geom_priority[gid] == self.model.geom_priority[floor]:
                    mu = float(max(self.model.geom_friction[gid, 0], self.model.geom_friction[floor, 0]))
                    dim = int(max(self.model.geom_condim[gid], self.model.geom_condim[floor]))
                else:
                    higher = gid if self.model.geom_priority[gid] > self.model.geom_priority[floor] else floor
                    mu = float(self.model.geom_friction[higher, 0])
                    dim = int(self.model.geom_condim[higher])
                if dim < 3:
                    mu = 0.0
                coefficients.append(mu)
            self.sole_friction[side] = min(.7, min(coefficients))
            self.offsets[body] = (world.mean(axis=0) - self.data.xpos[bid]) @ rotation
        for side in ('left', 'right'):
            for kind, point in (('palm', 'palm'),):
                body = side + '_' + kind
                p = np.array(self.spec['points_world_m']['left_' + point], dtype=float)
                if side == 'right':
                    p[1] *= -1
                i = self.body_ids[body]
                self.offsets[body] = self.data.xmat[i].reshape(3, 3).T @ (p - self.data.xpos[i])
        self.neutral_feet = {s: self.point(s + '_foot').copy() for s in ('left', 'right')}
        for p in self.neutral_feet.values():
            p[2] = self.ground_z
        self.neutral_rotations = {s: self.rotation(s + '_foot').copy() for s in ('left', 'right')}

    def forward(self, q):
        self.data.qpos[:] = q
        self.data.qvel[:] = 0
        mujoco.mj_forward(self.model, self.data)

    def rotation(self, body):
        return self.data.xmat[self.body_ids[body]].reshape(3, 3)

    def point(self, body):
        return self.data.xpos[self.body_ids[body]] + self.rotation(body) @ self.offsets[body]

    def jacobian(self, body, point):
        jp = np.zeros((3, self.model.nv))
        jr = np.zeros((3, self.model.nv))
        mujoco.mj_jac(self.model, self.data, jp, jr, point, self.body_ids[body])
        return jp

    def assign(self, q, values):
        for name, value in values.items():
            q[self.model.jnt_qposadr[self.model.joint(name).id]] = value

    def planted_ik(self, q, targets):
        selected = [i for i, j in enumerate(self.joints) if any(
            j['name'].startswith(s + '_') and j['name'].split('_', 1)[1].startswith(
                ('hip_', 'knee_', 'fold_', 'ankle_')) for s in targets)]
        qa = self.qadr[selected]
        bounds = np.array([self.joints[i]['range_rad'] for i in selected])
        preferred = q[qa].copy()

        def residual(x):
            trial = q.copy()
            trial[qa] = x
            self.forward(trial)
            result = []
            for side, target in targets.items():
                result.extend((self.point(side + '_foot') - target) * 10)
                result.extend((self.rotation(side + '_foot') - self.neutral_rotations[side]).ravel() * 2)
            return np.r_[result, .002 * (x - preferred)]

        result = least_squares(residual, np.clip(preferred, bounds[:, 0], bounds[:, 1]),
                               bounds=(bounds[:, 0], bounds[:, 1]), max_nfev=120,
                               xtol=1e-10, ftol=1e-10, gtol=1e-10)
        q[qa] = result.x
        self.forward(q)
        error = max(float(np.linalg.norm(self.point(s + '_foot') - p)) for s, p in targets.items())
        orientation = max(float(np.linalg.norm(self.rotation(s + '_foot') -
                                               self.neutral_rotations[s])) for s in targets)
        return q, error, orientation

    def arm_ik(self, q, targets):
        errors = []
        for side, target in targets.items():
            selected = [i for i,j in enumerate(self.joints) if j['name'].startswith(side+'_') and
                        j['name'].split('_',1)[1].startswith(('shoulder_','elbow_','wrist_'))]
            qa=self.qadr[selected]
            bounds=np.asarray([self.joints[i]['range_rad'] for i in selected])
            preferred=q[qa].copy()
            def residual(x):
                trial=q.copy();trial[qa]=x;self.forward(trial)
                return np.r_[10*(self.point(side+'_palm')-target),.001*(x-preferred)]
            solved=least_squares(residual,np.clip(preferred,bounds[:,0],bounds[:,1]),
                bounds=(bounds[:,0],bounds[:,1]),max_nfev=160,xtol=1e-10,ftol=1e-10,gtol=1e-10)
            q[qa]=solved.x;self.forward(q)
            errors.append(float(np.linalg.norm(self.point(side+'_palm')-target)))
        return q,max(errors,default=0.)

    def poses(self):
        poses = []
        for name in ('neutral', 'chest_hold', 'front_reach', 'low_reach', 'door_handle', 'single_support'):
            q = self.neutral.copy()
            values = {}
            if name in ('chest_hold', 'front_reach', 'low_reach', 'single_support'):
                pitch, roll, elbow = {
                    'chest_hold': (-.45, .85, -.8),
                    'front_reach': (-.9, .6, -.12),
                    'low_reach': (-.15, .5, -.25),
                    'single_support': (-.45, .85, -.8),
                }[name]
                for side, sign in (('left', 1), ('right', -1)):
                    values.update({side + '_shoulder_pitch': pitch,
                                   side + '_shoulder_roll': -sign * roll,
                                   side + '_elbow_pitch': elbow,
                                   side + '_wrist_pitch': .4})
            if name == 'low_reach':
                q[2] -= .39
                values['waist_pitch'] = .22
            if name == 'single_support':
                q[1] += .40
                q[2] -= .06
            if name == 'door_handle':
                values.update(right_shoulder_pitch=-.65, right_shoulder_roll=.25,
                              right_elbow_pitch=-.15)
            self.assign(q, values)
            hand_targets={}
            if name in ('chest_hold','front_reach','low_reach','single_support'):
                x,z={'chest_hold':(.70,1.58),'front_reach':(.75,1.50),
                     'low_reach':(.50,.90),'single_support':(.70,1.58)}[name]
                hand_targets={s:np.array([q[0]+x,q[1]+sign*.32,z])
                              for s,sign in (('left',1),('right',-1))}
            elif name=='door_handle':
                hand_targets={'right':np.array([.65,-.45,1.30])}
            q,hand_error=self.arm_ik(q,hand_targets)
            targets = {s: p.copy() for s, p in self.neutral_feet.items()}
            if name == 'single_support':
                targets['right'][2] += .12
                targets['right'][1] += .30
            q, error, orientation = self.planted_ik(q, targets)
            poses.append({'name': name, 'qpos': q, 'feet': ['left'] if name == 'single_support'
                          else ['left', 'right'], 'ik_position_error_m': error,
                          'hand_ik_error_m':hand_error,
                          'hand_targets_world_m':{s:p.tolist() for s,p in hand_targets.items()},
                          'ik_rotation_matrix_error': orientation,
                          'horizontal_door_force_n': 150 if name == 'door_handle' else 0})
        return poses

    def contacts(self, feet):
        points, jacobians, height_errors = [], [], []
        for side in feet:
            body = side + '_foot'
            bid = self.body_ids[body]
            world = self.data.xpos[bid] + self.sole_corners_local[side] @ self.rotation(body).T
            for p in world:
                points.append(p)
                jacobians.append(self.jacobian(body, p))
                height_errors.append(abs(p[2] - self.ground_z))
        return np.array(points), np.vstack(jacobians), max(height_errors)

    def collision_report(self):
        pairs = []
        sole_ids = {gid for ids in self.sole_geom_ids.values() for gid in ids}
        for c in self.data.contact:
            if c.dist >= -.0005:
                continue
            a, b = (int(x) for x in c.geom)
            ba, bb = int(self.model.geom_bodyid[a]), int(self.model.geom_bodyid[b])
            names = [self.model.geom(x).name for x in (a, b)]
            if ((a == self.ground_geom and b in sole_ids) or
                    (b == self.ground_geom and a in sole_ids)):
                continue
            pairs.append({'geoms': names, 'penetration_m': float(-c.dist),
                          'bodies': [self.model.body(ba).name, self.model.body(bb).name]})
        return {'nonfoot_or_self_penetration_count': len(pairs),
                'max_penetration_m': max((p['penetration_m'] for p in pairs), default=0),
                'pairs': pairs, 'threshold_m': .0005,
                'scope': 'modeled primitive contacts only, finite sample; omitted/internal geometry not cleared'}

    def static(self, pose, payload_kg, scale=1.0):
        self.forward(pose['qpos'])
        points, jc, height_error = self.contacts(pose['feet'])
        # At qvel=0 bias is gravity. Springs are not scaled with robot mass.
        demand = self.data.qfrc_bias.copy() * scale - self.data.qfrc_passive
        load_points = {}
        for side in ('left', 'right'):
            body = side + '_palm'
            p = self.point(body)
            load_points[side] = p.tolist()
            demand += self.jacobian(body, p).T @ np.array([0, 0, .5 * payload_kg * 9.81])
        door_force = pose['horizontal_door_force_n']
        if door_force:
            demand += self.jacobian('right_palm', self.point('right_palm')).T @ np.array([door_force, 0, 0])
        jt = jc.T
        count = jc.shape[0]
        aub, bub = [], []
        for d, limit in zip(self.dadr, self.limits):
            aub.extend([np.r_[-jt[d], -limit], np.r_[jt[d], -limit]])
            bub.extend([-demand[d], demand[d]])
        mu = min(self.sole_friction[s] for s in pose['feet'])
        for k in range(0, count, 3):
            for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                row = np.zeros(count + 1)
                row[k:k + 3] = [sx, sy, -mu]
                aub.append(row)
                bub.append(0)
        objective = np.zeros(count + 1)
        objective[-1] = 1
        aeq = np.column_stack([jt[:6], np.zeros(6)])
        bounds = [(None, None) if i % 3 != 2 else (0, None) for i in range(count)] + [(0, None)]
        result = linprog(objective, A_ub=np.array(aub), b_ub=bub,
                         A_eq=aeq, b_eq=demand[:6], bounds=bounds, method='highs')
        collisions = self.collision_report()
        output = {'pose': pose['name'], 'payload_proxy_kg': payload_kg,
                  'robot_mass_scale': scale, 'ik_position_error_m': pose['ik_position_error_m'],
                  'ik_rotation_matrix_error': pose['ik_rotation_matrix_error'],
                  'hand_ik_error_m':pose.get('hand_ik_error_m',0.),
                  'foot_corner_height_error_m': height_error,
                  'payload_force_points_m': load_points, 'door_reaction_force_n': door_force,
                  'contact_points_m': points.tolist(), 'robot_com_m': self.data.subtree_com[0].tolist(),
                  'support_source_geoms': {s: self.sole_geoms[s] for s in pose['feet']},
                  'ground_geom': self.model.geom(self.ground_geom).name,
                  'ground_height_m': self.ground_z,
                  'passive_joint_force_nm': dict(zip((j['name'] for j in self.joints),
                                                       self.data.qfrc_passive[self.dadr].tolist())),
                  'friction_pyramid_mu': mu,
                  'contact_lp_success': bool(result.success), 'contact_lp_message': result.message,
                  'collision': collisions,
                  'scope': 'oracle FK and virtual hand wrenches; design torque hypotheses, no object or thermal proof'}
        if result.success:
            force = result.x[:count]
            torque = demand[self.dadr] - jt[self.dadr] @ force
            ratios = np.abs(torque) / self.limits
            worst = int(np.argmax(ratios))
            output.update(max_design_torque_utilization=float(ratios[worst]),
                          worst_joint=self.joints[worst]['name'],
                          worst_joint_demand_nm=float(torque[worst]),
                          joint_torque_nm=dict(zip((j['name'] for j in self.joints), torque.tolist())),
                          contact_forces_n=force.reshape(-1, 3).tolist(),
                          root_equilibrium_residual=float(np.max(np.abs(jt[:6] @ force - demand[:6]))))
        output['limited_screen_pass'] = bool(result.success and result.x[-1] <= 1 and
            pose['ik_position_error_m'] <= .002 and pose['ik_rotation_matrix_error'] <= .005 and
            pose.get('hand_ik_error_m',0.) <= .002 and
            height_error <= .0005 and not collisions['nonfoot_or_self_penetration_count'])
        return output

    def reject_run(self, dt, seconds=.25):
        model = self.model
        old_dt = model.opt.timestep
        model.opt.timestep = dt
        data = mujoco.MjData(model)
        data.qpos[:] = self.neutral
        actuator_qadr = model.jnt_qposadr[model.actuator_trnid[:, 0]]
        data.ctrl[:] = self.neutral[actuator_qadr]
        failures, max_penetration, saturation_ticks = [], 0.0, 0
        max_speed_ratio, max_positive_power, max_regen_power = 0.0, 0.0, 0.0
        root = model.body('pelvis').id
        ticks = int(round(seconds / dt))
        actual = 0
        for _ in range(ticks):
            previous_velocity = data.qvel.copy()
            mujoco.mj_step(model, data)
            applied_force = data.actuator_force.copy()
            step_mean_velocity = .5 * (previous_velocity + data.qvel)
            # mj_step leaves contacts/xmat at the old state; refresh without integrating.
            mujoco.mj_forward(model, data)
            actual += 1
            if not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all():
                failures.append('nonfinite')
                break
            if any(int(w.number) for w in data.warning):
                failures.append('mujoco_warning')
                break
            max_penetration = max(max_penetration, max((-float(c.dist) for c in data.contact), default=0))
            caps = np.max(np.abs(model.actuator_forcerange), axis=1)
            saturation_ticks += int(np.any(np.abs(applied_force) >= caps * .999))
            speed_ratio = float(np.max(np.abs(data.qvel[self.dadr]) / self.speed_limits))
            max_speed_ratio = max(max_speed_ratio, speed_ratio)
            actuator_dadr = model.jnt_dofadr[model.actuator_trnid[:, 0]]
            mechanical = applied_force * step_mean_velocity[actuator_dadr]
            max_positive_power = max(max_positive_power, float(np.maximum(mechanical, 0).sum()))
            max_regen_power = max(max_regen_power, float(np.maximum(-mechanical, 0).sum()))
            if speed_ratio > 1.1:
                failures.append('design_joint_speed_exceeded')
                break
            if data.xmat[root].reshape(3, 3)[2, 2] < .8:
                failures.append('root_tilt_exceeded')
                break
            if max_penetration > .005:
                failures.append('contact_penetration_exceeded_5mm')
                break
            if data.qpos[2] < self.neutral[2] - .05:
                failures.append('root_height_drop_exceeded_50mm')
                break
            if actual >= 5 and saturation_ticks / actual > .5:
                failures.append('actuator_saturation_exceeded_half_ticks')
                break
        mujoco.mj_forward(model, data)
        warnings = {str(i): int(w.number) for i, w in enumerate(data.warning) if w.number}
        output = {'dt_s': dt, 'requested_duration_s': seconds,
                  'actual_duration_s': float(data.time), 'actual_integrations': actual,
                  'completed': actual == ticks,
                  'finite': bool(np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all()),
                  'limited_rejection_pass': actual == ticks and not failures,
                  'stop_reasons': failures, 'warnings': warnings,
                  'root_height_start_m': float(self.neutral[2]),
                  'root_height_end_m': float(data.qpos[2]),
                  'root_up_cosine_end': float(data.xmat[root].reshape(3, 3)[2, 2]),
                  'max_contact_penetration_m': max_penetration,
                  'actuator_saturation_ticks': saturation_ticks,
                  'max_design_joint_speed_ratio': max_speed_ratio,
                  'max_positive_mechanical_power_w': max_positive_power,
                  'max_negative_mechanical_power_w': max_regen_power,
                  'power_sampling': 'applied step force times mean endpoint joint velocity; diagnostic approximation',
                  'speed_and_bus_limits_enforced_by_actuator': False,
                  'root_contract': self.root_contract,
                  'actuation_contract': self.actuation_contract,
                  'rejection_boundaries': {'root_up_cosine_min': .8, 'root_height_drop_max_m': .05,
                      'contact_penetration_max_m': .005, 'design_speed_ratio_max': 1.1,
                      'saturated_tick_fraction_max': .5, 'saturation_min_ticks': 5},
                  'controller': 'limited position hold, zero root assistance; not a walking controller',
                  'scope': 'short MuJoCo rejection run only; 20ms is a separate diagnostic, never Bevy acceptance'}
        model.opt.timestep = old_dt
        return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, default=ROOT / 'robots/gorilla_v0_1/models/full/robot.xml')
    parser.add_argument('--spec', type=Path, default=ROOT / 'robots/gorilla_v0_1/configs/layout_b_spec.json')
    parser.add_argument('--out', type=Path, default=ROOT / 'robots/gorilla_v0_1/evidence/layout_b_screen.json')
    args = parser.parse_args()
    screen = Screen(args.model, args.spec)
    poses = screen.poses()
    samples = [screen.static(p, load) for p in poses for load in screen.spec['task_load_scan_kg']]
    samples.extend(screen.static(p, 20, scale) for p in poses for scale in (.8, 1.2))
    for p in poses:
        p['qpos'] = p['qpos'].tolist()
    battery = screen.spec['battery']
    output = {'schema': 'gorilla_layout_screen_v1', 'robot_id': 'gorilla_v0_1',
              'checkpoint_id': screen.spec['checkpoint_id'], 'model_sha256': digest(args.model),
              'spec_sha256': digest(args.spec), 'finite_model_load': True,
              'evaluator_sha256': digest(__file__),
              'model_contract_sha256': screen.model_contract_sha256,
              'robot_mass_kg': float(screen.model.body_mass.sum()),
              'body_count': screen.model.nbody - 1, 'active_joint_count': screen.model.nu,
              'root_contract': screen.root_contract, 'actuation_contract': screen.actuation_contract,
              'joint_order': [j['name'] for j in screen.joints],
              'poses': poses, 'static_samples': samples,
              'static_sample_count': len(samples),
              'limited_static_pass_count': sum(s['limited_screen_pass'] for s in samples),
              'mass_perturbation_scope': 'uniform gravity scaling only; not all procurement/COM/inertia uncertainty',
              'diagnostic_rejection_runs': [screen.reject_run(.002), screen.reject_run(.02)],
              'energy_hypotheses': {'nominal_energy_wh': battery['nominal_energy_wh'],
                  'usable_fraction_assumption': battery['usable_fraction_assumption'],
                  'average_input_w_to_minutes': {str(p): battery['nominal_energy_wh'] *
                    battery['usable_fraction_assumption'] / p * 60
                    for p in battery['task_average_power_hypotheses_w']},
                  'status': 'scenario arithmetic, not runtime endurance verification'},
              'physical_hard_freeze': False, 'manufacturing_release': False,
              'walking_acceptance': False, 'object_pickup_acceptance': False,
              'bevy_acceptance': False, 'policy_included': False,
              'speed_recommendation': None, 'rated_payload_recommendation_kg': None,
              'capability_status': 'finite engineering demand screen only; red gates prevent rated capability claim'}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'out': str(args.out), 'mass_kg': output['robot_mass_kg'],
                      'limited_static_passes': f"{output['limited_static_pass_count']}/{len(samples)}",
                      'physical_hard_freeze': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
