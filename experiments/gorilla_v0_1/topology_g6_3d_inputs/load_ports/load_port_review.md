# G6 actual child conditional load ports

Executable input: `assemble_load_ports.py`. Frozen G4 child source SHA `9a88efe894625e7ed3d3f15e544ead7b574382035594ab8d4b81f530fbb7b21a`, actual `g4_child_load_carrier`. This branch applies no FEM, alters no source geometry, and makes no strength or robot reduction claim.

The selected primary case is original G4 index18: neutral pitch, 29430 N upward at ground CoP [0.25,0.75,0]m, equal cylinder allocation with the paired journals taking roll/yaw reaction. Module and robot gravity are absent. This is the G4 conditional 3t static-pressure example, not a walking/payload rating. Five force/moment interfaces are independently compared directly against the original frozen G4 handoff, without importing the sibling's equilibrium routine.

| Actual port | Source load center m | Force XYZ N | Moment XYZ about center N m | Tet surface nodes | Surface area m² | Arbitrary-traction wrench rank |
|---|---|---|---|---:|---:|---:|
| moving_pin_bore_-1 | [0.26, 0.49, 0.33999999999999997] | [10758.608, 0.0, -12910.33] | [0.0, 0.0, 0.0] | 338 | 0.00383919 | 6 |
| moving_pin_bore_1 | [0.26, 0.81, 0.33999999999999997] | [10758.608, 0.0, -12910.33] | [0.0, 0.0, 0.0] | 306 | 0.00378793 | 6 |
| journal_radial_-1 | [-0.06, 0.505, 0.3] | [-10758.608, 0.0, 8343.606] | [0.0, 0.0, 0.0] | 128 | 0.00968745 | 6 |
| journal_radial_1 | [-0.06, 0.795, 0.3] | [-10758.608, 0.0, -11952.946] | [0.0, 0.0, 0.0] | 129 | 0.00968745 | 6 |
| downstream_mount | [0.29, 0.65, 0.285] | [0.0, 0.0, 29430.0] | [2943.0, 1177.2, 0.0] | 12 | 0.03431400 | 6 |

Surface regions preserve exact native facet identifiers. Independent checks use actual child ownership, journal29.95mm and pin-bore20.2mm radii, axial-Y normals, outward journal/inward bore normal directions, planar stop z=.388 and downstream x=.29 surfaces. All seven native regions pass those geometry checks. The stop patches exist but are inactive in case18; cylinder-bore patches are inactive in separate case20, the static shoe route. No region is chosen from the nearest pivot or assigned an all-DOF clamp.

For each selected patch, triangle area/3 is lumped to actual nodes. Initial force is area-proportional. A minimum weighted correction satisfies all six force/moment equations at the original load center, so pressure-center/patch-centroid offsets do not silently change the applied wrench. Each weighted wrench matrix has rank6. Source journal load centers Y=.505/.795 differ from actual whole-sleeve patch centroids .50175/.79825; those offsets remain in the report. This **arbitrary vector traction includes tangential/tensile components and corrective couples**; it is not a solution for compression-only bearing/pin pressure or contact friction. A catalogue bearing does not justify this distribution.

Native case18 has2944 surface nodes; geometry-tet case18 has2954 nodes/12722tet. Per-port residual is≤1.28e−11 in the separately listed N/Nm components; total-force components≤6.16e−11N and total-moment components≤1.98e−11Nm. Case20 mechanical-stop route has force components≤1.19e−11N, moment≤5.01e−12Nm, port residual≤4.01e−11. Independent sums and six rigid virtual-work residuals are saved in `verification_receipt.json`.

The exported six integral gauge rows span only translations/rotations: C=RᵀW and rank(CR)=6. Use an augmented [K,Cᵀ;C,0] system for a compatible self-balanced free-body conditional analysis. This does not freeze the journal, prevent elastic surface motion or model actual supports. With a valid free-body linear elastic K whose kernel is exactly R, gauges select a displacement representative; gauge reactions should approach zero for these balanced loads. That K/kernel premise has not been tested here. Surface-only files use area weighting for gauges; the tet file uses actual tet volume lumping, without interpreting surface weight as mass.

The available tet mesh is geometry-only, SHA `e0b45d8fce7013903cde7e3f1862d3387c7310c7868ee4eb5eca7f499c8795c4`, minimum float64-determinant volume1.88e-23m³. One extreme sliver cancels to zero in float64 cross-dot volume while extended precision remains positive~2e−23m³; this diagnoses ill-conditioning, not a proven geometric collapse. Severe slivers and failed quality refinement make it **FE-inadmissible for trusted stress**. Successful facet mapping and balanced loading do not repair it. Root's next choices are: retain all five self-equilibrated source ports with only rigid gauges after a valid mesh; or solve the complete physical bearing/pin/stop/downstream contact allocation first and replace these conditional tractions. The second route must establish preload, pressure centers, axial/radial stiffness, clearance/friction and actual mounting bolts. Both routes still need material/process, connections, fatigue/dynamics and full-machine loads.

Reproduce the actual mappings:

```bash
.venv/bin/python .scratch/gorilla_internal_g6_load_ports/assemble_load_ports.py
.venv/bin/python .scratch/gorilla_internal_g6_load_ports/assemble_load_ports.py --mesh .scratch/gorilla_internal_g6_3d_domain_review/geometry_tetra.npz --prefix tetra_case18
.venv/bin/python .scratch/gorilla_internal_g6_load_ports/assemble_load_ports.py --case-index 20 --prefix native_case20_stop
.venv/bin/python .scratch/gorilla_internal_g6_load_ports/verify_and_freeze.py
```

The NPZ interface exports `points_m`, `boundary_faces`, exact `native_face_markers_1based`, assembled `F_xyz_N`/flattened XYZ DOFs, per-port force arrays, `gauge_rows` and `rigid_mode_matrix`; the tet result also includes tetra connectivity. All physical support/contact boundaries remain conditional.
