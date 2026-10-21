"""Offline recorded states only. No integration or native-geometry substitution."""
import os
os.environ['MUJOCO_GL']='egl'
import json,hashlib,subprocess,sys
from pathlib import Path
import numpy as np,mujoco as mj
from PIL import Image,ImageDraw,ImageFont
P=Path(sys.argv[1]);bench=sys.argv[2]=='bench';z=np.load(P/('trajectory_substeps.npz'if bench else'trajectory.npz'));ini=np.load(P/'initial_state.npz');m=mj.MjModel.from_binary_path(str(P/'actual_scene.mjb'));d=mj.MjData(m);m.vis.global_.offwidth=640;m.vis.global_.offheight=640;m.vis.headlight.ambient[:]=.6;m.vis.headlight.diffuse[:]=.8;r=mj.Renderer(m,640,640);hist=[]
if bench:
 for line in open(P/'contacts_substeps.jsonl'):
  x=json.loads(line);hist.append(x['observation'])
f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18);sm=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15);vid=P/'complete_actual_closeout_045.mp4';ff=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','1280x800','-r','200','-i','-','-an','-r','30','-c:v','libx264','-crf','20','-pix_fmt','yuv420p',str(vid)],stdin=subprocess.PIPE);ids=[-1]+list(range(0,len(z['time']),10 if bench else 1))
if ids[-1]!=len(z['time'])-1:ids.append(len(z['time'])-1)
for i in ids:
 d.qpos[:]=ini['qpos']if i<0 else z['qpos'][i];d.qvel[:]=ini['qvel']if i<0 else z['qvel'][i];d.time=0 if i<0 else z['time'][i];mj.mj_forward(m,d);im=Image.new('RGB',(1280,800),'#19252e');dr=ImageDraw.Draw(im)
 cams=[([-.04,0,.86],1.13,115,-3),([-.038,0,.999],.235,115,-8)]if bench else[([.60,0,.30],2.30,125,-12),([.30,0,.35],.52,125,-8)]
 for j,(look,dist,az,el)in enumerate(cams):
  c=mj.MjvCamera();c.lookat[:]=look;c.distance=dist;c.azimuth=az;c.elevation=el;r.update_scene(d,camera=c);im.paste(Image.fromarray(r.render()),(640*j,90))
 title='14 / 20kg FIXED-HEAD | WORKFACE DOMAIN EXIT / NO 5s QUALIFICATION'if bench else'020 / 13 FREE ROBOT + CART20kg | ONLY FIRST .20s TRANSFER, NOT WALKING'
 dr.text((12,7),title,font=f,fill='#ffd17d');dr.text((12,32),f'Complete actual0-{z["time"][-1]:.4f}s at1x | saved states only, no new physics',font=sm,fill='white');dr.text((12,56),'Original external CONTACT PROXIES shown; new internal mechanism NOT displayed | NOT native contact fidelity proof',font=sm,fill='white')
 if bench:
  o=hist[max(i,0)];N=o['grip_normal_N'];tau=0 if i<0 else z['actuator_force'][i,0];hud=f'SIM{d.time:.4f} | input{tau:+.4f}Nm | upper/lower normal{N["upper"]:.1f}/{N["lower"]:.1f}N | table{o["platform_N"]:.1f}N';note='Normals are NOT traction; fixed head is NOT wholeGoose | valid full-load max .133s, then slipped/table recontact'
 else:
  N=[0,0]if i<0 else z['grip_normal'][i];tau=0 if i<0 else z['actuator_force'][i,5];foot=[0,0]if i<0 else z['foot_contact_force'][i];hud=f'SIM{d.time:.4f} | input{tau:+.4f}Nm | grip normals{N[0]:.1f}/{N[1]:.1f}N | footN{foot[0]:.1f}/{foot[1]:.1f}';note='Actual first .20s COM left+.252mm only; no completed support change/step/.5m transport qualification'
 dr.text((12,740),hud,font=f,fill='white');dr.text((12,771),note,font=sm,fill='#ffd17d')
 if i in [ids[len(ids)//2],ids[-1]]:im.save(P/('closeout045_final.png'if i==ids[-1]else'closeout045_middle.png'))
 ff.stdin.write(im.tobytes())
ff.stdin.close();assert ff.wait()==0;r.close();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();out=dict(physics_steps=0,saved_forward_only=True,video=str(vid),video_sha256=sha(vid),frames=len(ids),actual_end_s=float(z['time'][-1]),source_sha256=sha(Path(__file__)),bindings={n:sha(P/n)for n in ['actual_scene.mjb','initial_state.npz','trajectory_substeps.npz'if bench else'trajectory.npz']});(P/'offline_closeout_video_receipt_045.json').write_text(json.dumps(out,indent=2)+'\n');print(out,flush=True)
