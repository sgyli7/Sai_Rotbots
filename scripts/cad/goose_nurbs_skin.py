"""Cubic NURBS skins from the accepted structured quad construction.

Millimetres throughout. Uses uniform interpolation parameters so trimmed patch
boundaries and ruled wall boundaries share the exact same native curves.
Source quads remain editable; exchange STEP surfaces are continuous CAD.
The CAD validity result alone never releases a part for manufacture.
"""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/cad'))
import numpy as np
from build_goose_fuller_exterior import PROFILE
from OCP.TColgp import TColgp_Array2OfPnt
from OCP.gp import gp_Pnt
from OCP.GeomAPI import GeomAPI_PointsToBSplineSurface
from OCP.Approx import Approx_ParametrizationType
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace,BRepBuilderAPI_MakeEdge,BRepBuilderAPI_Sewing,BRepBuilderAPI_MakeSolid
from OCP.BRepFill import BRepFill
from OCP.TopoDS import TopoDS
from OCP.ShapeFix import ShapeFix_Solid
from build123d import Solid,export_step,export_stl
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps

def native_properties(shape):
    """Adaptive integration matters for thin skins with many BSpline spans.

    Default non-adaptive shape.volume/center can bias COM by ~0.4mm here.
    Return mm^3, mm and the geometric inertia tensor in mm^5, about COM.
    """
    props=GProp_GProps()
    error=BRepGProp.VolumeProperties_s(shape.wrapped,props,1e-7,True,False)
    matrix=props.MatrixOfInertia()
    inertia=np.array([[matrix.Value(i+1,j+1) for j in range(3)] for i in range(3)])
    volume=float(props.Mass());center=np.array(props.CentreOfMass().Coord())
    if volume<=0 or not np.isfinite(inertia).all() or np.linalg.eigvalsh(inertia).min()<=0:
        raise ValueError('invalid adaptive native mass properties')
    return volume,center,inertia,float(error)

def grids(side):
    out=np.zeros((65,49,3));inside=out.copy()
    for i in range(65):
        for j in range(49):
            v=np.clip((j-25)/11,-1,1);rear=-142+22*abs(v)**3;front=83-24*abs(v)**3
            x=np.interp(i,[0,10,48,64],[-170,rear,front,148]);t=np.clip((i-10)/38,0,1)
            half=.11+.45*np.sin(t*np.pi/2)**.7;center=.14-.07*t
            angle=np.interp(j,[0,14,36,48],[-np.pi/2,center-half,center+half,np.pi/2])
            cz,ry,rz=PROFILE(x);co,si=np.cos(angle),np.sin(angle)
            out[i,j]=x,side*(ry*co+.12),cz+rz*si
            czd,ryd,rzd=PROFILE.derivative()(x)
            normal=np.array([-co*co*ryd/ry-si*czd/rz-si*si*rzd/rz,side*co/ry,si/rz]);normal/=np.linalg.norm(normal)
            inside[i,j]=out[i,j]-2.4*normal
    return out,inside

def surface(grid):
    a=TColgp_Array2OfPnt(1,len(grid),1,len(grid[0]))
    for i,row in enumerate(grid):
        for j,p in enumerate(row):a.SetValue(i+1,j+1,gp_Pnt(*map(float,p)))
    fit=GeomAPI_PointsToBSplineSurface();fit.Interpolate(a,Approx_ParametrizationType.Approx_IsoParametric,False)
    return fit.Surface()

def rectangles(mask):
    work=mask.copy();rect=[]
    while work.any():
        i,j=np.argwhere(work)[0];w=1
        while j+w<work.shape[1] and work[i,j+w]:w+=1
        h=1
        while i+h<work.shape[0] and work[i+h,j:j+w].all():h+=1
        rect.append((i,i+h,j,j+w));work[i:i+h,j:j+w]=False
    return rect

def skin(out,inside,mask):
    from collections import Counter,defaultdict
    so,si=surface(out),surface(inside);nu,nv=mask.shape
    sewing=BRepBuilderAPI_Sewing(1e-5)
    for i,I,j,J in rectangles(mask):
        for s in (so,si):sewing.Add(BRepBuilderAPI_MakeFace(s,i/nu,I/nu,j/nv,J/nv,1e-7).Face())
    counts=Counter()
    for i,j in np.argwhere(mask):
        p=[(i,j),(i+1,j),(i+1,j+1),(i,j+1)]
        for a,b in zip(p,p[1:]+p[:1]):counts[tuple(sorted((a,b)))]+=1
    rows=defaultdict(list)
    for (a,b),n in counts.items():
        if n!=1:continue
        if a[0]==b[0]:rows[(0,int(a[0]))].append((int(a[1]),int(b[1])))
        else:rows[(1,int(a[1]))].append((int(a[0]),int(b[0])))
    for (axis,fixed),segments in rows.items():
        segments.sort();joined=[]
        for a,b in segments:
            if joined and joined[-1][1]==a:joined[-1]=(joined[-1][0],b)
            else:joined.append((a,b))
        for a,b in joined:
            edges=[]
            for s in (so,si):
                c=s.UIso(fixed/nu) if axis==0 else s.VIso(fixed/nv)
                scale=nv if axis==0 else nu
                edges.append(BRepBuilderAPI_MakeEdge(c,a/scale,b/scale).Edge())
            sewing.Add(BRepFill.Face_s(*edges))
    sewing.Perform();wrapped=sewing.SewedShape()
    solid=BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(wrapped)).Solid()
    fix=ShapeFix_Solid(solid);fix.Perform()
    result=Solid(fix.Solid())
    return result
