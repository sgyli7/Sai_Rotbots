"""Read back real native pad faces against a compiled training collision model.

This checks finite support directions and source placement, without modifying
the hardware or model, or using a parent collision proxy as native truth.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import build123d as bd
import mujoco
import numpy as np
from scipy.spatial import ConvexHull


def identity(path):
    p = Path(path).resolve()
    return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())


def run(package, reference):
    contract = json.loads((package/"physical_contract.json").read_text())
    ledger = json.loads((package/"mass_ledger.json").read_text())["items"]
    spec = importlib.util.spec_from_file_location("saved_contact_helpers",package/"verify_contacts.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    model=mujoco.MjModel.from_xml_path(str(package/"robot.xml"))
    data=mujoco.MjData(model)
    helper.pose(model,data,contract,{},root_z=0.)
    delta=np.array([-13.55,0.,32.305])
    angles=np.arange(1440)*2*np.pi/1440
    directions=np.c_[np.cos(angles),np.sin(angles)]
    rows=[]
    failures=[]
    for prefix,face_index,owner,geom in (("upper",1,"head_roll","upper_bill_envelope"),("lower",3,"beak_hinge","lower_bill_envelope")):
        name=prefix+"_grip_cassette_pad"
        source=reference/(name+".brep")
        shape=bd.import_brep(str(source))
        face=list(shape.faces())[face_index]
        raw=np.array([tuple(v.center()) for v in face.vertices()])
        points=raw+delta
        material_row=next(r for r in ledger if r["name"]=="frozen_upper/"+name)
        com_error=float(np.max(abs(np.array(tuple(shape.center(bd.CenterOf.MASS)))+delta-material_row["centre_zero_mm"])))
        mass_error=float(shape.volume*1100e-9-material_row["mass_kg"])
        gid=model.geom(geom).id
        mid=int(model.geom_dataid[gid]);lo=int(model.mesh_vertadr[mid]);count=int(model.mesh_vertnum[mid])
        vv=(model.mesh_vert[lo:lo+count].astype(float)@data.geom_xmat[gid].reshape(3,3).T+data.geom_xpos[gid])*1000
        z=float(vv[:,2].min() if prefix=="upper" else vv[:,2].max())
        coplanar=vv[abs(vv[:,2]-z)<.001]
        exact_h=(points[:,:2]@directions.T).max(0)
        proxy_h=(coplanar[:,:2]@directions.T).max(0)
        differences=exact_h-proxy_h
        native_polygon=ConvexHull(points[:,:2])
        proxy_polygon=ConvexHull(coplanar[:,:2])
        native_is_convex=bool(len(face.wires())==1 and abs(native_polygon.volume-face.area)<1e-4)
        maximum_outside=float((coplanar[:,:2]@native_polygon.equations[:,:2].T+native_polygon.equations[:,2]).max())
        worst=int(np.argmax(differences))
        plane_error=z-float(points[:,2].mean())
        straight=all(edge.geom_type==bd.GeomType.LINE for edge in face.edges())
        passed=bool(shape.is_valid and face.geom_type==bd.GeomType.PLANE and straight and len(points)==8 and native_is_convex
                    and abs(plane_error)<.001 and abs(differences).max()<.05 and com_error<1e-6 and abs(mass_error)<1e-12)
        rows.append(dict(name=name,owner=owner,native=identity(source),native_face_index=face_index,native_strict_valid=shape.is_valid,
                         actual_face_area_mm2=face.area,all8_boundary_edges_straight=straight,
                         native_wire_count=len(face.wires()),native_face_is_convex_without_holes=native_is_convex,
                         native_planar_polygon_area_mm2=native_polygon.volume,proxy_planar_polygon_area_mm2=proxy_polygon.volume,
                         proxy_to_native_contact_area_ratio=proxy_polygon.volume/face.area,
                         maximum_proxy_vertex_outside_native_polygon_mm=maximum_outside,
                         native_original_vertices_mm=raw.tolist(),native_to_current_translation_mm=delta.tolist(),
                         actual_face_world_zero_vertices_mm=points.tolist(),native_plane_world_zero_mm=float(points[:,2].mean()),
                         proxy_plane_world_zero_mm=z,plane_error_mm=plane_error,source_mass_at1100_kg_m3=shape.volume*1100e-9,
                         native_mass_delta_to_frozen_item_kg=mass_error,native_COM_delta_to_frozen_item_max_mm=com_error,
                         maximum1440_direction_contact_edge_support_loss_mm=float(differences.max()),
                         maximum_support_excess_mm=float((-differences).max()),worst_loss_direction_xy=directions[worst].tolist(),
                         limits=dict(plane_error_mm=.001,finite_support_abs_error_mm=.05),passed=passed))
        if not passed:failures.append(name)
    return dict(schema="goose_native_grip_eight_edge_contour_gate_v1",candidate=identity(package/"robot.xml"),
                collision_manifest=identity(package/"collision_manifest.json"),script=identity(__file__),
                actual_assets=[identity(package/r["asset"]) for r in json.loads((package/"collision_manifest.json").read_text())["collision_geometries"]],
                status="PASS_NATIVE_EIGHT_EDGE_FINITE_SUPPORT" if not failures else "REJECT_NATIVE_EIGHT_EDGE_FINITE_SUPPORT",failures=failures,pads=rows,
                reference_scope="Two actual planar native contact faces, all eight straight boundary vertices, zero articulation and1440 directions; original body ownership retained.",
                limitations=["No whole-body native surface or whole-ROM certification.","Source nominal TPU85A/material density is not measured friction or compliance.","Mass/COM matches corroborate adopted identity; saved whole05 surface placement proof is separate."],owned_running_jobs=[])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--package",type=Path,required=True)
    p.add_argument("--native-reference",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    r=run(a.package.resolve(),a.native_reference.resolve())
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2)+"\n")
    print(json.dumps(dict(status=r["status"],failures=r["failures"],output=identity(a.output),pads=[dict(name=x["name"],edge_loss_mm=x["maximum1440_direction_contact_edge_support_loss_mm"],plane_error_mm=x["plane_error_mm"])for x in r["pads"]])))
    raise SystemExit(bool(r["failures"]))


if __name__=="__main__":main()
