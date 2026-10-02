# Gorilla F1 minimal read-in

Read `structure_scene.json.parts` for neutral native geometry. `pose_scenes[i].parts` are already world-posed and root-Z-aligned; do not reapply `body_transforms` or rootshift. Eachrow has `body` displayowner, `mass_owner_body` gravity assumption, `material_union_group`; union only same materialgroup once. Do not infer a rigid attachment merely fromowner. Mainserial tree22bodies is candidate; actuator loops and inertia unknown.

`pose_scenes[i].actual_endpoint_link_transforms` has18cyl+8brace records. `barrel_link_transform_world` is neutral-world→pose-world rigid; `rod_link_transform_world` includes actual prismatic displacement. Apply theformer toholding/brackets definedin neutralbarrelworldframe; apply `barrel_neutral_frame_world` first only if sourceholding coordinates are cylindermodule-local. Do not use `base_body` T alone. Fourrecords with `finite_geometry_present=false` are endpoint mathematics only; no barrel hardware/mountbay exists.

Exact replacementsets are in `owners_and_replacements.json` and source. Retain5convertedaxescontroller/encoder/brake/wire20functions unresolved; all4fullrotarypackages representedbyunscaledsourcecomponent+finitehousing, actualcoolingcasesin `system_handoff.json`. Original111armor are comparators, not in375newparts. SixC15contact candidates are not all replaced: fourgroundpads remainoriginal; twopadupperedgeproxies are declaredreplacedbyoldE2trayreference, stillcollisionrejected.

Reusable parameters: `candidate_parameters.json` + `interface.json`; all18eyes/strokes/ports/newaxes; `axis_deltas.json` gives exactE2changes. Nativefinite factories in `build_f1.py`,2stocktemplatesin `axes_and_modules.py`. Use nextNEWbranch for waist/hip stacks and full3Dlowerleg rebuild; do notoverwritefrozenF1.

Rerun from repository root with `.venv/bin/python .scratch/gorilla_internal_f1_structure/build_f1.py`, then `check_f1.py`, then `finalize_f1.py`. These overwrite onlythisscratchbranch, so copyfolderfornewcandidate. No stableSI or currentF1completeLP/thermal/3tstrength result. Explicit rejection livesinchecks andreport.
