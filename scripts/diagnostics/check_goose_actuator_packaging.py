"""Nominal oriented motor body-box overlap check, not assembly clearance."""
import argparse,itertools,json
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser(); p.add_argument('basis',type=Path); p.add_argument('--report',type=Path,required=True); a=p.parse_args()
data=json.loads(a.basis.read_text()); motors=data['actuators']; boxes=[]
for m in motors:
    y=np.array(m['axis_world'],float); y/=np.linalg.norm(y)
    z=np.array(m['up_world'],float); x=np.cross(y,z); r=np.column_stack((x,y,z))
    w,h,d=m['case_whd_mm']; top=13.75 if '540' in m['model'] else 11.25 if '430' in m['model'] else 9.5
    center=np.array(m['shaft_world_mm'])+z*(top-h/2)
    boxes.append((m['joint'],center,r,np.array([w,d,h])/2))
issues=[]
for (na,ca,ra,ha),(nb,cb,rb,hb) in itertools.combinations(boxes,2):
    axes=[*ra.T,*rb.T]+[np.cross(x,y) for x in ra.T for y in rb.T]; overlaps=[]
    for axis in axes:
        norm=np.linalg.norm(axis)
        if norm<1e-9: continue
        axis/=norm
        overlaps.append(float(np.sum(ha*np.abs(ra.T@axis))+np.sum(hb*np.abs(rb.T@axis))-abs(np.dot(cb-ca,axis))))
    if min(overlaps)>.05: issues.append(dict(a=na,b=nb,minimum_sat_overlap_mm=min(overlaps)))
report=dict(scope='Nominal motor case boxes only. No horns, brackets, wires, shell fit, motion sweep, strength or physical stability acceptance.',parts=len(boxes),passed=not issues,body_box_overlaps=issues)
a.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
