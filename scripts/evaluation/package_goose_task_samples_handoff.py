"""Publish selected, source-bound sample diagnostics and actual geometry plots."""
from pathlib import Path
import argparse
import hashlib
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mujoco
import numpy as np
from scipy.spatial import ConvexHull

from sai_agent.goose.convex_support import compiled_body_vertices
from sai_agent.goose.task_samples import primitives, aggregate_si, rotation

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/Goose_V0.1'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def primitive_points(part):
    if part['type'] == 'box':
        points = np.array([[x,y,z] for x in [-1,1] for y in [-1,1] for z in [-1,1]]) * part['size']
    else:
        radius, half = part['size']
        theta = np.arange(96) * (2*np.pi/96)
        points = np.array([[radius*np.cos(t),radius*np.sin(t),z] for z in [-half,half] for t in theta])
    return points @ rotation(part['quat']).T + part['pos']


def polygon(ax, points, axes, color, alpha=1.):
    projected = np.unique(points[:,axes],axis=0)*1000
    hull = ConvexHull(projected)
    poly = projected[hull.vertices]
    ax.fill(poly[:,0],poly[:,1],color=color,alpha=alpha,edgecolor='#344553',linewidth=.6)


def jaw_sections():
    """Native cooked-hull sections; oblique nearest distance is separate."""
    model=mujoco.MjModel.from_xml_path(str(ROBOT/'models/task_proxy_11_v1/robot.xml'))
    data=mujoco.MjData(model);result=[]
    for angle in [0.,.1,.2,.3,.4,.55]:
        for name,multiplier in [('beak_hinge',1),('beak_input_rotor',1),('beak_coupler_link',-1)]:
            data.qpos[int(model.joint(name).qposadr[0])]=angle*multiplier
        mujoco.mj_forward(model,data)
        for x in [.220,.250]:
            intervals=[]
            for name in ['head_upper_bill_envelope','lower_bill_envelope']:
                g=model.geom(name).id;b=model.geom_bodyid[g]
                points=compiled_body_vertices(model,g)@data.xmat[b].reshape(3,3).T+data.xpos[b]
                lo=-np.inf;hi=np.inf;empty=False
                for a,bv,az,k in ConvexHull(points).equations:
                    rhs=-(a*x+k)
                    if abs(az)<1e-12:
                        if rhs<-1e-10:empty=True
                    elif az>0:hi=min(hi,rhs/az)
                    else:lo=max(lo,rhs/az)
                intervals.append(None if empty or lo>hi else [float(lo),float(hi)])
            result.append({'jaw_rad':angle,'world_zero_section_xy_m':[x,0.],
                'upper_z_interval_m':intervals[0],'lower_z_interval_m':intervals[1],
                'vertical_gap_m':intervals[0][0]-intervals[1][1] if all(intervals) else None})
    return result


def plot_geometry(report, path):
    fig = plt.figure(figsize=(15,10.5),facecolor='#f5f7fa')
    grid = fig.add_gridspec(2,6,height_ratios=[1,1.9],hspace=.5,wspace=.5)
    for index,family in enumerate(['cylinder_weight','handle_weight']):
        ax = fig.add_subplot(grid[0,index*3:(index+1)*3])
        parts = primitives(family,.1); si = aggregate_si(parts)
        for p in parts:
            polygon(ax,primitive_points(p),[1,2],'#ed8a32' if p['role']=='grip' else '#5895b1')
        com = np.array(si['com_body_m'])*1000
        ax.plot(0,0,'+',color='#a92346',ms=12,mew=2,label='Body frame / grip centre')
        ax.plot(com[1],com[2],'o',color='#252932',ms=6,label='100 g COM')
        ax.axhline(si['bounds_body_m'][0][2]*1000,color='#697581',ls='--',lw=1)
        dimensions='Grip D12; bar 88; discs D80 x 16 mm' if index==0 else 'Grip D12; bar 60; weight 40 x 60 x 30 mm'
        ax.set_title(('Cylindrical grip + end weights (3 convex leaves)' if index==0 else 'Open handle + box weight (4 convex leaves)')+'\n100 / 200 / 300 g: identical shape, explicit SI\n'+dimensions,fontsize=10,pad=10)
        ax.set_xlabel('Body Y [mm]'); ax.set_ylabel('Body Z [mm]');ax.set_aspect('equal')
        ax.legend(fontsize=8,loc='lower right');ax.grid(alpha=.15)

    cases = report['selected_pose_ids']
    rows = report['ground_endpoint_screen']['results']
    model = mujoco.MjModel.from_xml_path(str(ROBOT/'models/task_proxy_11_v1/robot.xml'))
    for index,(label,identifier) in enumerate(cases.items()):
        row = rows[identifier]; data = mujoco.MjData(model);data.qpos[:]=row['qpos'];mujoco.mj_forward(model,data)
        ax = fig.add_subplot(grid[1,index*2:(index+1)*2])
        for g in range(model.ngeom):
            if model.geom(g).name=='ground':continue
            b = model.geom_bodyid[g]
            points = compiled_body_vertices(model,g)@data.xmat[b].reshape(3,3).T+data.xpos[b]
            color = '#ce4f6a' if label=='handled_middle_rejection' and model.geom(g).name=='lower_bill_envelope' else '#859ba9'
            polygon(ax,points,[0,2],color,.55)
        origin = np.array(row['object_grip_origin_world_m'])
        for p in primitives(row['family'],.1):
            polygon(ax,primitive_points(p)+origin,[0,2],'#ed8a32' if p['role']=='grip' else '#5895b1')
        point = data.site('grip').xpos+data.xmat[model.body('head_roll').id].reshape(3,3)@np.array(row['grip_offset_body_m'])
        ax.plot(point[0]*1000,point[2]*1000,'+',color='#b72350',ms=10,mew=2)
        ax.axhline(0,color='#273744');ax.grid(alpha=.15);ax.set_aspect('equal')
        ax.set_xlim(-180,430);ax.set_ylim(-10,510);ax.set_xlabel('World X [mm]');ax.set_ylabel('World Z [mm]')
        titles={'cylindrical_middle':'Cylinder: middle pad', 'handled_middle_rejection':'Handle: middle pad REJECTED','handled_distal':'Handle: distal pad (+30 mm)'}
        ax.set_title(titles[label],fontsize=11)
        if row['actual_sample_robot_clear']:
            detail=f"Finite jaw closure reaches bar\n300 g ideal static utilization: {row['load_static']['0.3']['minimum_continuous_utilization']:.3f}"
        else:
            depth=-min(x['signed_distance_m'] for x in row['sample_robot_penetrations'])*1000
            detail=f'Weight / jaw overlap: {depth:.2f} mm\nRobot-only FK misses this obstruction'
        ax.text(.02,.98,detail,transform=ax.transAxes,va='top',fontsize=9)
    fig.suptitle('GOOSE 004 | NAMED VIRTUAL TASK SAMPLES v1',fontsize=20,fontweight='bold',y=.985)
    fig.text(.5,.022,'Actual declared primitives and compiled robot convex hulls. Finite geometry / ideal static screens only.\nNo learned pickup, continuous path, calibrated material, contact-quality or hardware qualification.',ha='center',fontsize=10,color='#45515d')
    fig.savefig(path,dpi=130,bbox_inches='tight');plt.close(fig)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True);args=parser.parse_args()
    catalog_path=ROBOT/'models/task_samples_v1/object_catalog.json'
    catalog=json.loads(catalog_path.read_text())
    contact=json.loads((args.run/'contact_closed_envelope/summary.json').read_text())
    ground=json.loads((args.run/'native_contacts/summary.json').read_text())
    raw=json.loads((args.run/'ground_static.json').read_text())
    sources=[catalog_path,ROBOT/'models/task_proxy_11_v1/robot.xml',ROBOT/'configs/task_proxy_11_v1_contract.json',
        ROOT/'src/sai_agent/goose/task_samples.py',ROOT/'scripts/evaluation/check_goose_sample_contact.py',
        ROOT/'scripts/evaluation/check_goose_sample_ground_static.py',ROOT/'scripts/evaluation/check_goose_sample_pose_contacts.py',
        Path(__file__),ROOT/'tests/test_goose_task_samples.py']
    selected={}
    for label,family,offset,clear in [('cylindrical_middle','cylinder_weight',0.,True),
            ('handled_middle_rejection','handle_weight',0.,False),('handled_distal','handle_weight',.03,True)]:
        choices=[(i,r) for i,r in enumerate(ground['results']) if r['family']==family and r['grip_offset_body_m'][0]==offset and r['actual_sample_robot_clear']==clear]
        selected[label]=min(choices,key=lambda pair:pair[1]['load_static']['0.3']['minimum_continuous_utilization'])[0]
    clear=[r for r in ground['results'] if r['actual_sample_robot_clear']]
    report={'schema':'goose_task_samples_v1_handoff','robot_candidate':'goose_task_proxy_11_v1_004',
        'robot_modified':False,'source_bindings':{str(p.relative_to(ROOT)):digest(p) for p in sources},
        'native_mujoco_version':mujoco.__version__,'formal_objects':[x['object_id'] for x in catalog['objects'] if not x['development_only']],
        'native_zero_pose_jaw_sections':jaw_sections(),
        'finite_search':{'cases':len(raw),'robot_floor_self_clear':len(ground['results']),
            'sample_robot_clear':len(clear),'closure_reaches_bar_before_other_collision':sum(x['finite_closure_reaches_bar_before_other_collision'] for x in clear),
            'all_clear_cases_three_masses_continuous_static_ok':all(s['continuous_ok'] for r in clear for s in r['load_static'].values()),
            'static_screen':'Ideal rigid flat-ground eight-point equilibrium; payload gravity wrench at nominal COM transmitted to head. No clamping pressure/compliance or PD guarantee.',
            'grip_site_offsets_body_m':[[0,0,0],[.03,0,0]],'existing_robot_site_or_contract_changed':False,
            'search_crouch_drops_m':[0,.04,.07,.09],'search_object_x_m':[.22,.26,.30,.34],
            'search_head_pitch_rad':[0,.35,.7,1.05,1.4],
            'rejected_pose_examples':[min((r for r in raw if r['family']==f and not r['geometry_possible']),key=lambda r:r['ik_max_residual']) for f in ['cylinder_weight','handle_weight']],
            'raw_pose_record_sha256':digest(args.run/'ground_static.json')},
        'ground_endpoint_screen':ground,'selected_pose_ids':selected,'isolated_contact_bench':contact,
        'full_pickup_qualification':False,'contact_quality_qualification':False,'PPO_updates':0,
        'physical_material_qualification':False,'robot_source_or_GPU_qualification_added':False}
    out=ROBOT/'evidence/task_samples_v1_handoff.json';out.write_text(json.dumps(report,indent=2)+'\n')
    image=ROBOT/'images/task_samples_v1_geometry.png';plot_geometry(report,image)
    print(json.dumps({'evidence':str(out.relative_to(ROOT)),'image':str(image.relative_to(ROOT)),
        'finite_search':{k:v for k,v in report['finite_search'].items() if k in ('cases','robot_floor_self_clear','sample_robot_clear','closure_reaches_bar_before_other_collision')}}))


if __name__=='__main__':main()
