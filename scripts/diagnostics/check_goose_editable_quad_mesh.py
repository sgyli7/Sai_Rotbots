"""Check an editable OBJ shell before using it as a Goose part source.

This applies to polygon modelling sources, not BREP/STEP or triangulated
exchange formats such as STL and GLB. One OBJ should describe one closed part.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict, deque
from pathlib import Path


def _triangle_twice_area(a: tuple[float, ...], b: tuple[float, ...], c: tuple[float, ...]) -> float:
    ab = tuple(b[i] - a[i] for i in range(3))
    ac = tuple(c[i] - a[i] for i in range(3))
    cross = (
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    )
    return math.sqrt(sum(value * value for value in cross))


def inspect_obj(path: Path) -> dict[str, object]:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    errors: list[str] = []
    try:
        with path.open(encoding="utf-8") as source:
            for line_number, raw in enumerate(source, 1):
                fields = raw.split("#", 1)[0].split()
                if not fields:
                    continue
                if fields[0] == "v":
                    if len(fields) < 4:
                        errors.append(f"line {line_number}: vertex has fewer than 3 coordinates")
                        continue
                    try:
                        vertex = tuple(float(value) for value in fields[1:4])
                    except ValueError:
                        errors.append(f"line {line_number}: invalid vertex coordinate")
                        continue
                    if not all(math.isfinite(value) for value in vertex):
                        errors.append(f"line {line_number}: nonfinite vertex coordinate")
                        continue
                    vertices.append(vertex)
                elif fields[0] == "f":
                    indices = []
                    try:
                        for token in fields[1:]:
                            raw_index = int(token.split("/", 1)[0])
                            if raw_index == 0:
                                raise ValueError("OBJ index zero")
                            index = raw_index - 1 if raw_index > 0 else len(vertices) + raw_index
                            if not 0 <= index < len(vertices):
                                raise ValueError("vertex index out of range")
                            indices.append(index)
                    except ValueError as exc:
                        errors.append(f"line {line_number}: {exc}")
                        continue
                    faces.append(tuple(indices))
    except (OSError, UnicodeError) as exc:
        errors.append(str(exc))

    face_sides = Counter(len(face) for face in faces)
    edges: dict[tuple[int, int], list[tuple[int, tuple[int, int]]]] = defaultdict(list)
    degenerate_faces = 0
    if vertices:
        diagonal_squared = sum(
            (max(v[i] for v in vertices) - min(v[i] for v in vertices)) ** 2
            for i in range(3)
        )
    else:
        diagonal_squared = 0.0
    area_threshold = max(diagonal_squared * 1e-12, 1e-24)
    for face_number, face in enumerate(faces):
        if len(face) < 3 or len(set(face)) != len(face):
            degenerate_faces += 1
        elif len(face) == 4 and (
            _triangle_twice_area(vertices[face[0]], vertices[face[1]], vertices[face[2]])
            <= area_threshold
            or _triangle_twice_area(vertices[face[0]], vertices[face[2]], vertices[face[3]])
            <= area_threshold
        ):
            degenerate_faces += 1
        for start, end in zip(face, face[1:] + face[:1]):
            edges[tuple(sorted((start, end)))].append((face_number, (start, end)))

    open_edges = sum(len(uses) == 1 for uses in edges.values())
    nonmanifold_edges = sum(len(uses) > 2 for uses in edges.values())
    winding_conflicts = sum(
        len(uses) == 2 and uses[0][1] == uses[1][1] for uses in edges.values()
    )
    neighbors: list[set[int]] = [set() for _ in faces]
    for uses in edges.values():
        if len(uses) == 2:
            left, right = uses[0][0], uses[1][0]
            neighbors[left].add(right)
            neighbors[right].add(left)
    unvisited = set(range(len(faces)))
    components = 0
    while unvisited:
        components += 1
        queue = deque([unvisited.pop()])
        while queue:
            for neighbor in neighbors[queue.popleft()] & unvisited:
                unvisited.remove(neighbor)
                queue.append(neighbor)

    passed = (
        not errors
        and bool(faces)
        and face_sides == {4: len(faces)}
        and degenerate_faces == 0
        and open_edges == 0
        and nonmanifold_edges == 0
        and winding_conflicts == 0
        and components == 1
    )
    return {
        "path": str(path),
        "passed": passed,
        "vertices": len(vertices),
        "faces": len(faces),
        "face_sides": {str(sides): count for sides, count in sorted(face_sides.items())},
        "all_quads": bool(faces) and face_sides == {4: len(faces)},
        "degenerate_faces": degenerate_faces,
        "open_edges": open_edges,
        "nonmanifold_edges": nonmanifold_edges,
        "winding_conflicts": winding_conflicts,
        "connected_components": components,
        "parse_errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("obj", type=Path, nargs="+", help="one closed editable OBJ per part")
    parser.add_argument("--report", type=Path, help="write machine-readable JSON")
    args = parser.parse_args()
    results = [inspect_obj(path) for path in args.obj]
    report = {"passed": all(item["passed"] for item in results), "parts": results}
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
