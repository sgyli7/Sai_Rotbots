"""Experimental repair of the torso skin parameterization, in millimetres.

Latitude features follow physical X. X is monotone in authoring U, so the
analytic (X, latitude) mapping has positive Jacobian X_U * latitude_V.
Cubic interpolation still needs an independent native self-interference gate.
The original body profile and existing runtime model remain unchanged.
"""
import numpy as np
from scipy.interpolate import PchipInterpolator


def service_skin_grids(profile_rows, side, wall_mm, lower_exit_profile):
    rows = np.asarray(profile_rows, dtype=float)
    exits = np.asarray(lower_exit_profile, dtype=float)
    if (side not in (-1, 1) or not np.isfinite(wall_mm) or wall_mm <= 0
            or rows.ndim != 2 or rows.shape[1] != 4 or len(rows) < 3
            or not np.isfinite(rows).all() or np.any(np.diff(rows[:, 0]) <= 0)
            or np.any(rows[:, 2:] <= wall_mm)
            or rows[0, 0] >= -142 or rows[-1, 0] <= 83
            or exits.ndim != 2 or exits.shape[1] != 2 or len(exits) < 2
            or not np.isfinite(exits).all() or np.any(np.diff(exits[:, 0]) <= 0)
            or np.any(exits[:, 1] < 0) or np.any(exits[:, 1] > 17)):
        raise ValueError('Valid section, wall, side and limb-exit data required')
    profile = PchipInterpolator(rows[:, 0], rows[:, 1:], axis=0)
    derivative = profile.derivative()
    exit_curve = PchipInterpolator(exits[:, 0], exits[:, 1], extrapolate=False)
    outer = np.zeros((65, 49, 3))
    inner = outer.copy()
    for j in range(49):
        lat = np.clip((j-25)/11, -1, 1)
        rear, front = -142+22*abs(lat)**3, 83-24*abs(lat)**3
        x_curve = PchipInterpolator([0, 10, 48, 64], [rows[0, 0], rear, front, rows[-1, 0]])
        for i in range(65):
            x = float(x_curve(i))
            authoring_u = np.interp(x, [rows[0, 0], -142, 83, rows[-1, 0]], [0, 10, 48, 64])
            lower = float(exit_curve(authoring_u)) if exits[0, 0] <= authoring_u <= exits[-1, 0] else 0.
            door_lower = 14+5*(lower/17)**2
            t = np.clip((x+142)/225, 0, 1)
            half, center = .11+.45*t, .14-.07*t
            def nominal(q):
                return np.interp(q, [0, 14, 36, 48], [-np.pi/2, center-half, center+half, np.pi/2])
            angle = float(PchipInterpolator([0, 14, 36, 48],
                [nominal(lower), nominal(door_lower), center+half, np.pi/2])(j))
            cz, ry, rz = profile(x)
            co, si = np.cos(angle), np.sin(angle)
            outer[i, j] = [x, side*(ry*co+.12), cz+rz*si]
            czd, ryd, rzd = derivative(x)
            n = np.array([-co*co*ryd/ry-si*czd/rz-si*si*rzd/rz, side*co/ry, si/rz])
            n /= np.linalg.norm(n)
            inner[i, j] = outer[i, j]-wall_mm*n
    return outer, inner


def service_skin_domains(door_trim=(.010, .030), fixed_seam_trim=.0015):
    """Named masks and exact CAD UV coordinates; trim units are dimensionless."""
    du, dv = door_trim
    if not (0 < du < 10/64 and 0 < dv < 10/48 and 0 < fixed_seam_trim < 1/64):
        raise ValueError('Invalid seam trim')
    aft = np.zeros((64, 48), dtype=bool)
    fore = aft.copy()
    for i in range(64):
        for j in range(48):
            if (39 <= i < 49 and j >= 42) or (10 <= i < 48 and 14 <= j < 36):
                continue
            (aft if i < 30 else fore)[i, j] = True
    ua = np.linspace(0, 1, 65)
    uf = ua.copy()
    ua[30] -= fixed_seam_trim
    uf[30] += fixed_seam_trim
    return dict(aft=(aft, ua, np.linspace(0, 1, 49)),
                fore=(fore, uf, np.linspace(0, 1, 49)),
                door=(np.ones((38, 22), dtype=bool),
                      np.linspace(10/64+du, 48/64-du, 39),
                      np.linspace(14/48+dv, 36/48-dv, 23)))
