"""Source-bound four-bar coordinates and virtual-work torque conversion.

The 020 package defines q_in = -(t - t0), q_out = jaw angle and
q_coupler = -(a - a0) - q_in. Its lower circle-intersection branch and
60-bisection reset are reproduced without loading or compiling MuJoCo.
With E=C-D, C'=dC/dq_out and D'=dD/dt, closure gives
J=dq_out/dq_in=-(E.D')/(E.C'). Thus qdot_out=J*qdot_in and
tau_in=J*tau_out, preserving signed power. This is an ideal linkage map,
not a motor capability, loss, dynamics or engineering-acceptance model.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import json
import math
from numbers import Real
from pathlib import Path


def _finite(value: float, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{label} must be a finite scalar")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{label} must be a finite scalar")
    return value


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


@dataclass(frozen=True)
class BeakDriveState:
    input_rad: float
    output_rad: float
    coupler_rad: float
    output_per_input: float
    coupler_per_input: float
    closure_residual_m: float


@dataclass(frozen=True)
class BeakDriveMapping:
    """Immutable planar geometry in the contract's millimetres/radians.

    Construct with ``from_package`` for hash-bound production use. No
    saturation is hidden in this API: caller clips physical motor torque
    *after* conversion, using motor-side speed and separately sourced limits.
    """

    a: tuple[float, float]
    o: tuple[float, float]
    rin: float
    rout: float
    length: float
    phase: float
    input_range: tuple[float, float]
    output_range: tuple[float, float]
    source_sha256: tuple[tuple[str, str], ...] = ()

    @classmethod
    def from_package(cls, package: str | Path) -> BeakDriveMapping:
        package = Path(package).resolve(strict=True)
        manifest_path = package / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        files = {row["path"]: row["sha256"] for row in manifest["files"]}
        if len(files) != len(manifest["files"]):
            raise ValueError("Ambiguous source manifest")
        bound = {"manifest.json": hashlib.sha256(manifest_path.read_bytes()).hexdigest()}
        required = ("physical_contract.json", "runtime_interface.json", "robot.xml",
                    "parent_runtime_adapter.py", "runtime_adapter.py")
        for name in required:
            digest = hashlib.sha256((package / name).read_bytes()).hexdigest()
            if files.get(name) != digest:
                raise ValueError(f"Beak source SHA256 mismatch: {name}")
            bound[name] = digest
        tree = ast.parse((package / "parent_runtime_adapter.py").read_text())
        methods = [method for node in tree.body if isinstance(node, ast.ClassDef)
                   for method in node.body if isinstance(method, ast.FunctionDef)
                   and method.name in ("linkage", "jaw_from_input")]
        algorithm = ast.dump(ast.Module(body=methods, type_ignores=[]), include_attributes=False)
        if hashlib.sha256(algorithm.encode()).hexdigest() != (
                "8dc0cc9a3c5cd02861855f414513a164e84115ed9c359684f4fb8d783ac93076"):
            raise ValueError("Unsupported source linkage/reset algorithm")
        contract = json.loads((package / "physical_contract.json").read_text())
        interface = json.loads((package / "runtime_interface.json").read_text())
        if (contract["release_id"] != manifest["release_id"]
                or interface["release_id"] != manifest["release_id"]
                or contract["joint_order"][5] != "beak_input_rotor"
                or interface["public_joint_order"] != contract["joint_order"]
                or contract["action_size"] != 18 or interface["action_size"] != 18):
            raise ValueError("Source physical-input identity mismatch")
        transmission = contract["beak_transmission"]
        g = transmission["geometry"]
        result = cls(tuple(g["A"]), tuple(g["O"]), g["rin"], g["rout"],
                     g["L"], g["phase"], tuple(transmission["input_rom_rad"]),
                     tuple(transmission["output_rom_rad"]), tuple(sorted(bound.items())))
        if (contract["joints"][5]["range_rad"] != list(result.input_range)
                or result.output_range[0] != 0.0
                or not 0 < result.output_range[1] <= 0.55):
            raise ValueError("Unsupported source reset/output range")
        for q, expected in ((result.output_range[0], result.input_range[1]),
                            (result.output_range[1], result.input_range[0])):
            if abs(result.from_output(q).input_rad - expected) > 1e-12:
                raise ValueError("Source four-bar endpoint mismatch")
        return result

    def _pose(self, output_rad):
        z = self.phase - output_rad
        c = (self.o[0] + self.rout * math.cos(z), self.o[1] + self.rout * math.sin(z))
        v = (c[0] - self.a[0], c[1] - self.a[1])
        r = math.hypot(*v)
        cosine = (self.rin**2 + r**2 - self.length**2) / (2 * self.rin * r)
        if not -1.0 < cosine < 1.0:
            raise ValueError("Infeasible or singular four-bar circle intersection")
        t = math.atan2(v[1], v[0]) - math.acos(cosine)
        d = (self.a[0] + self.rin * math.cos(t), self.a[1] + self.rin * math.sin(t))
        e = (c[0] - d[0], c[1] - d[1])
        angle = math.atan2(e[1], e[0])
        return t, angle, e, (self.rout * math.sin(z), -self.rout * math.cos(z)), (
            -self.rin * math.sin(t), self.rin * math.cos(t))

    def _source_linkage(self, output_rad):
        t, angle, *_ = self._pose(output_rad)
        t0, angle0, *_ = self._pose(0.0)
        qin = -(t - t0)
        return qin, -(angle - angle0) - qin

    def from_output(self, output_rad: float) -> BeakDriveState:
        """Exact source inverse map: passive jaw target -> physical input."""
        q = _finite(output_rad, "Jaw position")
        if not self.output_range[0] <= q <= self.output_range[1]:
            raise ValueError("Jaw position outside source output ROM")
        qin, coupler = self._source_linkage(q)
        _, _, e, cq, dt = self._pose(q)
        numerator, denominator = _dot(e, dt), _dot(e, cq)
        if min(abs(numerator), abs(denominator)) < 1e-12 * self.length * max(self.rin, self.rout):
            raise ValueError("Singular four-bar velocity/torque map")
        j = -numerator / denominator
        eqin = (cq[0] * j + dt[0], cq[1] * j + dt[1])
        jc = -_cross(e, eqin) / _dot(e, e) - 1.0
        return BeakDriveState(qin, q, coupler, j, jc,
                              abs(math.hypot(*e) - self.length) * 1e-3)

    def from_input(self, input_rad: float) -> BeakDriveState:
        """Source's 60-bisection reset, with strict physical command ROM."""
        q = _finite(input_rad, "Input position")
        if not self.input_range[0] <= q <= self.input_range[1]:
            raise ValueError("Input position outside source physical ROM")
        lo, hi = 0.0, 0.55
        for _ in range(60):
            mid = (lo + hi) / 2
            if self._source_linkage(mid)[0] > q:
                lo = mid
            else:
                hi = mid
        state = self.from_output((lo + hi) / 2)
        return BeakDriveState(q, state.output_rad, state.coupler_rad,
                              state.output_per_input, state.coupler_per_input,
                              state.closure_residual_m)

    def input_torque(self, output_torque_nm: float, input_rad: float) -> float:
        """Signed ideal motor torque required for a signed jaw effort."""
        return _finite(output_torque_nm, "Jaw torque") * self.from_input(input_rad).output_per_input

    def output_torque(self, input_torque_nm: float, input_rad: float) -> float:
        """Signed ideal jaw effort from motor torque; no capability claim."""
        return _finite(input_torque_nm, "Input torque") / self.from_input(input_rad).output_per_input
