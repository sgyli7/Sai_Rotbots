"""Static engineering diagram from R2 bounds; no physical stepping."""
from pathlib import Path
import json,os
os.environ['CUDA_VISIBLE_DEVICES']=''
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle
W=Path(__file__).resolve().parents[2];E=W/'robots/goose_v0_2/evidence/low_profile_stock_cart_01';IMG=W/'robots/goose_v0_2/images/low_profile_stock_cart_01'
p=json.loads((E/'geometry_mass_screen.json').read_text());s=json.loads((E/'support_stability_review_r2.json').read_text())
fig,(ax,bx)=plt.subplots(1,2,figsize=(13,6),gridspec_kw={'width_ratios':[1.8,1]},layout='constrained')
fig.patch.set_facecolor('#f7f8fa')
ax.add_patch(Rectangle((0,-225),650,450,fc='#e7e2d7',ec='#667985',lw=1.5,label='650 x 450 platform'))
ax.add_patch(Rectangle((25,-200),600,400,fill=False,ec='#3c7c9b',ls='--',lw=1.5,label='600 x 400 tote envelope'))
ax.add_patch(Rectangle((80,-165),490,330,fc='#8bb3a4',alpha=.32,ec='#297657',lw=2,label='conservative INNER support rectangle'))
ax.add_patch(Rectangle((225,-75),200,150,fc='#e6b35c',alpha=.7,ec='#ab781e',label='allowed 20 kg cargo COM XY'))
for y in [-190,190]:
 ax.add_patch(Circle((55,y),25,fill=False,ec='#4f6b7a',ls=':',lw=1.4))
 for x in [80,570]:ax.plot(x,y,'o',c='#283c47',ms=8)
ec=p['estimated_empty_COM_mm'];ax.plot(ec[0],ec[1],'+',ms=13,mew=2,c='#51384c',label='estimated empty cart COM')
for c in s['cargo_extreme_static_screen']:ax.plot(c['gross_COM_mm'][0],c['gross_COM_mm'][1],'x',c='#a63d2c',ms=7)
ax.plot([],[],'x',c='#a63d2c',label='gross COM at allowed cargo extremes')
ax.set_xlim(-80,710);ax.set_ylim(-300,300);ax.set_aspect('equal');ax.grid(alpha=.15);ax.set_xlabel('Cart X / mm');ax.set_ylabel('Cart Y / mm');ax.set_title('R2 static support: use x80, not sweep outer edge x30')
ax.legend(loc='lower center',bbox_to_anchor=(.5,-.34),fontsize=8,ncol=2)
rr=[r['c_rr_assumption'] for r in s['force_scenarios']];flat=[r['flat_constant_speed_N'] for r in s['force_scenarios']];startup=[r['flat_start_accel_0p2_N_without_caster_start'] for r in s['force_scenarios']];grade=[r['2pct_grade_plus_accel_0p2_N_without_caster_start'] for r in s['force_scenarios']]
for vals,label,col in [(flat,'flat constant speed','#477f8e'),(startup,'+ acceleration 0.2 m/s2','#d59a39'),(grade,'+ 2% grade','#a95d4c')]:bx.plot(rr,vals,'o-',label=label,color=col)
bx.set_xlabel('Assumed rolling coefficient');bx.set_ylabel('Required pull / N');bx.set_title(f'{p["gross_mass_kg"]:.2f} kg gross force scenarios');bx.set_xticks(rr);bx.grid(alpha=.2);bx.legend(fontsize=8,loc='upper left');bx.text(.5,-.2,'Caster alignment / seams / seals are NOT included.\nStatic estimate, not measured towing ability.',transform=bx.transAxes,ha='center',fontsize=9)
fig.suptitle('20 kg cargo + actual cart mass; four-contact analytical screen only\nThree-wheel and dynamic turning/stop qualification remain open',fontsize=12)
fig.savefig(IMG/'support_stability_r2.png',dpi=160,bbox_inches='tight');plt.close(fig)
