"""Render actual task colliders in three views; never substitute visual CAD."""
from pathlib import Path
import mujoco,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from scipy.spatial import ConvexHull
from sai_agent.goose.convex_support import compiled_body_vertices
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
m=mujoco.MjModel.from_xml_path(str(R/'models/task_proxy_11_v1/robot.xml'));d=mujoco.MjData(m);mujoco.mj_forward(m,d)
labels=['Torso','Lower neck','Upper neck','Head + upper bill','Lower bill','Right thigh','Right shin','Right shoe','Left thigh','Left shin','Left shoe']
colors=['#4285B4','#C6538C','#8662BE','#ED9228','#D3533F','#228A81','#72AC51','#C3AC42','#40ACC6','#77B6B4','#6778B8']
shapes=[]
for g in range(1,m.ngeom):
 b=m.geom_bodyid[g];v=compiled_body_vertices(m,g)@d.xmat[b].reshape(3,3).T+d.xpos[b];shapes.append((m.geom(g).name,v,ConvexHull(v).simplices))
fig=plt.figure(figsize=(15,9),facecolor='#f4f6f8')
fig.suptitle('GOOSE V0.1  |  11 TASK COLLIDERS',fontsize=23,fontweight='bold',y=.965)
fig.text(.5,.916,'21 physical bodies • 18 motor axes • complete SI mass / inertia retained',ha='center',fontsize=12,color='#55616a')
for i,(elev,azim,title) in enumerate([(16,-64,'Three-quarter'),(0,-90,'Side'),(0,0,'Front')]):
 ax=fig.add_subplot(1,3,i+1,projection='3d',facecolor='#f4f6f8')
 for k,(_,v,tri) in enumerate(shapes):
  ax.add_collection3d(Poly3DCollection(v[tri],facecolor=colors[k],edgecolor=colors[k],linewidth=.08,alpha=.88))
 ax.set_xlim(-.22,.32);ax.set_ylim(-.27,.27);ax.set_zlim(0,.67);ax.set_box_aspect((.54,.54,.67));ax.view_init(elev=elev,azim=azim);ax.set_proj_type('ortho');ax.set_axis_off();ax.set_title(title,fontsize=14,color='#34424f',y=.9)
fig.legend([Patch(facecolor=c) for c in colors],labels,ncol=6,loc='lower center',bbox_to_anchor=(.5,.13),frameon=False,fontsize=10)
fig.text(.5,.075,'Collision geometry only. Shoe exterior and sole support face share one shape per foot.',ha='center',fontsize=11,color='#46525d')
fig.text(.5,.045,'Finite pose / flat-floor M0 entry verified. Uneven terrain and learned tasks require separate acceptance.',ha='center',fontsize=10,color='#65717b')
fig.subplots_adjust(left=.01,right=.99,top=.87,bottom=.21,wspace=0)
path=R/'images/task_proxy_11_v1_colliders.png';fig.savefig(path,dpi=160,facecolor=fig.get_facecolor());print(path)
