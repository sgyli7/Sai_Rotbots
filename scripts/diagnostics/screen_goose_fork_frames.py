"""Independent 3D Euler-Bernoulli frame screen from native attachment dimensions.

This intentionally cannot release machined holes, bearing posts or the robot:
motor output is treated as fixed, rear idler as radial-only, and local holes,
preload, fatigue and assembly contact are absent from the beam idealization.
"""
from pathlib import Path
import json,sys,hashlib
import numpy as np

ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path[:0]=[str(ROOT/'scripts/models')]
from build_goose_stage_two import candidate


def beam(a,b,E,G,A,Iy,Iz,J,up):
    dx=np.array(b)-a;L=np.linalg.norm(dx);x=dx/L
    y=np.array(up)-x*np.dot(x,up);y/=np.linalg.norm(y);z=np.cross(x,y)
    q=np.vstack([x,y,z]);T=np.zeros((12,12))
    for i in range(4):T[3*i:3*i+3,3*i:3*i+3]=q
    k=np.zeros((12,12))
    for indices,value in [([0,6],E*A/L),([3,9],G*J/L)]:
        k[np.ix_(indices,indices)]+=value*np.array([[1,-1],[-1,1]])
    pattern=np.array([[12,6*L,-12,6*L],[6*L,4*L*L,-6*L,2*L*L],[-12,-6*L,12,-6*L],[6*L,2*L*L,-6*L,4*L*L]])
    k[np.ix_([1,5,7,11],[1,5,7,11])]+=E*Iz/L**3*pattern
    sign=np.diag([1,-1,1,-1]);k[np.ix_([2,4,8,10],[2,4,8,10])]+=E*Iy/L**3*(sign@pattern@sign)
    return T.T@k@T,k,T,L


def cantilever_check():
    # Independent textbook displacement/reaction, rotated into arbitrary3D.
    a=np.zeros(3);direction=np.array([2.,3.,4.]);direction/=np.linalg.norm(direction)
    b=direction*100.;up=np.array([0.,1.,0.]);E=69000.;G=26538.;A=80.;Iy=1000.;Iz=500.;J=100.
    K,k,T,L=beam(a,b,E,G,A,Iy,Iz,J,up);f=np.zeros(12);local=np.zeros(12);local[7]=10.;f=T.T@local
    u=np.zeros(12);u[6:]=np.linalg.solve(K[6:,6:],f[6:]);v=T@u
    expected=10.*100**3/(3*E*Iz);error=abs(v[7]-expected)
    if error>1e-10:raise ValueError(('cantilever solver',v[7],expected))
    return dict(force_n=10.,length_mm=100.,computed_deflection_mm=float(v[7]),textbook_deflection_mm=expected,error_mm=error)


def main():
    path=R/'cad/exports/pitch_fork_assembly/manifest.json';pfile=R/'evidence/manufacturing_component_parameters.json'
    native=json.loads(path.read_text());data=json.loads(pfile.read_text());s=candidate()
    lift=data['rigid_coordinate_lift_m']
    for n in s.pivots:s.pivots[n]=s.pivots[n]+[0,0,lift]
    s.pivots['torso']=np.zeros(3)
    E=69000.;G=E/(2*(1+.3));results=[]
    for a in native['assemblies']:
        upper=a['upper_joint'];lower=a['lower_joint'];rot0=np.eye(3) if s.axes[upper][1]>0 else np.diag([1.,-1.,-1.])
        delta=rot0.T@((s.pivots[lower]-s.pivots[upper])*1000);direction=delta/np.linalg.norm(delta)
        yn=a['near_plate_center_local_y_mm'];yf=a['far_plate_center_local_y_mm']
        nodes=np.array([delta*t+[0,y,0] for t in [0.,.5,1.] for y in [yn,yf]])
        connections=[(0,2,'plate'),(2,4,'plate'),(1,3,'plate'),(3,5,'plate'),(2,3,'bridge')]
        K=np.zeros((36,36));elements=[]
        for i,j,kind in connections:
            if kind=='plate':
                b=3.5;h=14.8;A=b*h;Iy=b*h**3/12;Iz=h*b**3/12
                J=h*b**3/3*(1-.63*b/h+.052*(b/h)**5);up=[0,1,0]
            else:
                b=14.;h=18.;A=4*h;Iy=4*h**3/12;Iz=2*(2*h*(6**2+2**2/12));J=2*h*2**3/3;up=direction
            kg,kl,T,L=beam(nodes[i],nodes[j],E,G,A,Iy,Iz,J,up)
            ids=np.r_[np.arange(i*6,(i+1)*6),np.arange(j*6,(j+1)*6)]
            K[np.ix_(ids,ids)]+=kg
            elements.append(dict(ids=ids,local=kl,T=T,A=A,Iy=Iy,Iz=Iz,J=J,b=b,h=h,kind=kind))
        fixed=set(range(6))|{6,8};free=[i for i in range(36) if i not in fixed]
        for case in data['results']:
            from scipy.spatial.transform import Rotation
            root=case['root_position_m'];rr=Rotation.from_quat(np.array(case['root_quaternion_wxyz'])[[1,2,3,0]]).as_matrix()
            poses,_=s.fk(case['joint_q_rad'],root,rr);po,ro=poses[upper];local_rot=ro@rot0
            F=np.zeros(36)
            def point_load(point,force,moment=np.zeros(3)):
                p=local_rot.T@(np.array(point)-po)*1000;f=local_rot.T@np.array(force);torque=local_rot.T@np.array(moment)*1000
                along=np.clip(np.dot(p,direction)/np.linalg.norm(delta),0,1)*2
                lo=min(1,int(along));weight=along-lo
                near=np.clip((p[1]-yf)/(yn-yf),0,1)
                for rank,w in [(lo,1-weight),(lo+1,weight)]:
                    for side,v in [(0,near),(1,1-near)]:
                        index=rank*2+side;ww=w*v
                        F[index*6:index*6+3]+=f*ww
                        F[index*6+3:index*6+6]+=(torque+np.cross(p-nodes[index],f))*ww
            for item in data['items']:
                if item['body'] not in s.desc[upper]:continue
                position=s.point(poses,item['body'],item['center_m'])
                mass=item['mass_kg']*(1+case['mass_variant']*item['relative_uncertainty'])
                point_load(position,[0,0,-9.81*mass])
            point_load(case['grip_m'],[case['drag_x_n'],0,0]) if 'head_roll' in s.desc[upper] else None
            for contact in case['contacts']:
                if contact['side']+'_ankle_roll' in s.desc[upper]:
                    point_load(contact['cop_m'],contact['force_n'],contact['torsion_at_cop_nm'])
            u=np.zeros(36);u[free]=np.linalg.solve(K[np.ix_(free,free)],F[free]);reaction=K@u-F
            torque_error=abs(reaction[4]/1000-case['joint_torque_nm'][upper])
            if torque_error>1e-7:raise ValueError((a['name'],case['name'],'whole-system torque disagreement',torque_error))
            stresses=[]
            for e in elements:
                force=e['local']@e['T']@u[e['ids']]
                for f in [force[:6],force[6:]]:
                    normal=abs(f[0])/e['A']+abs(f[4])*e['h']/2/e['Iy']+abs(f[5])*e['b']/2/e['Iz']
                    shear=1.5*np.linalg.norm(f[1:3])/e['A']+abs(f[3])*min(e['b'],e['h'])/2/e['J']
                    stresses.append(dict(kind=e['kind'],beam_von_mises_mpa=float(np.sqrt(normal**2+3*shear**2))))
            worst=max(stresses,key=lambda x:x['beam_von_mises_mpa'])
            idler=float(np.linalg.norm(reaction[[6,8]]))
            results.append(dict(assembly=a['name'],case=case['name'],mass_variant=case['mass_variant'],drag_n=case['drag_x_n'],
                max_beam_von_mises_mpa=worst['beam_von_mises_mpa'],worst_element=worst['kind'],
                max_displacement_mm=float(np.linalg.norm(u.reshape(-1,6)[:,:3],axis=1).max()),
                rear_idler_radial_reaction_n=idler,catalog_static_ratio=830/max(idler,1e-9),
                output_torque_agreement_nm=torque_error,nominal_yield_ratio=200/max(worst['beam_von_mises_mpa'],1e-9),
                stress_with_2x_notch_multiplier_mpa=2*worst['beam_von_mises_mpa']))
    worst=max(results,key=lambda x:x['stress_with_2x_notch_multiplier_mpa'])
    report=dict(schema='goose_fork_frame_screen_v1',scope='beam idealization of six manufactured link candidates under63whole-system static wrenches',
        cantilever_regression=cantilever_check(),case_count=len(results),results=results,worst_case=worst,
        screen_below_200mpa_with_2x_notch=all(x['stress_with_2x_notch_multiplier_mpa']<=200 for x in results),
        frame_stress_release=False,manufacturing_pass=False,
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [path,pfile,Path(__file__)]},
        limitations=['Fixed motor output assumes infinite gearbox/shaft stiffness; actual bearing/shaft contact not represented',
            'Rear bearing reacts radial translation only; no preload or axial bearing load modeled',
            'Plate uses3.5x14.8mm section, conservatively ignoring5.5mm local lands; bridge uses two2mm rails',
            '2x notch factor is a sensitivity screen, not a measured stress concentration or fatigue proof',
            'Machined attachment holes, thin bearing shoulder, idler steel spider and long standoff screws require local/contact validation',
            '200MPa is an assumed6061-T6 material floor; it is not a safety-factor-adjusted allowable or a material certificate'])
    (R/'evidence/manufacturing_fork_frame_screen.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['case_count','screen_below_200mpa_with_2x_notch','worst_case']},indent=2))


if __name__=='__main__':main()
