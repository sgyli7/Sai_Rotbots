# F1 local valve installation templates

These two source-calibrated templates are editable native SI geometry, **not chosen hardware, OEM CAD, an installed robot module or a pressure/thermal release**. They have not been placed at eighteen actual barrels. `vertices_world_m` is a compatibility field carrying **template-local coordinates** until the caller applies an explicit rigid transform; origin is the reference core mounting-plane center, +Z upward. Every part is assigned the placeholder `template_mount_owner`.

Use `holding_template_scene.json` or `directional_template_scene.json` for nominal geometry. Their `parts`, `mass_rows`, `ports`, `service_spaces` and `fluid_void_inventory` are separate. Lower/nominal/upper files are independently rebuilt dimensional sensitivities, not OEM tolerances or probabilistic limits. Native GLBs provide local inspection only. No raw OEM asset was downloaded or copied into this folder.

| Template | Source core mass | Accounted dry mass lower/nominal/upper | Physical AABB mm lower / nominal / upper |
|---|---:|---:|---|
| HAWE LHDV33-21 reference | 3.5 kg | 5.350 / 5.987 / 6.704 kg | 237×140×107 / 257×147×109 / 277×154×111 |
| Parker D1FB C, double coils + OBE reference | 2.9 kg | 4.907 / 5.849 / 6.963 kg | 240×112×198 / 240×122×204 / 240×132×210 |

These are the listed inventories for our explicit accessories, **not complete manufacturing upper bounds or unavoidable minimums**. Own guards/baseplates can be co-designed later; arbitrary percentage mass removal is not supported. Eighteen nominal holding templates alone account for 107.768 kg dry; this fact does not select eighteen LHDVs or resolve the original 113.209 kg inventory. Eighteen directional templates would account for 105.291 kg dry, before system hoses/valve-bank support and external power switching. Valve count is not reduced here.

The holding template includes fifteen positive-mass native pieces: one catalogue-mass core envelope, four steel hollow G1/2 fitting shells, a four-hole steel bracket, four M8 envelope fasteners, four finite seal rings and an aluminum U guard. Known main drawing dimensions are 175×88×70 mm with 10 mm top bolt projection. The **left adjustment projection is not dimensioned**: an explicitly own 20/35/50 mm sensitivity space is reserved, not asserted as an OEM bound. The optional WD variant is only metadata: 3.6 kg and 31.3 mm top projection, not our baseline -21 geometry. Our four interface coordinates are routing proposals; they must be mapped to the actual OEM ports/drawing before fabrication. Generic P/T aliases mean **F1/F2 work lines**, and T is not a permanently designated tank port. A/B alias V1/V2 cylinder chambers.

The directional template has twenty-one positive-mass pieces: complete 222×46×125 mm catalogue-mass C/OBE core envelope, a finite steel manifold with four independent bent channels, four hollow fittings, four M5×30 envelope fasteners, four provisional mounting seals, a finite mating-connector shell, four copper contact proxies, a drilled aluminum heat spreader and U guard. The guard contains actual passage holes for the four fittings. The proprietary NG6/OEM port positions, mating connector contacts and supplied-seal scope are not reconstructed or qualified; local P/T/A/B centers are our mounting proposal. No long lever is deleted from an inherited module and called an equivalent function.

OEM cores are occupied reference envelopes plus catalogue masses; their envelope volume is **not steel material**, and their COM/rotational inertia remains a proxy. Own material uses steel 7850, aluminum 2700, polymer 1200 and copper 8960 kg/m³ as declared design assumptions. Finite attachment pieces are closed and have positive net volumes. Nominal pair checks find only four intentional threaded-engagement intersections into each OEM *envelope*, not native material proof of those holes: each holding fastener intersects the envelope by 0.499431 cm³, each directional fastener by 0.073009 cm³. No positive own-material/own-material intersections remain above 1e-10 m³ in the nominal local templates. Real OEM attachment and whole-robot collisions remain unknown. All thirty-six nominal pieces have one connected closed surface component.

Known external oil voids are holding 0.009425/0.013305/0.018096 L and directional 0.010043/0.015378/0.022323 L. They **draw from the parent hydraulic stock once**, and are excluded from the dry mass rows. OEM internal oil is unknown. Do not add these volumes to the existing 30 L stock a second time. Service tool/cover-removal spaces have no mass and are deliberately not physical pieces. In particular, the holding template fails the previous 180×100×110 mm installation window already at the lower X/Y envelope; this is a macro relocation or architecture constraint, not permission to shrink the OEM reference.

Source facts and limits:

- [HAWE D7770](https://productfinder.hawe.com/downloads/D7770-en.pdf), 08-2024/1.0, printed pp1/4/7/9/10/16/27/38. Cached upstream file is outside this folder at `.scratch/gorilla_internal_f_holding_sources/cache/hawe_lhdv_d7770.pdf`, SHA256 `4e89b99d3be03fe06d1ada50b70e980b1c04c009aaef1bee9fb31755fad64eb0`. Setting maximum420 bar, family load maximum350 bar are distinct. D/E examples allow25/16 L/min; return pressure maximum10 bar, preset at least1.2×true maximum load, fully open pressure loss at maximum flow can reach the catalogue50 bar reference. Robot damping, two-cylinder tuning, fault response and current load/preset/control pressures are unqualified. No zero-loss or universal oscillation immunity is inferred.
- [Parker D1FB](https://www.parker.com/content/dam/Parker-com/Literature/Industrial-Systems-Division-Europe/Catalogues/Industrial-Valves-UK/03/D1FB-UK.pdf), MSG11-3500/UK, D1FB25.03.2024, pp3-4/3-5/3-6/3-7/3-12/3-13. Official PDF read previously in the browser; direct download returned403, so raw PDF SHA is **unknown**, with no bypass. OBE supply18–30 V, maximum input2 A,100% coil duty, possible coil temperature150°C. P/A/B350 bar, T210 bar are distinct. Symmetric20 L/min reference uses5 bar per metering edge; asymmetric cylinder transfer, spool leakage, neutral pilot behavior, loss heat and power-cut safety remain unknown.

Neither catalogue proves Gorilla load-holding, continuous heat rejection or fault-stop behavior. The source-selected pressure/flow/tuning reference must be matched at the **same actual working point**, with true load pressure distinguished from the204 bar supply design point. Thread proof, pressure proof, bracket/case strength, port sealing, service access, body ownership and pose-dependent hoses remain red.

Reproduce locally:

```bash
.venv/bin/python .scratch/gorilla_internal_f1_system/module_templates/build_templates.py
.venv/bin/python .scratch/gorilla_internal_f1_system/module_templates/verify_templates.py
.venv/bin/python .scratch/gorilla_internal_f1_system/module_templates/finalize_receipt.py
```

`manifest.json` binds source research, builder, all templates/GLBs/spec and the verification receipt. No frozen E2/F1 structure, upper/system source, controlled file or Git content is changed.
