# Gorilla G7 — true-CAD carrier and two actual volume meshes

**One same-function carrier was rebuilt as valid parametric CAD and produced two healthy new volume meshes.** This closes the G6 tool/native-sliver obstruction for this internal piece, not the Gorilla structural or load-release gate. No external packaging, full leg design, FEM or topology optimization was performed.

## Tool and input identity

The [official Gmsh Linux download](https://gmsh.info/) executable in current4.15.2Linux64 archive is actually ELF x86-64 (e_machine62,64-byte header saved and hashed; no fullarchive hash claimed). The host is aarch64. Ubuntu noble universe ARM64 Gmsh4.12.1 was downloaded/extracted independently in tools/ with23package hashes and their copyrights; globalapt/venv/lock are unchanged. Actual CLI/API/OCC/tet cube regression passed: netvolume0.000875m³,4386tet,minSICN0.29784. [Gmsh license](https://gmsh.info/LICENSE.txt) isGPL2+ with its stated linking exception; dependency notices remain in the extracted cache. This route succeeds without inferring runtime absence from PyPI wheels.

OriginalG4 source remains9a88efe894625e7ed3d3f15e544ead7b574382035594ab8d4b81f530fbb7b21a. New BREP `d720bc177493451fcc728c8358228006443de31c2c7edd265ef551bc84356d30` and STEP `4520d7e6db3daf0f33996ab3395352a05bc73cc0c1ec92e4ca185cbf157b1dd8` are independently bound. Original59.9/28.2mm journals,40.4mm pin holes,6.3mm keeper holes,6mm closed mainbox cavity, stop and endmount planes and axes retain nominal dimensions. Mathematical circles replace64-facet chords; maximum sourcefacet radial sag is66.25µm at55mm fork radius and36.07µm at29.95mm journal. No STL repair, geometry healing, triangle deletion or density scaling.

## Actual material and mesh evidence

OCC7.6.3construction and independentOCCT7.9STEPcheck both give a valid **single material solid**, net0.004074563072m³. At conditional7850kg/m³ the carrier mass is**31.985320113kg**, +8.300756g versus oldfacet source. This is geometry-discretization delta, not weight optimization. Full exactCADCOM and3×3 inertia are in cad_source_manifest.json/report.json.

| Actual level | Nodes | Tet | Minimum mean-ratio | Minimum SICN | CAD volume error |
|---|---:|---:|---:|---:|---:|
| coarse | 96645 | 376820 | 0.232138 | 0.248839 | -0.001336% |
| fine | 247675 | 1085296 | 0.294361 | 0.188632 | -0.000583% |

Both have all-positive finite tet, no tinytet below1e-20m³, no mean-ratio below0.01, material-node graph1and no unused volume-mesh nodes. Each newly exported signed boundary independently passes the strong material contract with1material root. Boundary triangles are induced outward by positive tetrahedra and mapped one-to-one to actualCADsurface elements; no fix_normals. Native compact exports preserve coordinates/triangles with explicit originalnode map, not geometric repair.

Independent exact CADray and material probes preserve actual six-mm selected closed-box walls, main cavity, journal/pin/keeper bores and stop material.27selected uncut-wall rays per mesh yield54material6mm intervals; minimum3tet intersects each selected interval for both levels. This is not an everywhere-thickness, strain, stress or convergence proof.

Seven actual CADsurface physicalgroups are exported: journal±,movingpinbore±,stop±,downstreammount. Each port_groups.json carries actualOCCtag, area, analytic circle/plane and input hashes. Vertex circle radius errors are below8e-16m. Linear triangles retain their finite chord/normal/area errors explicitly. The journal group covers the full exposed51.5mm shaft; actual29.75mm bearing contact distribution and pressurecenters are unknown, so this area must not be treated as an OEM ratedload band. Independent assembly check is bound at .scratch/gorilla_internal_g7_assembly_review/assembly_receipt.json, SHA c67750a4e76479c6c93b0d14992bfa838c1892d79dbb6af5b6f6cd999c924f27: four newchild poses and21release samples have no material intersection. It is an external same-source check, not inheritedG4green. The mixednewcircle/oldfacet reference-bearing gap is13.8637µm, not an actualSKFfit certificate.

## Re-run and handoff

Copy only build_cad_carrier.py and mesh_cad_carrier.py to a fresh repository .scratch branch for re-running. From repository root call `.venv/bin/python .scratch/gorilla_internal_g7_cad_carrier/run_isolated.py <fresh_branch>/build_cad_carrier.py`, then the same isolated runner with `<fresh_branch>/mesh_cad_carrier.py --level coarse/fine`. The runner reuses the hashed extracted toolcache; producer scripts output beside themselves. Existing meshdirs intentionally refuse overwrite. Do not re-run the builder in this frozen branch. Inputs are worldSI and rootshift0. NPZ volume fields:points_m,tetra,boundary_faces,boundary_physical_tags,boundary_cad_surface_tags. Compactnative boundary adds original_tetra_node_indices. Seven name/tag identities are in eachlevelport_groups.json. Native four-view/threequarter renders display only this internal piece and bind native_surface_scene.json; they do not propose leg-foot exterior.

The old42external-only6D force cases may be referenced only under their explicit nominalinterface/reaction assumptions. Newmass/contact/pressurecenter and gravity must be rebound. No bearing circumference was fixed by this branch. Actual newBC/load mapping, elasticmatrix/energy validation, mesh convergence, fatigue/pressure/material/process/assembly and fullGorilla capability remain unqualified. No3tcarry/walking or strong-weight claim follows from the validmesh. The lawfulpartition fallback remains available but was not executed because the first exactCADgeometry gave both mesh levels.
