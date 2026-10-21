"""Read-only actual virtual-mass experiment replay and plots; no mj_step."""
import os
os.environ['MUJOCO_GL']='egl'
import json,hashlib,subprocess,sys
from pathlib import Path
import numpy as np,mujoco as mj
from PIL import Image,ImageDraw,ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(sys.argv[1]);z=np.load(P/'trajectory_substeps.npz');ini=np.load(P/'initial_state.npz');result=json.load(open(P/'result.json'));ids=[-1]+list(range(0,len(z['time']),10));
if ids[-1]!=len(z['time'])-1:ids.append(len(z['time'])-1)
wanted=set(ids);obs={}
for i,line in enumerate(open(P/'contacts_substeps.jsonl')):
 if i in wanted:obs[i]=json.loads(line)['observation']
t=np.array([z['time'][i]for i in ids if i>=0]);mass=np.array([z['actual_test_total_mass_kg'][i]for i in ids if i>=0]);tau=np.array([z['actuator_force'][i,0]for i in ids if i>=0]);slip=np.array([obs[i]['native_workpiece_center_mm'][0]-231.5 for i in ids if i>=0]);rate=np.array([obs[i]['hold_ledger']['last_up_to1s_outward_rate_mm_s']or 0. for i in ids if i>=0]);table=np.array([obs[i]['platform_N']for i in ids if i>=0]);gap=np.array([obs[i]['platform_ballast_signed_gap_m']*1000 for i in ids if i>=0]);csv=P/'actual_mass_torque_slip_200Hz.csv';np.savetxt(csv,np.c_[t,mass,tau,slip,rate,table,gap],delimiter=',',header='actual_time_s,testobject_total_kg,input_actual_Nm,outward_slide_mm,last1s_outward_rate_mm_s,table_normal_N,actual_gap_mm',comments='')
fig,ax=plt.subplots(4,1,figsize=(11,8),sharex=True);ax[0].plot(t,mass);ax[0].set_ylabel('Virtual load (kg)');ax[1].plot(t,tau,color='darkorange');ax[1].set_ylabel('Input torque (Nm)');ax[2].plot(t,slip,color='crimson');ax[2].set_ylabel('Outward slide (mm)');ax[3].plot(t,table,label='Table N');ax[3].plot(t,gap,label='Signed gap mm');ax[3].legend();ax[3].set_ylabel('Table / clearance');ax[-1].set_xlabel('Actual simulation time (s)')
for a in ax:a.grid(alpha=.3);a.axvline(t[-1],color='black',linestyle='--',alpha=.6)
fig.suptitle('034 candidate15: one grip, continuously increasing virtual test-object mass\nStop: lower conditional strength screen (NOT fracture); 5.210kg peak is NOT a stable lifting limit');fig.tight_layout();fig.savefig(P/'actual_mass_torque_slip_curve_034.png',dpi=150);plt.close(fig)
m=mj.MjModel.from_binary_path(str(P/'modified_initial_scene.mjb'));d=mj.MjData(m);m.vis.global_.offwidth=640;m.vis.global_.offheight=640;m.vis.headlight.ambient[:]=.6;m.vis.headlight.diffuse[:]=.8;r=mj.Renderer(m,640,640);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18);sm=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15);video=P/'continuous_virtual_mass034_complete_actual.mp4';ff=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','1280x820','-r','200','-i','-','-an','-r','30','-c:v','libx264','-threads','2','-crf','20','-pix_fmt','yuv420p',str(video)],stdin=subprocess.PIPE)
for i in ids:
 d.qpos[:]=ini['qpos']if i<0 else z['qpos'][i];d.qvel[:]=ini['qvel']if i<0 else z['qvel'][i];d.time=0 if i<0 else z['time'][i];mj.mj_forward(m,d);im=Image.new('RGB',(1280,820),'#19252e');dr=ImageDraw.Draw(im)
 for j,(look,dist,az,el)in enumerate([([-.04,0,.86],1.13,115,-3),([-.038,0,.999],.235,115,-8)]):
  c=mj.MjvCamera();c.lookat[:]=look;c.distance=dist;c.azimuth=az;c.elevation=el;r.update_scene(d,camera=c);im.paste(Image.fromarray(r.render()),(640*j,90))
 o=obs[max(0,i)];N=o['grip_normal_N'];a=0 if i<0 else z['actuator_force'][i,0];ma=.166659815616 if i<0 else z['actual_test_total_mass_kg'][i];sx=0 if i<0 else o['native_workpiece_center_mm'][0]-231.5;sp=0 if i<0 else(o['hold_ledger']['last_up_to1s_outward_rate_mm_s']or 0.);tn=0 if i<0 else o['platform_N'];gp=0 if i<0 else o['platform_ballast_signed_gap_m']*1000
 dr.text((12,6),'034 CANDIDATE15 SINGLE GRIP / CONTINUOUS VIRTUAL MASS RAMP | STOP: CONDITIONAL STRENGTH SCREEN STOP',font=font,fill='#ffd17d');dr.text((12,32),f'Complete actual0-{t[-1]:.4f}s at1x | test-object m/I changes, fixed envelope; NOT a real steel-block calibration',font=sm,fill='white');dr.text((12,56),'Original external CONTACT PROXIES shown; internal drive NOT displayed | no root/object binding or pose reset',font=sm,fill='white');dr.text((12,740),f'SIM{d.time:.4f}s | actual mass{ma:.4f}kg | input{a:+.4f}Nm | upper/lower normal{N["upper"]:.1f}/{N["lower"]:.1f}N',font=font,fill='white');dr.text((12,768),f'Rod outward slide{sx:.2f}mm / last1s{sp:.2f}mm/s | support table{tn:.3f}N | actual clearance{gp:+.2f}mm',font=font,fill='white');dr.text((12,796),'Peak5.210kg is NOT a stable weight limit; no5s qualification / not wholeGoose suspension or transport',font=sm,fill='#ffd17d')
 if i in [ids[len(ids)//2],ids[-1]]:im.save(P/('virtual_mass034_final.png'if i==ids[-1]else'virtual_mass034_middle.png'))
 ff.stdin.write(im.tobytes())
ff.stdin.close();assert ff.wait()==0;r.close();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();receipt=dict(physics_steps=0,source_sha256=sha(Path(__file__)),video_sha256=sha(video),plot_sha256=sha(P/'actual_mass_torque_slip_curve_034.png'),csv_sha256=sha(csv),saved_samples=len(ids),actual_end_s=float(t[-1]),mass_peak_kg=float(mass.max()),five_second_top_qualification=False,bindings={n:sha(P/n)for n in ['modified_initial_scene.mjb','initial_state.npz','trajectory_substeps.npz','result.json']});(P/'offline_virtual_mass034_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt,flush=True)
