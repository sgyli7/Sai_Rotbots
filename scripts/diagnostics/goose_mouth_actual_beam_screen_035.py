"""Conditional actual-native beam screen; no physics, geometry or allowable change.

Full native section tensor supplies normal stress; a continuously proven real
contained core supplies a conservative rectangle Saint-Venant torsion model.
This remains a beam/notch engineering screen, not local3D/warping certification.
"""
import math
from goose_mouth_actual_wrench_screen_034 import wrench

def screen_beams(points, table):
    rows=[];reasons=[]
    for sec in table['sections']:
        side,x=sec['side'],sec['x_mm'];name=side+'_bill_envelope'
        loaded=[p for p in points if p['mouth']==name and p['native_point_mm'][0]>=x]
        normal=sec['normal_tensor'];cy,cz=normal['centroid_yz_mm']
        f,m=wrench(loaded,[x,cy,cz]);B=normal['B_yz_area_mm4'];aa,ab,bb=B[0][0],B[0][1],B[1][1];det=aa*bb-ab*ab
        if det<=0:raise ValueError('Nonpositive actual native area tensor')
        # sigma(y,z)=a*y+b*z; Mz=-int(y*sigma), My=int(z*sigma).
        a=(-m[2]*1000*bb-ab*m[1]*1000)/det
        b=(aa*m[1]*1000+ab*m[2]*1000)/det
        sigma=abs(f[0])/normal['area_mm2']+abs(a)*normal['max_abs_y_mm']+abs(b)*normal['max_abs_z_mm']
        rect=sec['torsion_rectangle'];ry,rz=rect['center_yz_mm'];_,mr=wrench(loaded,[x,ry,rz])
        direct=1.5*math.hypot(f[1],f[2])/normal['area_mm2']
        torsion=4.8*abs(mr[0])*1000/rect['SV_denominator_long_short2_mm3']
        tau=direct+torsion;vm=6*math.sqrt(sigma*sigma+3*tau*tau);util=vm/sec['conditional_yield_MPa']
        rows.append(dict(side=side,x_mm=x,force_native_N=f,moment_section_native_Nm=m,
                         moment_torsion_rectangle_native_Nm=mr,normal_reference_native_mm=[x,cy,cz],torsion_reference_native_mm=[x,ry,rz],
                         sigma_nom_MPa=sigma,direct_shear_nom_MPa=direct,torsion_bound_nom_MPa=torsion,shear_bound_nom_MPa=tau,
                         VM_2load_Kt3_MPa=vm,conditional_yield_MPa=sec['conditional_yield_MPa'],utilization=util,outboard_contact_count=len(loaded)))
        if util>1:reasons.append(side+'_actual_wrench_section_strength_domain_exited')
    return dict(beam_sections=rows,reasons=sorted(set(reasons)),scope=table['scope'],manufacturing_or_dynamic_qualification=False)
