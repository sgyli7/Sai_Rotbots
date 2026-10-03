# G8 actual envelope numerical audit

All three root FEM datasets use the exact source-bound load files, eight actual original case columns and their own unchanged coefficient arrays. All 42 original case indices, factors, CoP, poses and allocations are present. The complete original force matrix reconstructs to the frozen load-envelope tolerance. No basis-only maximum is substituted for the original envelope: every reported VM maximum, VM p99, maximum displacement, compliance, peak tetrahedron index and centroid is recomputed from all 42 reconstructed stored fields and matches the root report.

| Mesh | Worst VM original case | All42 maximum VM diagnostic MPa | Worst compliance original case | Compliance J |
|---|---:|---:|---:|---:|
| g7 | 29 | 692.021694 | 23 | 66.117336 |
| a | 23 | 537.841804 | 29 | 62.541053 |
| b | 7 | 490.918484 | 29 | 11.424610 |

These coarse-mesh VM values are numerical diagnostics under prescribed generic traction. They are not physical stress allowables, contact solutions, converged singularity values or robot strength decisions.

The selected independent field checks use isolated scikit-fem 12.0.2 scalar MeshTet/P1 gradients on exact source nodes and tetrahedra. Root strain/stress/assembly/solver functions are not imported. Gradient → symmetric small strain → uniform isotropic 3D stress is evaluated with E=210 GPa, ν=0.3, and tensor/Voigt components xx/yy/zz/xy/yz/zx. VM is independently evaluated from those stresses. Internal nodal forces are independently scattered from volume·σ·∇N and compared with the complete original external force array; no stiffness matrix is assembled and no new solve runs.

| Mesh | Independently checked original case | Stress field relative error | VM field relative error | Internal force vs original external F relative residual | Integral canonical gauge maximum |
|---|---:|---:|---:|---:|---:|
| g7 | 18 | 2.593e-13 | 8.001e-14 | 1.348e-09 | 1.186e-19 |
| g7 | 20 | 1.702e-13 | 6.558e-14 | 8.408e-10 | 1.175e-19 |
| a | 20 | 1.868e-13 | 7.397e-14 | 8.433e-10 | 2.31e-19 |
| b | 20 | 1.69e-13 | 5.325e-14 | 9.101e-10 | 3.907e-20 |

Independent gradient evaluation covers G7 cases18/20 and A/B case20. Other cases' summary verification reconstructs the stored root stress/displacement basis; it is not an independent gradient evaluation of every one of the 42 states. G7 selected fields also agree with the previously solved direct G7 cases: displacement relative difference ≤4.57e−11 and stress relative difference ≤8.63e−11.

The root solver uses a QR-selected set of exactly six algebraic displacement DOFs to remove six rigid modes, then removes the volume-weighted rigid displacement from the solution. It does not directly solve the exported integral-gauge KKT system. For a connected compatible linear elastic free body with only six rigid null modes and balanced original loads, these are displacement-gauge choices rather than physical supports. The independent canonical integral gauge has rank6 and near-zero weighted residual; independent internal-force checks retain the original full external loads. Root's original-K basis residual and tiny six-DOF reaction diagnostics are retained in each receipt. No journal circumference is clamped as a real bearing support.

The source declares no force projection, gravity, real contact, dynamics or fatigue, and no physical/whole-robot acceptance. Uniform density is a material inventory datum; it does not add selfweight here. Real bearing pressure bands/preload/clearance, pin load sharing, stop engagement, mounting bolts, material strength, mesh stress convergence and whole-robot loading remain outside this numerical audit. Existing root mesh-admission file identity and flag are checked separately, not reexecuted or promoted to contact/strength qualification.

Reproduce with OPENBLAS_NUM_THREADS=1 .venv/bin/python audit_envelope_fields.py --name g7 --prefix g7_coarse_full42 --cases 18 20, then corresponding --name a/b --prefix g8_a_full42/g8_b_full42 --cases 20. Run freeze_audit.py last. The manifest records absolute inputs, all hashes and exact repository commands. Frozen G8 load envelopes and every upstream CAD/mesh/FEM file remain read only.
