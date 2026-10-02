"""Trace the specified camera FOV through the printable head cover."""
from __future__ import annotations

import hashlib
import json
import math

from build123d import Axis, import_brep
import numpy as np
from scipy.spatial.transform import Rotation

from sai_agent.paths import resource_root


def main():
    robot=resource_root()/'robots/Goose_V0.1'
    specpath=robot/'configs/robot_spec.json';cadpath=robot/'cad/exports/cad_manifest.json'
    spec=json.loads(specpath.read_text());cad=json.loads(cadpath.read_text())
    if cad['spec_sha256']!=hashlib.sha256(specpath.read_bytes()).hexdigest():
        raise ValueError('Camera and CAD revision mismatch')
    camera=spec['camera'];q=camera['orientation_head_from_cv_wxyz']
    rotation=Rotation.from_quat([q[1],q[2],q[3],q[0]]).as_matrix()
    origin=np.asarray(camera['position_head_m'])*1000
    cover=import_brep(str(robot/'cad/source/head_cover.brep'))
    blocked=[]
    for h in np.linspace(-47.5,47.5,9):
        for v in np.linspace(-35,35,9):
            direction=rotation@np.array([math.tan(math.radians(h)),math.tan(math.radians(v)),1.])
            direction/=np.linalg.norm(direction)
            hits=[]
            for point,_normal in cover.find_intersection_points(Axis(tuple(origin),tuple(direction))):
                distance=float(np.dot(np.asarray(tuple(point))-origin,direction))
                if .1<distance<75:hits.append(distance)
            if hits:blocked.append({'horizontal_deg':round(float(h),2),'vertical_deg':round(float(v),2),
                                    'first_hit_mm':round(min(hits),2)})
    result={'scope':'head cover only; 9x9 angular rays from design lens-front, first 75 mm; not a physical optical calibration',
            'camera_sku':camera['sku'],'cad_manifest_sha256':hashlib.sha256(cadpath.read_bytes()).hexdigest(),
            'spec_sha256':hashlib.sha256(specpath.read_bytes()).hexdigest(),
            'rays':81,'blocked_rays':blocked,'pass':not blocked,
            'unverified':['other head parts in full articulation','lens housing and actual FOV/distortion',
                          'hand-eye and focus calibration at 80-300 mm']}
    out=robot/'evidence/camera_clearance_check.json';out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));return 0 if result['pass'] else 2


if __name__=='__main__':raise SystemExit(main())
