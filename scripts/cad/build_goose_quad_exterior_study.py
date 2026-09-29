"""Build a whole-form Goose R2 quad-surface study for appearance review.

This deliberately starts from the selected pointed-bill silhouette rather
than inherited RC2 CAD. It exports closed, editable quad OBJ parts and separate
triangulated *preview* STL files. None of these parts has yet passed mechanical,
packaging, or manufacturing review.
"""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

os.environ.setdefault("MUJOCO_GL", "egl")

import mujoco
import numpy as np
from PIL import Image
from scipy.spatial.transform import Rotation
import trimesh


COLORS = {
    "white": "0.93 0.92 0.89 1",
    "orange": "0.98 0.39 0.025 1",
    "black": "0.045 0.05 0.055 1",
    "dark": "0.12 0.13 0.14 1",
    "metal": "0.37 0.40 0.42 1",
    "lens": "0.008 0.019 0.03 1",
}


@dataclass
class QuadMesh:
    vertices: np.ndarray
    faces: np.ndarray

    def transformed(self, rotation: np.ndarray, translation: tuple[float, ...]) -> QuadMesh:
        return QuadMesh(self.vertices @ rotation.T + np.asarray(translation), self.faces.copy())

    def triangles(self) -> np.ndarray:
        faces = self.faces
        return np.concatenate((faces[:, [0, 1, 2]], faces[:, [0, 2, 3]]), axis=0)

    def orient_outward(self) -> QuadMesh:
        if len(self.faces) == 0:
            raise ValueError("empty mesh")
        uses: dict[tuple[int, int], list[tuple[int, tuple[int, int]]]] = defaultdict(list)
        for face_number, face in enumerate(self.faces):
            for start, end in zip(face, np.roll(face, -1)):
                edge = (int(start), int(end))
                uses[tuple(sorted(edge))].append((face_number, edge))
        neighbors: list[list[tuple[int, bool]]] = [[] for _ in self.faces]
        for edge_uses in uses.values():
            if len(edge_uses) != 2:
                raise ValueError("source quad shell is not a closed manifold")
            (left, left_edge), (right, right_edge) = edge_uses
            same_direction = left_edge == right_edge
            neighbors[left].append((right, same_direction))
            neighbors[right].append((left, same_direction))
        flips: dict[int, bool] = {}
        for first in range(len(self.faces)):
            if first in flips:
                continue
            flips[first] = False
            queue = deque([first])
            while queue:
                current = queue.popleft()
                for neighbor, same_direction in neighbors[current]:
                    desired = flips[current] ^ same_direction
                    if neighbor in flips:
                        if flips[neighbor] != desired:
                            raise ValueError("source quad shell cannot be oriented")
                        continue
                    flips[neighbor] = desired
                    queue.append(neighbor)
        for face_number, flip in flips.items():
            if flip:
                self.faces[face_number] = self.faces[face_number, ::-1]
        triangles = self.triangles()
        signed_volume = trimesh.Trimesh(vertices=self.vertices, faces=triangles,
                                        process=False).volume
        if signed_volume < 0:
            self.faces = self.faces[:, ::-1]
        return self

    def write_obj(self, path: Path) -> None:
        with path.open("w", encoding="utf-8") as target:
            target.write("# Editable closed quad source; millimetres\n")
            for vertex in self.vertices:
                target.write(f"v {vertex[0]:.9f} {vertex[1]:.9f} {vertex[2]:.9f}\n")
            for face in self.faces:
                target.write("f " + " ".join(str(int(index) + 1) for index in face) + "\n")

    def write_stl(self, path: Path) -> None:
        mesh = trimesh.Trimesh(vertices=self.vertices, faces=self.triangles(), process=False)
        mesh.export(path)

    def subdivided(self, iterations: int = 1) -> QuadMesh:
        result = self
        for _ in range(iterations):
            old = result.vertices
            face_points = old[result.faces].mean(axis=1)
            edges: dict[tuple[int, int], list[int]] = defaultdict(list)
            vertex_faces: list[list[int]] = [[] for _ in old]
            vertex_edges: list[set[tuple[int, int]]] = [set() for _ in old]
            for face_number, face in enumerate(result.faces):
                for index, vertex in enumerate(face):
                    vertex_faces[vertex].append(face_number)
                    following = int(face[(index + 1) % 4])
                    edge = tuple(sorted((int(vertex), following)))
                    edges[edge].append(face_number)
                    vertex_edges[vertex].add(edge)
                    vertex_edges[following].add(edge)
            if any(len(uses) != 2 for uses in edges.values()):
                raise ValueError("subdivision requires a closed manifold")
            new_vertices = []
            for vertex_number, point in enumerate(old):
                incident_faces = vertex_faces[vertex_number]
                incident_edges = vertex_edges[vertex_number]
                degree = len(incident_faces)
                face_average = face_points[incident_faces].mean(axis=0)
                edge_average = np.asarray([(old[a] + old[b]) / 2
                                           for a, b in incident_edges]).mean(axis=0)
                new_vertices.append((face_average + 2 * edge_average
                                     + (degree - 3) * point) / degree)
            edge_indices = {}
            for edge, uses in edges.items():
                edge_indices[edge] = len(new_vertices)
                new_vertices.append((old[edge[0]] + old[edge[1]]
                                     + face_points[uses[0]] + face_points[uses[1]]) / 4)
            face_indices = {}
            for face_number, point in enumerate(face_points):
                face_indices[face_number] = len(new_vertices)
                new_vertices.append(point)
            new_faces = []
            for face_number, face in enumerate(result.faces):
                for index, vertex in enumerate(face):
                    prev = int(face[(index - 1) % 4])
                    following = int(face[(index + 1) % 4])
                    new_faces.append((int(vertex),
                                      edge_indices[tuple(sorted((int(vertex), following)))],
                                      face_indices[face_number],
                                      edge_indices[tuple(sorted((prev, int(vertex))))]))
            result = QuadMesh(np.asarray(new_vertices), np.asarray(new_faces, dtype=int))
        return result.orient_outward()


def _finish(vertices: list[tuple[float, ...]], faces: list[tuple[int, ...]]) -> QuadMesh:
    mesh = QuadMesh(np.asarray(vertices, dtype=float), np.asarray(faces, dtype=int))
    return mesh.orient_outward()


def _cube_surface(
    center: tuple[float, float, float],
    extents: tuple[float, float, float],
    count: int,
    projection,
) -> QuadMesh:
    half = np.asarray(extents, dtype=float) / 2
    center_xyz = np.asarray(center, dtype=float)
    vertices: list[tuple[float, ...]] = []
    faces: list[tuple[int, ...]] = []
    lookup: dict[tuple[float, ...], int] = {}
    coordinates = np.linspace(-1, 1, count + 1)
    for axis in range(3):
        other = [value for value in range(3) if value != axis]
        for side in (-1, 1):
            grid = np.zeros((count + 1, count + 1), dtype=int)
            for i, u in enumerate(coordinates):
                for j, v in enumerate(coordinates):
                    unit = np.zeros(3)
                    unit[axis] = side
                    unit[other[0]] = u
                    unit[other[1]] = v
                    point = projection(unit, half) + center_xyz
                    key = tuple(np.round(point, 9))
                    if key not in lookup:
                        lookup[key] = len(vertices)
                        vertices.append(tuple(point))
                    grid[i, j] = lookup[key]
            for i in range(count):
                for j in range(count):
                    face = (grid[i, j], grid[i + 1, j],
                            grid[i + 1, j + 1], grid[i, j + 1])
                    points = np.asarray([vertices[index] for index in face])
                    normal = np.cross(points[1] - points[0], points[2] - points[0])
                    if normal[axis] * side < 0:
                        face = tuple(reversed(face))
                    faces.append(face)
    return _finish(vertices, faces)


def rounded_box(center: tuple[float, float, float],
                extents: tuple[float, float, float], radius: float,
                count: int = 12) -> QuadMesh:
    half = np.asarray(extents, dtype=float) / 2
    if radius <= 0 or radius > min(half):
        raise ValueError("invalid rounded box radius")

    def project(unit: np.ndarray, _: np.ndarray) -> np.ndarray:
        outer = unit * half
        inner = np.clip(outer, -(half - radius), half - radius)
        displacement = outer - inner
        return inner + radius * displacement / np.linalg.norm(displacement)

    return _cube_surface(center, extents, count, project)


def ellipsoid(center: tuple[float, float, float],
              radii: tuple[float, float, float], count: int = 10) -> QuadMesh:
    def project(unit: np.ndarray, _: np.ndarray) -> np.ndarray:
        direction = unit / np.linalg.norm(unit)
        return direction * np.asarray(radii)

    return _cube_surface(center, tuple(2 * value for value in radii), count, project)


def quad_plate(center: tuple[float, float, float],
               axes: tuple[int, int, int],
               size: tuple[float, float, float],
               corner: tuple[float, float], count: int = 12) -> QuadMesh:
    """Rounded planar panel: axes are the two surface axes and the normal."""
    if sorted(axes) != [0, 1, 2] or count < 4:
        raise ValueError("invalid plate axes or subdivision")
    ha, hb, thickness = np.asarray(size, dtype=float) / 2
    ca, cb = corner
    if min(ha, hb, thickness) <= 0 or not (0 <= ca < ha and 0 <= cb < hb):
        raise ValueError("invalid plate dimensions")
    coordinates = np.linspace(-1, 1, count + 1)
    vertices: list[tuple[float, ...]] = []
    grid = np.zeros((2, count + 1, count + 1), dtype=int)
    for side_index, normal in enumerate((-thickness, thickness)):
        for i, u in enumerate(coordinates):
            for j, v in enumerate(coordinates):
                point = np.asarray(center, dtype=float).copy()
                point[axes[0]] += u * (ha - ca * abs(v) ** 4)
                point[axes[1]] += v * (hb - cb * abs(u) ** 4)
                point[axes[2]] += normal
                grid[side_index, i, j] = len(vertices)
                vertices.append(tuple(point))
    faces: list[tuple[int, ...]] = []
    for side_index in (0, 1):
        for i in range(count):
            for j in range(count):
                face = (grid[side_index, i, j], grid[side_index, i + 1, j],
                        grid[side_index, i + 1, j + 1], grid[side_index, i, j + 1])
                faces.append(face if side_index else tuple(reversed(face)))
    perimeter = [(i, 0) for i in range(count)]
    perimeter += [(count, j) for j in range(count)]
    perimeter += [(i, count) for i in range(count, 0, -1)]
    perimeter += [(0, j) for j in range(count, 0, -1)]
    for index, current in enumerate(perimeter):
        following = perimeter[(index + 1) % len(perimeter)]
        faces.append((grid[0, *current], grid[0, *following],
                      grid[1, *following], grid[1, *current]))
    return _finish(vertices, faces)


def conform_to_round_box(mesh: QuadMesh, axis: int, side: int,
                         box_center: tuple[float, float, float],
                         extents: tuple[float, float, float],
                         radius: float, offset: float) -> QuadMesh:
    """Wrap a thin quad plate around a round-box exterior without remeshing."""
    position = mesh.vertices.copy()
    center = np.asarray(box_center, dtype=float)
    inner = np.asarray(extents, dtype=float) / 2 - radius
    other = [value for value in range(3) if value != axis]
    outside = np.maximum(np.abs(position[:, other] - center[other]) - inner[other], 0)
    radial_squared = (outside ** 2).sum(axis=1)
    if np.any(radial_squared >= radius ** 2):
        raise ValueError("plate footprint extends past the rounded box")
    position[:, axis] += center[axis] + side * (
        inner[axis] + np.sqrt(radius ** 2 - radial_squared) + offset)
    return QuadMesh(position, mesh.faces.copy()).orient_outward()


def lofted_bill(rows: list[tuple[float, float, float, float]]) -> QuadMesh:
    """A pointed, articulated bill shell with four-sided cross-sections."""
    vertices: list[tuple[float, ...]] = []
    for x, z, half_width, half_height in rows:
        vertices += [(x, -half_width, z - half_height),
                     (x, half_width, z - half_height),
                     (x, half_width, z + half_height),
                     (x, -half_width, z + half_height)]
    faces: list[tuple[int, ...]] = [(3, 2, 1, 0)]
    for section in range(len(rows) - 1):
        start, end = section * 4, (section + 1) * 4
        for corner in range(4):
            following = (corner + 1) % 4
            faces.append((start + corner, start + following,
                          end + following, end + corner))
    last = (len(rows) - 1) * 4
    faces.append(tuple(last + corner for corner in range(4)))
    return _finish(vertices, faces)


def fairing_between(start: tuple[float, float, float],
                    end: tuple[float, float, float],
                    width: float, depth: float, radius: float) -> QuadMesh:
    direction = np.asarray(end, dtype=float) - np.asarray(start, dtype=float)
    length = np.linalg.norm(direction)
    rotation, _ = Rotation.align_vectors([direction / length], [[0, 0, 1]])
    shape = rounded_box((0, 0, 0), (width, depth, length), radius, count=10)
    return shape.transformed(rotation.as_matrix(), tuple((np.asarray(start) + end) / 2))


def build_parts() -> list[tuple[str, str, QuadMesh]]:
    parts: list[tuple[str, str, QuadMesh]] = []

    def add(name: str, color: str, mesh: QuadMesh) -> None:
        parts.append((name, color, mesh))

    # Whole-body proportions are provisional and must later be reconciled with
    # real battery, motor, linkage, and joint package volumes.
    body_center = (-10, 0, 290)
    body_size = (282, 190, 184)
    body_radius = 60
    add("body_shell", "white", rounded_box(body_center, body_size, body_radius))
    add("body_undertray", "black", ellipsoid((-10, 0, 200), (126, 81, 13)))
    add("body_button", "orange", ellipsoid((-87, 0, 384), (9, 9, 3)))
    for side in (-1, 1):
        add(f"wing_door_seam_{side}", "dark",
            conform_to_round_box(quad_plate((-43, 0, 293), (0, 2, 1),
                                            (165, 87, 1.6), (14, 13)),
                                 1, side, body_center, body_size, body_radius, 0.55))
        add(f"wing_service_door_{side}", "white",
            conform_to_round_box(quad_plate((-43, 0, 293), (0, 2, 1),
                                            (162, 84, 2.0), (13, 12)),
                                 1, side, body_center, body_size, body_radius, 1.45))
        add(f"hip_joint_{side}", "black", ellipsoid((-10, side * 89, 229), (27, 24, 27)))
        add(f"hip_rim_{side}", "metal", ellipsoid((-10, side * 107, 229), (18, 5, 18)))
        add(f"hip_center_{side}", "orange", ellipsoid((-10, side * 112, 229), (10, 3, 10)))

    add("neck_root", "black", ellipsoid((46, 0, 405), (25, 26, 25)))
    for side in (-1, 1):
        add(f"neck_root_rim_{side}", "metal",
            ellipsoid((46, side * 25, 405), (17, 3, 17)))
        add(f"neck_root_center_{side}", "orange",
            ellipsoid((46, side * 28, 405), (9, 2, 9)))
    add("neck_lower_back", "black", fairing_between((39, 0, 405), (-17, 0, 516), 19, 24, 9))
    add("neck_lower", "white", fairing_between((48, 0, 415), (-7, 0, 521), 38, 34, 14))
    add("neck_elbow", "black", ellipsoid((-10, 0, 520), (23, 27, 23)))
    add("neck_elbow_rim_left", "metal", ellipsoid((-10, -28, 520), (16, 3, 16)))
    add("neck_elbow_rim_right", "metal", ellipsoid((-10, 28, 520), (16, 3, 16)))
    add("neck_upper_back", "black", fairing_between((-14, 0, 523), (53, 0, 609), 19, 24, 9))
    add("neck_upper", "white", fairing_between((-2, 0, 528), (63, 0, 610), 36, 33, 13))
    add("head_yoke", "black", ellipsoid((60, 0, 610), (23, 27, 23)))

    head_center = (119, 0, 590)
    head_size = (114, 88, 92)
    head_radius = 29
    add("head_shell", "white", rounded_box(head_center, head_size, head_radius))
    add("camera_panel", "black",
        conform_to_round_box(quad_plate((0, 0, 590), (1, 2, 0),
                                        (65, 60, 2.5), (10, 9)),
                             0, 1, head_center, head_size, head_radius, 1.0))
    add("camera_ring", "orange", ellipsoid((179, 0, 588), (4, 24, 24)))
    add("camera_lens", "lens", ellipsoid((184, 0, 588), (4, 19, 19)))
    add("camera_glass", "dark", ellipsoid((187, 0, 588), (1.5, 13, 13)))
    for side in (-1, 1):
        add(f"beak_hinge_{side}", "orange", ellipsoid((171, side * 34, 545), (14, 4, 14)))
        add(f"head_side_port_{side}", "black", ellipsoid((115, side * 44, 590), (3, 1.3, 3)))
    add("beak_upper", "orange", lofted_bill([
        (168, 552, 23, 15), (175, 553, 24, 15), (198, 551, 24, 14),
        (223, 547, 22, 12), (256, 541, 16, 8), (284, 537, 8, 4), (297, 535, 3, 2),
    ]).subdivided(2))
    add("beak_lower", "orange", lofted_bill([
        (169, 526, 21, 8), (178, 527, 22, 8), (213, 527, 21, 7),
        (253, 527, 15, 5), (283, 529, 8, 3), (296, 531, 3, 1.5),
    ]).subdivided(2))
    add("beak_nostril", "black", ellipsoid((218, 0, 561), (4, 2.5, 1)))

    for side in (-1, 1):
        y = side * 86
        hip, knee, ankle = (-10, y, 229), (-38, y, 135), (-5, y, 52)
        add(f"thigh_back_{side}", "black", fairing_between(hip, knee, 29, 33, 12))
        add(f"thigh_shell_{side}", "white", fairing_between(hip, knee, 41, 39, 15))
        add(f"knee_joint_{side}", "black", ellipsoid(knee, (21, 23, 21)))
        add(f"knee_rim_{side}", "metal", ellipsoid((knee[0], y + side * 20, knee[2]), (14, 4, 14)))
        add(f"knee_center_{side}", "orange", ellipsoid((knee[0], y + side * 24, knee[2]), (8, 2, 8)))
        add(f"shin_back_{side}", "black", fairing_between(knee, ankle, 27, 31, 11))
        add(f"shin_shell_{side}", "white", fairing_between(knee, ankle, 38, 37, 14))
        add(f"ankle_joint_{side}", "black", ellipsoid(ankle, (20, 22, 20)))
        add(f"ankle_rim_{side}", "metal", ellipsoid((ankle[0], y + side * 18, ankle[2]), (13, 3, 13)))
        add(f"ankle_center_{side}", "orange", ellipsoid((ankle[0], y + side * 21, ankle[2]), (7, 2, 7)))
        add(f"foot_sole_{side}", "black", quad_plate((10, y, 6), (0, 1, 2),
                                                       (184, 88, 11), (25, 17)))
        add(f"foot_orange_rim_{side}", "orange", quad_plate((10, y, 13), (0, 1, 2),
                                                              (180, 84, 5), (24, 16)))
        add(f"foot_white_deck_{side}", "white", quad_plate((10, y, 23), (0, 1, 2),
                                                             (173, 79, 15), (22, 15)))
        add(f"foot_toe_pad_{side}", "orange", quad_plate((62, y, 31.3), (0, 1, 2),
                                                          (39, 44, 1.2), (5, 5)))
    return parts


def render(parts: list[tuple[str, str, QuadMesh]], directory: Path) -> None:
    xml = ET.Element("mujoco", model="goose_quad_exterior_study")
    ET.SubElement(xml, "compiler", angle="radian")
    visual = ET.SubElement(xml, "visual")
    ET.SubElement(visual, "headlight", ambient=".26 .26 .26",
                  diffuse=".7 .7 .7", specular=".2 .2 .2")
    assets = ET.SubElement(xml, "asset")
    ET.SubElement(assets, "texture", type="skybox", builtin="gradient",
                  rgb1=".94 .94 .93", rgb2=".78 .79 .79", width="512", height="3072")
    for color, rgba in COLORS.items():
        ET.SubElement(assets, "material", name=f"mat_{color}", rgba=rgba,
                      specular=".5", shininess=".55")
    for name, _, _ in parts:
        ET.SubElement(assets, "mesh", name=name, file=f"{name}.stl", scale=".001 .001 .001")
    world = ET.SubElement(xml, "worldbody")
    ET.SubElement(world, "light", pos="-1 -1 2", dir=".4 .4 -1", diffuse=".8 .8 .8")
    ET.SubElement(world, "geom", name="floor", type="plane", size="2 2 .1",
                  rgba=".79 .79 .77 1")
    for name, color, _ in parts:
        ET.SubElement(world, "geom", name=name, type="mesh", mesh=name,
                      material=f"mat_{color}", contype="0", conaffinity="0")
    path = directory / "appearance.xml"
    ET.ElementTree(xml).write(path, encoding="unicode")
    model = mujoco.MjModel.from_xml_path(str(path))
    model.vis.global_.offwidth = 1000
    model.vis.global_.offheight = 1000
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    bounds = np.asarray([mesh.vertices for _, _, mesh in parts], dtype=object)
    lower = np.min(np.vstack(bounds), axis=0)
    upper = np.max(np.vstack(bounds), axis=0)
    renderer = mujoco.Renderer(model, width=1000, height=1000)
    for name, azimuth, elevation in (("side", 90, -7), ("three_quarter", 125, -7),
                                     ("front", 180, -7), ("rear", 0, -7)):
        camera = mujoco.MjvCamera()
        camera.lookat[:] = (lower + upper) / 2000
        camera.distance = max(upper - lower) / 1000 * 1.55
        camera.azimuth = azimuth
        camera.elevation = elevation
        camera.orthographic = True
        renderer.update_scene(data, camera=camera)
        Image.fromarray(renderer.render()).save(directory / f"{name}.png")
    renderer.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=Path("artifacts/Goose_V0.1/quad_exterior_study"))
    args = parser.parse_args()
    output = args.output.resolve()
    source = output / "quad_source"
    source.mkdir(parents=True, exist_ok=True)
    parts = build_parts()
    records = []
    for name, color, mesh in parts:
        mesh.write_obj(source / f"{name}.obj")
        mesh.write_stl(output / f"{name}.stl")
        triangle_mesh = trimesh.Trimesh(vertices=mesh.vertices, faces=mesh.triangles(), process=False)
        records.append({"name": name, "color": color, "quad_faces": len(mesh.faces),
                        "closed_after_triangulation": bool(triangle_mesh.is_watertight),
                        "bbox_mm": np.round(np.ptp(mesh.vertices, axis=0), 3).tolist()})
    render(parts, output)
    report = {"status": "appearance_only_unapproved", "appearance_review_pass": False,
              "physics_pass": False, "manufacturing_pass": False,
              "coordinate_unit": "mm", "parts": records}
    (output / "manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "parts": len(parts),
                      "all_triangulated_closed": all(item["closed_after_triangulation"] for item in records)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
