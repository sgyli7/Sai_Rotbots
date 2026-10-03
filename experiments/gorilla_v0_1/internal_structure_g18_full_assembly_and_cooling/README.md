# G18 complete internal integration and cooling

Gorilla V0.1 actual engineering candidates, frozen 2026-10-03. Continuous body material and pack interfaces improved, but complete installation, load paths, drive/thermal capability, aesthetics and stable SI remain rejected. No runtime model, ABI, default policy or main-branch hardware baseline changes.

The [root integration report](root_review/README.md) explains the exact composed sources and scope. [Body A/B](body_codesign/README.md), [complete shoulder/arm A/B](shoulder_arm_codesign/README.md), [full cooling comparison](cooling_architecture/README.md) and [independent accounting review](accounting_review/README.md) preserve their own source identity and failure history.

The actual full-source bodyB+armB [bare four views](root_review/body_b_arm_b/bare_four_view.png) and [original-armor four views](root_review/body_b_arm_b/original_armor_four_view.png) bind source `9873e9db…`. These show the actual rejected internal candidate; old lower legs are historical placeholders and do not implement the user's new lower-body artwork. The root inspected these views. Existing skin does not fit the complete stocks. This is not an exterior proposal or an assertion that no alternative can fit.

BodyB's 94.691083 kg conditional own cage/receiver is a continuous material root, not total robot mass or validated strength. Three original metal load-hold guards still intersect the new cage/oil container; the author's narrower finite classification was corrected independently without changing its frozen report. Full-source B has four valid finite–finite and one finite–fluid positive in the changed/moved-versus-all neutral diagnostic. Four new shoulder material resources are rejected and complete shoulder load paths/service routes remain unclosed. OEM reference stocks and bad resources are reported separately, not treated as qualified net material.

Whole mass/COM/inertia remain null. Actual per-axis gravity is only a numeric/proxy subset with 422 unmapped owners explicitly preserved; all 480 cells retain only a 33.6 kg upper mass bound. Conditional sums omit unknowns and are not whole-machine bounds or weight-loss results. New lower-body geometry will require fresh engineering reconstruction and mass/contact/loading evidence after user art acceptance.

Split cooling preserves 6 ES0707, 1 ES0714, 8 fans, 2 WP32 stocks and all functions. Conditional low-duty temperature improves, but cold curves, flooded suction, TIM, sealed airflow and simultaneous continuous capability remain red. Full auxiliary source-upper budget 3.1575 kW at 28 V leaves the original 480-cell 30-minute duty plus 10% reserve unclosed (conditional 24.50–23.57 min). No theoretical PWM energy saving is credited. The independent 133 checks cover arithmetic and identity only.

Both shoulder macros stopped. Next checkpoint returns to complete joint architecture and functional allocation: integrated load-bearing actuator/housing versus proximal drive/remote transmission, full reaction chain, input/output ownership, complete cooling and skin space. No third local housing patch, false custom rating or repeated FE/PPO on an unassembled source. User's lower-body art continues in “Gorilla 设计”; this project does not send unsolicited messages or require external CAD delivery.

## Selected preservation and restore

[snapshot_manifest.json](snapshot_manifest.json) maps exact original paths/bytes to selected stored objects, reusing unchanged controlled dependencies and compressing large CAD/JSON. Producers use `.py.txt` in this evidence package. Frozen upstream reports keep original path meanings; they are not executable live state. Publications, extracted publication text/images, Python caches and runtime logs are explicitly excluded, while primary-source URLs/hashes and engineering extraction remain.

Restore selected bytes into a separate empty directory:

```bash
python experiments/gorilla_v0_1/internal_structure_g18_full_assembly_and_cooling/restore_snapshot.py.txt --destination /absolute/empty/directory
```

This recovers only selected bytes, not dependencies/runtime installations, downloaded publications or full historical regeneration. Exact before-owner and before-mission-duration evaluator versions are preserved; actual correction scope is recorded. A future source edit requires a new stage. [selected_snapshot_verification.json](selected_snapshot_verification.json) records isolated byte/JSON/producer/document validation; none of these checks admit physics or aesthetics.
