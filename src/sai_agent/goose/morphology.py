"""Structured torso authoring grids from explicit millimetre section data.

This describes a candidate skin only. It does not assert room for hardware,
attachment strength, minimum wall after interpolation, or manufacturing.
"""
from __future__ import annotations
import numpy as np
from scipy.interpolate import PchipInterpolator


def body_grids(profile_rows, side: int, wall_mm: float = 2.4, lower_exit_profile=None):
    if side not in (-1, 1) or wall_mm <= 0:
        raise ValueError('side must be +/-1 and wall must be positive')
    rows = np.asarray(profile_rows, dtype=float)
    if rows.shape[1:] != (4,) or np.any(np.diff(rows[:, 0]) <= 0) or np.any(rows[:, 2:] <= wall_mm):
        raise ValueError('expected ascending X, centreZ, lateralRadius, verticalRadius sections')
    profile = PchipInterpolator(rows[:, 0], rows[:, 1:], axis=0)
    derivative = profile.derivative()
    exit_curve=None
    if lower_exit_profile is not None:
        exit_rows=np.asarray(lower_exit_profile,dtype=float)
        if exit_rows.shape[1:]!=(2,) or np.any(np.diff(exit_rows[:,0])<=0) or np.any(exit_rows[:,1]<0) or np.any(exit_rows[:,1]>17):
            raise ValueError('ascending authoring U and lower boundary V in0..17 required')
        exit_curve=PchipInterpolator(exit_rows[:,0],exit_rows[:,1],extrapolate=False)
    outer = np.zeros((65, 49, 3)); inner = outer.copy()
    for i in range(65):
        for j in range(49):
            # Continuous lower lip: reparameterise the surface's latitude,
            # rather than cutting staircase cells from the editable mesh.
            lower=float(exit_curve(i)) if exit_curve is not None and exit_rows[0,0]<=i<=exit_rows[-1,0] else 0.
            door_lower=14+5*(lower/17)**2
            jj=np.interp(j,[0,14,36,48],[lower,door_lower,36,48])
            v = np.clip((jj-25)/11, -1, 1)
            rear = -142+22*abs(v)**3; front = 83-24*abs(v)**3
            x = np.interp(i, [0, 10, 48, 64], [rows[0, 0], rear, front, rows[-1, 0]])
            t = np.clip((i-10)/38, 0, 1)
            half = .11+.45*np.sin(t*np.pi/2)**.7; centre = .14-.07*t
            angle = np.interp(jj, [0, 14, 36, 48], [-np.pi/2, centre-half, centre+half, np.pi/2])
            cz, ry, rz = profile(x); co, si = np.cos(angle), np.sin(angle)
            outer[i, j] = [x, side*(ry*co+.12), cz+rz*si]
            czd, ryd, rzd = derivative(x)
            normal = np.array([-co*co*ryd/ry-si*czd/rz-si*si*rzd/rz, side*co/ry, si/rz])
            normal /= np.linalg.norm(normal)
            inner[i, j] = outer[i, j]-wall_mm*normal
    return outer, inner


def apply_leg_layout(system, layout):
    """Apply declared neutral leg pivots to a mutable candidate, without lift.

    The caller remains responsible for rebuilding geometry and all mass items.
    No old policy or inertial compatibility is inferred from this operation.
    """
    if not layout.get('left_mirror_y'):
        raise ValueError('this candidate requires an explicit Y-mirrored left leg')
    suffixes = ('hip_yaw','hip_roll','hip_pitch','knee_pitch','ankle_pitch','ankle_roll')
    if set(layout['hip_pivots_right_mm']) != set(suffixes):
        raise ValueError('all six leg pivot definitions are required')
    for suffix in suffixes:
        right = np.asarray(layout['hip_pivots_right_mm'][suffix], dtype=float)/1000
        if right.shape != (3,) or not np.isfinite(right).all():
            raise ValueError('finite XYZ pivot required')
        system.pivots['right_'+suffix] = right
        system.pivots['left_'+suffix] = right*np.array([1,-1,1])
