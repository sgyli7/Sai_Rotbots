"""Engineering parameter figure from the SI contract; no image generation."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
def main():
 c=json.loads((R/'configs/stage_one_contract.json').read_text());s=json.loads((R/'configs/stage_one_structure.json').read_text());g=json.loads((R/'evidence/stage_one_system_gate.json').read_text());p={j['name']:np.array(j['pivot_world_at_zero_m'])*1000 for j in c['joints']};p['torso']=np.array(c['root_origin_at_zero_m'])*1000
 com=sum(b['mass_kg']*(p[b['name']]+np.array(b['com_local_m'])*1000) for b in c['bodies'])/c['nominal_robot_mass_kg']
 fig=plt.figure(figsize=(12,7),layout='constrained');grid=fig.add_gridspec(2,2,width_ratios=[1,1.25]);ax=fig.add_subplot(grid[:,0]);ax.set_title('Neutral joint axes / estimated COM')
 for j in c['joints']:
  a,b=p[j['parent']],p[j['name']]
  if j['name'].startswith('right'):continue
  ax.plot([a[0],b[0]],[a[2],b[2]],'-o',color='#df6920',lw=2,ms=5)
 for name in ['neck_pitch','neck_mid_pitch','head_pitch','left_hip_pitch','left_knee_pitch','left_ankle_pitch','left_ankle_roll']:
  a=p[name];ax.annotate(name.replace('left_',''),(a[0],a[2]),xytext=(7,5),textcoords='offset points',fontsize=8)
 lo,hi=np.array(s['torso_visual_aabb_m'])*1000;ax.add_patch(plt.Rectangle((lo[0],lo[2]),hi[0]-lo[0],hi[2]-lo[2],fill=False,linestyle='--',edgecolor='#909090'));ax.plot(com[0],com[2],'x',color='#174e75',ms=12,mew=3,label=f'COM estimate: {com[0]:.1f}, {com[2]:.1f} mm');ax.axhline(0,color='#333333');ax.set(xlabel='X forward (mm)',ylabel='Z up (mm)',xlim=(-180,280),ylim=(-10,665));ax.set_aspect('equal');ax.legend(fontsize=8,loc='upper left');ax.grid(alpha=.2)
 ax=fig.add_subplot(grid[0,1]);ax.set_title('Actual sole support polygons - neutral stance')
 for side,f in s['feet'].items():xy=np.array(f['support_polygon_world_xy_m'])*1000;ax.add_patch(Polygon(xy,facecolor='#d4d8dc',edgecolor='#df6920',lw=2));ax.text(22,-89 if side=='right' else 89,side,ha='center')
 ax.plot(com[0],com[1],'x',color='#174e75',ms=10,mew=2);ax.set(xlabel='X forward (mm)',ylabel='Y left (mm)',xlim=(-100,145),ylim=(-155,155));ax.set_aspect('equal');ax.grid(alpha=.2)
 ax=fig.add_subplot(grid[1,1]);names=['neck_pitch','neck_mid_pitch','head_pitch','beak_hinge','left_hip_roll','left_knee_pitch','left_ankle_pitch'];vals=[g['joint_summary'][n]['worst_static_nm'] for n in names];caps=[g['joint_summary'][n]['continuous_design_limit_nm'] for n in names];x=np.arange(len(names));ax.barh(x,caps,color='#d6dfe5',label='Continuous design limit');ax.barh(x,vals,height=.45,color=['#b74337' if v>b else '#246b89' for v,b in zip(vals,caps)],label='63-case static demand');ax.set_yticks(x,[n.replace('left_','') for n in names],fontsize=8);ax.set_xlabel('Torque (Nm)');ax.legend(fontsize=8);ax.grid(axis='x',alpha=.2);ax.set_title('Sizing screen - no dynamic/thermal acceptance')
 fig.suptitle(f'Goose Stage 1 | 18 axes | nominal mass {c["nominal_robot_mass_kg"]:.3f} kg | engineering candidate',fontsize=14);fig.savefig(R/'images/stage_one_parameters.png',dpi=150);plt.close(fig)
if __name__=='__main__':main()
