# G22 typed copper and dielectric routing prototype

One terminal and two adjacent sense nets from frozen G21 B pack0 now have executable finite routes. This is a limited geometry prototype; it does not qualify the 720-cell pack, robot electrical system, cooling plate or installation.

Frozen native scene SHA256: `ebe9cefbc523539feed7702d0d97152d7715c198e968857b6ee736f0a7529eeb`. Input G21 B SHA256: `683da8b329db49bdd25a36725a71619eb92b4646f090da033e3430840e0d94cb`. G21, the robot shell and earlier frozen branches were not changed. No additional whole-body layout was generated.

## Actual geometry and checks

`build_typed_route.py` unions all copper segments, bend pieces, cropped source lands and end lug/pins for each net, then subtracts that **complete same-net copper union** from the complete outer sweep. It never subtracts another net to hide a collision. The 17 original native meshes pass the signed-source contract, each has one material root and all edges have degree two. All 136 part pairs have no positive intersection above `1e-12 m³`; the producer's aggregate Cu/dielectric union residual is `8.44e-15 m³`, while the independent 27 individual Cu/dielectric queries have maximum positive residual `5.02e-22 m³`. These are numerical tolerance statements, not an exact-zero proof.

The copper routes positively join their source-cropped collector land and end lug/pin, with one copper material root each. These are self-designed source lands, not validated OEM cell terminals or certified welded contacts. Source polarity/can/vent and actual terminal contact remain unknown.

| Item | Own finite prototype value |
|---|---:|
| Terminal Cu / outer radii | 3.35 / 5.00 mm |
| Sense Cu / outer radii | 0.25 / 0.65 mm |
| Nominal centerline bend radius | terminal 50 mm; sense 6 mm |
| Derived centerline spacing requirement with own 3 mm surface target | terminal/sense 8.65 mm; sense/sense 4.30 mm |
| Actual complete-outer minimum gaps | 70.15, 82.50 and 10.70 mm |
| New route, Cu land/pin/lug, sleeves and connector-bank mass | 0.142416 kg |
| Full prototype with five modified barrier copies | 5.395234 kg |

Mass is counted once from finite signed volume with own density assumptions (Cu8960, polymer1200, TIM2500, Al2700 kg/m³). Independent tetrahedral integration differs by at most `4.49e-12 kg` per part. The five source-barrier copies are included once in the full prototype figure; original full-pack barriers are not added again. Neither mass figure is a complete pack mass or a retirement credit.

## Real holes and added space

The immutable G21 skin/TIM/coldplate/enclosure genuinely conflict with these paths. Independent source copies contain real 13.2 mm terminal and 3.4 mm sense bores, finite insulating annuli, and a 32×24×16 mm two-pin bank with actual bores. There is no same-owner waiver. These copies are a feedthrough proposal and do not replace the robot's frozen pack or shell.

This subset's local routing box is `[-430,-153,-57] → [-153.75,121,123] mm`. Combined with the prior complete mounted pack, the actual local envelope is **781.05×274×220.5 mm**. Compared with that original slot, lower-side extensions are X71.25/Y90.925 mm, upper-side extensions Y58.650239/Z24.7 mm. This already excludes the unbuilt remaining HV return/series links, full19 taps, BMS and clamps. Actual package space must grow or routes/components must be jointly redistributed; nominal case dimensions cannot cover this subset.

The first stock-minus-source water query used incorrect port datums and its zero gap is retained as a rejected diagnostic. Independent literal reconstruction from frozen `build_b.py` gives real candidate channel-to-bore gaps **2.875 mm (terminal)** and **7.775 mm (sense2)**, and no positive channel/bore intersection. This does not verify pressure, seal, thermal performance, thin-wall strength or the full water boundary.

## Evidence and replay

- `scene.json.gz`, `input_and_route_spec.json`: same-source actual finite geometry and path parameters.
- `native_signed_resource.json`, `typed_route_audit.json`: original topology, all pair volumes, holes, endpoint joins and spacing.
- `independent_typed_check.json`: independent signed integrals and pair check, without modifying source topology.
- `water_channel_literal_review.json`: literal-source correction to the earlier stock query; initial query remains in the original audit.
- `native_typed_route_four_view.png`, `native_cu_cutaway_four_view.png`, `native_feedthrough_sections.png`: actual native triangles and 0.5 mm slice geometry. Barrier clipping and explicitly withdrawn dielectric layers are visualization only.
- `final_receipt.json`, `freeze_manifest.json`: bounded scope, input/output hashes and replay commands.

To replay, copy the two exact Python producers to a fresh directory under this branch and run them with `/home/ethan/Projects/Sai_Rotbots/.venv/bin/python`. They use absolute frozen inputs and write beside the copied producer. Do not import the geometry builder or overwrite this frozen directory. The initial syntax-error source and render filename correction are preserved as exact history. No failed geometry was discarded.

Electrical ampacity/short circuit/creepage, true cell contact/vent, wire bend/fatigue, attachment and strain relief, fluid pressure/seal/thermal performance, remaining routes and full installation remain red lines. The configured 3 mm gap and own bend radii are geometric hypotheses, not manufacturer ratings. Whole M/COM/I and stable SI remain unqualified.
