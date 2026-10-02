"""Engine-independent nominal neck gravity feedforward from encoder/IMU data.

No contact force, simulator root position, actual randomized mass, or velocity
is an input. Coordinates and inertia/mass conventions come from the SI contract.
"""
import numpy as np

def quat_matrix(wxyz):
 w,x,y,z=np.asarray(wxyz,float)/np.linalg.norm(wxyz)
 return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                  [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                  [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])

class NominalNeckGravity:
 def __init__(self,contract):
  self.joints=contract['joints'][:6];self.bodies={b['name']:b for b in contract['bodies']}
  self.root=np.array(contract['root_origin_at_zero_m']);self.pivots={j['name']:np.array(j['pivot_world_at_zero_m']) for j in self.joints}
  self.pivots['torso']=self.root;self.axes=[np.array(j['axis_parent']) for j in self.joints];self.skews=[]
  self.passive=contract.get('passive_linkage_joints',[])
  self.pivots.update({j['name']:np.array(j['pivot_world_at_zero_m']) for j in self.passive})
  for x,y,z in self.axes:self.skews.append(np.array([[0,-z,y],[z,0,-x],[-y,x,0]]))
 def __call__(self,q,imu_wxyz):
  positions={'torso':np.zeros(3)};rotations={'torso':quat_matrix(imu_wxyz)};axes=[];centers=[];forces=[]
  for k,j in enumerate(self.joints):
   n,p=j['name'],j['parent'];pr=rotations[p];positions[n]=positions[p]+pr@(self.pivots[n]-self.pivots[p]);axes.append(pr@self.axes[k]);K=self.skews[k]
   rotations[n]=pr@(np.eye(3)+np.sin(q[k])*K+(1-np.cos(q[k]))*(K@K));b=self.bodies[n]
   centers.append(positions[n]+rotations[n]@b['com_local_m']);forces.append(np.array([0,0,-9.81*b['mass_kg']]))
  for j in self.passive:
   n,p=j['name'],j['parent'];pr=rotations[p]
   positions[n]=positions[p]+pr@(self.pivots[n]-self.pivots[p])
   a=np.array(j['axis_parent']);x,y,z=a;K=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
   angle=j['mimic_multiplier']*q[next(k for k,v in enumerate(self.joints) if v['name']==j['mimic_joint'])]+j['mimic_offset_rad']
   rotations[n]=pr@(np.eye(3)+np.sin(angle)*K+(1-np.cos(angle))*(K@K));b=self.bodies[n]
   centers.append(positions[n]+rotations[n]@b['com_local_m']);forces.append(np.array([0,0,-9.81*b['mass_kg']]))
  diff=np.array(centers)[None,:,:]-np.array([positions[j['name']] for j in self.joints[:5]])[:,None,:]
  descendants=np.c_[np.triu(np.ones((5,6))),np.ones((5,len(self.passive)))]
  moment=np.cross(diff,np.array(forces)[None,:,:])*descendants[:,:,None]
  return -np.sum(np.sum(moment,axis=1)*np.array(axes[:5]),axis=1)
