# G7 new OCC carrier load-port mapping

Actual new CAD BREP `d720bc177493451fcc728c8358228006443de31c2c7edd265ef551bc84356d30` and independently supplied Gmsh physical groups are the geometry source. G4 `9a88efe8…` is used only for two literal conditional reaction allocations at unchanged interfaces: neutral case18 (equal cylinders, bearing roll/yaw reactions) and static-shoe case20, both with29430N upward at CoP[.25,.75,0]m and no module/robot gravity. No new geometry is tagged using old facet IDs or nearest pivots.

Coarse(96645nodes/376820tet) and fine(247675nodes/1085296tet) both have actual generic nodal F/Fport and rank6 integral rigid gauges in `*_loads.npz`. Reports bind new BREP/mesh/physicalgroup hashes. Seven actual circle/plane regions are independently checked for new world-SI coordinates, radius, material-outward normals, area and centroid. Cylindrical vertices lie on true CAD circles; planar mesh chords and CAD areas are distinguished.

| Actual active physical group | Exact new CAD area m² | Coarse triangle area m² | Fine triangle area m² |
|---|---:|---:|---:|
| moving_pin_bore_negative_y | 0.004251944 | 0.004249989 | 0.004251137 |
| moving_pin_bore_positive_y | 0.004251944 | 0.004249988 | 0.004251137 |
| journal_radial_negative_y | 0.009691342 | 0.009689287 | 0.009690500 |
| journal_radial_positive_y | 0.009691342 | 0.009689279 | 0.009690492 |
| downstream_mount | 0.034314000 | 0.034314000 | 0.034314000 |

Generic arbitrary-vector traction can transmit rank6 but is not a physical radial bearing/pin pressure distribution. Independent decomposition records its axial/tangential components and negative radial projections. The separate case18 probe instead uses the four actual new journal/pin groups, their complete real axial regions and a load-direction compressive nodal half surface. Pressure acts strictly opposite the analytic material normal: inward on the outer journal, outward on the pin bore, with no axial force, tangential force or negative pressure.

The radial operator has rank4 (Fx/Fz/Mx/Mz); Fy and local-axis My are null invariants. Every literal source6D target is checked as reachable, and all original components remain unchanged. Four physical equations are solved by minimizing integral area*p² over the chosen nodal half surface. In these actual cases the unconstrained minimum is already nonnegative, so the fallback Dykstra branch was not needed. Independent negative tests adding Fy1N or My1Nm are outside the radial range and rejected. No target projection or total-force/moment repair is used.

| Radial condition | Actual group | Operator rank | Nodal equivalent pressure maximum MPa | Negative-pressure nodes |
|---|---|---:|---:|---:|
| coarse_case18_radial_pressure | moving_pin_bore_negative_y | 4 | 19.171956 | 0 |
| coarse_case18_radial_pressure | moving_pin_bore_positive_y | 4 | 19.172083 | 0 |
| coarse_case18_radial_pressure | journal_radial_negative_y | 4 | 7.741411 | 0 |
| coarse_case18_radial_pressure | journal_radial_positive_y | 4 | 9.143544 | 0 |
| fine_case18_radial_pressure | moving_pin_bore_negative_y | 4 | 19.167785 | 0 |
| fine_case18_radial_pressure | moving_pin_bore_positive_y | 4 | 19.167810 | 0 |
| fine_case18_radial_pressure | journal_radial_negative_y | 4 | 7.744661 | 0 |
| fine_case18_radial_pressure | journal_radial_positive_y | 4 | 9.147419 | 0 |

These nodal equivalent **contact pressures are not hydraulic circuit pressures or bearing/roller contact ratings**. Minimum-pressure regularization is a chosen condition, not solved elastic contact. Real bearing loading width/pressure center/preload, both fork-face pin compliance/clearance, friction and actual reaction allocation remain unknown. Maximum pressure is mesh-sensitive, even though this particular coarse/fine regularized field changes little. The downstream mount remains arbitrary6D equivalent traction because actual bolts/foot attachment are omitted; the static shoe route also needs compression fit/retention/unload-release evidence.

Independent vector summation against the original frozen G4 handoff, without importing either distribution solver, gives port-force residual≤1.53e-10N, port-moment residual≤1.77e-11Nm, whole-body force components≤2.23e-10N and moments≤6.42e-11Nm. Every loading array's node/tet/boundary/group payload exactly equals its new source mesh. All seven patches retain actual physical-group provenance. Integral C=RᵀW gives rank(CR)=6, removes only six rigid motions and is not a bearing clamp. The premise of a valid free-body elastic K with only six rigid modes belongs to root's separate mesh admission/FEM checks.

Reproduction from repository root:

```bash
.venv/bin/python .scratch/gorilla_internal_g7_load_ports/assemble_g7_load_ports.py --mesh .scratch/gorilla_internal_g7_cad_carrier/coarse/carrier_tetra.npz --cad-source .scratch/gorilla_internal_g7_cad_carrier/carrier_exact.brep --cad-port-report .scratch/gorilla_internal_g7_cad_carrier/coarse/port_groups.json --prefix coarse
.venv/bin/python .scratch/gorilla_internal_g7_load_ports/assemble_g7_load_ports.py --mesh .scratch/gorilla_internal_g7_cad_carrier/fine/carrier_tetra.npz --cad-source .scratch/gorilla_internal_g7_cad_carrier/carrier_exact.brep --cad-port-report .scratch/gorilla_internal_g7_cad_carrier/fine/port_groups.json --prefix fine
.venv/bin/python .scratch/gorilla_internal_g7_load_ports/radial_pressure_probe.py --generic-prefix coarse
.venv/bin/python .scratch/gorilla_internal_g7_load_ports/radial_pressure_probe.py --generic-prefix fine
.venv/bin/python .scratch/gorilla_internal_g7_load_ports/verify_g7_snapshot.py
```

Only load mapping and independent conservation were executed here. Root chooses whether and how to apply these conditions after independent mesh admission. No FEM/optimization, bearing/pin/stop qualification, robot strength, payload/walking capacity, topology weight saving, source mutation, Git or GPU work is claimed.
