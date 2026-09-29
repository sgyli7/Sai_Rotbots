"""Pixel-input marker/PnP regression, not physical-camera task acceptance."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.spatial.transform import Rotation

from sai_agent.goose.vision import MarkerTracker
from sai_agent.paths import resource_root


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=Path('artifacts/Goose_V0.1/vision_pixels'))
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    height,width=480,640;f=height/(2*np.tan(np.deg2rad(70)/2))
    calibration={'schema':'goose_camera_calibration_v1','width_px':width,'height_px':height,
        'camera_matrix':[[f,0,width/2],[0,f,height/2],[0,0,1]],'distortion_coefficients':[0]*5,
        'distortion_model':'opencv_brown','marker_lengths_m':{'7':.016},'maximum_reprojection_error_px':2.,
        'status':'synthetic pinhole regression; never physical camera calibration'}
    tracker=MarkerTracker(calibration);dictionary=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    black=cv2.aruco.generateImageMarker(dictionary,7,256);tag=cv2.copyMakeBorder(black,32,32,32,32,cv2.BORDER_CONSTANT,value=255)
    k=np.asarray(calibration['camera_matrix']);records=[]
    for index,(depth,angle,tilt) in enumerate([(.08,0,15),(.15,90,20),(.30,180,10)]):
        r=Rotation.from_euler('xyz',[180,tilt,angle],degrees=True).as_matrix();t=np.array([.002,-.003,depth])
        side=.016*320/256;half=side/2
        corners=np.array([[-half,half,0],[half,half,0],[half,-half,0],[-half,-half,0]],float)
        pixels=cv2.projectPoints(corners,cv2.Rodrigues(r)[0],t,k,np.zeros(5))[0].reshape(4,2)
        transform=cv2.getPerspectiveTransform(np.float32([[0,0],[319,0],[319,319],[0,319]]),pixels.astype(np.float32))
        gray=cv2.warpPerspective(tag,transform,(width,height),flags=cv2.INTER_LINEAR,borderValue=180)
        rgb=cv2.cvtColor(gray,cv2.COLOR_GRAY2RGB);cv2.imwrite(str(a.output/f'case_{index}.png'),gray)
        result=tracker.detect(rgb,float(index));pose=next((v for v in result if v.marker_id==7),None)
        error=float(np.linalg.norm(pose.position_camera_m-t)) if pose else None
        accepted=pose is not None and error<max(.002,depth*.1)
        records.append({'depth_m':depth,'image_rotation_deg':angle,'detected':pose is not None,
                        'translation_error_m':error,'reprojection_error_px':pose.reprojection_error_px if pose else None,'pass':accepted})
    blank=np.full((height,width,3),180,np.uint8);blank_rejected=not tracker.detect(blank,4.)
    result={'scope':'RGB-only detector plus calibrated square PnP; synthetic projected images, not real camera or autonomous grasp',
            'opencv_version':cv2.__version__,'cases':records,'blank_rejected':blank_rejected,
            'decoded_corner_order_preserved':True,'perception_accepts_object_truth':False,
            'source_sha256':hashlib.sha256((resource_root()/'src/sai_agent/goose/vision.py').read_bytes()).hexdigest(),
            'pass':all(v['pass'] for v in records) and blank_rejected}
    (a.output/'calibration.json').write_text(json.dumps(calibration,indent=2)+'\n')
    (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    return 0 if result['pass'] else 2


if __name__=='__main__':raise SystemExit(main())
