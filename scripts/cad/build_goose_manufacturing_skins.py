"""Make native smooth CAD skins without replacing the accepted body profile.

This is a manufacturing BASE, not a released assembly: attachment bosses, head
optical/roll apertures, actual frame mating and swept installation are gates.
The historical stage-two model and all of its hashes remain unchanged.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
import trimesh
from build123d import CenterOf,export_brep,export_step,export_stl,import_step
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/cad'))
from goose_nurbs_skin import grids,skin,surface,native_properties
from build_goose_fuller_exterior import closed_skin

ROBOT=ROOT/'robots/Goose_V0.1'
SOURCE=ROBOT/'cad/source/manufacturing_skins'
EXPORT=ROBOT/'cad/exports/manufacturing_skins'

def quad_surface(out,inner,mask):
    nv=mask.shape[1]+1
    faces=[(i*nv+j,(i+1)*nv+j,(i+1)*nv+j+1,i*nv+j+1) for i,j in np.argwhere(mask)]
    return closed_skin(out.reshape(-1,3),inner.reshape(-1,3),faces)

def sampled_quad_source(out,inner,mask,factor=7):
    """Sample the native CAD surface, rather than only smoothing coarse normals."""
    nu,nv=mask.shape
    sampled=[]
    for grid in (out,inner):
        s=surface(grid);arr=np.empty((nu*factor+1,nv*factor+1,3))
        for i in range(len(arr)):
            for j in range(len(arr[0])):
                arr[i,j]=s.Value(i/(nu*factor),j/(nv*factor)).Coord()
        sampled.append(arr)
    refined_mask=np.repeat(np.repeat(mask,factor,axis=0),factor,axis=1)
    return quad_surface(*sampled,refined_mask),sampled,refined_mask

def boundary_deviation(out,inner,mask,native_surfaces=None):
    # The CAD surface interpolates every authoring node. Quantify what lies
    # between nodes: smooth CAD vs the two triangles of the interchange quad.
    result={};nu,nv=mask.shape
    for index,(label,grid) in enumerate([('outer',out),('inner',inner)]):
        s=surface(grid) if native_surfaces is None else native_surfaces[index]
        maximum=0.;worst=None
        for i,j in np.argwhere(mask):
            for u,v in [(.5,.5),(.25,.25),(.75,.25),(.25,.75),(.75,.75)]:
                p=np.array(tuple(s.Value((i+u)/nu,(j+v)/nv).Coord()))
                a,b,c,d=grid[i,j],grid[i+1,j],grid[i+1,j+1],grid[i,j+1]
                linear=(1-u)*a+(u-v)*b+v*c if u>=v else (1-v)*a+u*c+(v-u)*d
                delta=float(np.linalg.norm(p-linear))
                if delta>maximum:maximum=delta;worst=[int(i),int(j),u,v]
        result[label]={'max_sampled_mm':maximum,'sample_cell_uv':worst,'scope':'five points per source cell, not a continuous Hausdorff bound'}
    return result

def head_grid(scene):
    p=next(p for p in scene['parts'] if p['name']=='goose_head_shell')
    # section_solid: 57 rings, 64 perimeter nodes; caps follow the rings.
    ring=np.array(p['vertices'][:57*64])*1000
    ring=ring.reshape(57,64,3)
    indices=np.arange(8,73)%64
    # The perimeter is periodic. A one-sided end derivative gives the two
    # halves different inner seam positions even though outer nodes coincide.
    du=np.gradient(ring,axis=0)
    dv=(np.roll(ring,-1,axis=1)-np.roll(ring,1,axis=1))/2
    normals=np.cross(du,dv);normals/=np.linalg.norm(normals,axis=2,keepdims=True)
    centers=ring.mean(axis=1)[:,None,:]
    flip=np.sum(normals*(ring-centers),axis=2)<0
    normals[flip]*=-1
    inner=ring-2.2*normals
    return ring[:,indices].copy(),inner[:,indices].copy()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--only-heads',action='store_true');args=parser.parse_args()
    SOURCE.mkdir(parents=True,exist_ok=True);EXPORT.mkdir(parents=True,exist_ok=True)
    scene_path=ROBOT/'cad/source/stage_two_architecture/scene.json'
    scene=json.loads(scene_path.read_text());records=[];source_parts=[]
    layout_path=ROBOT/'configs/manufacturing_head_layout.json';layout=json.loads(layout_path.read_text())
    if args.only_heads:
        records=[p for p in json.loads((EXPORT/'manifest.json').read_text())['parts'] if not p['name'].startswith('goose_head_shell_')]
        source_parts=[p for p in json.loads((SOURCE/'quad_scene.json').read_text())['parts'] if not p['name'].startswith('goose_head_shell_')]
    def emit(name,out,inner,mask,extra_gates):
        print('BUILD',name,flush=True)
        shape=skin(out,inner,mask);q,sampled,refined_mask=sampled_quad_source(out,inner,mask)
        volume,center_mm,inertia_geom,integration_error=native_properties(shape)
        tri=np.concatenate([q.faces[:,[0,1,2]],q.faces[:,[0,2,3]]])
        tm=trimesh.Trimesh(q.vertices,tri,process=False)
        if not shape.is_valid or len(shape.solids())!=1 or shape.volume<=0:raise RuntimeError(('native_solid_invalid',name))
        if not tm.is_watertight or not tm.is_winding_consistent or tm.volume<=0:raise RuntimeError(('quad_source_invalid',name))
        brep=SOURCE/(name+'.brep');step=EXPORT/(name+'.step');stl=EXPORT/(name+'.stl')
        export_brep(shape,brep);export_step(shape,step)
        # Native OCCT meshing of these trimmed cubic surfaces reproducibly
        # generates degenerate triangles/open seams (raw evidence preserved).
        # Use one shared structured quad sampling of the SAME NURBS surfaces.
        # It closes every boundary without hole filling or normal repair.
        tm.export(stl)
        rt=import_step(step)
        if not rt.is_valid or len(rt.solids())!=1:raise RuntimeError(('step_roundtrip_invalid',name))
        rt_volume,_,_,_=native_properties(rt)
        if abs(rt_volume-volume)>max(.01,volume*1e-7):raise RuntimeError(('step_volume_change',name))
        # These are fully dense geometric masses, without claimed infill saving.
        rho=1270.;mass=volume*rho*1e-9
        npz=SOURCE/(name+'_quad.npz')
        np.savez_compressed(npz,vertices=q.vertices/1000,faces=q.faces)
        payload={'name':name,'material':'ivory','group':'shell' if name.startswith(('torso','wing')) else 'head','role':'native_nurbs_skin_attachment_pending','geometry_npz':str(npz.relative_to(ROBOT)),'source_sha256':hashlib.sha256(npz.read_bytes()).hexdigest()}
        source_parts.append(payload)
        rec={'name':name,'unit':'mm','material':'PETG','density_kg_m3':rho,'volume_mm3':volume,'full_density_mass_kg':mass,'center_of_mass_world_m':(center_mm/1000).tolist(),'inertia_at_com_world_kg_m2':(inertia_geom*rho*1e-15).tolist(),'mass_property_method':'OCCT adaptive 2D Gauss volume integration, relative eps1e-7, OnlyClosed=true','estimated_native_integration_error':integration_error,'native_surface_faces':len(shape.faces()),'quad_faces':len(q.faces),'quad_closed':True,'cad_valid':True,'step_roundtrip_valid':True,'quad_vs_native_volume_relative':abs(tm.volume-volume)/volume,'source_node_interpolation_status':'cubic uniform NURBS through accepted construction nodes; sevenfold quad nodes sampled directly from native surfaces','stl_method':'triangulated shared quad sampling of native surfaces, mm; no hole filling/mesh repair','accepted_coarse_mesh_vs_native':boundary_deviation(out,inner,mask),'render_quad_vs_native':boundary_deviation(*sampled,refined_mask,native_surfaces=(surface(out),surface(inner))),'manufacturing_released':False,'remaining_gates':extra_gates,'files':{}}
        for f in (brep,step,stl):rec['files'][f.suffix[1:]]={'path':str(f.relative_to(ROBOT)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
        records.append(rec);print('CAD',name,'mass_g',round(mass*1000,2),'faces',len(shape.faces()),flush=True)
    for side,label in [(-1,'right'),(1,'left')]:
        if args.only_heads:continue
        out,inner=grids(side);aft=np.zeros((64,48),bool);fore=aft.copy();door=aft.copy()
        for i in range(64):
            for j in range(48):
                if 39<=i<49 and j>=42 or 27<=i<45 and j<8:continue
                if 10<=i<48 and 14<=j<36:door[i,j]=True
                elif i<30:aft[i,j]=True
                else:fore[i,j]=True
        for suffix,mask,offset in [('aft',aft,-.08),('fore',fore,.08)]:
            oo=out.copy();ii=inner.copy();oo[:,:,0]+=offset;ii[:,:,0]+=offset
            emit('torso_shell_'+label+'_'+suffix,oo,ii,mask,['seam interlock and internal mounting bosses','actual neck/hip mating clearance','print orientation and assembly tolerance'])
        oo=out.copy();ii=inner.copy()
        for arr in (oo,ii):
            for i in range(65):
                for j in range(49):
                    u=np.clip((i-10)/38,0,1);v=np.clip((j-14)/22,0,1)
                    arr[i,j,1]+=side*1.2*np.sin(np.pi*u)*np.sin(np.pi*v)
            arr[:,:,0]=-32+(arr[:,:,0]+32)*.988;arr[:,:,2]=293+(arr[:,:,2]-293)*.974;arr[:,:,1]+=side*.25
        emit('wing_access_cover_'+label,oo,ii,door,['manual hinge and latch mating geometry','cover sweep and opening accessibility','print orientation and tolerance'])
    out,inner=head_grid(scene)
    for label,lo,hi in [('left',0,32),('right',32,64)]:
        mask=np.zeros((56,64),bool);mask[:,lo:hi]=True
        # Cut cells overlapping the full roll-case sweep in the shell frame.
        # Stage-two head_roll is +/-0.6rad about X at (81,0,585.5)mm. The
        # union below encloses all rotated box corners, plus 2mm. This is a
        # conservative assembly opening,
        # not a swept connector certification or a final trimmed edge finish.
        from scipy.spatial.transform import Rotation
        pivot=np.array([81.,0.,585.5]);sweep_bounds=[]
        margin=layout['head_roll_aperture_margin_m']*1000
        for bb in [layout['head_roll_case_world_bounds_m']]+list(layout['head_pitch_fixed_envelopes_world_m'].values()):
            bounds=np.array(bb)*1000;corners=np.array([(x,y,z) for x in bounds[:,0] for y in bounds[:,1] for z in bounds[:,2]])
            swept=np.concatenate([(corners-pivot)@Rotation.from_rotvec([q,0,0]).as_matrix()+pivot for q in np.linspace(*layout['head_roll_aperture_range_rad'],241)])
            sweep_bounds.append((swept.min(axis=0)-margin,swept.max(axis=0)+margin))
        for i,j in np.argwhere(mask):
            cell=np.concatenate([out[i:i+2,j:j+2].reshape(-1,3),inner[i:i+2,j:j+2].reshape(-1,3)])
            if any(np.all(cell.max(axis=0)>=cut_lo) and np.all(cell.min(axis=0)<=cut_hi) for cut_lo,cut_hi in sweep_bounds):mask[i,j]=False
        # An aperture must not leave free-standing plastic scraps at the rear.
        # Author a single connected half-shell; this edits the CAD patch mask
        # before solid construction, rather than repairing an exported mesh.
        from scipy.ndimage import label as connected_regions
        labels,count=connected_regions(mask)
        if count>1:
            sizes=np.bincount(labels.ravel());sizes[0]=0;mask=labels==sizes.argmax()
        emit('goose_head_shell_'+label,out,inner,mask,['rear aperture edge finishing and full head-roll/connector sweep','camera window mounting','beak motor connector/cooling and internal frame','seam fasteners and optical clearance'])
    input_files=[Path(__file__),ROOT/'scripts/cad/goose_nurbs_skin.py',ROOT/'scripts/cad/build_goose_fuller_exterior.py',ROOT/'scripts/cad/build_goose_r2_reference_rebuild.py',ROOT/'scripts/cad/build_goose_quad_exterior_study.py',scene_path,layout_path]
    manifest={'schema':'goose_native_skin_candidate_v1','status':'NATIVE_SKINS_NOT_MANUFACTURING_RELEASE','manufacturing_pass':False,'final_appearance_pass':False,'source_scene_sha256':hashlib.sha256(scene_path.read_bytes()).hexdigest(),'source_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'source_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in input_files},'parts':records,'scope':'Six torso/door smooth hollow skins and two head half-skins only; not the full assembly.'}
    (EXPORT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (SOURCE/'quad_scene.json').write_text(json.dumps({'status':manifest['status'],'unit':'m','manufacturing_pass':False,'parts':source_parts},separators=(',',':'))+'\n')
    print('DONE',len(records),'native skin solids',flush=True)
if __name__=='__main__':main()
