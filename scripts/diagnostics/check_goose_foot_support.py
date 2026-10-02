"""Check source contact preservation, six-part intersections and STEP agreement."""
from __future__ import annotations
import hashlib
import itertools
import json
from pathlib import Path
import numpy as np
import trimesh
from build123d import import_step

ROOT=Path(__file__).resolve().parents[2]
R=ROOT/'robots/Goose_V0.1'

def mesh(part):
    f=np.asarray(part['faces'])
    return trimesh.Trimesh(np.asarray(part['vertices'])*1000,np.vstack((f[:,[0,1,2]],f[:,[0,2,3]])),process=False)

def main():
    base=R/'cad/source/fuller_exterior_candidate/closed/scene.json'
    source={p['name']:p for p in json.loads(base.read_text())['parts']}
    candidate=R/'cad/source/foot_support_candidate/foot_parts.json'
    data=json.loads(candidate.read_text()); pp={p['name']:p for p in data['parts']}
    mm={n:mesh(p) for n,p in pp.items()}; checks=[]
    assert data['approved_scene_sha256']==hashlib.sha256(base.read_bytes()).hexdigest()
    for label in ('right','left'):
        old=source[label+'_foot_sole']; new=pp[label+'_foot_sole']
        # Compare actual vertices, including the complete bottom grid and heel.
        original=np.asarray(old['vertices']); current=np.asarray(new['vertices'])
        def face_key(vertices, face):
            return tuple(sorted(tuple(row) for row in np.round(vertices[face],10)))
        current_faces={face_key(current,face) for face in new['faces']}
        old_faces=np.asarray(old['faces'])
        exposed=old_faces[~np.all(np.isclose(original[old_faces,2],original[:,2].max()),axis=1)]
        missing=sum(face_key(original,face) not in current_faces for face in exposed)
        checks.append(dict(name=label+'_all_original_sole_outer_quads',missing_quads=missing,passed=missing==0))
        nearest=trimesh.proximity.closest_point_naive(mm[label+'_foot_sole'], original[original[:,2]<.002001]*1000)[1]
        checks.append(dict(name=label+'_original_contact_surface',max_deviation_mm=float(max(nearest)),passed=bool(max(nearest)<1e-7)))
        for a,b in itertools.combinations(('sole','trim','load_plate'),2):
            with np.errstate(invalid='ignore',divide='ignore'):
                common=trimesh.boolean.intersection([mm[label+'_foot_'+a],mm[label+'_foot_'+b]],engine='manifold')
            v=0.0 if len(common.faces)==0 else abs(float(common.volume))
            checks.append(dict(name=label+'_'+a+'_vs_'+b,intersection_volume_mm3=v,passed=v<.01))
        name=label+'_foot_load_plate'
        solid=import_step(R/'cad/exports/foot_support_candidate'/f'{name}.step')
        error=abs(solid.volume-mm[name].volume)/mm[name].volume
        checks.append(dict(name=name+'_step_reload',volume_relative_error=error,valid=bool(solid.is_valid),passed=bool(solid.is_valid and error<1e-8)))
    report=dict(status='GEOMETRY_CHECK_ONLY',passed=all(c['passed'] for c in checks),checks=checks,
        candidate_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
        scope='Six candidate foot parts only; no ankle bracket, upper foot shell, articulated motion, material strength or walking acceptance')
    (R/'evidence/foot_support_geometry.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)

if __name__=='__main__':main()
