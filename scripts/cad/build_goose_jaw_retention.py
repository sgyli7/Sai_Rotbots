"""Independent jaw axial-retention kit, with separate inner/outer race paths.

The 698 installation envelope is not a detailed bearing race drawing. This kit
adds real shaft grooves, spacer stacks, outer-race caps and six threaded cap
attachments; tolerances, bearing abutments and load qualification stay explicit.
"""
from pathlib import Path
import json
import sys

import numpy as np
from build123d import Solid, Wire, import_step

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "robots/Goose_V0.1"
sys.path.insert(0, str(ROOT / "scripts/cad"))
from build_goose_cad import box, cylinder, holes
from goose_candidate_export import CandidateExport
from build_goose_beak_linkage import bar
from sai_agent.native_cad import common_solid_volume_mm3

J = np.array([160., 0., 576.])
CAP_BOLTS = [(14.5, 0.), (14.5, 90.), (17., 300.)]


def polar(radius, angle, y):
    t = np.deg2rad(angle)
    return [160 + radius*np.cos(t), y, 576 + radius*np.sin(t)]


def wedge(angle_a, angle_b, radius, lo, hi):
    points = [(160., lo, 576.)] + [polar(radius, a, lo) for a in np.linspace(angle_a, angle_b, 45)]
    second = [(x, hi, z) for x, _, z in points]
    return Solid.make_loft([Wire.make_polygon(points, close=True),
                            Wire.make_polygon(second, close=True)], ruled=True)


def cap(y, front):
    inner = 8.8 if front else 5.6
    shape = cylinder(12., 2., [160, y, 576], 'y') - cylinder(inner, 5., [160, y, 576], 'y')
    for radius, angle in CAP_BOLTS:
        shape += bar(polar(11., angle, y), polar(radius, angle, y), 4.5, 2., y)
        shape += cylinder(3.5, 2., polar(radius, angle, y), 'y')
    if front:
        # 12mm crank, 6mm half-width and 0.5mm allowance: the largest angular
        # silhouette near radius8.8mm stays in160..288deg for q=0..0.55rad.
        shape -= wedge(160, 288, 22., y-2, y+2)
    return holes(shape, [polar(rad, a, y) for rad, a in CAP_BOLTS], 3.2, 5, 'y')


def ring(y):
    # Own nominal installed shape, not redistributed or reverse-labelled OEM
    # CAD. Catalogue dimensions constrain the groove, thickness, eyes and mass;
    # maximum7.2mm radial envelope is retained for the independent sweep.
    shape = cylinder(5.3, .85, [160, y, 576], 'y') - cylinder(3.8, 2, [160, y, 576], 'y')
    shape -= wedge(65, 115, 9., y-1, y+1)
    for a in [60., 120.]:
        p = polar(5.6, a, y)
        shape += cylinder(1.5, .85, p, 'y')
        shape -= cylinder(.6, 2, p, 'y')
    return shape


def main():
    paths = [R / 'cad/exports' / folder / 'manifest.json' for folder in
             ['bill_backbones', 'head_load_path', 'beak_native_linkage']]
    manifests = [json.loads(p.read_text()) for p in paths]
    shapes = {p['name']: import_step(R/p['files']['step']['path']).solids()[0]
              for manifest in manifests for p in manifest['parts']}
    export = CandidateExport(R, 'jaw_retention')
    frame = shapes['head_frame_with_bill_mounts']
    caps = {'front': cap(27.5, True), 'rear': cap(-30.5, False)}
    threaded = []
    for side, seat in [('front', 23.5), ('rear', -26.5)]:
        for radius, angle in CAP_BOLTS:
            frame += cylinder(3.5, 8., polar(radius, angle, seat), 'y')
        # A physical recess, not suppression of a cap/frame intersection.
        frame -= caps[side]
        face_trim_y = 27.0 if side == 'front' else -30.0
        for radius, angle in CAP_BOLTS:
            # Cutting only the cap shape leaves a tap-boss plug within the
            # cap's clearance hole. Recess the complete boss face by1mm.
            frame -= cylinder(3.5, 1., polar(radius, angle, face_trim_y), 'y')
        frame = holes(frame, [polar(rad, a, seat) for rad, a in CAP_BOLTS], 2.5, 10, 'y')
    # The rear outer spacer passes through the frame's axial lip, independently
    # of the9.5mm bearing-envelope seat. Do not fill that passage with a cap.
    frame -= cylinder(5.7, 4., [160, -31.5, 576], 'y')
    export.emit('head_frame_with_jaw_retention', frame, 'head_roll', notes=[
        'Replacement fixed frame with three M3 cap bosses per bearing and explicit cap installation recesses.',
        'M3 tap-drill2.5; nominal major-thread overlap is reported separately from unrelated interference.',
        'Bearing seat abutments, lug/root stress and tapping specification remain release gates.',
    ])
    for side in ['front', 'rear']:
        export.emit('jaw_'+side+'_outer_race_cap', caps[side], 'head_roll', notes=[
            '2mm machined cap; outer-race retention separate from moving shaft spacer stack.',
            'Front cap has explicit crank clearance sector; detailed698 race/chamfer abutment still requires supplier drawing.',
        ])
    shaft = cylinder(4, 76, J, 'y')
    for lo, hi in [(-20., 19.), (27.75, 32.25)]:
        shaft -= box([6, hi-lo, 12], [154, .5*(lo+hi), 576])
    grooves = [('rear', -32.9, -32.0)]
    for side, lo, hi in grooves:
        cutter = cylinder(6, hi-lo, [160, .5*(lo+hi), 576], 'y') - cylinder(3.8, hi-lo+2, [160, .5*(lo+hi), 576], 'y')
        shaft -= cutter
    shaft -= cylinder(1.65, 11., [160, 32.5, 576], 'y')
    export.emit('beak_retained_d_shaft', shaft, 'beak_hinge', rho=7850., material='titanium', notes=[
        'Round8mm journals; central and output-arm D-flats only. Ring lands are round, outside the torque-carrying D-flat.',
        'One rear diameter7.6mm x0.9mm groove for DIN4718x0.8,5.1mm end margin. FrontM4tap-drill3.3mm x11mm deep.',
        '76mm length retained. Groove tolerances/fillets, D-flat/tapped wall strength and shaft material certificate remain mandatory.',
    ])
    # The rear ring is behind the rear cap, with full rotational clearance.
    # Front uses a face-fastened washer: a freely rotating circlip's lugs would
    # enter the coupler's envelope here, so orientation cannot establish fit.
    for side, y in [('rear', -32.475)]:
        export.emit('jaw_'+side+'_din471_ring', ring(y), 'beak_hinge', rho=1, material='titanium', catalog_mass=.0002, notes=[
            'RotorClipDSH-8/DIN4718x0.8 family, catalogue0.2g; own nominal installed geometry and conservative radial envelope, not OEM CAD.',
            'Model uses0.85mm thickness allowance; actual finish, supplied outline and installation-tool envelope require confirmation.',
        ])
    spacer_ranges = {
        'rear_outer': (-32., -29.5), 'rear_inner': (-23.5, -16.5),
        'front_inner': (16.5, 20.5), 'front_bearing_to_arm': (26.5, 27.75),
        'front_arm_to_stop': (32.25, 37.9),
    }
    for name, (lo, hi) in spacer_ranges.items():
        shape = cylinder(5.5, hi-lo, [160, .5*(lo+hi), 576], 'y') - cylinder(4.05, hi-lo+2, [160, .5*(lo+hi), 576], 'y')
        export.emit('jaw_'+name+'_spacer', shape, 'beak_hinge', rho=7850., material='titanium', notes=[
            'Own ground11OD/8.1ID spacer; no axial interference with nominal shaft or bearing envelopes.',
            'Nominal length'+str(hi-lo)+'mm. Detailed698 inner-race abutment and selected endfloat/shims still require release.',
        ])
    for side, direction, face in [('front', -1., 29.), ('rear', 1., -32.)]:
        for k, (rad, angle) in enumerate(CAP_BOLTS):
            center = polar(rad, angle, face)
            wash_center = np.array(center) + [0, direction*.25, 0]
            washer = cylinder(3.5, .5, wash_center, 'y') - cylinder(1.6, 2, wash_center, 'y')
            stem = cylinder(1.5, 8., np.array(center)+[0, direction*4, 0], 'y')
            head = cylinder(2.85, 1.65, np.array(center)-[0, direction*.825, 0], 'y')
            screw_name = 'jaw_'+side+'_cap_screw_'+str(k)
            export.emit('jaw_'+side+'_cap_washer_'+str(k), washer, 'head_roll', rho=7850., material='titanium', notes=['M3washer7OD/3.2ID/0.5mm nominal envelope; supplierSKU and preload pending.'])
            export.emit(screw_name, stem+head, 'head_roll', rho=7850., material='titanium', notes=['ISO7380-1M3x8 button-head envelope,5.5mm nominal threaded engagement; socket/thread helices omitted.'])
            volume = common_solid_volume_mm3(stem+head, frame)
            expected = np.pi/4*(3.0**2-2.5**2)*5.5
            threaded.append(dict(screw=screw_name, frame='head_frame_with_jaw_retention',
                                 nominal_thread_engagement_mm=5.5, measured_thread_overlap_mm3=volume,
                                 expected_thread_overlap_mm3=float(expected),
                                 nominal_thread_contact_pass=abs(volume-expected)<.02,
                                 preload_and_pullout_release=False))
    front_washer = cylinder(6., 1., [160, 38.5, 576], 'y') - cylinder(2.15, 3., [160, 38.5, 576], 'y')
    front_screw = cylinder(2., 10., [160, 34., 576], 'y') + cylinder(3.8, 2.2, [160, 40.1, 576], 'y')
    export.emit('jaw_front_axial_stop_washer', front_washer, 'beak_hinge', rho=7850., material='titanium', notes=[
        'M4large washer12OD/4.3ID/1mm envelope. Clamps against the shaft end atY38; nominal0.1mm gap to the moving spacer stack.',
        'Retains the output arm/inner-race stack without relying on frontcirclip angular orientation. Actual washer/bearing abutments pending.',
    ])
    export.emit('jaw_front_axial_stop_screw', front_screw, 'beak_hinge', rho=7850., material='titanium', notes=[
        'ISO7380-1M4x10 nominal envelope,9mm threaded insertion into11mm blind tap; grade/preload/removable threadlocking pending.',
    ])
    v = common_solid_volume_mm3(front_screw, shaft)
    expected = np.pi/4*(4.0**2-3.3**2)*9.
    threaded.append(dict(screw='jaw_front_axial_stop_screw', frame='beak_retained_d_shaft',
                         nominal_thread_engagement_mm=9., measured_thread_overlap_mm3=v,
                         expected_thread_overlap_mm3=float(expected), nominal_thread_contact_pass=abs(v-expected)<.02,
                         preload_and_pullout_release=False))
    # Complete installation geometry includes the shaft/spacers and cap bolt
    # heads. The earlier seven-part kit did not cover those neighbours.
    upper = shapes['upper_bill_metal_backbone']
    for y in [23.5, -26.5]:
        upper -= cylinder(4., 20., polar(17., 300., y), 'y')
    export.emit('upper_bill_retention_backbone', upper, 'head_roll', notes=[
        'Fixed blade and tabs retained; local4mm-radius installation relief around the lower cap boss.',
        'Minimum nominal web to the adjacent3.2mm mounting hole about1.65mm; actual local stress/fatigue and tolerances remain release gates.',
    ])
    upper_shell = shapes['upper_bill_backbone_shell']
    upper_shell -= cylinder(4.3, 80., J, 'y')
    upper_shell -= cylinder(5.8, 49., [160, -1.5, 576], 'y')
    upper_shell -= cylinder(12.4, 3.2, [160, 27.5, 576], 'y')
    for radius, angle in CAP_BOLTS:
        for y in [25.5, -28.5]:
            upper_shell -= cylinder(5.3, 13., polar(radius, angle, y), 'y')
    # A deliberate rear-top service opening removes the now unsupported root
    # lip as a CAD cut. Never silently select only the largest boolean solid.
    upper_shell -= box([18., 48., 8.], [164., 0., 575.])
    export.emit('upper_bill_retention_shell', upper_shell, 'head_roll', rho=1270., material='orange', notes=[
        'Physical shaft/spacer passage, front-cap window and18x48x8mm rear-top service opening; distal outside contour retained.',
        'Local10.6mm-diameter bolt/washer and cap-lug access channels; normal wall thickness and printed local closure not released.',
    ])
    rear_skin = shapes['head_bill_access_shell_right']
    for radius, angle in CAP_BOLTS:
        rear_skin -= cylinder(3.8, 7., polar(radius, angle, -32.5), 'y')
    export.emit('head_retention_access_shell_right', rear_skin, 'head_roll', rho=1270., material='ivory', notes=[
        'Three local7.6mm-diameter rear-cap screw/tool installation ports, not a deleted head shell.',
        'Actual driver tool path, plug covers and shell fasteners remain release gates.',
    ])
    source_url = 'https://www.rotorclip.com/product/dsh-8/'
    value = export.save(ROOT, paths+[Path(__file__), ROOT/'scripts/cad/goose_candidate_export.py'],
        replaces=['head_frame_with_bill_mounts', 'beak_native_d_shaft', 'upper_bill_metal_backbone',
                  'upper_bill_backbone_shell', 'head_bill_access_shell_right'], extra=dict(
            status='JAW_AXIAL_RETENTION_CANDIDATE_NOT_INSTALLED', installed=False,
            source_urls=[source_url], clip_catalog=dict(shaft_diameter_mm=8., groove_diameter_range_mm=[7.54, 7.6],
                groove_width_mm=.9, ring_thickness_range_mm=[.75,.8], minimum_end_margin_mm=.6,
                mass_each_kg=.0002, catalogue_groove_thrust_kn=.8, catalogue_ring_thrust_kn=3.,
                stock_CAD_reconstructed=False, catalogue_thrust_not_assembly_rating=True),
            groove_ranges_world_y_mm=grooves, spacer_ranges_world_y_mm=spacer_ranges,
            nominal_stack_endfloat_mm=.15, shim_selection_pending=True,
            nominal_thread_contacts=threaded, full_assembly_pass=False,
            shaft_and_outer_race_load_qualification_pass=False,
        ))
    print('JAW RETENTION', len(value['parts']), value['native_mass_kg'],
          'thread contact', all(t['nominal_thread_contact_pass'] for t in threaded), flush=True)
    for t in threaded:
        if not t['nominal_thread_contact_pass']:
            print('THREAD STACK FAILURE', t, flush=True)
    return 0 if all(t['nominal_thread_contact_pass'] for t in threaded) else 1


if __name__ == '__main__':
    raise SystemExit(main())
