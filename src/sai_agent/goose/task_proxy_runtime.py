"""Goose-only single-integration 50 Hz CPU source runtime, without training.

The previous checkpoint environment cannot be monkeypatched to support this
contract: its inner torque loop and its locomotion-only terminations differ.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import mujoco

import hashlib
DT = .02
JOINT_ORDER = tuple('neck_yaw neck_pitch neck_mid_pitch head_pitch head_roll beak_hinge right_hip_yaw right_hip_roll right_hip_pitch right_knee_pitch right_ankle_pitch right_ankle_roll left_hip_yaw left_hip_roll left_hip_pitch left_knee_pitch left_ankle_pitch left_ankle_roll'.split())
def sha256(path): return hashlib.sha256(path.read_bytes()).hexdigest()
from .task_goal import TaskGoal, invalid_goal_extension
from .stage_one_gravity import NominalNeckGravity

RUNTIME_REVISION = "goose_task_proxy_be_contact_v1"


class TaskProxyRuntime:
    def __init__(self, model_path: Path, contract_path: Path, *, skill="locomotion", seed=17):
        if skill not in ("locomotion", "recovery", "pickup"):
            raise ValueError("Unknown Goose skill")
        self.skill = skill
        if mujoco.__version__ != "3.10.0":
            raise ValueError("Task proxy contact mapping is pinned to MuJoCo 3.10.0")
        self.contract = json.loads(contract_path.read_text())
        if (self.contract.get("schema") != "goose_task_proxy_si_v1" or self.contract.get("candidate") != "goose_task_proxy_11_v1" or self.contract.get("runtime_revision") != RUNTIME_REVISION):
            raise ValueError("Explicit task proxy runtime identity required")
        for name, digest in self.contract.get("source_module_sha256", {}).items():
            path = Path(__file__).with_name(name)
            if sha256(path) != digest:
                raise ValueError("Source runtime module identity mismatch")
        cfg = self.contract.get("contact_mapping", {})
        if (cfg.get("method") != "whole_sole_native_manifold_backward_euler_v1"
                or abs(cfg.get("per_foot_stiffness_n_m", 0) - 140142.1824) > 1e-8
                or cfg.get("per_foot_damping_n_s_m") != 12.
                or cfg.get("prediction_band_m") != .01):
            raise ValueError("Unknown contact mapping requires a new runtime revision")
        for rel, digest in self.contract["asset_sha256"].items():
            path = (model_path.parent / rel).resolve()
            if not path.is_relative_to(model_path.parent.resolve()) or sha256(path) != digest:
                raise ValueError("Model asset identity mismatch")
        if self.contract.get("native_discrete") is not None and type(self) is TaskProxyRuntime:
            raise ValueError("Native discrete contract requires its explicit versioned runtime")
        if self.contract.get("numerical_metric") is not None and type(self) is TaskProxyRuntime:
            raise ValueError("Numerical metric requires the explicit experimental runtime")
        if any(self.contract[k] != DT for k in ("physics_dt_s", "torque_dt_s", "policy_dt_s")):
            raise ValueError("Goose requires one .02s physics/torque/policy update")
        if self.contract.get("physics_steps_per_tick") != 1 or self.contract["joint_order"] != list(JOINT_ORDER):
            raise ValueError("Incorrect Goose integration count or axis order")
        if sha256(model_path) != self.contract["model_sha256"]:
            raise ValueError("Model/contract hash mismatch")
        self.model = mujoco.MjModel.from_xml_path(str(model_path))
        self.data = mujoco.MjData(self.model)
        if self.model.opt.timestep != DT or self.model.nu != 18:
            raise ValueError("Model timestep/action mismatch")
        # Preserve a failed state for the independent evaluator. MuJoCo's
        # native numerical recovery must not silently reset a failed rollout.
        self.model.opt.disableflags |= int(mujoco.mjtDisableBit.mjDSBL_AUTORESET)
        self.names = list(JOINT_ORDER)
        joints = self.contract["joints"]
        self.qidx = np.array([int(self.model.joint(n).qposadr[0]) for n in self.names])
        self.vidx = np.array([int(self.model.joint(n).dofadr[0]) for n in self.names])
        self.kp = np.array([j["kp_nm_rad"] for j in joints])
        self.kd = np.array([j["kd_nm_s_rad"] for j in joints])
        self.peak = np.array([j["torque_peak_limit_nm"] for j in joints])
        self.cont = np.array([j["continuous_design_limit_nm"] for j in joints])
        self.speed = np.array([j["speed_limit_rad_s"] for j in joints])
        self.scale = np.array([j["action_scale_rad"] for j in joints])
        self.neutral = np.array([j["q_neutral_rad"] for j in joints])
        self.ranges = np.array([j["range_rad"] for j in joints])
        self.torso = self.model.body("torso").id
        self.ground = self.model.geom("ground").id
        self.foot_geoms = {self.model.geom(p["name"]).id for p in self.contract["passive_contacts"]}
        self.foot_geoms.update(self.model.geom(g["name"]).id for g in self.contract["collision_geometries"]
                               if g["part"] in ("right_flexible_sole", "left_flexible_sole"))
        module_path = Path(__file__).with_name("stage_one_gravity.py")
        if sha256(module_path) != self.contract["source_module_sha256"]["stage_one_gravity.py"]:
            raise ValueError("Nominal gravity source identity mismatch")
        self.gravity = NominalNeckGravity(self.contract)
        self.rng = np.random.default_rng(seed)
        self.nominal = {name: getattr(self.model, name).copy() for name in ("body_mass", "body_inertia", "body_ipos", "geom_friction")}
        self.goal = None
        self.pickup_stage = 0
        self.commands = np.zeros(3)
        self.reset()

    def reset(self, *, randomize=False):
        m, d = self.model, self.data
        for name, values in self.nominal.items():
            getattr(m, name)[:] = values
        self.strength = 1.0
        self.delay = 0
        if randomize:
            for body in self.contract["bodies"]:
                bid = m.body(body["name"]).id
                factor = self.rng.uniform(1 - body["mass_relative_design_uncertainty"], 1 + body["mass_relative_design_uncertainty"])
                m.body_mass[bid] *= factor
                m.body_inertia[bid] *= factor * self.rng.uniform(*body["inertia_multiplier_range"])
                m.body_ipos[bid] += self.rng.uniform(-body["com_randomization_m"], body["com_randomization_m"], 3)
            m.geom_friction[:, 0] = self.rng.uniform(*self.contract["foot_friction_range"])
            self.strength = self.rng.uniform(*self.contract["strength_multiplier_range"])
            self.delay = self.rng.integers(*[self.contract["latency_policy_steps"][0], self.contract["latency_policy_steps"][1] + 1])
        mujoco.mj_setConst(m, d)
        mujoco.mj_resetData(m, d)
        d.qpos[2] += .002
        d.qpos[self.qidx] = self.neutral
        for joint in self.contract["passive_linkage_joints"]:
            source, target = m.joint(joint["mimic_joint"]), m.joint(joint["name"])
            d.qpos[int(target.qposadr[0])] = joint["mimic_multiplier"] * d.qpos[int(source.qposadr[0])] + joint["mimic_offset_rad"]
        mujoco.mj_forward(m, d)
        self.actions = np.zeros(18)
        self.target = self.neutral.copy()
        self.thermal = np.zeros(18)
        self.last_tau = np.zeros(18)
        self.phase = 0.0
        self.age = 0
        self.physics_integrations = 0
        self.controller_updates = 0
        self.nominal_com_height = float(d.subtree_com[self.torso, 2])
        return self.observations()

    def observations(self):
        d = self.data
        rotation = d.xmat[self.torso].reshape(3, 3)
        base = np.r_[d.qvel[3:6] * .25, rotation.T @ [0., 0., -1.], self.commands,
                     d.qpos[self.qidx] - self.neutral, d.qvel[self.vidx] * .1,
                     self.actions, np.sin(self.phase), np.cos(self.phase)].astype(np.float32)
        base = np.clip(base, -20, 20)
        if self.skill == "pickup":
            if self.goal is None:
                extension = invalid_goal_extension(self.pickup_stage)
            elif isinstance(self.goal, TaskGoal):
                extension = self.goal.actor_extension(d.xpos[self.torso], d.xquat[self.torso], rotation, self.pickup_stage)
            else:
                raise ValueError("Pickup requires a typed TaskGoal")
            base = np.r_[base, extension]
        if base.shape != ((82 if self.skill == "pickup" else 65),) or not np.isfinite(base).all():
            raise FloatingPointError("Nonfinite/wrong-size Goose observation")
        return base

    def step(self, action):
        action = np.asarray(action, dtype=float)
        if action.shape != (18,) or not np.isfinite(action).all():
            raise ValueError("Goose action must be 18 finite values")
        action = np.clip(action, -1, 1)
        command = self.actions if self.delay else action
        desired = np.clip(self.neutral + self.scale * command, self.ranges[:, 0], self.ranges[:, 1])
        self.target += np.clip(desired - self.target, -self.speed * DT, self.speed * DT)
        q, qd = self.data.qpos[self.qidx], self.data.qvel[self.vidx]
        torque = self.kp * (self.target - q) - self.kd * qd
        torque[:5] += self.gravity(q[:6], self.data.qpos[3:7])
        cap = self.peak * self.strength * np.clip(1 - np.abs(qd) / (self.speed * 1.3), 0, 1)
        cap = np.minimum(cap, np.where(self.thermal > (self.cont * self.strength) ** 2, self.cont, self.peak) * self.strength)
        torque = np.clip(torque, -cap, cap)
        positive = torque * qd > 0
        power = float(np.sum(torque[positive] * qd[positive]))
        if power > self.contract["positive_mechanical_power_limit_w"]:
            torque[positive] *= self.contract["positive_mechanical_power_limit_w"] / power
        self.thermal += DT / 2 * (torque ** 2 - self.thermal)
        self.data.ctrl[:] = torque
        self.last_tau = torque.copy()
        before = float(self.data.time)
        # No nstep argument and no inner physics/torque loop.
        self._integrate()
        self.physics_integrations += 1
        self.controller_updates += 1
        if abs(self.data.time - before - DT) > 1e-12:
            raise RuntimeError("Integration did not advance exactly one 20ms tick")
        finite = all(np.isfinite(getattr(self.data, name)).all() for name in ("qpos", "qvel", "qacc", "ctrl"))
        if not finite or any(w.number for w in self.data.warning):
            raise FloatingPointError("Nonfinite Goose state or native solver warning; no automatic reset")
        # mj_step leaves pose-derived arrays at the pre-integration state.
        # Refresh kinematics and COM only: no extra integration, collision
        # detection, constraint solve, or replacement of this Tick's forces.
        mujoco.mj_kinematics(self.model, self.data)
        mujoco.mj_comPos(self.model, self.data)
        self.age += 1
        self.phase = (self.phase + 2 * np.pi * self.contract["phase_frequency_hz"] * DT) % (2 * np.pi)
        self.actions = action
        upright = float(self.data.xmat[self.torso].reshape(3, 3)[2, 2])
        height = float(self.data.subtree_com[self.torso, 2])
        nonfoot = self._nonfoot_ground_contact()
        # Recovery explicitly permits body contact and low COM. No auto reset;
        # a scorer must observe stable recovery and continuation separately.
        failure = False if self.skill in ("recovery", "pickup") else bool(height < .18 or upright < .65 or nonfoot)
        return self.observations(), {"failure": failure, "height_m": height, "upright": upright,
                                     "nonfoot_ground_contact": nonfoot, "auto_reset": False,
                                     "task_goal_invalid": self.skill == "pickup" and (self.goal is None or not self.goal.valid),
                                     "recovery_requested": upright < .65,
                                     "physics_integrations": self.physics_integrations,
                                     "controller_updates": self.controller_updates, "time_s": float(self.data.time)}

    def _integrate(self):
        m,d=self.model,self.data
        cfg=self.contract['contact_mapping']
        self.foundation_k_by_geom={g:cfg['per_foot_stiffness_n_m'] for g in self.foot_geoms}
        self.foundation_c_by_geom={g:cfg['per_foot_damping_n_s_m'] for g in self.foot_geoms}
        mujoco.mj_step1(m,d)
        self._planar_sole_quadrature()
        contacts=[]
        for cid,c in enumerate(d.contact):
            if self.ground not in c.geom: continue
            gid=next(int(g) for g in c.geom if g!=self.ground)
            if gid not in self.foot_geoms or c.efc_address<0: continue
            contacts.append((cid,c,gid))
        counts={g:sum(v[2]==g for v in contacts) for g in self.foot_geoms}
        for cid,c,gid in contacts:
            row=int(c.efc_address);num=counts[gid]
            k=self.foundation_k_by_geom[gid]/num;cc=self.foundation_c_by_geom[gid]/num
            alpha=1./(.02*(.02*k+cc))
            ref=-d.efc_vel[row]/.02-k*float(c.dist)/(.02*(.02*k+cc))
            d.efc_R[row]=alpha;d.efc_D[row]=1/alpha;d.efc_aref[row]=ref
            # MuJoCo's regularized elliptic cone uses a master coefficient
            # derived from BOTH normal and tangent impedances. Rebind it after
            # replacing the normal compliance; keeping its old value changes
            # the physical Coulomb force ratio despite unchanged geom friction.
            if c.dim > 1:
                c.mu = c.friction[0] * np.sqrt(d.efc_R[row+1] / alpha)
            if d.nisland:
                ir=int(d.map_efc2iefc[row])
                d.iefc_R[ir]=alpha;d.iefc_D[ir]=1/alpha;d.iefc_aref[ir]=ref
        mujoco.mj_step2(m,d)

    def _planar_sole_quadrature(self):
        """Four material points on the declared sole support face, one collider.

        Plane/upright-foot mapping only. Other shoe contacts keep native geometry.
        These are solver contact points, not extra shapes or root support forces.
        """
        m,d=self.model,self.data
        patches=[p for p in self.contract['contact_mapping'].get('ground_contact_quadrature', [])
                 if m.geom_type[m.geom(p['geom']).id] == mujoco.mjtGeom.mjGEOM_MESH
                 and d.xmat[m.body(p['body']).id].reshape(3,3)[2,2] > .7]
        if not patches:return
        replacement={m.geom(p['geom']).id for p in patches}
        retained=[]
        vector_fields=['geom','flex','elem','vert','frame','pos','friction','solref','solreffriction','solimp','H']
        scalar_fields=['dim','dist','includemargin','exclude','efc_address','mu']
        for c in d.contact:
            if self.ground in c.geom and any(g in replacement for g in c.geom):continue
            copy=mujoco.MjContact()
            for name in vector_fields:getattr(copy,name)[:]=getattr(c,name)
            for name in scalar_fields:setattr(copy,name,getattr(c,name))
            retained.append(copy)
        d.ncon=0
        for c in retained:
            if mujoco.mj_addContact(m,d,c):raise RuntimeError('Contact capacity exceeded')
        for p in patches:
            bid=m.body(p['body']).id;gid=m.geom(p['geom']).id
            for v in p['bottom_corners_body_m']:
                point=d.xmat[bid].reshape(3,3)@v+d.xpos[bid]
                gap=point[2]-d.geom_xpos[self.ground,2]
                if gap>.01:continue
                c=mujoco.MjContact();c.geom[:]=[self.ground,gid];c.flex[:]=-1;c.elem[:]=-1;c.vert[:]=-1
                c.dim=3;c.dist=gap;c.includemargin=.01;c.efc_address=-1
                c.pos[:]=point-[0.,0.,gap/2];c.frame[:]=[0,0,1,1,0,0,0,1,0]
                friction=max(m.geom_friction[gid,0],m.geom_friction[self.ground,0]);c.friction[:]=[friction,friction,.01,.002,.002];c.solref[:]=m.geom_solref[gid];c.solreffriction[:]=0;c.solimp[:]=m.geom_solimp[gid]
                if mujoco.mj_addContact(m,d,c):raise RuntimeError('Contact capacity exceeded')
        mujoco.mj_makeConstraint(m,d);mujoco.mj_island(m,d);mujoco.mj_projectConstraint(m,d);mujoco.mj_referenceConstraint(m,d)

    def _nonfoot_ground_contact(self):
        # Warp's public host bridge populates canonical geom[2]. The legacy
        # geom1/geom2 members can remain zero in MuJoCo 3.10 bridge results.
        return any(self.ground in c.geom and
                   int(c.geom[1] if c.geom[0] == self.ground else c.geom[0])
                   not in self.foot_geoms for c in self.data.contact)
