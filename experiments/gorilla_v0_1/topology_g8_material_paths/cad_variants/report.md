# Gorilla G8 — bounded carrier material-path comparisons

Both actual variants produced valid single-solid raw STEP/BREP and a positive quality coarse volume mesh. These are same-envelope internal comparators for root physics evaluation; generation, material-resource checks and zero sampled intersections do not release strength or whole Gorilla capability.

| Variant | Actual material path | Conditional steel mass | Delta vs G7 | Tetra | Min mean ratio / SICN |
|---|---|---:|---:|---:|---:|
| A | Eight actual OCC R8 toe cylinders; local top wall total10mm | 32.457585 kg | +0.472265 kg | 422697 | 0.3051 / 0.2525 |
| B | Original6mm skin + two continuous6mm webs at Y±75mm | 37.295319 kg | +5.309999 kg | 401748 | 0.2321 / 0.2488 |

A adds the top patch inward from the original6mm skin to a total10mm within its90×75mm footprints. Selected exact rays measure6mm floor and10mm top at the patch. Its toe transition is actually constructed by OCC fillet; independent OCCT7.9 finds eight radius8mm cylinder faces. Neither variant moves the axes, seven port planes/cylinders or original component AABB. All seven actual port areas match G7 exactly.

B webs run between both existing end walls and join the top/floor. Exact probes and one material solid demonstrate the finite connections. Functional shaft/pin/keeper bores are subtracted after fusion; journal bore and all pin/keeper probes remain empty. The center/adjacent main cavity stays open. B adds material; it is neither optimized nor a mass-reduction result.

Each newly generated signed material boundary passes the strong gate, and the newchild plus retained29components passes30/30 resource checks. Four actual stored transforms (neutral stop closed/open and±25°) have zero positive-volume material/reference intersections at1e-10m³ threshold. Twenty-one sampled+X shoe withdrawal positions are clear. Closed neutral stop gaps are zero without positive material intersection. Constant material-volume errors are below6e-18m³. These are discrete geometry checks, not continuous motion/contact qualifications.

The same-scale `actual_cad_sections.png` is drawn from actual STEP/plane sections at child-localY=+75mm and0. Grey fill is a2mm exact solid-classifier sampling raster; section lines sample the actual CAD curves. It is an internal material diagram, not a new leg-foot appearance proposal or a stress image.

**Legacy metadata caution:** copied `true_circle_delta_*` CAD-manifest fields now contain total material differences relative to oldG4, including the patch/ribs. They must not be called circle-only differences. For this comparison use `net_added_material_vs_G7_m3`, `net_added_mass_vs_G7_kg` and the complete actual mass/volume. The manifest bytes were kept stable for the load mapper; this report binds that interpretation explicitly.

Build entry: use the frozen G7 isolated runner with `build_variants.py --variant a/b` in a fresh copied branch. Then `mesh_variant.py --variant a/b` gives the same G7 coarse field settings and physical-group IDs1–7. Output directories refuse overwriting. Current sources/meshes are frozen, so do not rerun here. `cad_surface_helpers.py` must accompany the mesher. Checkers and original source references are retained.

No FE or topology optimization was run by this branch. Root owns the same42-case force/moment comparison. Material/process, bearing/pin contact/fit, real pressure centers, gravity, stiffness/stress convergence, service exclusions, continuous motion and full-system integration remain unqualified. G7 frozen sources and robot exterior are unchanged.
