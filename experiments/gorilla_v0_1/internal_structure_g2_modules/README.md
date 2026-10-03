# Gorilla G2: module installation and packaging checkpoint

Frozen 2026-10-03. **No integrated robot, installation, physical, aesthetic or stable SI acceptance.** AA3 remains the exterior authority. C15/E2a/G1 source bytes remain historical; no new exterior was adopted. Two macro layouts per module and bounded producer installation derivatives are retained separately.

Actual progress is limited but concrete: three complete rotary waist kits and narrower net load carriers remove neutral finite carrier interference; five real screw/carriage channels fit their own fixed stock at 21 positions over 180 mm. Their unresolved interfaces and neighboring collisions prevent release. Neither result closes the whole robot.

| Module | Final native source | Result and next mechanical action |
|---|---|---|
| Waist | [44-part source](waist/scene.json.gz), SHA `3c462863…26edb`; [report](waist/README.md) | Neutral finite carrier collisions zero; negative pitch −10°/−15° collides. Sampled [−5°, +15°] is a candidate, not a continuous validated range. Seven OEM/input-interface items remain unresolved; QTR holder misses verified rotor bore by 3.5 mm radially. Next: build an actual rotor→shaft→WG, brake and encoder connection. |
| Left lower chain | [38-part B source](lower/chain_scene.json.gz), SHA `34da78b8…c875a0`; [report](lower/report.md) | Legal finite resources; neutral/lower-end/split still have 19/19/18 metal pairs. Some disconnected bearing seats are producer errors, not proof AA3 must change. Next: fixed load-bearing heel/arch, separate folding forefoot, real compression stops and redesigned hidden cover returns. |
| Left hand | [585-part installation source](hand/selected_installation_scene.json.gz), SHA `1ead0c8d…fb9e22`; [report](hand/selected_installation_report.md) | Five local channels sampled clear; full wrist/hand remains rejected. Reaction bridge still intersects yaw motor 1.4697 cm³; brackets enter gear/cooling references, tendon termination incomplete. Next: source-bound 25/32 wrist-family comparison for an initial 25 kg conditional domain, retaining 50 kg sensitivity. |

Mass ranges are **module scope only**, not compatible or additive whole-body totals: waist 158.412/162.402/170.202 kg; lower 123.451/127.195/133.311 kg including original pads and holding allowance; selected left-hand new inventory 42.3245/48.9240/61.8778 kg excluding retained old fingers/armor/system. Hand A/B force results were not recomputed for the heavier selected derivative. No whole-robot reduction is claimed.

The lower pure 3 t forefoot-CoP+.250 m sensitivity gives 716.812 MPa von Mises in the current Ø48/28 hollow shaft under an assumed pure-torsion loadpath. It rejects that stated path; it does not establish the required shaft after stop/contact reactions share the load, or a 3 t mobile payload rating.

## Exterior and packaging boundary

The user allows packaging changes when aesthetic quality is maintained. AA3 defines visible form; our guessed C15 inner thickness/returns are engineering candidates. Hidden skins, returns and attachments may be reconstructed with a new shell source, explicit material deltas and preserved visible surfaces. Their earlier byte identity is not a release requirement. [G3 hidden packaging allowance](lower/g3_packaging_constraints_supplement.md) is a proposal, not achieved clearance. If visible changes are needed, show a concrete conflict, minimal change budget and the same candidate's equal-scale FRONT/LEFT/REAR/TOP for user aesthetic acceptance before adoption. Aesthetic acceptance does not close physical gates.

## Reproduction and independent review

[Snapshot manifest](snapshot_manifest.json) binds selected original bytes to stored copies; large JSON is deterministic gzip and frozen producer inputs use `.py.txt`. Restore exact scratch files with:

```bash
.venv/bin/python experiments/gorilla_v0_1/internal_structure_g2_modules/restore_snapshot.py.txt --root /home/ethan/Projects/Sai_Rotbots
```

The restorer verifies both stored/raw hashes and refuses changed target bytes. Earlier C15/E2a/G/G1 and source dependencies are needed for their producers. Vendor cache pages/PDFs and full logs are deliberately excluded; original manifests retain source URLs/hashes and may list excluded logs. This is not a claim that every historical dependency can be restored recursively.

[Root review](root_review/independent_review.json) independently checks the 44/38/585 native resources, four agent manifests, unchanged source identity, one complete carriage channel at the stated 21 positions, the yaw-bridge witness and the pressure formula. Final waist/leg/carriage diagnostic images were opened. These are scoped resource/geometry/math checks, not strength, continuous motion, thermal or contact acceptance. Software CI for `298bf1c16` succeeded; its software/existing-robot scope does not qualify Gorilla physics.

Current decisions remain in [Gorilla's single index](../../../robots/gorilla_v0_1/design/current_decisions.md). G3 may create new candidates; frozen G2 bytes must not be overwritten.
