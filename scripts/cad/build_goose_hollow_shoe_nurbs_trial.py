"""Native thin shoe covers with real ankle openings; not structural sole parts."""
from pathlib import Path
import sys
import numpy as np
from scipy.interpolate import PchipInterpolator
ROOT=Path(__file__).resolve().parents[2]; R=ROOT/'robots/Goose_V0.1'
sys.path.insert(0,str(ROOT/'scripts/cad'))
from build_goose_cad import cylinder,box
from goose_nurbs_skin import skin
from goose_candidate_export import CandidateExport


def half(x,rows,side):
    grid=np.zeros((len(x),49,3))
    for i,(xx,(yy,zz,ry,rz)) in enumerate(zip(x,rows)):
        a=np.linspace(-np.pi/2,np.pi/2,49); co=np.maximum(0,np.cos(a)); si=np.sin(a)
        grid[i,:,0]=xx; grid[i,:,1]=yy+side*ry*co**(2/3.1)
        grid[i,:,2]=zz+rz*np.sign(si)*abs(si)**(2/3.1)
    u=np.gradient(grid,axis=0); v=np.gradient(grid,axis=1)
    normal=np.cross(u,v); normal/=np.linalg.norm(normal,axis=2)[:,:,None]
    if side>0:normal=-normal
    # Exact seam Y=centre is shared by the paired native halves. The seam
    # normal has no Y component; finite differencing alone would spoil this.
    normal[:,[0,-1],1]=0; normal/=np.linalg.norm(normal,axis=2)[:,:,None]
    inside=grid-2.4*normal
    return skin(grid,inside,np.ones((len(x)-1,48),bool))


def main():
    export=CandidateExport(R,'hollow_shoe_covers'); replaced=[]
    for label,sgn in [('right',-1),('left',1)]:
        yy=sgn*76
        rows=np.array([(-68,yy,19,3,2.5),(-59,yy,23,25,7),(-32,yy,28,37,12),
            (1,yy,31,42,15),(33,yy,36,47,20),(61,yy,37,49,21),
            (83,yy,36,50,20),(103,yy,26,46,10),(120,yy,19,25,3),(126,yy,18,3,2)],float)
        profile=PchipInterpolator(rows[:,0],rows[:,1:])
        for suffix,lo,hi,mat in [('aft',-68,27.9,'ivory'),('fore',28.1,126,'orange')]:
            x=np.linspace(lo,hi,49); rr=profile(x)
            shape=half(x,rr,-1)+half(x,rr,1)
            shape-=box((400,400,200),(30,yy,-84)) # actual open bottom Z16
            shape-=cylinder(35,180,[1,yy,62],'y') # pitching case swept aperture
            shape-=cylinder(29,100,[61,yy,36],'x') # roll case and foot saddle opening
            name=label+'_foot_upper_'+suffix; replaced.append(name)
            export.emit(name,shape,label+'_ankle_roll',rho=1270,material=mat,
                notes=['Native 2.4mm nominal normal-offset NURBS cover, underside open atZ16mm.',
                    'R35 pitch and R29 roll mechanism apertures; explicit exposed ankle, not filled shoe volume.',
                    'Screw mounting, sweep clearance and print tolerances remain separate gates.'])
    value=export.save(ROOT,[Path(__file__),ROOT/'scripts/cad/goose_nurbs_skin.py',ROOT/'scripts/cad/goose_candidate_export.py'],replaces=replaced,
        extra=dict(wall_nominal_mm=2.4,bottom_open_z_mm=16,actual_mounting_released=False))
    print('hollow shoes',len(value['parts']),'kg',value['native_mass_kg'],flush=True)

if __name__=='__main__':main()
