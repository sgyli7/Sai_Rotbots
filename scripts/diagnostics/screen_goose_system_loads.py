"""Same-geometry 18-axis kinematic/static architecture screen, NOT a training model.

Links use explicit parent assignments and conditional masses. Contact forces
satisfy whole-body static equilibrium. An independent MuJoCo gravity/Jacobian
calculation checks the analytical joint moments. No collision, gait, thermal,
friction identification or manufacturing acceptance is implied.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import mujoco
import trimesh
from scipy.optimize import least_squares, brentq, linprog
from scipy.spatial.transform import Rotation
from scipy.spatial import ConvexHull

ROOT=Path(__file__).resolve().parents[2]
R=ROOT/'robots/Goose_V0.1'
SCENE=R/'cad/source/fuller_exterior_candidate/closed/scene.json'
BASIS=SCENE.parent/'hardware_basis.json'
MASS=R/'evidence/accepted_mass_neck_screen.json'
FOOT=R/'cad/source/foot_support_candidate/foot_parts.json'
OUT=R/'evidence/system_static_screen.json'


def vec(v):return ' '.join(f'{x:.12g}' for x in v)
def ry(degrees):return Rotation.from_rotvec([0,np.deg2rad(degrees),0]).as_matrix()


class System:
    def __init__(self):
        self.source=json.loads(SCENE.read_text()); self.parts={p['name']:p for p in self.source['parts']}
        self.motors={m['joint']:m for m in json.loads(BASIS.read_text())['actuators']}
        self.parents={'neck_yaw':'torso','neck_pitch':'neck_yaw','neck_mid_pitch':'neck_pitch',
            'head_pitch':'neck_mid_pitch','head_roll':'head_pitch','beak_hinge':'head_roll'}
        for side in ('right','left'):
            prev='torso'
            for suffix in ('hip_yaw','hip_roll','hip_pitch','knee_pitch','ankle_pitch','ankle_roll'):
                name=side+'_'+suffix;self.parents[name]=prev;prev=name
        self.names=list(self.parents)
        self.pivots={'torso':np.zeros(3)};self.axes={}
        for n in self.names:
            hardware='beak_drive' if n=='beak_hinge' else n
            self.pivots[n]=np.array(self.motors[hardware]['shaft_world_mm'])/1000
            self.axes[n]=np.array(self.motors[hardware]['axis_world'],float)
        self.pivots['beak_hinge']=np.array([.160,0,.576])
        self.grip=np.array([.240,0,.553]);self.tip=np.array([.263,0,.5514])
        self.items=json.loads(MASS.read_text())['items']
        for item in self.items:item['body']=self.owner(item['name'])
        # Replace only the four physically changed solids; add two metal plates.
        foot_report=json.loads((R/'evidence/foot_support_candidate.json').read_text())
        densities={p['name']:p['density_kg_m3'] for p in foot_report['parts']}
        foot_parts=json.loads(FOOT.read_text())['parts']; changed={p['name'] for p in foot_parts}
        self.items=[i for i in self.items if i['name'] not in changed]
        self.contact_hulls={}
        for p in foot_parts:
            f=np.asarray(p['faces']);m=trimesh.Trimesh(p['vertices'],np.vstack((f[:,[0,1,2]],f[:,[0,2,3]])),process=False)
            side=p['name'].split('_')[0]
            self.items.append(dict(name=p['name'],body=side+'_ankle_roll',mass_kg=float(m.volume*densities[p['name']]),
                center_m=m.center_mass.tolist(),relative_uncertainty=.1 if p['name'].endswith('plate') else .3,
                basis='actual foot candidate solid volume; assumed material density'))
            if p['name'].endswith('sole'):
                v=np.asarray(p['vertices']);xy=v[np.isclose(v[:,2],v[:,2].min()),:2]
                self.contact_hulls[side]=ConvexHull(xy)
        self.items.append(dict(name='specified_payload_50g',body='head_roll',mass_kg=.05,
            center_m=self.grip.tolist(),relative_uncertainty=0,basis='specified held object lump; not actual grasp contact simulation'))
        self.spec=json.loads((R/'configs/robot_spec.json').read_text())['servos']
        self.spec={s['model']:s for s in self.spec.values()}
        self.desc={n:{n} for n in self.names}
        for n in reversed(self.names):
            p=self.parents[n]
            if p in self.desc:self.desc[p]|=self.desc[n]

    def owner(self,name):
        if name.endswith('_mount_reserve'):name=name.removesuffix('_mount_reserve')
        if name in self.motors:
            return 'head_roll' if name=='beak_drive' else self.parents[name]
        if name in ('camera_module','head_internal_frame_reserve'):return 'head_roll'
        group=self.parts[name]['group']
        if group=='neck_cable':return 'neck_pitch' if name.endswith(('0','1','2')) else 'neck_mid_pitch'
        mapping={'lower_neck_fork':'neck_pitch','upper_neck_fork':'neck_mid_pitch',
            'head_roll_bridge':'head_pitch','neck_mount':'neck_yaw','head':'head_roll',
            'head_internal':'head_roll','lower_beak':'beak_hinge','beak_transmission':'head_roll'}
        for side in ('right','left'):
            mapping.update({side+'_thigh_fork':side+'_hip_pitch',side+'_shin_fork':side+'_knee_pitch',side+'_foot':side+'_ankle_roll'})
            if name==side+'_ankle_crossmember':return side+'_ankle_pitch'
        return mapping.get(group,'torso')

    def fk(self,q,root_p=None,root_r=None):
        poses={'torso':(np.zeros(3) if root_p is None else np.array(root_p),np.eye(3) if root_r is None else root_r)}
        axes={}
        for n,p in self.parents.items():
            pp,rr=poses[p]; pos=pp+rr@(self.pivots[n]-self.pivots[p]);axis=rr@self.axes[n]
            rot=rr@Rotation.from_rotvec(self.axes[n]*q.get(n,0)).as_matrix()
            poses[n]=(pos,rot);axes[n]=axis
        return poses,axes

    def point(self,poses,body,original):
        p,r=poses[body];return p+r@(np.array(original)-self.pivots[body])

    def masses(self,poses,scale):
        return [(i,i['mass_kg']*(1+scale*i['relative_uncertainty']),self.point(poses,i['body'],i['center_m'])) for i in self.items]

    def model(self,scale):
        mj=ET.Element('mujoco',model='goose_system_static_screen')
        ET.SubElement(mj,'compiler',angle='radian',inertiafromgeom='false')
        ET.SubElement(mj,'option',gravity='0 0 -9.81')
        w=ET.SubElement(mj,'worldbody');nodes={}
        for body in ['torso']+self.names:
            parent=self.parents.get(body); delta=self.pivots[body]-(self.pivots[parent] if parent else 0)
            node=ET.SubElement(w if parent is None else nodes[parent],'body',name=body,pos=vec(delta));nodes[body]=node
            if parent is None:ET.SubElement(node,'freejoint',name='root')
            else:ET.SubElement(node,'joint',name=body,type='hinge',axis=vec(self.axes[body]),limited='false')
            items=[i for i in self.items if i['body']==body]
            mm=np.array([i['mass_kg']*(1+scale*i['relative_uncertainty']) for i in items]);cc=np.array([i['center_m'] for i in items])-self.pivots[body]
            mass=mm.sum();com=(mm[:,None]*cc).sum(0)/mass;inertia=np.zeros((3,3))
            for m,c in zip(mm,cc):
                d=c-com;inertia+=m*((d@d)*np.eye(3)-np.outer(d,d)+1e-4*np.eye(3))
            ET.SubElement(node,'inertial',mass=f'{mass:.12g}',pos=vec(com),fullinertia=vec([inertia[0,0],inertia[1,1],inertia[2,2],inertia[0,1],inertia[0,2],inertia[1,2]]))
        xml=ET.tostring(mj,encoding='unicode');return mujoco.MjModel.from_xml_string(xml),xml

    def pose(self,drop_mm=0,neck=None):
        q={n:0. for n in self.names};root=np.array([0.,0.,-drop_mm/1000])
        if drop_mm:
            def residual(a):
                # Both legs have the same sagittal world rotation, opposite axis signs.
                for side,sign in [('right',-1),('left',1)]:
                    q[side+'_hip_pitch']=a[0]*sign;q[side+'_knee_pitch']=a[1]*sign;q[side+'_ankle_pitch']=(-a[0]-a[1])*sign
                poses,_=self.fk(q,root)
                return (poses['left_ankle_roll'][0]-self.pivots['left_ankle_roll'])[[0,2]]
            sol=least_squares(residual,[.25,-.5],bounds=([-1.5,-2],[1.5,2]),xtol=1e-12,gtol=1e-12,ftol=1e-12)
            if np.linalg.norm(residual(sol.x))>1e-7:raise ValueError('crouch IK failed')
        if neck is not None:
            # Contact target is forward of the torso, 40 mm above the floor.
            target=np.array([.280,0,.040]);pitch=np.deg2rad(70)
            def residual(a):
                q['neck_pitch']=a[0];q['neck_mid_pitch']=a[1];q['head_pitch']=pitch-a[0]-a[1]
                poses,_=self.fk(q,root)
                return (self.point(poses,'head_roll',self.grip)-target)[[0,2]]
            sol=least_squares(residual,[2.,-.2],bounds=([0,-2],[2.8,2]),xtol=1e-12,ftol=1e-12,gtol=1e-12)
            if np.linalg.norm(residual(sol.x))>1e-6:raise ValueError('ground reach IK failed')
        return q,root,np.eye(3)

    def bank(self,side,q,root):
        # Reverse-chain ankle roll: support foot stays flat, upper body banks.
        pivot=self.fk(q,root)[0][side+'_ankle_roll'][0];other=dict(q)
        def state(angle):
            rot=Rotation.from_rotvec([angle,0,0]).as_matrix();p=pivot+rot@(root-pivot)
            other[side+'_ankle_roll']=-angle
            poses,_=self.fk(other,p,rot);items=self.masses(poses,0)
            com=sum(m*c for _,m,c in items)/sum(m for _,m,c in items)
            return com[1]-pivot[1],dict(other),p,rot
        angle=brentq(lambda x:state(x)[0],-.9,.9,xtol=1e-12)
        return state(angle)[1:]

    def evaluate(self,name,q,root,rot,supports,scale,drag,model):
        poses,axes=self.fk(q,root,rot);items=self.masses(poses,scale)
        total=sum(m for _,m,c in items);com=sum(m*c for _,m,c in items)/total
        grip=self.point(poses,'head_roll',self.grip);tip=self.point(poses,'head_roll',self.tip)
        zcontact=.0005;fz=total*9.81;cop_x=com[0]+drag*(grip[2]-zcontact)/fz
        forces=[('head_roll',grip,np.array([drag,0.,0.]),np.zeros(3))]
        # Opposed bite reactions close locally; they do not add a net neck load.
        normal=poses['head_roll'][1]@np.array([0.,0.,50.])
        forces.extend([('head_roll',grip,normal,np.zeros(3)),('beak_hinge',grip,-normal,np.zeros(3))])
        contacts=[]
        support_y = getattr(self, 'contact_center_y_m', {'right': -.089, 'left': .089})
        for side in supports:
            y = support_y[side]
            span = support_y['left']-support_y['right']
            fraction=1. if len(supports)==1 else ((support_y['left']-com[1])/span if side=='right' else (com[1]-support_y['right'])/span)
            # Single support uses CoP at COM lateral coordinate, within that foot.
            cp=np.array([cop_x,com[1] if len(supports)==1 else y,zcontact])
            force=np.array([-drag*fraction,0.,fz*fraction])
            couple=np.array([0.,0.,drag*(grip[1]-com[1])*fraction])
            forces.append((side+'_ankle_roll',cp,force,couple))
            hull=self.contact_hulls[side];dist=-(hull.equations[:,:2]@cp[:2]+hull.equations[:,2])
            # Verify this complete wrench admits nonnegative vertex normals and a
            # conservative |Fx|+|Fy| <= mu*Fz friction pyramid. Mu is assumed.
            xy=hull.points[hull.vertices];count=len(xy);aa=np.zeros((6,count*3));ub=np.zeros((4*count,count*3))
            for k,(x,yv) in enumerate(xy):
                dx,dy,dz=np.array([x,yv,zcontact])-cp
                aa[:3,k*3:k*3+3]=np.eye(3)
                aa[3:,k*3:k*3+3]=[[0,-dz,dy],[dz,0,-dx],[-dy,dx,0]]
                for j,(sx,sy) in enumerate([(1,1),(1,-1),(-1,1),(-1,-1)]):ub[4*k+j,3*k:3*k+3]=[sx,sy,-.6]
            lp=linprog(np.zeros(count*3),A_eq=aa,b_eq=np.r_[force,couple],A_ub=ub,b_ub=np.zeros(4*count),
                bounds=[(None,None),(None,None),(0,None)]*count,method='highs')
            contacts.append(dict(side=side,force_n=force.tolist(),cop_m=cp.tolist(),torsion_at_cop_nm=couple.tolist(),
                edge_margin_m=float(dist.min()),positive_normal=bool(force[2]>0),assumed_friction_coefficient=.6,
                vertex_wrench_feasible=bool(lp.success)))
        manual={}
        for n in self.names:
            jp=poses[n][0];moment=np.zeros(3)
            for item,m,c in items:
                if item['body'] in self.desc[n]:moment+=np.cross(c-jp,[0,0,-m*9.81])
            for body,p,f,t in forces:
                if body in self.desc[n]:moment+=np.cross(p-jp,f)+t
            manual[n]=-float(axes[n]@moment)
        d=mujoco.MjData(model);d.qpos[:3]=root;quat=Rotation.from_matrix(rot).as_quat();d.qpos[3:7]=quat[[3,0,1,2]]
        for n,value in q.items():d.qpos[model.joint(n).qposadr]=value
        mujoco.mj_forward(model,d);generalized=np.zeros(model.nv)
        for body,p,f,t in forces:mujoco.mj_applyFT(model,d,f,t,p,model.body(body).id,generalized)
        required=d.qfrc_bias-generalized
        errors={n:abs(manual[n]-required[int(model.joint(n).dofadr[0])]) for n in self.names}
        fk_error=max(np.linalg.norm(poses[n][0]-d.xpos[model.body(n).id]) for n in self.names)
        residual=float(np.max(np.abs(required[:6])))
        if max(errors.values())>1e-7 or fk_error>1e-9 or residual>1e-7:raise ValueError((name,errors,fk_error,residual))
        capacities={n:self.spec[self.motors['beak_drive' if n=='beak_hinge' else n]['model']]['torque_screening_Nm']*(3*.75 if n=='beak_hinge' else 1) for n in self.names}
        return dict(name=name,mass_variant=scale,drag_x_n=drag,total_mass_kg=total,com_m=com.tolist(),
            root_position_m=root.tolist(),root_quaternion_wxyz=d.qpos[3:7].tolist(),joint_q_rad=q,
            grip_m=grip.tolist(),beak_tip_m=tip.tolist(),contacts=contacts,
            static_contact_feasible=all(c['edge_margin_m']>=0 and c['positive_normal'] and c['vertex_wrench_feasible'] for c in contacts),
            joint_torque_nm=manual,screening_capacity_nm=capacities,
            max_mujoco_torque_difference_nm=max(errors.values()),max_mujoco_fk_difference_m=float(fk_error),floating_base_residual=residual,
            support_foot_orientation_error_rad=max(Rotation.from_matrix(poses[s+'_ankle_roll'][1]).magnitude() for s in supports),
            collision_and_joint_limit_status='NOT_CHECKED')


def main():
    s=System();cases=[]
    q,r,rot=s.pose();cases.append(('standing',q,r,rot,['right','left']))
    for drop in (40,60,80):
        q,r,rot=s.pose(drop);cases.append((f'crouch_{drop}',q,r,rot,['right','left']))
    q,r,rot=s.pose(60,neck=True);cases.append(('low_reach_geometry',q,r,rot,['right','left']))
    for side in ('right','left'):
        q,r,rot=s.pose();q,r,rot=s.bank(side,q,r);cases.append((side+'_single_support_bank',q,r,rot,[side]))
    results=[];out=ROOT/'artifacts/Goose_V0.1/system_static_screen';out.mkdir(parents=True,exist_ok=True)
    for scale in (-1,0,1):
        model,xml=s.model(scale)
        if scale==0:(out/'static_model.xml').write_text(xml)
        for name,q,root,rot,sides in cases:
            for drag in (-2,0,2):results.append(s.evaluate(name,q,root,rot,sides,scale,drag,model))
    summary={}
    for n in s.names:
        feasible=[r for r in results if r['static_contact_feasible']]
        worst=max(feasible,key=lambda r:abs(r['joint_torque_nm'][n]))
        torque=abs(worst['joint_torque_nm'][n]);capacity=worst['screening_capacity_nm'][n]
        summary[n]=dict(max_static_torque_nm=torque,case=worst['name'],mass_variant=worst['mass_variant'],drag_x_n=worst['drag_x_n'],
            old_capacity_screen_nm=capacity,capacity_screen_ratio=torque/capacity,
            architecture_allowance_1_5x_static_nm=1.5*torque,allowance_is_not_dynamic_simulation=True)
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (SCENE,BASIS,MASS,FOOT)}
    report=dict(status='SYSTEM_STATIC_ARCHITECTURE_SCREEN_NOT_TRAINING_HANDOFF',source_hashes=hashes,
        joint_count=len(s.names),cases=len(results),nominal_robot_mass_kg=sum(i['mass_kg'] for i in s.items)-.05,
        nominal_payload_kg=.05,joint_summary=summary,results=results,
        joint_tree={n:dict(parent=s.parents[n],pivot_at_visual_zero_m=s.pivots[n].tolist(),axis_at_visual_zero=s.axes[n].tolist()) for n in s.names},
        body_assignment_items=s.items,
        limitations=['Explicit parent assignment is a proposed structural interpretation of the appearance, not assembled hardware verification',
            '63 algebraic static cases: 7 poses, 3 correlated mass estimates, 3 drag directions; no motion or thermal model',
            'Single support bank pose and low reach have not passed self-collision, joint-limit or harness checks',
            'Contact feasibility includes positive normals, hull CoP and a vertex friction-pyramid LP at assumed mu=0.6; no measured material friction/compliance or actual pressure field',
            'Uniform 1.5x static torque is only an architecture sizing allowance, not a dynamic walking requirement',
            'Old motor capacities are 20-percent-stall screens, not measured continuous ratings',
            'Bite 50 N is an assumed opposed force at 80 mm lever; 3:1 beak drive remains unselected',
            'MuJoCo inertias contain a small artificial regularizer per mass lump; this XML must not be used to train a walking policy'])
    OUT.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),contact_feasible=sum(r['static_contact_feasible'] for r in results),nominal_robot_mass_kg=report['nominal_robot_mass_kg'],joint_summary=summary),indent=2))

if __name__=='__main__':main()
