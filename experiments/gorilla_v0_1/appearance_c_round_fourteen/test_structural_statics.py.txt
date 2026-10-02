import numpy as np
import pytest

from sai_agent.structural_statics import contact_extreme_allocations, hollow_section, nominal_section_stress, normal_contacts, resultant


def test_hollow_rectangle_matches_closed_form():
    w,h,t=.12,.18,.008
    outer=[[-w/2,-h/2],[w/2,-h/2],[w/2,h/2],[-w/2,h/2]]
    inner=[[-w/2+t,-h/2+t],[w/2-t,-h/2+t],[w/2-t,h/2-t],[-w/2+t,h/2-t]]
    s=hollow_section(outer,inner)
    assert s['area_m2']==pytest.approx(w*h-(w-2*t)*(h-2*t))
    assert s['Iuu_m4']==pytest.approx((w*h**3-(w-2*t)*(h-2*t)**3)/12)
    assert s['Ivv_m4']==pytest.approx((h*w**3-(h-2*t)*(w-2*t)**3)/12)
    assert s['Iuv_m4']==pytest.approx(0,abs=1e-12)


def test_force_moment_translation_matches_cantilever():
    loads=[{'position_world_m':[.4,0,0],'force_world_N':[0,0,-1000]}]
    f,m=resultant(loads,[0,0,0])
    assert np.allclose(f,[0,0,-1000])
    assert np.allclose(m,[0,400,0])
    assert np.allclose(resultant(loads,[.2,0,0])[1],[0,200,0])


def test_biaxial_section_stress_uses_correct_levers():
    outer=[[-.1,-.2],[.1,-.2],[.1,.2],[-.1,.2]]
    inner=[[-.09,-.19],[.09,-.19],[.09,.19],[-.09,.19]]
    s=hollow_section(outer,inner)
    r=nominal_section_stress(s,outer,np.eye(3),[1000,0,0],[0,200,300],.01,inner)
    expected=1000/s['area_m2']+200*.2/s['Iuu_m4']+300*.1/s['Ivv_m4']
    assert r['max_abs_normal_stress_Pa']==pytest.approx(expected)


def test_transverse_shear_matches_hollow_rectangle_first_moment():
    w,h,t=.12,.18,.008
    outer=[[-w/2,-h/2],[w/2,-h/2],[w/2,h/2],[-w/2,h/2]]
    inner=[[-w/2+t,-h/2+t],[w/2-t,-h/2+t],[w/2-t,h/2-t],[-w/2+t,h/2-t]]
    section=hollow_section(outer,inner)
    for axis,q,inertia in (
        (1,(h*w*w-(h-2*t)*(w-2*t)**2)/8,section['Ivv_m4']),
        (2,(w*h*h-(w-2*t)*(h-2*t)**2)/8,section['Iuu_m4'])):
        force=np.zeros(3);force[axis]=200000
        result=nominal_section_stress(section,outer,np.eye(3),force,np.zeros(3),t,inner)
        assert result['shear_envelope_Pa']==pytest.approx(200000*q/(inertia*2*t),rel=1e-7)


def test_unilateral_contacts_balance_without_fixed_foot_torque():
    vertices=[[x,y,0] for x in [-.2,.3] for y in [-.6,.6]]
    load=[{'position_world_m':[.1,0,2],'force_world_N':[0,0,-10000]}]
    r=normal_contacts(vertices,load)
    assert r['feasible']
    assert all(c['force_world_N'][2]>=0 for c in r['contacts'])
    f,m=resultant([*load,*r['contacts']],[0,0,0])
    assert np.linalg.norm(f)<1e-7
    assert np.linalg.norm(m)<1e-7
    single_left=[[x,y,0] for x in [-.2,.3] for y in [.4,.8]]
    assert not normal_contacts(single_left,load)['feasible']


def test_all_contact_extremes_obey_equilibrium_and_cover_load_share_range():
    vertices=np.array([[x,y,0] for x in [-.2,.3] for y in [-.8,-.4,.4,.8]])
    loads=[{'position_world_m':[0,0,2],'force_world_N':[0,0,-10000]}]
    extremes=contact_extreme_allocations(vertices,loads)
    assert len(extremes)>1
    assert np.min(extremes)>=0
    assert np.allclose(extremes.sum(1),10000)
    assert np.allclose(extremes@vertices[:,:2],0)
    left=vertices[:,1]>0
    share=extremes[:,left].sum(1)/10000
    assert share.min()==pytest.approx(1/3)
    assert share.max()==pytest.approx(2/3)


def test_raised_foot_cannot_supply_flat_ground_reactions():
    vertices=[[x,y,0 if y>0 else 1] for x in [-.2,.3] for y in [-.6,.6]]
    loads=[{'position_world_m':[0,0,2],'force_world_N':[0,0,-10000]}]
    assert not normal_contacts(vertices,loads)['feasible']
    with pytest.raises(ValueError,match='ground plane'):
        contact_extreme_allocations(vertices,loads)


def test_displaced_inner_void_is_rejected():
    outer=[[-.1,-.2],[.1,-.2],[.1,.2],[-.1,.2]]
    inner=[[.91,-.19],[1.09,-.19],[1.09,.19],[.91,.19]]
    with pytest.raises(ValueError,match='strictly inside'):
        hollow_section(outer,inner)
