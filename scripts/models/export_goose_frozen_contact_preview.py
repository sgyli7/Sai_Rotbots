"""Export the compiled runtime's actual convex contacts for rotatable review."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import mujoco
import numpy as np
import trimesh


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(a):
    package = a.package.resolve()
    spec = importlib.util.spec_from_file_location("packaged_runtime", package / "runtime_adapter.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    env = module.FrozenPhysics(package)
    env.reset()
    model, data = env.model, env.data
    scene, rows = trimesh.Scene(), []
    for gid in range(model.ngeom):
        if int(model.geom_bodyid[gid]) == 0 or model.geom_type[gid] != mujoco.mjtGeom.mjGEOM_MESH:
            continue
        mid = int(model.geom_dataid[gid])
        begin, count = int(model.mesh_vertadr[mid]), int(model.mesh_vertnum[mid])
        graph = int(model.mesh_graphadr[mid])
        if graph < 0:
            raise ValueError("Compiled collision mesh has no convex support graph")
        support_count, support_triangles = map(int, model.mesh_graph[graph:graph + 2])
        points = model.mesh_vert[begin:begin + count].copy()
        # MuJoCo mesh contacts use their convex support, including when a
        # source file has nonconvex display triangles. Show that actual hull.
        hull = trimesh.convex.convex_hull(points)
        transform = np.eye(4)
        transform[:3, :3] = data.geom_xmat[gid].reshape(3, 3)
        transform[:3, 3] = data.geom_xpos[gid]
        hull.apply_transform(transform)
        hull.visual.vertex_colors = (np.asarray(model.geom_rgba[gid]) * 255).astype(np.uint8)
        name = model.geom(gid).name
        owner = model.body(int(model.geom_bodyid[gid])).name
        hull.metadata.update(runtime_geom=name, owner=owner, units="metres")
        scene.add_geometry(hull, node_name=name, geom_name=name)
        rows.append(dict(name=name, owner=owner, loaded_mesh_vertices=count,
                         actual_convex_support_vertices=support_count,
                         actual_convex_hull_triangles=support_triangles,
                         exported_hull_vertices=len(hull.vertices),
                         world_bounds_m=hull.bounds.tolist()))
    a.output.mkdir(parents=True, exist_ok=True)
    glb, obj = a.output / "runtime_contacts.glb", a.output / "runtime_contacts.obj"
    scene.export(glb)
    scene.to_mesh().export(obj)
    obj.write_text("# units: metres; right-handed +X forward, +Y robot-left, +Z up\n" + obj.read_text())
    bodies = [dict(name=model.body(i).name, mass_kg=float(model.body_mass[i]),
                   centre_of_mass_world_m=data.xipos[i].tolist())
              for i in range(1, model.nbody)]
    receipt = dict(schema="goose_actual_compiled_contact_preview_v1",
                   runtime_model_sha256=sha(package / "robot.xml"),
                   physical_contract_sha256=sha(package / "physical_contract.json"),
                   geometry_source="Compiled MuJoCo mesh convex support at packaged reset; no visual CAD, AI image or painted repair",
                   leaf_count=len(rows), loaded_mesh_vertices=sum(r["loaded_mesh_vertices"] for r in rows),
                   actual_convex_support_vertices=sum(r["actual_convex_support_vertices"] for r in rows),
                   actual_maximum_convex_support_vertices=max(r["actual_convex_support_vertices"] for r in rows),
                   actual_convex_hull_triangles=sum(r["actual_convex_hull_triangles"] for r in rows),
                   support_measurement="MuJoCo3.10 mesh_graph header, independently calibrated on cube/octahedron by benchmark_goose_collision_cost.py",
                   units="metres", axes="right-handed +X forward, +Y robot-left, +Z up",
                   ground_excluded=True, per_body_COM=bodies, geometry=rows,
                   outputs=[dict(file=p.name, sha256=sha(p), bytes=p.stat().st_size) for p in (glb, obj)])
    (a.output / "runtime_contact_preview_manifest.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k not in {"geometry", "per_body_COM"}}, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("package", type=Path)
    p.add_argument("--output", type=Path, required=True)
    main(p.parse_args())
