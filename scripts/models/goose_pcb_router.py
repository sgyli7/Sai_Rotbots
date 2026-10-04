"""Bounded grid router for the independent Goose PCB comparison.

This is a geometry aid, not a current/thermal qualification or a replacement
for KiCad DRC. Copper pours carry the three power nets. Any routing failure is
retained as an unrouted net, never accepted by changing the electrical circuit.
"""
import heapq
import math

import numpy as np
from scipy.ndimage import distance_transform_edt
import pcbnew as pcb


def route(board, nets, cfg):
    step=cfg['routing']['grid_mm']; width=cfg['routing']['signal_width_mm']
    clear=cfg['routing']['clearance_mm']; nx,ny=round(80/step)+1,round(50/step)+1
    base=np.zeros((2,nx,ny),dtype=np.int16)
    parts={p['ref']:p for p in cfg['components']}
    by_net={n:[] for n in nets}
    holes=[]
    def cell(p):return (round(pcb.ToMM(p.x)/step),round(pcb.ToMM(p.y)/step))
    def disk(layer,x,y,r,code):
        lim=math.ceil(r/step)
        x0,x1=max(0,x-lim),min(nx,x+lim+1);y0,y1=max(0,y-lim),min(ny,y+lim+1)
        X,Y=np.ogrid[x0-x:x1-x,y0-y:y1-y]
        mask=(X*step)**2+(Y*step)**2 <= (r+step*.6)**2
        view=base[layer,x0:x1,y0:y1];view[mask]=code
    def track(a,b,layer,net,w=width):
        t=pcb.PCB_TRACK(board);t.SetStart(pcb.VECTOR2I(round(a[0]*step*1e6),round(a[1]*step*1e6)))
        t.SetEnd(pcb.VECTOR2I(round(b[0]*step*1e6),round(b[1]*step*1e6)))
        t.SetWidth(pcb.FromMM(w));t.SetLayer(pcb.F_Cu if layer==0 else pcb.B_Cu);t.SetNet(nets[net]);board.Add(t)
        count=max(abs(a[0]-b[0]),abs(a[1]-b[1]),1)
        for x,y in zip(np.linspace(a[0],b[0],count+1).round().astype(int),np.linspace(a[1],b[1],count+1).round().astype(int)):
            disk(layer,x,y,w/2,nets[net].GetNetCode())
    def via(c,net,size=.5,drill=.25):
        if any(pos==c and owner==net for pos,diameter,owner in holes):return
        v=pcb.PCB_VIA(board);v.SetPosition(pcb.VECTOR2I(round(c[0]*step*1e6),round(c[1]*step*1e6)))
        v.SetWidth(pcb.FromMM(size));v.SetDrill(pcb.FromMM(drill));v.SetViaType(pcb.VIATYPE_THROUGH)
        v.SetLayerPair(pcb.F_Cu,pcb.B_Cu);v.SetNet(nets[net]);board.Add(v)
        holes.append((c,drill,net))
        for layer in [0,1]:disk(layer,*c,size/2,nets[net].GetNetCode())
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if not pad.IsOnLayer(pcb.F_Cu):continue
            c=cell(pad.GetPosition());s=pad.GetSize();sx=pcb.ToMM(s.x);sy=pcb.ToMM(s.y)
            code=pad.GetNetCode() or -1
            if pad.GetDrillSize().x:
                holes.append((c,pcb.ToMM(pad.GetDrillSize().x),pad.GetNetname() or None))
            for layer in ([0,1] if pad.GetAttribute()!=pcb.PAD_ATTRIB_SMD else [0]):
                if pad.GetShape()==pcb.PAD_SHAPE_CIRCLE:disk(layer,*c,sx/2,code)
                else:
                    px=pcb.ToMM(pad.GetPosition().x)/step;py=pcb.ToMM(pad.GetPosition().y)/step
                    x0=max(0,math.ceil(px-sx/step/2));x1=min(nx,math.floor(px+sx/step/2)+1)
                    y0=max(0,math.ceil(py-sy/step/2));y1=min(ny,math.floor(py+sy/step/2)+1)
                    base[layer,x0:x1,y0:y1]=code
            if pad.GetNumber() and pad.GetNetname():by_net[pad.GetNetname()].append(c)
    # Ground vias on pad require filled/capped manufacture. Do not silently
    # publish ordinary open through vias as qualified soldering geometry.
    grounds=[]
    for fp in board.GetFootprints():
        if fp.GetReference().startswith('C') and int(fp.GetReference()[1:])<=10:continue
        grounds.extend(cell(p.GetPosition()) for p in fp.Pads()
            if p.GetNetname()=='GND' and p.GetAttribute()==pcb.PAD_ATTRIB_SMD)
    grounds=sorted(set(grounds))
    for c in grounds:via(c,'GND')
    for fp in board.GetFootprints():
        if fp.GetReference().startswith('C') and int(fp.GetReference()[1:])<=10:
            for pad in fp.Pads():
                if pad.GetNetname()=='GND':
                    c=cell(pad.GetPosition())
                    for dx in [-12,0,12]:
                        for dy in [-5,5]:via((c[0]+dx,c[1]+dy),'GND',.6,.3)
    # Sources have one direct ground via per package lead. The installed
    # current, loop inductance and via temperatures still need qualification.
    power={'BUS','GND','SW_RETURN'}
    moves=[(1,0,1.),(-1,0,1.),(0,1,1.),(0,-1,1.),(1,1,1.414),(-1,1,1.414),(1,-1,1.414),(-1,-1,1.414)]
    results=[]
    order=sorted((n for n in by_net if n not in power),key=lambda n:(len(by_net[n]),n))
    for net in order:
        points=sorted(set(by_net[net]));connected=points[:1];remaining=points[1:]
        code=nets[net].GetNetCode()
        while remaining:
            _,a,b=min((math.dist(a,b),a,b) for a in connected for b in remaining)
            obs=(base!=0)&(base!=code)
            dist=np.stack([distance_transform_edt(~obs[k])*step for k in [0,1]])
            allowed=dist>width/2+clear+step*.71
            # Existing same-net pad copper is already a legal connection.
            # Inflating the adjacent 0.65mm-pitch pad must not trap the start
            # inside its own pad. Keep the trace centre inside its pad width.
            own=np.stack([distance_transform_edt(base[k]==code)*step for k in [0,1]])
            allowed |= own>width/2+step*.6
            via_ok=np.all(dist>.25+clear+step*.71,axis=0)
            # Same-net holes still need drill-to-drill clearance. Reuse an
            # existing plated connection instead of creating another beside it.
            hole_mask=np.zeros((nx,ny),dtype=bool)
            for (hx,hy),diameter,owner in holes:
                radius=diameter/2+.125+.25+step*.71
                lim=math.ceil(radius/step)
                x0,x1=max(0,hx-lim),min(nx,hx+lim+1);y0,y1=max(0,hy-lim),min(ny,hy+lim+1)
                X,Y=np.ogrid[x0-hx:x1-hx,y0-hy:y1-hy]
                hole_mask[x0:x1,y0:y1] |= (X*step)**2+(Y*step)**2 <= radius*radius
            via_ok &= ~hole_mask
            for pos,diameter,owner in holes:
                if owner==net:via_ok[pos]=True
            margin=math.ceil((.5+width/2)/step)
            allowed[:,:margin,:]=False;allowed[:,-margin:,:]=False
            allowed[:,:,:margin]=False;allowed[:,:,-margin:]=False
            # Exact pad centres round by <=0.05mm; first/last short segment
            # stays on the pad. DRC independently checks this approximation.
            start=(0,*a);goal=(0,*b)
            allowed[start]=True;allowed[goal]=True
            queue=[(math.dist(a,b),0.,start)];cost={start:0.};parents={};end=None
            expanded=0
            while queue and expanded<600000:
                _,g,c=heapq.heappop(queue)
                if g!=cost.get(c):continue
                if c==goal:end=c;break
                expanded+=1;k,x,y=c
                choices=[((k,x+dx,y+dy),w) for dx,dy,w in moves
                    if 0<=x+dx<nx and 0<=y+dy<ny and allowed[k,x+dx,y+dy]
                    and (not (dx and dy) or (allowed[k,x+dx,y] and allowed[k,x,y+dy]))]
                if via_ok[x,y]:choices.append(((1-k,x,y),30.))
                for nxt,w in choices:
                    ng=g+w
                    if ng>=cost.get(nxt,float('inf')):continue
                    cost[nxt]=ng;parents[nxt]=c
                    h=math.hypot(nxt[1]-b[0],nxt[2]-b[1])+(30 if nxt[0] else 0)
                    heapq.heappush(queue,(ng+h,ng,nxt))
            if end is None:
                results.append({'net':net,'from_grid':a,'to_grid':b,'routed':False,'expanded':expanded})
                connected.append(b);remaining.remove(b);continue
            path=[end]
            while path[-1]!=start:path.append(parents[path[-1]])
            path.reverse();begin=path[0];direction=None;last=begin
            for cur in path[1:]:
                if cur[0]!=last[0]:
                    if begin!=last:track(begin[1:],last[1:],last[0],net)
                    via(cur[1:],net);begin=cur;direction=None
                else:
                    d=(cur[1]-last[1],cur[2]-last[2])
                    if direction is not None and d!=direction:
                        track(begin[1:],last[1:],last[0],net);begin=last
                    direction=d
                last=cur
            if begin!=last:track(begin[1:],last[1:],last[0],net)
            connected.append(b);remaining.remove(b)
            results.append({'net':net,'from_grid':a,'to_grid':b,'routed':True,'expanded':expanded})
    return {'status':'ROUTING_CANDIDATE_NOT_CURRENT_QUALIFICATION',
        'connections_routed':sum(r['routed'] for r in results),
        'connections_unrouted':sum(not r['routed'] for r in results),
        'ground_vias_in_pad_require_filled_capped_process':True,
        'signal_connections':results}
