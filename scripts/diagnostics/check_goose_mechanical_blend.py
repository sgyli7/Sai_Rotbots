"""Read saved Blender geometry and verify every current part retains source quads."""
from pathlib import Path
import argparse,ast,array,hashlib,json,sys,zipfile
import bpy
from mathutils import Vector


def array_2d(raw):
    if raw[:6]!=b'\x93NUMPY':raise ValueError('NPY')
    size=2 if raw[6]==1 else 4;length=int.from_bytes(raw[8:8+size],'little');start=8+size
    h=ast.literal_eval(raw[start:start+length].decode('latin1'));v=array.array('d' if h['descr'].endswith('f8') else 'q');v.frombytes(raw[start+length:])
    if (h['descr'][0]=='<')!=(sys.byteorder=='little'):v.byteswap()
    return h['shape'],v


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--robot-root',type=Path,required=True)
    parser.add_argument('--scene',type=Path,default=Path('cad/source/mechanical_preview/scene.json'))
    parser.add_argument('--blend',type=Path,default=Path('cad/source/mechanical_preview/quad_assembly.blend'))
    parser.add_argument('--evidence',type=Path,default=Path('evidence/mechanical_blend_identity.json'))
    a=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);r=a.robot_root.resolve()
    scene_path=(r/a.scene).resolve();blend=(r/a.blend).resolve();evidence=(r/a.evidence).resolve()
    if not all(p.is_relative_to(r) for p in [scene_path,blend,evidence]):raise ValueError('Identity inputs/output must belong to the selected robot')
    s=json.loads(scene_path.read_text());bpy.ops.wm.open_mainfile(filepath=str(blend));records=[]
    for p in s['parts']:
        obj=bpy.data.objects.get(p['name'])
        if obj is None or obj.type!='MESH':raise ValueError(('missing',p['name']))
        if p.get('geometry_npz'):
            file=r/p['geometry_npz'];digest=hashlib.sha256(file.read_bytes()).hexdigest()
            if digest!=p['source_sha256']:raise ValueError(('source hash',p['name']))
            with zipfile.ZipFile(file) as z:
                shape,values=array_2d(z.read('vertices.npy'));nvertex=shape[0]
                lo=[min(values[i::3]) for i in range(3)];hi=[max(values[i::3]) for i in range(3)]
                fshape,_=array_2d(z.read('faces.npy'));nfaces=fshape[0]
        else:
            digest=p.get('source_sha256',hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest());nvertex=len(p['vertices']);nfaces=len(p['faces'])
            lo=[min(v[i] for v in p['vertices']) for i in range(3)];hi=[max(v[i] for v in p['vertices']) for i in range(3)]
        quad=all(len(f.vertices)==4 for f in obj.data.polygons)
        expected=[tuple(lo[i]+s['assembly_translation_m'][i] for i in range(3)),tuple(hi[i]+s['assembly_translation_m'][i] for i in range(3))]
        world=[obj.matrix_world@Vector(c) for c in obj.bound_box];actual=[tuple(min(v[i] for v in world) for i in range(3)),tuple(max(v[i] for v in world) for i in range(3))]
        error=max(abs(actual[j][i]-expected[j][i]) for j in range(2) for i in range(3))
        passed=quad and len(obj.data.vertices)==nvertex and len(obj.data.polygons)==nfaces and obj.get('source_sha256')==digest and error<1e-7
        records.append(dict(name=p['name'],quad_faces=len(obj.data.polygons),vertex_count=len(obj.data.vertices),all_faces_quad=quad,world_bounds_error_m=error,source_identity_pass=passed))
    report=dict(schema='goose_current_mechanical_blend_identity_v1',parts=len(records),expected_parts=len(s['parts']),all_source_identity_pass=all(x['source_identity_pass'] for x in records),quad_faces=sum(x['quad_faces'] for x in records),records=records,
        final_appearance_pass=False,manufacturing_pass=False,source_hashes={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [scene_path,blend]},generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        limitations=['Saved Blender quads andneutral bounds match current source;this does not supply omitted fasteners,cables,closures or complete manufacture.','Actual screenshots are candidate assembly views,not final1:1manufacturing appearance.'])
    evidence.write_text(json.dumps(report,indent=2)+'\n');print('BLEND IDENTITY',report['parts'],'quads',report['quad_faces'],'pass',report['all_source_identity_pass'],flush=True)
    if not report['all_source_identity_pass']:raise ValueError('saved quad identity failed')

if __name__=='__main__':main()
