"""Same-version convex assembly and twelve passive soft-sole contacts.

This is a rejection-test candidate. It is not a certified manufacturing,
walking or manipulation release. All active axes retain the neutral SI order.
"""
from pathlib import Path
import copy,hashlib,json,sys
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
import mujoco
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path.insert(0,str(ROOT/'scripts/models'))
from build_goose_mechanical_reference import vec,save_xml


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def inertia(node,mass,com,tensor):
    values,rotation=np.linalg.eigh(tensor)
    if min(values)<=0:raise ValueError('non-positive adjusted inertia')
    if np.linalg.det(rotation)<0:rotation[:,0]*=-1
    q=Rotation.from_matrix(rotation).as_quat()
    node.attrib.update(mass=str(mass),pos=vec(com),diaginertia=vec(values),quat=vec(np.r_[q[3],q[:3]]))


def main():
    paths=[R/'configs/mechanical_reference_contract.json',R/'models/mechanical_collisions/manifest.json',
        R/'evidence/body_bay_mechanical_parameters.json',R/'cad/exports/compliant_foot/manifest.json',
        R/'evidence/manufacturing_compliant_foot.json']
    reference,collision,ledger,feet,spring=[json.loads(p.read_text()) for p in paths]
    for data in [reference,collision,ledger]:
        for path,expected in data['source_hashes'].items():
            if sha(ROOT/path)!=expected:raise ValueError(('stale source',path))
    if {p['name'] for p in collision['parts']}!={p['name'] for p in reference['visual_sources']}:raise ValueError('collision/visual coverage')
    if {p['name']:p['body'] for p in collision['parts']}!={p['name']:p['body'] for p in reference['visual_sources']}:raise ValueError('collision/visual rigid ownership mismatch')
    out=R/'models/mechanical_physics';out.mkdir(exist_ok=True);(out/'collision_assets').mkdir(exist_ok=True)
    mj=ET.parse(R/'models/mechanical_reference/robot.xml').getroot()
    mj.attrib['model']='goose_mechanical_collision_candidate'
    mj.find('compiler').attrib.update(meshdir='.',balanceinertia='false')
    # 0.223g native tread pads with23kN/m springs have a roughly0.61ms
    # undamped natural period. A1ms integrator step failed at that passive DOF.
    # Resolve its period rather than changing pad mass or spring geometry.
    mj.find('option').attrib.update(timestep='.0001',iterations='100',cone='elliptic')
    mj.find('custom/text').attrib['data']='COLLISION_REJECTION_CANDIDATE_NOT_TRAINING_OR_HARDWARE_RELEASE'
    assets=mj.find('asset');world=mj.find('worldbody')
    for mesh in assets.findall('mesh'):mesh.attrib['file']='../mechanical_reference/assets/'+mesh.attrib['file']
    ET.SubElement(world,'geom',name='ground',type='plane',size='2 2 .01',contype='1',conaffinity='2',friction='.65 .01 .002',solref='.005 1')
    nodes={p.attrib['name']:p for p in world.findall('.//body')}
    urdf=ET.parse(R/'models/mechanical_reference/robot.urdf').getroot();urdf.attrib['name']='goose_mechanical_collision_candidate'
    links={p.attrib['name']:p for p in urdf.findall('link')}
    for mesh in urdf.findall('.//visual/geometry/mesh'):mesh.attrib['filename']='../mechanical_reference/'+mesh.attrib['filename']
    pivots={k:np.array(v) for k,v in ledger['pivots_world_at_zero_m'].items()}
    pivots.update({j['name']:np.array(j['pivot_world_at_zero_m']) for j in reference.get('passive_linkage_joints',[])})
    lift=np.array([0,0,ledger['rigid_coordinate_lift_m']])
    geometries=[];local_files={}
    for part in collision['parts']:
        owner=part['body']
        for number,h in enumerate(part['hulls']):
            source=R/h['path']
            if sha(source)!=h['sha256']:raise ValueError(('stale hull',source))
            mesh=trimesh.load(source,force='mesh',process=False)
            mesh.vertices+=lift-pivots[owner]
            name=part['name']+f'_collision_{number:03d}';file=out/'collision_assets'/(name+'.obj')
            mesh.export(file,include_normals=False);local_files[str(file.relative_to(out))]=sha(file)
            ET.SubElement(assets,'mesh',name=name,file='collision_assets/'+file.name,maxhullvert='64')
            ET.SubElement(nodes[owner],'geom',name=name,type='mesh',mesh=name,contype='2',conaffinity='3',group='3',rgba='.1 .2 .4 .2',
                density='0',friction='.65 .01 .002',solref='.005 1',solimp='.95 .99 .001',margin='0')
            u=ET.SubElement(links[owner],'collision',name=name);ET.SubElement(u,'origin',xyz='0 0 0',rpy='0 0 0')
            ET.SubElement(ET.SubElement(u,'geometry'),'mesh',filename='collision_assets/'+file.name)
            geometries.append(dict(name=name,part=part['name'],body=owner,asset=str(file.relative_to(out)),method=part['method']))
    # Remove actual 5x24x1.5mm tread mass from the parent, then move it to
    # passive bodies. This preserves the ledger mass/COM/full tensor at zero.
    pads=[];size=np.array([.005,.024,.0015]);pad_mass=float(np.prod(size)*1240)
    runtime_bodies=copy.deepcopy(reference['bodies'])
    pad_tensor=np.diag(pad_mass*(sum(size*size)-size*size)/12)
    stiffness=spring['elementary_nominal_leaf_stiffness_n_mm']*1000
    for f in feet['feet']:
        side=f['side'];owner=side+'_ankle_roll';parent=next(b for b in ledger['bodies'] if b['name']==owner)
        centers=np.array(f['pad_centers_world_xy_mm'])/1000
        centers[:,0]+=.008;centers[:,1]+= -.013 if side=='left' else .013
        world_centers=np.c_[centers,np.full(6,f['undeformed_contact_plane_world_z_mm']/1000+size[2]/2)]+lift
        local=world_centers-pivots[owner]
        M=parent['mass_kg'];C=np.array(parent['com_local_m']);T=np.array(parent['inertia_at_com_body_kg_m2'])+M*(np.dot(C,C)*np.eye(3)-np.outer(C,C))
        adjusted_mass=M-6*pad_mass;adjusted_com=(M*C-pad_mass*local.sum(axis=0))/adjusted_mass
        for p in local:T-=pad_tensor+pad_mass*(np.dot(p,p)*np.eye(3)-np.outer(p,p))
        adjusted_tensor=T-adjusted_mass*(np.dot(adjusted_com,adjusted_com)*np.eye(3)-np.outer(adjusted_com,adjusted_com))
        next(b for b in runtime_bodies if b['name']==owner).update(mass_kg=adjusted_mass,com_local_m=adjusted_com.tolist(),inertia_at_com_body_kg_m2=adjusted_tensor.tolist())
        inertia(nodes[owner].find('inertial'),adjusted_mass,adjusted_com,adjusted_tensor)
        u=links[owner].find('inertial');u.find('mass').attrib['value']=str(adjusted_mass);u.find('origin').attrib['xyz']=vec(adjusted_com)
        u.find('inertia').attrib.update(**{k:str(adjusted_tensor[i,j]) for k,i,j in [('ixx',0,0),('iyy',1,1),('izz',2,2),('ixy',0,1),('ixz',0,2),('iyz',1,2)]})
        for k,p in enumerate(local):
            name=side+f'_sole_pad_{k}';joint=name+'_compression'
            node=ET.SubElement(nodes[owner],'body',name=name,pos=vec(p))
            ET.SubElement(node,'joint',name=joint,type='slide',axis='0 0 1',range='0 .0015',stiffness=str(stiffness),damping='2',springref='0',solreflimit='.005 1')
            inertia(ET.SubElement(node,'inertial'),pad_mass,[0,0,0],pad_tensor)
            ET.SubElement(node,'geom',name=name,type='box',size=vec(size/2),contype='2',conaffinity='1',friction='.65 .01 .002',solref='.005 1',solimp='.95 .99 .001',group='3')
            link=ET.SubElement(urdf,'link',name=name);ui=ET.SubElement(link,'inertial');ET.SubElement(ui,'mass',value=str(pad_mass));ET.SubElement(ui,'origin',xyz='0 0 0',rpy='0 0 0')
            ET.SubElement(ui,'inertia',ixx=str(pad_tensor[0,0]),iyy=str(pad_tensor[1,1]),izz=str(pad_tensor[2,2]),ixy='0',ixz='0',iyz='0')
            uc=ET.SubElement(link,'collision',name=name);ET.SubElement(ET.SubElement(uc,'geometry'),'box',size=vec(size))
            uj=ET.SubElement(urdf,'joint',name=joint,type='prismatic');ET.SubElement(uj,'parent',link=owner);ET.SubElement(uj,'child',link=name);ET.SubElement(uj,'origin',xyz=vec(p),rpy='0 0 0');ET.SubElement(uj,'axis',xyz='0 0 1')
            ET.SubElement(uj,'limit',lower='0',upper='.0015',effort='1000',velocity='1');ET.SubElement(uj,'dynamics',damping='2',friction='0')
            pads.append(dict(name=name,joint=joint,body=owner,world_at_zero_m=world_centers[k].tolist(),mass_kg=pad_mass,size_m=size.tolist(),travel_m=.0015,stiffness_n_m=stiffness,damping_n_s_m=2))
            runtime_bodies.append(dict(name=name,mass_kg=pad_mass,com_local_m=[0,0,0],inertia_at_com_body_kg_m2=pad_tensor.tolist(),
                                       mass_relative_design_uncertainty=.05,com_randomization_m=0.,inertia_multiplier_range=[.95,1.05]))
    exclusions=[]
    if reference.get('passive_linkage_joints'):
        # The second coupler pin is a native, checked revolute mating between
        # separate tree branches. It receives the same adjacent-body filtering
        # as the first pin (parent/child); no unrelated bodies are excluded.
        contact=ET.SubElement(mj,'contact')
        ET.SubElement(contact,'exclude',body1='beak_coupler_link',body2='beak_hinge')
        exclusions=[dict(body1='beak_coupler_link',body2='beak_hinge',
                         reason='actual second coupler revolute pin; native assembly sweep independently checked')]
    save_xml(mj,out/'robot.xml');save_xml(urdf,out/'robot.urdf')
    contract=copy.deepcopy(reference);contract.update(schema='goose_mechanical_collision_candidate_si_v1',
        status='COLLISION_REJECTION_CANDIDATE_NOT_TRAINING_OR_HARDWARE_RELEASE',model_kind='approximate_convex_assembly_with_passive_tread',
        model_sha256=sha(out/'robot.xml'),urdf_sha256=sha(out/'robot.urdf'),collision_geometries=geometries,passive_contacts=pads,
        bodies=runtime_bodies,physics_dt_s=.0001,
        active_axes=18,passive_axes=12+len(reference.get('passive_linkage_joints',[])),physical_collision_model_complete=False,training_release=False,
        mechanical_mating_collision_exclusions=exclusions,
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in paths+[Path(__file__)]},
        asset_sha256=local_files,physical_collision_release=False,
        limitations=collision['limitations']+['Pad springs use typical TPU coupon modulus and uncalibrated damping/friction. No terrain-walking success inferred.',
        'URDF carries prismatic travel and damping; stiffness/contact settings are authoritative in this neutral contract and must be explicitly imported by other engines.',
        'Default adjacent-body filtering and the explicit second jaw coupler pin mating filter are active; native CAD mating checks remain mandatory.',
        'No payload or object manipulation task is added to bare robot.'])
    (R/'configs/mechanical_physics_contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    print('COLLISION assets',len(geometries),'passive pads',len(pads),flush=True)
    model=mujoco.MjModel.from_xml_path(str(out/'robot.xml'))
    np.testing.assert_allclose(model.body_mass.sum(),ledger['nominal_conditional_mass_kg'],atol=1e-12)
    count=len(reference.get('passive_linkage_joints',[]))
    assert model.nu==18 and model.nq==37+count and model.nv==36+count
    print('COMPILED',model.nq,model.nv,model.nu,'mass',model.body_mass.sum(),flush=True)

if __name__=='__main__':main()
