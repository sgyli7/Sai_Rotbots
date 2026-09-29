"""Limited preflight of the hinged beak candidate; not a physical acceptance test."""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
from scipy.optimize import brentq


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scene',type=Path)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    scene=json.loads(args.scene.read_text()); parts={p['name']:p for p in scene['parts']}
    def verts(name): return np.asarray(parts[name]['vertices'])*1000
    shells=[]
    for name,p in parts.items():
        if p.get('role') not in ('hollow_shell_candidate','removable_cover_candidate'): continue
        v=verts(name); n=len(v)//2
        offsets=np.linalg.norm(v[:n]-v[n:],axis=1)
        extent=np.ptp(v,axis=0)
        shells.append(dict(part=name,bounding_box_mm=extent.tolist(),fits_256_cube=bool(np.max(extent)<256),paired_surface_offset_mm=[float(offsets.min()),float(offsets.max())]))
    pivot=np.array([160.,0.,576.]); tip=np.array([261.,0.,551.4])-pivot
    angle=brentq(lambda q: tip[0]*np.sin(q)+tip[2]*(1-np.cos(q))-30,0,np.pi/3)
    # Normal forces at a contact perpendicular to the lever; efficiencies are assumptions.
    force_rows=[dict(efficiency=eta,lever_mm=r,screened_output_torque_nm=2.12*3*eta,normal_force_n=2.12*3*eta/(r/1000)) for eta in (.60,.75,.85) for r in (60,80,95,103)]
    gaps=[dict(closed_contact_x_mm=x,lower_contact_vertical_drop_mm=(x-160)*np.sin(angle)+(553-576)*(1-np.cos(angle))) for x in (179,208,238,244)]
    # A sufficient separating-plane test for these two shells, sampled across the hinge arc.
    shell_sweep=[]
    lower=verts('hinged_lower_bill')-pivot
    upper_min=float(verts('fixed_upper_bill')[:,2].min())
    for q in np.linspace(0,angle,19):
        zz=-np.sin(q)*lower[:,0]+np.cos(q)*lower[:,2]+pivot[2]
        shell_sweep.append(dict(angle_deg=float(np.degrees(q)),vertical_separating_gap_mm=upper_min-float(zz.max())))
    # Analytic candidate camera box vs servo case axes: only this layout and these proxies.
    camera_board=verts('camera_board_proxy'); motor=verts('beak_drive_case'); shaft=verts('beak_supported_output_shaft')
    reserve=dict(camera_board_to_beak_motor_x_gap_mm=float(camera_board[:,0].min()-motor[:,0].max()),camera_board_to_output_shaft_z_gap_mm=float(camera_board[:,2].min()-shaft[:,2].max()),camera_board_to_pinion_gear_y_gap_mm=float(verts('beak_pinion_envelope')[:,1].min()-camera_board[:,1].max()))
    report=dict(status='PRELIMINARY ANALYTIC SCREEN ONLY',appearance_pass=False,physics_pass=False,manufacturing_pass=False,
        scene_sha256=hashlib.sha256(args.scene.read_bytes()).hexdigest(),
        design_target=dict(force_n=50,contact_definition='Normal compressive force at a defined grip-pad station; not pull-out force or arbitrary beak-tip force',proposed_station_x_mm=240,closed_lever_mm=80,adjustable_force_required=True),
        bird_reference=dict(force_n=50.32,species='Anser anser',source='https://bicyt.conicet.gov.ar/fichas/produccion/5443291',primary_abstract_pdf='https://revistas.unlp.edu.ar/Morfol/article/download/915/869/3338',limitation='2010 conference abstract; bite station, sample size and duration not provided in retrieved abstract; not a universal biological specification'),
        motor_basis=dict(model='XM540-W270-T',nominal_mass_g=165,former_motor_mass_g=23,motor_only_mass_increase_g=142,source='https://robotis.us/products/dynamixel-xm540-w270-t',screen_torque_nm=2.12,basis='Manufacturer estimated continuous torque = 20% of 10.6 Nm stall; no measured thermal-duty rating established here',nominal_case_whd_mm=[33.5,58.5,44],dimension_note='e-manual depth is 44 mm; shop metadata lists 45 mm. Detailed fit must resolve drawing/horn/cable envelopes; current screen uses e-manual body.'),
        transmission=dict(ratio=3,centers_mm=24,pitch_radii_mm=[6,18],envelopes_not_released_gears=True,possible_tooth_combination='20/60 teeth at module 0.6 fits the pitch envelopes; tooth form, SKU and strength unvalidated',estimated_tangential_load_at_4_77_nm_n=4.77/.018,motor_catalog_radial_load_n=40,requires_independently_supported_pinion_and_output=True,notes='A single bearing reservation is not a released bearing pair or frame. Do not put the gear mesh load directly on the servo output bearing.'),
        force_sensitivity=force_rows,
        jaw_kinematics=dict(hinge_world_mm=pivot.tolist(),opening_degrees=float(np.degrees(angle)),tip_drop_mm=30,pad_station_drops=gaps,limitation='Rigid rotation only; excludes object contact, elastic pad compression, full swept collision and pulling grip.'),
        beak_shell_sweep=dict(scope='19 sampled poses; sufficient global Z separating plane for upper/lower orange shell solids only. Excludes heels, head, pads, gears and other parts.',passed=all(p['vertical_separating_gap_mm']>0 for p in shell_sweep),poses=shell_sweep),
        camera_nominal_axis_gaps=reserve,
        shell_print_envelope=dict(scope='Bounding boxes and paired surface offsets, not minimum wall thickness, print supports, fastening or assembly',passed=all(p['fits_256_cube'] for p in shells),parts=shells),
        remaining=['Head and beak load path, shell cavities, fasteners and bearing pair design','Force sensor/current calibration, thermal duty and compliant pads','Updated head mass and inertia, neck torque, seated ground reach, balance and dynamic simulation','Object retention, fabric-edge grip and drag tests; grip force is not traction capacity','Camera field of view and beak occlusion','Full mesh self-intersections, assembly clearances and complete motion sweep'])
    args.report.parent.mkdir(parents=True,exist_ok=True); args.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(opening_degrees=report['jaw_kinematics']['opening_degrees'],camera_gaps=reserve,shell_box_fit=report['shell_print_envelope']['passed'],force_at_80mm_n=[r['normal_force_n'] for r in force_rows if r['lever_mm']==80])))

if __name__=='__main__': main()
