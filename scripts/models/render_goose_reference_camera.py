#!/usr/bin/env python3
"""Render saved Goose GLB triangles in an explicit reference-photo camera.

Requires Python, NumPy, Pillow, and g++ or clang++. No CAD engine, display, or GPU
is needed. A small embedded C++ depth-buffer rasterizer is compiled in a temporary
directory and removed after the render. It never changes the mesh or fits a camera.

GLB scene transforms are applied in glTF metres, then converted to Goose native
millimetres: [X, Y, Z] = 1000 * [gltf_x, -gltf_z, gltf_y]. The camera uses these
native coordinates, with camera rows x-right, y-down, z-forward.

Perspective camera JSON:
  {"kind": "perspective", "world_to_camera_rotation": [[...], [...], [...]],
   "position_mm": [...], "focal_length_px": 1877,
   "principal_point_px": [171, 224], "calibrated": false}
Orthographic camera JSON:
  {"kind": "orthographic", "matrix_2x4": [[...], [...]]}

Camera pixels refer to the original 342 x 448 viewport. --width/--height scale
both axes equally; omitted dimensions are derived. Use e.g. 684 x 896. Optional
camera "viewport_px": [width, height] declares a different base viewport.

Only static opaque triangle primitives and stored base/vertex colours are supported.
Unsupported skins, morphs, compressed accessors, textures, or transparent materials
fail explicitly. Lighting is a diagnostic Lambert model, not a photograph or full
PBR simulation. Every render writes a unique timestamped SHA256 receipt beside PNG.

Example:
  python3 scripts/models/render_goose_reference_camera.py \
    --input robots/goose_v0_2/cad/exports/tangpa_side_mount_study_14/lower_body_with_neck_datum.glb \
    --camera artifacts/goose_v0_2/tangpa_macro_reconstruction_18/conditional_camera.json \
    --output artifacts/goose_v0_2/tangpa_macro_reconstruction_18/reference_camera.png
"""

from __future__ import annotations

import argparse
import ctypes
import datetime as dt
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import uuid

import numpy as np
from PIL import Image


RASTERIZER_CPP = r"""
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>

struct Vertex { double a[9]; }; // screen x/y, positive camera depth, normal, RGB

static void raster_triangle(const Vertex* p, int width, int height, bool perspective,
                            double* depth, unsigned char* image, uint64_t* stats) {
    const double area = (p[1].a[0]-p[0].a[0])*(p[2].a[1]-p[0].a[1])
                      - (p[1].a[1]-p[0].a[1])*(p[2].a[0]-p[0].a[0]);
    if (!std::isfinite(area) || std::abs(area)<1e-12) { ++stats[2]; return; }
    double minx = std::min({p[0].a[0],p[1].a[0],p[2].a[0]});
    double maxx = std::max({p[0].a[0],p[1].a[0],p[2].a[0]});
    double miny = std::min({p[0].a[1],p[1].a[1],p[2].a[1]});
    double maxy = std::max({p[0].a[1],p[1].a[1],p[2].a[1]});
    if (maxx<0.5 || maxy<0.5 || minx>width-0.5 || miny>height-0.5) return;
    const int x0=(int)std::ceil(std::max(0.0,minx-0.5));
    const int x1=(int)std::floor(std::min((double)width-1,maxx-0.5));
    const int y0=(int)std::ceil(std::max(0.0,miny-0.5));
    const int y1=(int)std::floor(std::min((double)height-1,maxy-0.5));
    if (x1<x0 || y1<y0) return;
    ++stats[1];
    const double lx=-0.3713906763541037, ly=-0.5570860145311556, lz=-0.7427813527082074;
    for(int y=y0;y<=y1;++y) for(int x=x0;x<=x1;++x) {
        const double px=x+0.5, py=y+0.5;
        double w[3];
        w[0]=((p[1].a[0]-px)*(p[2].a[1]-py)-(p[1].a[1]-py)*(p[2].a[0]-px))/area;
        w[1]=((p[2].a[0]-px)*(p[0].a[1]-py)-(p[2].a[1]-py)*(p[0].a[0]-px))/area;
        w[2]=1-w[0]-w[1];
        if(w[0]<-1e-9 || w[1]<-1e-9 || w[2]<-1e-9) continue;
        double z;
        if(perspective) {
            for(int i=0;i<3;++i) w[i]/=p[i].a[2];
            const double sum=w[0]+w[1]+w[2];
            if(sum<=0 || !std::isfinite(sum)) continue;
            z=1/sum; for(int i=0;i<3;++i) w[i]/=sum;
        } else z=w[0]*p[0].a[2]+w[1]*p[1].a[2]+w[2]*p[2].a[2];
        const size_t idx=(size_t)y*width+x;
        if(z>=depth[idx]) continue;
        depth[idx]=z;
        double n[3]={0,0,0};
        for(int c=0;c<3;++c) for(int i=0;i<3;++i) n[c]+=w[i]*p[i].a[3+c];
        const double len=std::sqrt(n[0]*n[0]+n[1]*n[1]+n[2]*n[2]);
        if(len>1e-14) for(int c=0;c<3;++c) n[c]/=len;
        // Both sides are rasterized so cut mouths/interiors remain visible.
        if(n[2]>0) for(int c=0;c<3;++c) n[c]=-n[c];
        const double light=0.50+0.50*std::max(0.0,n[0]*lx+n[1]*ly+n[2]*lz);
        for(int c=0;c<3;++c) {
            double col=0; for(int i=0;i<3;++i) col+=w[i]*p[i].a[6+c];
            col=std::clamp(col*light,0.0,1.0);
            const double srgb=col<=0.0031308 ? 12.92*col : 1.055*std::pow(col,1/2.4)-0.055;
            image[idx*3+c]=(unsigned char)std::lround(255*std::clamp(srgb,0.0,1.0));
        }
        ++stats[3];
    }
}

extern "C" void render_mesh(const double* vertices, const uint32_t* indices, uint64_t triangles,
                            int width, int height, int perspective, double focal,
                            double cx, double cy, double near_plane, double* depth,
                            unsigned char* image, uint64_t* stats) {
    for(uint64_t t=0;t<triangles;++t) {
        ++stats[0];
        Vertex orig[3];
        for(int i=0;i<3;++i) for(int k=0;k<9;++k) orig[i].a[k]=vertices[(size_t)indices[t*3+i]*9+k];
        Vertex clipped[5]; int count=0;
        if(perspective) {
            // Clip the actual camera-space triangle to z >= near_plane.
            for(int i=0;i<3;++i) {
                const Vertex &a=orig[i], &b=orig[(i+1)%3];
                const bool ain=a.a[2]>=near_plane, bin=b.a[2]>=near_plane;
                if(ain) clipped[count++]=a;
                if(ain!=bin) {
                    const double u=(near_plane-a.a[2])/(b.a[2]-a.a[2]);
                    Vertex v; for(int k=0;k<9;++k) v.a[k]=a.a[k]+u*(b.a[k]-a.a[k]);
                    v.a[2]=near_plane; clipped[count++]=v;
                }
            }
            if(count!=3) ++stats[4];
            for(int i=0;i<count;++i) {
                clipped[i].a[0]=cx+focal*clipped[i].a[0]/clipped[i].a[2];
                clipped[i].a[1]=cy+focal*clipped[i].a[1]/clipped[i].a[2];
            }
        } else { count=3; for(int i=0;i<3;++i) clipped[i]=orig[i]; }
        for(int i=1;i+1<count;++i) {
            const Vertex tri[3]={clipped[0],clipped[i],clipped[i+1]};
            raster_triangle(tri,width,height,perspective!=0,depth,image,stats);
        }
    }
}
"""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def finite_array(value, shape, label: str) -> np.ndarray:
    arr = np.asarray(value, dtype=np.float64)
    if arr.shape != shape or not np.isfinite(arr).all():
        raise ValueError(f"{label} must be a finite array of shape {shape}")
    return arr


def load_glb(data: bytes):
    if len(data) < 20 or data[:4] != b"glTF":
        raise ValueError("Input must be a binary glTF 2.0 GLB")
    version, length = struct.unpack_from("<II", data, 4)
    if version != 2 or length != len(data):
        raise ValueError("GLB version/declared length does not match its bytes")
    offset, document, binary = 12, None, None
    while offset < length:
        size, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        chunk = data[offset:offset + size]
        if len(chunk) != size:
            raise ValueError("Truncated GLB chunk")
        if kind == 0x4E4F534A:
            document = json.loads(chunk)
        elif kind == 0x004E4942:
            binary = chunk
        offset += size
    if document is None or binary is None:
        raise ValueError("GLB must have JSON and BIN chunks")
    if document.get("skins") or document.get("animations"):
        raise ValueError("Only saved static scene geometry is supported")
    buffers = document.get("buffers", [])
    if len(buffers) != 1 or "uri" in buffers[0]:
        raise ValueError("External/multiple buffers are not supported")

    def accessor(index):
        a = document["accessors"][index]
        if "sparse" in a or "bufferView" not in a:
            raise ValueError("Sparse/implicit accessors are not supported")
        view = document["bufferViews"][a["bufferView"]]
        if view.get("buffer", 0) != 0 or view.get("extensions"):
            raise ValueError("Compressed or external buffer views are not supported")
        components = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}
        types = {5120: "i1", 5121: "u1", 5122: "<i2", 5123: "<u2", 5125: "<u4", 5126: "<f4"}
        if a["type"] not in components or a["componentType"] not in types:
            raise ValueError("Unsupported accessor type")
        dtype = np.dtype(types[a["componentType"]])
        count, cols = a["count"], components[a["type"]]
        stride = view.get("byteStride", cols * dtype.itemsize)
        start = view.get("byteOffset", 0) + a.get("byteOffset", 0)
        end = start + max(0, count - 1) * stride + cols * dtype.itemsize
        if stride < cols * dtype.itemsize or end > view.get("byteOffset", 0) + view["byteLength"] or end > len(binary):
            raise ValueError("Accessor exceeds its buffer view")
        result = np.ndarray((count, cols), dtype=dtype, buffer=binary, offset=start,
                            strides=(stride, dtype.itemsize)).copy()
        if a.get("normalized") and dtype.kind in "iu":
            info = np.iinfo(dtype)
            result = result.astype(np.float64) / info.max
            if dtype.kind == "i":
                result = np.maximum(result, -1)
        return result

    def local_transform(node):
        if "matrix" in node:
            return finite_array(node["matrix"], (16,), "node matrix").reshape(4, 4, order="F")
        q = finite_array(node.get("rotation", [0, 0, 0, 1]), (4,), "node rotation")
        if not math.isclose(float(q @ q), 1, abs_tol=1e-4):
            raise ValueError("Node quaternion must be normalized")
        x, y, z, w = q
        rot = np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                        [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                        [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
        mat = np.eye(4)
        mat[:3, :3] = rot @ np.diag(finite_array(node.get("scale", [1, 1, 1]), (3,), "node scale"))
        mat[:3, 3] = finite_array(node.get("translation", [0, 0, 0]), (3,), "node translation")
        return mat

    basis = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=np.float64)
    primitives = []
    scene = document["scenes"][document.get("scene", 0)]

    def visit(index, parent, ancestry):
        if index in ancestry:
            raise ValueError("GLB node hierarchy contains a cycle")
        node = document["nodes"][index]
        world = parent @ local_transform(node)
        if not np.allclose(world[3], [0, 0, 0, 1], atol=1e-10):
            raise ValueError("GLB node transform must be affine")
        if "mesh" in node:
            mesh = document["meshes"][node["mesh"]]
            for number, prim in enumerate(mesh["primitives"]):
                if prim.get("mode", 4) != 4 or prim.get("targets") or prim.get("extensions"):
                    raise ValueError("Only uncompressed static TRIANGLES primitives are supported")
                attrs = prim["attributes"]
                raw = accessor(attrs["POSITION"]).astype(np.float64)
                if raw.shape[1] != 3 or not np.isfinite(raw).all():
                    raise ValueError("POSITION accessor must contain finite VEC3 vertices")
                vertices = (raw @ world[:3, :3].T + world[:3, 3]) @ basis.T * 1000
                indices = accessor(prim["indices"]).reshape(-1) if "indices" in prim else np.arange(len(raw), dtype=np.uint32)
                if indices.dtype.kind not in "iu" or len(indices) % 3 or (len(indices) and (indices.min() < 0 or indices.max() >= len(raw))):
                    raise ValueError("Triangle indices must refer to original saved vertices")
                indices = indices.astype(np.uint32).reshape(-1, 3)
                if "NORMAL" in attrs:
                    normals = accessor(attrs["NORMAL"]).astype(np.float64)
                    if normals.shape != raw.shape or not np.isfinite(normals).all():
                        raise ValueError("NORMAL accessor does not match POSITION")
                    normals = (normals @ np.linalg.inv(world[:3, :3])) @ basis.T
                    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-14)
                    normal_source = "saved GLB vertex normals; inverse transpose node transform"
                else:
                    # Flat normals duplicate only render vertices; original faces/positions are identical.
                    vertices = vertices[indices.reshape(-1)]
                    tri = vertices.reshape(-1, 3, 3)
                    face_normals = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
                    face_normals /= np.maximum(np.linalg.norm(face_normals, axis=1, keepdims=True), 1e-14)
                    normals = np.repeat(face_normals, 3, axis=0)
                    indices = np.arange(len(vertices), dtype=np.uint32).reshape(-1, 3)
                    normal_source = "flat normals derived from saved triangles"
                materials = document.get("materials", [])
                material = materials[prim["material"]] if "material" in prim else {}
                pbr = material.get("pbrMetallicRoughness", {})
                if material.get("alphaMode", "OPAQUE") != "OPAQUE" or "baseColorTexture" in pbr:
                    raise ValueError("Transparent/textured base colour is unsupported; refusing to silently replace it")
                colour = finite_array(pbr.get("baseColorFactor", [1, 1, 1, 1]), (4,), "baseColorFactor")
                colours = np.broadcast_to(colour[:3], normals.shape).copy()
                if "COLOR_0" in attrs:
                    vc = accessor(attrs["COLOR_0"]).astype(np.float64)
                    if vc.shape[0] != len(raw) or vc.shape[1] not in (3, 4):
                        raise ValueError("COLOR_0 does not match POSITION")
                    if "NORMAL" not in attrs:
                        original_indices = accessor(prim["indices"]).reshape(-1) if "indices" in prim else np.arange(len(raw))
                        vc = vc[original_indices]
                    colours *= vc[:, :3]
                if not np.isfinite(colours).all():
                    raise ValueError("Material/vertex colours must be finite")
                primitives.append({"name": node.get("name", str(index)), "primitive": number,
                                   "vertices": vertices, "normals": normals, "indices": indices,
                                   "colours": colours, "normal_source": normal_source,
                                   "material_name": material.get("name"),
                                   "world_bounds_native_mm": [vertices.min(0).tolist(), vertices.max(0).tolist()]})
        for child in node.get("children", []):
            visit(child, world, ancestry | {index})

    for node in scene.get("nodes", []):
        visit(node, np.eye(4), set())
    if not primitives:
        raise ValueError("GLB active scene has no triangle geometry")
    return primitives


class Rasterizer:
    def __init__(self, directory: str):
        compiler = shutil.which("g++") or shutil.which("clang++")
        if not compiler:
            raise RuntimeError("g++ or clang++ is required for the offline triangle rasterizer")
        library = Path(directory) / ("rasterizer.dylib" if sys.platform == "darwin" else "rasterizer.so")
        command = [compiler, "-x", "c++", "-std=c++17", "-O3", "-shared", "-fPIC", "-", "-o", str(library)]
        result = subprocess.run(command, input=RASTERIZER_CPP, text=True, capture_output=True, check=False)
        if result.returncode:
            raise RuntimeError("Rasterizer compilation failed: " + result.stderr.strip())
        self.compiler = compiler
        self.source_sha256 = sha256(RASTERIZER_CPP.encode())
        self.library = ctypes.CDLL(str(library))
        self.function = self.library.render_mesh
        ptr = ctypes.c_void_p
        self.function.argtypes = [ptr, ptr, ctypes.c_uint64, ctypes.c_int, ctypes.c_int,
                                  ctypes.c_int, ctypes.c_double, ctypes.c_double, ctypes.c_double,
                                  ctypes.c_double, ptr, ptr, ptr]
        self.function.restype = None

    def draw(self, attributes, indices, image, depth, perspective, focal, principal, near, stats):
        attrs = np.ascontiguousarray(attributes, dtype=np.float64)
        inds = np.ascontiguousarray(indices, dtype=np.uint32)
        self.function(attrs.ctypes.data, inds.ctypes.data, len(inds), image.shape[1], image.shape[0],
                      int(perspective), focal, *principal, near,
                      depth.ctypes.data, image.ctypes.data, stats.ctypes.data)


def render(primitives, camera, width, height, supersample, near, rasterizer):
    base = finite_array(camera.get("viewport_px", [342, 448]), (2,), "viewport_px")
    if (base <= 0).any():
        raise ValueError("Base viewport dimensions must be positive")
    scale = width / base[0]
    if not math.isclose(height / base[1], scale, rel_tol=1e-10):
        raise ValueError("Output width/height must have exactly the camera viewport aspect ratio")
    raster_scale = scale * supersample
    perspective = camera.get("kind") == "perspective"
    if perspective:
        rotation = finite_array(camera["world_to_camera_rotation"], (3, 3), "world_to_camera_rotation")
        if not np.allclose(rotation @ rotation.T, np.eye(3), atol=1e-5) or not math.isclose(float(np.linalg.det(rotation)), 1, abs_tol=1e-5):
            raise ValueError("Camera rotation must be right-handed orthonormal rows xright/ydown/zforward")
        position = finite_array(camera["position_mm"], (3,), "position_mm")
        focal = float(camera["focal_length_px"]) * raster_scale
        principal = finite_array(camera["principal_point_px"], (2,), "principal_point_px") * raster_scale
        if not math.isfinite(focal) or focal <= 0:
            raise ValueError("focal_length_px must be positive")
        depth_offset = 0
    elif camera.get("kind") == "orthographic":
        matrix = finite_array(camera["matrix_2x4"], (2, 4), "matrix_2x4")
        rows = matrix[:, :3]
        lens = np.linalg.norm(rows, axis=1)
        if min(lens) <= 0:
            raise ValueError("Orthographic rows must span a camera plane")
        xy = rows / lens[:, None]
        if abs(float(xy[0] @ xy[1])) > 1e-5:
            raise ValueError("Orthographic rows must be perpendicular, without shear")
        rotation = np.vstack([xy, np.cross(xy[0], xy[1])])
        all_min = min(float((p["vertices"] @ rotation[2]).min()) for p in primitives)
        depth_offset = 1 - all_min
        focal, principal = 0., [0., 0.]
    else:
        raise ValueError("Camera kind must be perspective or orthographic")
    image = np.full((height * supersample, width * supersample, 3), 248, dtype=np.uint8)
    depth = np.full(image.shape[:2], np.inf, dtype=np.float64)
    stats = np.zeros(5, dtype=np.uint64)
    details = []
    for part in primitives:
        vertices = part["vertices"]
        if perspective:
            projected = (vertices - position) @ rotation.T
        else:
            projected = np.column_stack([vertices @ matrix[:, :3].T + matrix[:, 3],
                                         vertices @ rotation[2] + depth_offset])
            projected[:, :2] *= raster_scale
        normals = part["normals"] @ rotation.T
        attrs = np.column_stack([projected, normals, part["colours"]])
        rasterizer.draw(attrs, part["indices"], image, depth, perspective, focal, principal, near, stats)
        details.append({k: v for k, v in part.items() if k not in {"vertices", "normals", "indices", "colours"}} |
                       {"triangle_count": len(part["indices"]), "render_vertex_count": len(vertices)})
    covered = np.isfinite(depth)
    yy, xx = np.nonzero(covered)
    bbox = [int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1] if len(xx) else None
    output = Image.fromarray(image)
    if supersample > 1:
        output = output.resize((width, height), Image.Resampling.LANCZOS)
    metrics = {"triangles_submitted": int(stats[0]), "triangles_with_pixel_bounds": int(stats[1]),
               "degenerate_triangles": int(stats[2]), "depth_buffer_writes": int(stats[3]),
               "triangles_clipped_or_rejected_at_near_plane": int(stats[4]),
               "covered_raster_pixels": int(covered.sum()), "covered_raster_bbox_xyxy": bbox,
               "minimum_visible_depth_native_mm": float(depth[covered].min()) if covered.any() else None,
               "maximum_visible_depth_native_mm": float(depth[covered].max()) if covered.any() else None,
               "orthographic_depth_offset_native_mm": depth_offset}
    return output, metrics, details


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, type=Path, help="Saved static Goose GLB")
    parser.add_argument("--camera", required=True, type=Path, help="Explicit camera JSON")
    parser.add_argument("--output", required=True, type=Path, help="Output PNG path")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--supersample", type=int, default=2, help="Antialias samples per axis (default 2)")
    parser.add_argument("--near-mm", type=float, default=0.1, help="Perspective near-plane depth in native mm")
    args = parser.parse_args()
    started = time.perf_counter()
    input_path, camera_path, output_path = (p.expanduser().resolve() for p in (args.input, args.camera, args.output))
    script_path = Path(__file__).resolve()
    if output_path.suffix.lower() != ".png" or output_path in {input_path, camera_path, script_path}:
        raise ValueError("Output must be a distinct PNG path")
    if not 1 <= args.supersample <= 8 or not math.isfinite(args.near_mm) or args.near_mm <= 0:
        raise ValueError("supersample must be 1..8 and near-mm must be positive")
    glb_bytes, camera_bytes, script_bytes = input_path.read_bytes(), camera_path.read_bytes(), script_path.read_bytes()
    camera = json.loads(camera_bytes)
    base = finite_array(camera.get("viewport_px", [342, 448]), (2,), "viewport_px")
    width, height = args.width, args.height
    if width is None and height is None:
        width, height = (int(v) for v in base)
    elif width is None:
        width = round(height * base[0] / base[1])
    elif height is None:
        height = round(width * base[1] / base[0])
    if min(width, height) <= 0 or max(width, height) * args.supersample > 16384:
        raise ValueError("Output dimensions must be positive and raster dimensions <=16384")
    primitives = load_glb(glb_bytes)
    with tempfile.TemporaryDirectory(prefix="goose_reference_raster_") as temporary:
        renderer = Rasterizer(temporary)
        output, metrics, parts = render(primitives, camera, width, height, args.supersample, args.near_mm, renderer)
        compiler, native_hash = renderer.compiler, renderer.source_sha256
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # PNG replacement is atomic; unique receipts preserve every invocation's identities.
    temporary_png = output_path.with_name(f".{output_path.name}.{uuid.uuid4().hex}.tmp")
    encoded = io.BytesIO()
    output.save(encoded, format="PNG")
    output_bytes = encoded.getvalue()
    try:
        temporary_png.write_bytes(output_bytes)
        os.replace(temporary_png, output_path)
    finally:
        temporary_png.unlink(missing_ok=True)
    now = dt.datetime.now(dt.timezone.utc)
    run_id = now.strftime("%Y%m%d_%H%M%S_%f") + "_" + uuid.uuid4().hex[:8]
    receipt_path = output_path.with_name(f"{output_path.stem}_{run_id}.receipt.json")
    inputs = {}
    for label, path, data in [("glb", input_path, glb_bytes), ("camera", camera_path, camera_bytes), ("script", script_path, script_bytes)]:
        inputs[label] = {"path": str(path), "sha256": sha256(data), "bytes": len(data),
                         "live_file_after_render_matches_read_bytes": path.exists() and sha256(path.read_bytes()) == sha256(data)}
    receipt = {"schema": "goose_saved_glb_reference_camera_triangle_render_v1",
               "run_id": run_id, "created_utc": now.isoformat(), "input_identities": inputs,
               "camera_used": camera, "camera_calibrated": camera.get("calibrated", False),
               "geometry": {"native_from_gltf_metres": "[x,-z,y]*1000; all saved scene node transforms applied",
                            "saved_triangle_positions_or_indices_deformed": False,
                            "mesh_or_pose_fitting_performed": False, "primitive_count": len(parts), "parts": parts},
               "renderer": {"algorithm": "actual triangles; nearest Z-buffer; perspective-correct depth/normal/colour interpolation; near-plane clipping",
                            "lighting": "diagnostic Lambert ambient0.5 + diffuse0.5; linear base/vertex RGB to sRGB",
                            "occlusion": "per sample nearest saved surface, both face sides; no shadows/AO/PBR textures",
                            "native_compiler": compiler, "embedded_cpp_sha256": native_hash,
                            "background_srgb": [248, 248, 248], "supersample_per_axis": args.supersample,
                            "near_plane_native_mm": args.near_mm, "base_viewport_px": base.tolist(),
                            "output_scale_from_base": width / base[0]},
               "metrics": metrics,
               "output": {"path": str(output_path), "sha256": sha256(output_bytes),
                          "bytes": len(output_bytes), "size_px": [width, height],
                          "live_file_after_render_matches_encoded_bytes": sha256(output_path.read_bytes()) == sha256(output_bytes)},
               "elapsed_seconds": time.perf_counter() - started}
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(output_path), "receipt": str(receipt_path),
                      "triangles": metrics["triangles_submitted"], "sha256": receipt["output"]["sha256"]}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, KeyError, OSError, json.JSONDecodeError) as error:
        print(f"reference camera render failed: {error}", file=sys.stderr)
        raise SystemExit(2)
