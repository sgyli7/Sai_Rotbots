# G22 actual common-body installation review

Root V2 scene `3190ec7d…` contains2958 actual source pieces. This review screened every464 changed member (246 actual core/joint plus218 arm rest-rebind pieces) against2489 foreign retained IDs using AABB followed by actual native positive-volume queries. Five old waist IDs appear once and are excluded from this foreign scope because the local251-piece probe already queried them. Local new/new21 failures were not re-counted here. No geometry, density, owner or source was changed.

2267 native queries produced752 positive records:27 between source-declared finite pieces with passing material resources,86 legacy/invalid finite candidates,472 complete reference installation obstacles,140 service clearances,12 normal-fluid/void overlaps, and15 computational-domain overlaps. The latter three are retained diagnostic scopes, not solid hardware collision claims. Same owner never exempts a pair. Four actual retained roll/yaw receiver resources still fail. Legacy polygons use an explicitly recorded query-only fan and are never declared triangle-contract material merely because the Boolean works.

Representative complete-body obstacles:

- g22_common_core_load_cage_net × e2_dual_fluid_HX_material: 1356.245 cm³; qualified_finite_material_overlap; smallest full-box separation 153.0 mm. This is not a proven layout window.
- g22_right_context_pitch_FS_official_gross × g16_low_es0707_segment_2_fullcore_reference: 710.704 cm³; complete_reference_installation_obstacle; smallest full-box separation 47.0 mm. This is not a proven layout window.
- g22_common_core_load_cage_net × g16_hot_es0714_complete_reference_fullcore_reference: 511.84 cm³; complete_reference_installation_obstacle; smallest full-box separation 63.0 mm. This is not a proven layout window.
- g22_common_core_load_cage_net × g18_WP32_full_pump_1: 388.197 cm³; complete_reference_installation_obstacle; smallest full-box separation 77.5 mm. This is not a proven layout window.
- g22_left_derived_fixed_pitch_receiver × left_blue_continuous_shoulder_sweep: 69.684 cm³; legacy_or_invalid_finite_candidate_overlap; smallest full-box separation 268.1 mm. This is not a proven layout window.

HX/neck is a real same-owner material overlap, while complete side cores/output stock, roof core/top beam and both WP32 packages require whole-group reassignment. The original shoulder shell overlap is a source geometry challenge, not proof that AA3 aesthetics must be changed. Fourpack energy has15 foreign records but0 cell-envelope records; this does not qualify pack wires, support, heat, dynamics or the complete layout.

328 records involve old lower-body history and are separated in report.json; they do not freeze the new leg positions or demonstrate new leg capacity. The rest-rebound arm/hand source is only a fixed-rest geometric probe: the actual terminal yaw output-to-arm adapter and rotating waist output are absent.

No continuous motion, FE, physics, net whole mass/inertia, storage/runtime claim or aesthetic acceptance was performed. Source resource/installation failures remain visible. The first classification receipt is preserved: computational domain was initially categorized as a reference and the finite HX as a reference; final classification corrects these exact source-role distinctions without changing any geometry or overlap value.

Reproduce with `.venv/bin/python review_installation.py`. The final root source and validator hashes are bound. All representative AABB movement options are conservative box-separation numbers; joint shifts, duct rerouting and an available free cavity were not proved.
