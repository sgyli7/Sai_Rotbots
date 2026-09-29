"""Calibrated, image-only specified-object perception shared by all backends."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation


@dataclass(frozen=True)
class MarkerPose:
    marker_id: int
    timestamp_s: float
    position_camera_m: np.ndarray
    rotation_camera_from_marker: np.ndarray
    reprojection_error_px: float
    corners_px: np.ndarray


class MarkerTracker:
    """No simulator state input. IPPE ambiguity is retained until observed.

    Corner order is the decoded marker order, including after rotation. A
    square's second pose is filtered by cheirality, reprojection and temporal
    continuity; callers must reject poor/stale observations before movement.
    """
    def __init__(self, calibration: dict):
        import cv2
        self.cv=cv2
        self.calibration=calibration
        if calibration['distortion_model']!='opencv_brown':
            raise ValueError('Unsupported distortion model; calibrate explicitly')
        self.k=np.asarray(calibration['camera_matrix'],float)
        self.dist=np.asarray(calibration['distortion_coefficients'],float)
        if self.k.shape!=(3,3) or not np.isfinite(self.k).all() or min(self.k[0,0],self.k[1,1])<=0:
            raise ValueError('Invalid camera intrinsics')
        if (self.dist.ndim!=1 or self.dist.size not in (4,5,8,12,14) or
                not np.isfinite(self.dist).all() or not np.allclose(self.k[2],[0,0,1])):
            raise ValueError('Invalid camera calibration')
        dictionary=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.detector=cv2.aruco.ArucoDetector(dictionary,cv2.aruco.DetectorParameters())
        self.lengths={int(k):float(v) for k,v in calibration['marker_lengths_m'].items()}
        if any(not np.isfinite(v) or v<=0 for v in self.lengths.values()):raise ValueError('Marker side must be positive')
        self.last:dict[int,MarkerPose]={}

    def detect(self, rgb: np.ndarray, timestamp_s: float) -> list[MarkerPose]:
        cv=self.cv
        if rgb.shape[:2]!=(self.calibration['height_px'],self.calibration['width_px']):
            raise ValueError('Image size differs from calibration')
        if rgb.ndim!=3 or rgb.shape[2]!=3 or rgb.dtype!=np.uint8:
            raise ValueError('Expected uint8 RGB image')
        if not np.isfinite(timestamp_s) or timestamp_s<0:raise ValueError('Invalid capture timestamp')
        corners,ids,_=self.detector.detectMarkers(cv.cvtColor(rgb,cv.COLOR_RGB2GRAY))
        poses=[]
        if ids is None:return poses
        for corners_i,marker_i in zip(corners,ids.ravel()):
            marker_i=int(marker_i)
            if marker_i not in self.lengths:continue
            s=self.lengths[marker_i]/2
            points=np.array([[-s,s,0],[s,s,0],[s,-s,0],[-s,-s,0]],np.float64)
            image_points=corners_i.reshape(4,2).astype(np.float64)
            success,rotations,translations,*_=cv.solvePnPGeneric(points,image_points,self.k,self.dist,flags=cv.SOLVEPNP_IPPE_SQUARE)
            if not success:continue
            candidates=[]
            previous=self.last.get(marker_i)
            for rvec,tvec in zip(rotations,translations):
                r=cv.Rodrigues(rvec)[0];t=tvec.ravel()
                if np.min((points@r.T+t)[:,2])<=0:continue
                projected=cv.projectPoints(points,rvec,tvec,self.k,self.dist)[0].reshape(4,2)
                error=float(np.sqrt(np.mean(np.sum((projected-image_points)**2,axis=1))))
                score=error
                if previous is not None and 0<=timestamp_s-previous.timestamp_s<.3:
                    # Tie-break ambiguity, without making a poor pixel fit valid.
                    score+=.02*np.linalg.norm(Rotation.from_matrix(previous.rotation_camera_from_marker.T@r).as_rotvec())
                candidates.append((score,MarkerPose(marker_i,float(timestamp_s),t,r,error,image_points)))
            if candidates:
                pose=min(candidates,key=lambda p:p[0])[1]
                if pose.reprojection_error_px<=float(self.calibration.get('maximum_reprojection_error_px',2.)):
                    self.last[marker_i]=pose;poses.append(pose)
        return poses


def camera_point_in_torso(pose: MarkerPose, marker_point_m, head_rotation,
                          head_position_m, camera_extrinsics: dict) -> np.ndarray:
    """Transform a declared marker/grasp offset using encoders and mount data.

    Head pose must be encoder FK relative to the torso. World object truth is
    neither accepted nor needed. Physical extrinsics require calibration.
    """
    q=np.asarray(camera_extrinsics['orientation_head_from_cv_wxyz'],float)
    r=Rotation.from_quat([*q[1:],q[0]]).as_matrix()
    p_camera=pose.position_camera_m+pose.rotation_camera_from_marker@np.asarray(marker_point_m,float)
    p_head=np.asarray(camera_extrinsics['position_head_m'],float)+r@p_camera
    return np.asarray(head_position_m)+np.asarray(head_rotation)@p_head


def load_calibration(path:Path) -> dict:
    return json.loads(path.read_text())
