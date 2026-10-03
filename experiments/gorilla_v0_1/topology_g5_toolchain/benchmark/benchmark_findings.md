# G5 synthetic Q4 topology tool benchmark

This is a CPU numerical tool experiment, using no Gorilla geometry, load or contact interface. It grants no robot mass reduction, strength or manufacturing qualification. Frozen calculation inputs are `input.json` and `mesh_loads.npz`; exact solution fields are in `solution_fields.npz`. The images show actual calculated cells rather than a proposed robot appearance.

The 0.30 × 0.12 m plane-stress domain uses E=210 GPa, nu=0.3, rho=7850 kg/m³, nominal thickness 10 mm and an 80 × 32 Q4 grid (3.75 mm square cells). All x=0 displacement DOFs are fixed. Two equal-weight loads act over the literal right-edge z=0.05–0.07 m interval: [Fx,Fz]=[0,+1000] and [−1000,−1000] N. Consistent linear-edge integration includes the truncated end edges, yielding z-centroid 0.06 m and global +Y moments −300/+240 N m exactly. The NPZ contains every node, BL/BR/TR/TL cell, DOF, load and fixed DOF.

Cells intersecting the left 20 mm support strip and right 10 mm × central 20 mm pad remain solid and count toward total volume fraction 0.5. Cell coverage conservatively retains a 22.5 mm left strip and an 11.25 × 22.5 mm right pad: 210/2560 cells, including 18 right-pad cells. SIMP uses p=3 and Emin/E=1e−9; physical density filtering uses radius 2.5 cells, with the full filter chain rule and an OC update/move limit 0.2. This filter is not a manufacturing minimum-wall guarantee.

The formulations follow the original-author DTU paper, equations 1–10 on printed pp.3–4: modified SIMP, constrained compliance, OC, weighted density filtering and the derivative chain rule. Multi-load compliance is the explicit weighted sum; passive physical-density rows are overridden to 1 and have zero derivative. Q4 stiffness is independently written from 2×2 Gauss plane-stress integration. No third-party MATLAB source was copied. [Andreassen et al., 2011, DTU author PDF](https://www.topopt.mek.dtu.dk/-/media/subsites/topopt/apps/dokumenter-og-filer-til-apps/topopt88.pdf). The cached uncorrected author PDF is local ignored research material, SHA `21f2f864bd0e53791fdef7c996ba9b8846e6ef59b555c5dbcd8ae087956181d9`. [scikit-fem official docs](https://scikit-fem.readthedocs.io/en/stable/) identify the separate assembler used by the parent for independent comparison; this generator uses its own Q4/SciPy assembly.

| Calculation | Mass kg | Material/equivalent area m² | Weighted compliance N m | Max node displacement µm | Max Q4-center VM MPa | Weighted strain energy J |
|---|---:|---:|---:|---:|---:|---:|
| full_10mm | 2.826000 | 0.03600000 | 0.03430028 | 34.327 | 15.772 | 0.01715014 |
| full_5mm_target_equal_mass | 1.413000 | 0.03600000 | 0.06860056 | 68.654 | 31.545 | 0.03430028 |
| virtual_SIMP_10mm | 1.413000 | 0.01800000 | 0.07214092 | 72.940 | 23.761 | 0.03607046 |
| binary_actual_void_10mm | 1.419623 | 0.01808437 | 0.05884706 | 58.249 | 22.675 | 0.02942353 |
| full_plate_binary_equal_mass_thickness | 1.419623 | 0.03600000 | 0.06828049 | 68.334 | 31.398 | 0.03414025 |

The optimized continuous density field stopped at the allowed 80 iterations, change=0.026615, and **did not reach change<0.01**. Its physical volume fraction is 0.500000000000. Its compliance is 5.16% worse than the full-planform 5 mm solid baseline; no favorable interpretation of the virtual result is substituted.

The rho>0.5 hard cut keeps 1286 actual 10 mm cells: material fraction 0.50234375, mass 1.41962344 kg. It is 0.00662344 kg heavier than the 1.413 kg target, so a separate 5.0234375 mm full-planform plate of exactly the binary mass is included. Hard-cut compliance is 13.82% lower than that exact-mass solid plate. There is one face-connected material component, all retained regions remain present, and all material was retained in the reassembled solve. Void cells contribute zero stiffness, without Emin, deleted islands or bridge repairs. Only unused void-node DOFs are dropped: 1093 nodes / 2186 DOFs. The original first-run DOF label and broad pad flag were corrected before freeze; bytewise array comparison proves the mesh, loads, density, binary mask and history unchanged.

The element has three rigid modes and five positive stiffness eigenvalues. Rigid residuals are <2.7e−17; constant-strain element energy error is 3.6e−16. A 4×3 assembled affine patch with solved interior DOFs has relative displacement error 5.95e-17. The filtered compliance derivative matches finite differences on four variables. The weakest derivative (~8.8e−8 N m) has 2.32% relative error at h=1e−5 due to subtraction of near-equal objectives; its h=1e−3 check reduces this to 0.0216%, and all tested steps remain in `verification_supplement.json`.

Across all five comparison variants, free residual norm ≤2.53e-12, force-balance component ≤8.84e-09 N and moment-balance error ≤2.02e-09 N m. Support reactions are [0,−1000] and [+1000,+1000] N to numerical tolerance. Coarse40×16→fine80×32 solid-baseline weighted compliance changes +0.319%, maximum displacement about +0.21%, but center VM about +16.1%. This is not a converged peak-stress result. VM is a Q4-center diagnostic; the virtual SIMP row uses virtual E(rho), not real solid stress. Clamp/cutout stress concentration, yielding, buckling, fatigue, 3D/contact, manufacturing and actual robot interfaces remain unchecked.

Reproduction from repository root:

```bash
.venv/bin/python .scratch/gorilla_internal_g5_topology_benchmark/run_benchmark.py --nx 80 --nz 32 --maxiter 80
.venv/bin/python .scratch/gorilla_internal_g5_topology_benchmark/verify_benchmark.py
.venv/bin/python .scratch/gorilla_internal_g5_topology_benchmark/finalize_snapshot.py
```

The final manifest inventories source and generated output hashes; regenerated timestamps/report hashes are expected to change while the NPZ array payloads and reported numerical results remain reproducible. A preliminary supplement assembly mistakenly tiled an 8×8 element matrix along columns and was singular; that local supplement producer was corrected to per-element matrix replication before these accepted patch results. It never affected the benchmark assembler or density optimization.
