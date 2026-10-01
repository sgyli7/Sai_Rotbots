"""Native-solid export for additional same-layout engineering candidates."""
from pathlib import Path
import hashlib,json
import numpy as np
import trimesh
from build123d import export_step,export_brep,export_stl,import_step
from build_goose_actuator_interfaces import quad_sampling
from goose_nurbs_skin import native_properties


class CandidateExport:
    def __init__(self,robot,folder):
        self.robot=robot;self.folder=folder;self.parts=[];self.scene=[]
        self.source=robot/'cad/source'/folder;self.out=robot/'cad/exports'/folder
        self.source.mkdir(parents=True,exist_ok=True);self.out.mkdir(parents=True,exist_ok=True)

    def emit(self,name,shape,body,rho=2700.,material='ivory',notes=(),catalog_mass=None):
        if not shape.is_valid or len(shape.solids())!=1:raise ValueError((name,'native validity'))
        shape=shape.solids()[0];v,c,I,_=native_properties(shape)
        if catalog_mass is not None:rho=catalog_mass/v*1e9
        paths={'brep':self.source/(name+'.brep'),'step':self.out/(name+'.step'),'stl':self.out/(name+'.stl'),'npz':self.source/(name+'_quad.npz')}
        export_brep(shape,paths['brep']);export_step(shape,paths['step'])
        rt=import_step(paths['step']);rv,*_=native_properties(rt)
        for tol,angle in [(.08,.15),(.025,.08),(.01,.05),(.003,.03)]:
            export_stl(shape,paths['stl'],tolerance=tol,angular_tolerance=angle)
            mesh=trimesh.load(paths['stl'],force='mesh',process=True)
            if mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0 and abs(mesh.volume/v-1)<.005:break
        if not rt.is_valid or len(rt.solids())!=1 or abs(rv/v-1)>1e-5 or not mesh.is_watertight or not mesh.is_winding_consistent or abs(mesh.volume/v-1)>.005:
            raise ValueError((name,'exchange',dict(step_valid=rt.is_valid,step_solids=len(rt.solids()),
                step_volume_relative_error=abs(rv/v-1),stl_watertight=mesh.is_watertight,
                stl_winding_consistent=mesh.is_winding_consistent,stl_volume_relative_error=abs(mesh.volume/v-1))))
        vertices,faces=quad_sampling(mesh);np.savez_compressed(paths['npz'],vertices=vertices,faces=faces)
        files={k:dict(path=str(p.relative_to(self.robot)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for k,p in paths.items()}
        self.parts.append(dict(name=name,body=body,unit='mm',density_kg_m3=rho,mass_kg=v*rho*1e-9,volume_mm3=v,
            center_of_mass_world_m=(c/1000).tolist(),inertia_at_com_world_kg_m2=(I*rho*1e-15).tolist(),
            notes=list(notes),files=files,quad_faces=len(faces),native_valid=True,stl_watertight=True,manufacturing_released=False,
            exchange_validation=dict(step_volume_relative_error=abs(rv/v-1),stl_volume_relative_error=abs(mesh.volume/v-1),
                stl_tolerance_mm=tol,stl_angular_tolerance_rad=angle),
            mass_basis='catalog mass; installation-envelope inertia' if catalog_mass is not None else 'native density estimate'))
        self.scene.append(dict(name=name,body=body,group=self.folder,material=material,role='native_candidate_attachment_unreleased',geometry_npz=files['npz']['path'],source_sha256=files['npz']['sha256']))
        return name

    def save(self,root,inputs,replaces=(),extra=None):
        payload=dict(schema='goose_'+self.folder+'_v1',parts=self.parts,replaces_existing_parts=list(replaces),
            native_mass_kg=sum(p['mass_kg'] for p in self.parts),manufacturing_pass=False,full_assembly_pass=False,
            source_hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
        payload.update(extra or {})
        (self.out/'manifest.json').write_text(json.dumps(payload,indent=2)+'\n')
        (self.source/'quad_scene.json').write_text(json.dumps(dict(unit='m',status='NATIVE_ATTACHMENT_CANDIDATE',parts=self.scene),separators=(',',':'))+'\n')
        return payload
