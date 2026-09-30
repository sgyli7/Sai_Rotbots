"""Refuse stale assets, scale mistakes and cosmetic release claims."""
import importlib.util,json,hashlib
from pathlib import Path
import pytest
import numpy as np
from build123d import Box,export_brep,export_step,export_stl

PATH=Path(__file__).resolve().parents[1]/'scripts/diagnostics/check_goose_manufacturing_appearance.py'
spec=importlib.util.spec_from_file_location('appearance_audit',PATH)
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)

@pytest.fixture
def assembly(tmp_path):
    # A real native 10mm cube and independent, outward wound SI quad cube.
    shape=Box(10,10,10);files={}
    for kind,fn in [('brep',export_brep),('step',export_step),('stl',export_stl)]:
        path=tmp_path/('part.'+kind);fn(shape,path)
        files[kind]={'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    verts=[[-.005,-.005,-.005],[.005,-.005,-.005],[.005,.005,-.005],[-.005,.005,-.005],[-.005,-.005,.005],[.005,-.005,.005],[.005,.005,.005],[-.005,.005,.005]]
    faces=[[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]
    part={'name':'cube','role':'custom_part','vertices':verts,'faces':faces}
    part['source_sha256']=hashlib.sha256(json.dumps({'vertices':verts,'faces':faces},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    manifest={'scope':'partial prototype','manufacturing_pass':False,'parts':[{'name':'cube','unit':'mm','volume_mm3':1000.,'center_of_mass_world_m':[0,0,0],'files':files,'manufacturing_released':False,'remaining_gates':['mounting']}]}
    scene={'unit':'m','parts':[part]}
    def run():
        m=tmp_path/'manifest.json';s=tmp_path/'scene.json'
        m.write_text(json.dumps(manifest));s.write_text(json.dumps(scene))
        return audit.inspect(tmp_path,m,s)
    return tmp_path,manifest,scene,run

def test_valid_partial_asset_is_not_final(assembly):
    _,_,_,run=assembly;r=run()
    assert r['integrity_pass'] and not r['final_appearance_pass']

def test_tampered_step_refused(assembly):
    root,_,_,run=assembly
    (root/'part.step').write_text('replaced after export')
    r=run();assert not r['integrity_pass']
    assert any('step: hash mismatch' in x for x in r['errors'])

def test_declared_metres_cannot_hide_mm_vertices(assembly):
    _,_,scene,run=assembly;p=scene['parts'][0]
    p['vertices']=[[x*1000 for x in v] for v in p['vertices']]
    p['source_sha256']=hashlib.sha256(json.dumps({'vertices':p['vertices'],'faces':p['faces']},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    r=run();assert not r['integrity_pass']
    assert any('SI/CAD volume mismatch' in x for x in r['errors'])

@pytest.mark.parametrize('which',['duplicate','missing'])
def test_part_identity_refused(assembly,which):
    _,_,scene,run=assembly
    scene['parts']=scene['parts']*2 if which=='duplicate' else []
    assert not run()['integrity_pass']

def test_cosmetic_success_flag_cannot_override_unreleased_hardware(assembly):
    _,manifest,scene,run=assembly
    manifest['scope']='FULL_ASSEMBLY';manifest['assembly_inventory']=['cube'];manifest['manufacturing_pass']=True
    scene['parts'][0]['role']='purchased_motor_envelope'
    r=run();assert r['integrity_pass'] and not r['final_appearance_pass']
    assert any('unreleased' in x for x in r['release_blockers'])
    assert any('envelope' in x for x in r['release_blockers'])

def test_export_path_cannot_escape_robot_root(assembly):
    _,manifest,_,run=assembly;manifest['parts'][0]['files']['step']['path']='../outside.step'
    r=run();assert not r['integrity_pass']
    assert any('path escapes' in x for x in r['errors'])

def test_compressed_quad_source_preserves_asset_identity(assembly):
    root,_,scene,run=assembly;part=scene['parts'][0]
    path=root/'cube_quad.npz'
    np.savez_compressed(path,vertices=part.pop('vertices'),faces=part.pop('faces'))
    part['geometry_npz']=path.name;part['source_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    assert run()['integrity_pass']
    with np.load(path) as data:vertices=data['vertices'].copy();faces=data['faces'].copy()
    vertices[0,0]+=.001;np.savez_compressed(path,vertices=vertices,faces=faces)
    assert not run()['integrity_pass']

def test_same_volume_at_wrong_world_position_refused(assembly):
    _,_,scene,run=assembly;part=scene['parts'][0]
    part['vertices']=[[x+.01,y,z] for x,y,z in part['vertices']]
    part['source_sha256']=hashlib.sha256(json.dumps({'vertices':part['vertices'],'faces':part['faces']},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    r=run();assert not r['integrity_pass']
    assert any('placement mismatch' in e for e in r['errors'])
