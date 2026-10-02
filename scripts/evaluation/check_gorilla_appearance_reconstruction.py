#!/usr/bin/env python3
"""Check C source/render/export identity and mesh integrity, never beauty."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[2]
ROBOT=ROOT/"robots/gorilla_v0_1"


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scene",type=Path,default=ROBOT/"cad/source/appearance_c_scene.json")
    p.add_argument("--render",type=Path,default=ROBOT/"cad/exports/appearance_c/appearance_c_render_manifest.json")
    p.add_argument("--output",type=Path,default=ROBOT/"evidence/appearance_c_resource_check.json")
    args=p.parse_args();source=json.loads(args.scene.read_text());render=json.loads(args.render.read_text())
    errors=[];control_bad=[];export_bad=[]
    bindings=[*source["build_inputs"],{"path":source["spec_path"],"sha256":source["spec_sha256"]},
              {"path":source["appearance_authority_path"],"sha256":source["image_sha256"]},
              {"path":render["renderer_script_path"],"sha256":render["renderer_script_sha256"]},
              *render["images"],*render.get("exports",[])]
    for b in bindings:
        f=ROOT/b["path"]
        if not f.is_file() or sha(f)!=b["sha256"]:errors.append("Changed/missing bound file: "+b["path"])
    if render["scene_sha256"]!=sha(args.scene):errors.append("Render belongs to a different scene")
    for k in ("spec_sha256","image_authority_sha256"):
        expected=source["spec_sha256" if k=="spec_sha256" else "image_sha256"]
        if render[k]!=expected:errors.append("Identity mismatch: "+k)
    groups={}
    for part in source["parts"]:
        faces=[[f[0],f[i],f[i+1]] for f in part["faces"] for i in range(1,len(f)-1)]
        m=trimesh.Trimesh(vertices=part["vertices_world_m"],faces=faces,process=False)
        if not(m.is_watertight and m.is_winding_consistent and m.volume>0):control_bad.append(part["name"])
        if part.get("physical_mass_assigned") is not False:errors.append("Unexpected physical mass claim: "+part["name"])
        if part.get("surface_projection_unresolved_vertices",0):errors.append("Unattached surface detail: "+part["name"])
        groups[part["name"]+"_mesh"]=[]
    glb=ROBOT/"cad/exports/appearance_c/appearance_c.glb"
    loaded=trimesh.load(glb,force="scene")
    unassigned=[]
    for name,m in loaded.geometry.items():
        if name in groups:groups[name].append(m)
        else:
            matches=[k for k in groups if name.startswith(k+"_")]
            if len(matches)==1:groups[matches[0]].append(m)
            else:unassigned.append(name)
    for name,meshes in groups.items():
        if not meshes:export_bad.append({"part":name,"problem":"missing"});continue
        m=trimesh.util.concatenate(meshes)
        # Material/normal seams split vertices in glTF; topology is evaluated
        # after positional welding. Geometry coordinates are not modified.
        m.merge_vertices(merge_tex=True,merge_norm=True)
        if not(m.is_watertight and m.is_winding_consistent and m.volume>0):
            export_bad.append({"part":name,"closed":m.is_watertight,"winding_consistent":m.is_winding_consistent,"signed_volume_m3":float(m.volume)})
    if unassigned:errors.append("Unexpected GLB mesh primitives: "+str(unassigned))
    # Blender glTF Y-up: world (X,Y,Z) -> glTF (X,Z,-Y).
    lo,hi=np.asarray(source["bounds_world_m"])
    expected=np.array([[lo[0],lo[2],-hi[1]],[hi[0],hi[2],-lo[1]]])
    bound_error=float(np.abs(loaded.bounds-expected).max())
    if bound_error>2e-5:errors.append("GLB bound difference exceeds 20 micrometres")
    if source["appearance_accepted"] or render["appearance_accepted"]:errors.append("This checker cannot authorize appearance acceptance")
    if source["physics_accepted"] or render["physics_accepted"]:errors.append("Appearance assets cannot authorize physical acceptance")
    passed=not(errors or control_bad or export_bad)
    report={"schema":"gorilla_appearance_resource_check_v1","checkpoint_id":"gorilla_appearance_c",
        "scene_sha256":sha(args.scene),"render_manifest_sha256":sha(args.render),"glb_sha256":sha(glb),
        "checker_path":str(Path(__file__).resolve().relative_to(ROOT)),"checker_sha256":sha(Path(__file__).resolve()),
        "scope":"Input/file identities, closed oriented control surfaces and actual exported part surfaces. Does not judge shape fidelity, manufacture, collision, mass or dynamics.",
        "mesh_vertices_note":"Export normals/materials split vertices; positional welding is used solely for topology inspection. Multi-material primitives are combined by original named source part.",
        "control_part_count":len(source["parts"]),"export_material_primitive_count":len(loaded.geometry),
        "glb_bound_max_abs_difference_m":bound_error,"binding_errors":errors,"control_mesh_failures":control_bad,"export_mesh_failures":export_bad,
        "render_assets_valid":passed,"appearance_accepted":False,"physics_accepted":False}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report));raise SystemExit(0 if passed else 1)


if __name__=="__main__":main()
