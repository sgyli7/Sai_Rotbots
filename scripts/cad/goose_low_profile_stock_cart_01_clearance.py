"""Zero-integration frozen04 versus exact outer cylinders of CAD tow head."""
from pathlib import Path
import json,xml.etree.ElementTree as ET,os
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['CUDA_VISIBLE_DEVICES']=''
import numpy as np
import mujoco as mj
W=Path(__file__).resolve().parents[2];PKG=W/'robots/goose_v0_2/models/physics_v0_2_20261018_04';E=W/'robots/goose_v0_2/evidence/low_profile_stock_cart_01'
t=ET.parse(PKG/'robot.xml');root=t.getroot()
for mesh in root.findall('./asset/mesh'):mesh.set('file',str((PKG/mesh.get('file')).resolve()))
rods={
 'bite_sleeve':([.3,-.08,.48],[.3,.08,.48],.006),
 'bite_yoke_positiveY':([.363,0,.48],[.3,.085,.48],.007),
 'bite_yoke_negativeY':([.363,0,.48],[.3,-.085,.48],.007),
 'shaft_socket':([.351,0,.48],[.375,0,.48],.007),
 'steel_roll_shaft':([.345,0,.48],[.455,0,.48],.004),
 'roll_housing_outer':([.405,0,.48],[.447,0,.48],.017)
}
for n,(a,b,r) in rods.items():ET.SubElement(root.find('worldbody'),'geom',name='cart_'+n,type='cylinder',fromto=' '.join(map(str,a+b)),size=str(r),density='0',contype='0',conaffinity='0')
m=mj.MjModel.from_xml_string(ET.tostring(root,encoding='unicode'));d=mj.MjData(m);state=json.loads((E/'goose_cart_context.json').read_text());d.qpos[:]=state['full_qpos'];mj.mj_forward(m,d)
dist=[]
for n in rods:
 for jaw in ['upper_bill_envelope','lower_bill_envelope']:
  seg=np.zeros(6);v=mj.mj_geomDistance(m,d,m.geom('cart_'+n).id,m.geom(jaw).id,1,seg);dist.append({'cart_part':n,'robot_geom':jaw,'signed_distance_m':float(v),'closest_segment_world_m':seg.tolist()})
out={'robot':'physics_v0_2_20261018_04','query':'mj_geomDistance on loaded convex robot proxies and exact outer cylindrical surfaces matching CAD toe-head rods','scope':'Hollow bores do not affect external mouth clearance. Only prescribed single FK posture; no swept assembly, gait or structural certification. Intended bite_sleeve contact is reported, not excluded as a pass.','distances':dist,'rod_world_endpoints_and_outer_radius_m':rods,'physics_integrations':0,'GPU':0,'training':0}
(E/'local_mouth_clearance.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
