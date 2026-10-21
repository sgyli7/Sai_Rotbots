"""Frozen finite025 actual-contact wrench screen, no physics/model mutation.

Contacts use oldnative mm and force/couple ON mouth in that body's axes.
The shaft item is explicitly a quasi-static full-input-cap C-force envelope,
not a measured internal constraint force. This module never commands motion.
"""
import math


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def add(a, b):
    return [x+y for x, y in zip(a, b)]


def ry(v, q):
    c, s = math.cos(q), math.sin(q)
    return [c*v[0]+s*v[2], v[1], -s*v[0]+c*v[2]]


def wrench(points, ref):
    f, m = [0., 0., 0.], [0., 0., 0.]
    for p in points:
        force = p['native_force_on_mouth_N']
        arm = [(x-y)*.001 for x, y in zip(p['native_point_mm'], ref)]
        couple = p.get('native_couple_on_mouth_Nm', [0., 0., 0.])
        f = add(f, force)
        m = add(m, add(cross(arm, force), couple))
    return f, m


def drive_row(q):
    """Exact fixed029 geometry, closing force on C at actual q, 4.4Nm input."""
    ri, ro, length, phi = 7.73, 29.87, 15., 2.4531
    c = [160+ro*math.cos(phi-q), 576+ro*math.sin(phi-q)]
    v = [c[0]-129, c[1]-601]
    d = math.hypot(*v)
    theta = math.atan2(v[1], v[0])-math.acos((ri*ri+d*d-length*length)/(2*ri*d))
    pin = [129+ri*math.cos(theta), 601+ri*math.sin(theta)]
    link = [c[0]-pin[0], c[1]-pin[1]]
    cp = [ro*math.sin(phi-q), -ro*math.cos(phi-q)]
    dp = [-ri*math.sin(theta), ri*math.cos(theta)]
    gain = sum(x*y for x, y in zip(link, cp))/sum(x*y for x, y in zip(link, dp))
    sine = abs((pin[0]-129)*link[1]-(pin[1]-601)*link[0])/(ri*length)
    magnitude = 4400/(ri*sine)
    force = [magnitude*(pin[0]-c[0])/length, 0., magnitude*(pin[1]-c[1])/length]
    return c, force, 4.4*gain


def screen_contacts(points, qjaw_rad, table):
    """Return utilization and reasons; input is real contact data, never COM.

    Only force-bearing contacts OUTBOARD of each cut load that beam cut.
    The true contained6x2/6x3mm metal strips supply conservative weak-axis
    and torsion bounds. Strong-axis Z and A come from actual final native.
    Conditional 2x load/Kt3 applies to beams; 2x/Kt1.5 to shaft.
    """
    reasons, beams = [], []
    for mouth in ['upper_bill_envelope', 'lower_bill_envelope']:
        net_y = sum(p['native_force_on_mouth_N'][1] for p in points if p['mouth'] == mouth)
        if abs(net_y) > 2.:
            reasons.append(mouth+'_net_Fy_finitefixture_domain_exited')
    for sec in table['sections']:
        side, x, cz = sec['side'], sec['x_mm'], sec['cz_mm']
        name = 'upper_bill_envelope' if side == 'upper' else 'lower_bill_envelope'
        loaded = [p for p in points if p['mouth'] == name and p['native_point_mm'][0] >= x]
        f, m = wrench(loaded, [x, 0., cz])
        w, t = sec['contained_width_mm'], sec['contained_thickness_mm']
        area, zy = sec['area_mm2'], sec['Z_mm3']
        zz = t*w*w/6
        sigma = abs(m[1])*1000/zy+abs(f[0])/area+abs(m[2])*1000/zz
        tau = 1.5*math.hypot(f[1], f[2])/area+4.8*abs(m[0])*1000/(w*t*t)
        vm = 6*math.sqrt(sigma*sigma+3*tau*tau)
        ratio = vm/sec['conditional_yield_MPa']
        beams.append(dict(side=side, x_mm=x, force_native_N=f, moment_section_native_Nm=m,
                          sigma_nom_MPa=sigma, shear_bound_nom_MPa=tau,
                          VM_2load_Kt3_MPa=vm, conditional_yield_MPa=sec['conditional_yield_MPa'],
                          utilization=ratio, outboard_contact_count=len(loaded)))
        if ratio > 1:
            reasons.append(side+'_actual_wrench_section_strength_domain_exited')

    lower = [p for p in points if p['mouth'] == 'lower_bill_envelope']
    headloads = []
    for p in lower:
        loc = [(v-o)*.001 for v, o in zip(p['native_point_mm'], [160., 0., 576.])]
        headloads.append(dict(pos=ry(loc, qjaw_rad), force=ry(p['native_force_on_mouth_N'], qjaw_rad),
                              couple=ry(p.get('native_couple_on_mouth_Nm', [0., 0., 0.]), qjaw_rad)))
    shaft_cases = []
    if not 0. <= qjaw_rad <= .55:
        reasons.append('qjaw_outside_native_strength_ROM')
    else:
        cp, cf, torque = drive_row(qjaw_rad)
        # Both endpoints cover any nonnegative quasistatic closing C-force
        # between zero and the full-input-cap envelope, including its actual
        # external mouth wrench. No unlogged force is called measured.
        for scale in [0., 1.]:
            loads = headloads+[dict(pos=[(cp[0]-160)*.001, .035, (cp[1]-576)*.001],
                                    force=[scale*v for v in cf], couple=[0., 0., 0.])]
            force = [0., 0., 0.]
            moment_rear = [0., 0., 0.]
            for load in loads:
                force = add(force, load['force'])
                arm = [load['pos'][0], load['pos'][1]+.0275, load['pos'][2]]
                moment_rear = add(moment_rear, add(cross(arm, load['force']), load['couple']))
            front = [moment_rear[2]/.0481, 0., -moment_rear[0]/.0481]
            rear = [-force[0]-front[0], 0., -force[2]-front[2]]
            bearing = 2*max(math.hypot(front[0], front[2]), math.hypot(rear[0], rear[2]))
            cutloads = loads+[dict(pos=[0., -.0275, 0.], force=rear, couple=[0., 0., 0.]),
                                dict(pos=[0., .0206, 0.], force=front, couple=[0., 0., 0.])]
            maximum = 0.
            external_torque = 0.
            for load in headloads:
                external_torque += cross(load['pos'], load['force'])[1]+load['couple'][1]
            for y in sorted(set([-.0275, .0206, .035]+[p['pos'][1] for p in headloads])):
                moment = [0., 0., 0.]
                for load in cutloads:
                    if load['pos'][1] < y:
                        arm = [load['pos'][0], load['pos'][1]-y, load['pos'][2]]
                        moment = add(moment, add(cross(arm, load['force']), load['couple']))
                bending = 1000*math.hypot(moment[0], moment[2])
                shaft_torque = max(torque, abs(external_torque))*1000 if -.012 <= y <= .035 else 0.
                sigma = 4*bending/(math.pi*5**3)
                tau = 2*shaft_torque/(math.pi*5**3)
                maximum = max(maximum, 3*math.sqrt(sigma*sigma+3*tau*tau))
            shaft_cases.append(dict(C_static_envelope_fraction=scale,
                                    front_radial_N=math.hypot(front[0], front[2]),
                                    rear_radial_N=math.hypot(rear[0], rear[2]),
                                    needle_2load_radial_N=bearing, shaft_VM_2load_Kt1p5_MPa=maximum,
                                    output_cap_reference_Nm=torque,
                                    actual_mouth_torque_about_O_Nm=external_torque))
        if max(p['shaft_VM_2load_Kt1p5_MPa'] for p in shaft_cases) > 900.:
            reasons.append('shaft_actual_mouth_plus_cap_reference_domain_exited')
        if max(p['needle_2load_radial_N'] for p in shaft_cases) > 8150.:
            reasons.append('needle_actual_mouth_plus_cap_reference_domain_exited')
        if 3*torque*1000/(7*11) > 1170.:
            reasons.append('DD7mm_twoflat_pressure_domain_exited')
    return dict(status='WITHIN_CONDITIONAL_SCREEN' if not reasons else 'OUT_OF_CONDITIONAL_SCREEN',
                reasons=sorted(set(reasons)), beam_sections=beams, shaft_cases=shaft_cases,
                pressure_centroid_Y_is_diagnostic_only=True,
                shaft_mode='quasistatic_closing_fullcap_C_envelope_NOT_measured_C_reaction',
                manufacturing_or_dynamic_qualification=False)
