# Gorilla E first serial leg branch — rejected finite CAD candidate

Native scene SHA `3038d716403936e209bdb3d593260545b3294ceec1523b9945c755dcebf3e6df`; parent frozen D master `2933318e60dfe786f5cae61d88682519589f1eb5f8a23c999e6f7c6566cdd280`.

The candidate is an actual mirrored subassembly with yaw → roll → hip pitch → knee → fold → ankle pitch → foot roll → independent fore/heel bodies. Full stock-reference gear/motor/brake/encoder/controller envelopes remain unscaled. Separate finite walls and support material are included; body names do not establish connections. This is not a complete robot or qualified serial leg.

Neutral 477 parts: all watertight, winding-consistent and positive volume. Five actual poses are supplied; the unloaded independent fold has 461 parts because inherited unlocked-lock omission is a diagnostic limitation. Native projection is candidate-only without original armor, not a revised aesthetic baseline.

| Pose | Cross-body material pairs | Original armor material pairs | Old D ankle/foot+seal target pairs |
|---|---:|---:|---:|
| neutral | 18 | 40 | 0 |
| crouch | 18 | 38 | 0 |
| serial_lateral_probe | 18 | 36 | 0 |
| deep_crouch_rejection_probe | 20 | 42 | 0 |
| unloaded_independent_fold | 18 | 42 | 0 |

The 40 neutral table entries are actual 7850 material body-union × individual original-armor mesh pairs in the posable pelvis/leg/foot subset. They are not 40 unique armor meshes. The later 42 count is a separate test: complete non-material reference-component envelopes × all 111 original-armor meshes in neutral, including chest/back pieces outside the leg subtree. It is not 42 material pairs or a revision of 40; both row lists are preserved separately.

Zero old-target pairs is a narrow geometric closure, not whole-foot acceptance. The largest neutral new intersection is hip-roll-carrier against hip-yaw-carrier: 84.936 cm³ per side, bounds X[-.160,.0493], left Y[.168,.4365], Z[1.6279,1.8359]. Foot-roll arch against heel is 42.311 cm³/side; against forefoot is 19.713 cm³/side. Distal to ankle carrier is 2.295 cm³/side. These real material pairs prevent integration as a valid moving mechanism.

Conditional actual metal union mass: 401.844 kg at 7850 kg/m³. Reference constituent mass range: 99.145/108.109/124.693 kg. The branch partial sum is 500.989/509.953/526.538 kg; armor/pads, upper body, all fluid/energy/thermal hardware remain excluded. No arbitrary discount is applied. Union for collision/mass does not prove welded/bolted connections.

Finite-cylinder sampled working strokes (design, not OEM): hip71.653, knee123.158, fold49.401, new ankle37.276 mm. Allocated custom zero-eye lengths254.575/300.877/207.846/227.796 mm. Each range includes10mm end allowance; OEM zero lengths and installed rating unknown. Hip/knee/fold preserve D eyes; ankle pitch is moved80mm up, output crank75→140mm. Endpoints are rebuilt under serial transforms; hydraulic parts are not rigidly attached by gravity-owner body.

Complete-reference components intersect 42 original armor pieces/pairs in neutral; full bounds are in branch_summary.json. This probes my industrial/reference placement, not AA3 impossibility.

## Required macro decision before more geometry

Parent frozen-D contact/drive LP has common normal minimax1.244–15.941, nominal neutral unloaded1.412. Hiproll witness862.8Nm vs611 and footroll251.3Nm vs178 reject blind retention of these reference capacities. The foot witness is not its independent minimum when waist controls the objective. Forward unloaded waistpitch1915.8Nm,100kg2680.4Nm,3t pressure9220.5Nm vs611 means the upper-body route must change too; 3t is not carry rating. Changed E geometry/masses require a fresh LP.

Rigidly reusing the complete CSG65/QTL210 reference kit along hip-roll +X gives a 294×280×280mm pack versus current281.75×210×230mm; this is a dimension probe, not an interchangeable qualified installation. Reusing the complete CSG50/QTL160 reference kit at foot roll gives281.75×210×230mm versus current253.75×176×213mm, with bare gear/motor mass increase5.7kg/side. A stock-reference hiproll CSG65/QTL210 would demand a complete custom-case diameter280mm (current210), gear+motor axial sum grows65mm and bare component mass grows16.187kg/side, before cases, bearing interfaces and thermal overhead. A stock-reference footroll CSG50/QTL160 would demand210mm complete case diameter (current176), gear axial+28mm: with current centerZ.220 and ankle output bottomZ.315 it overlaps vertically10mm. A3mm gap needs roll center≤.207 or anklepitch another≥13mm higher; the present cradle inner width is7.5mm too narrow per side, so cradle centers need≈±.130m rather than±.115. These are explicit next-layout dimensional constraints, not a new accepted gear selection. Increasing gear ratio, long-arm linear actuation or changing whole reaction/axis routes remains root decision.

The minimal next physical layout is a jointly reworked pelvis/yaw/roll/pitch package and ankle-pitch/foot-roll/independent low-foot package with complete interfaces and new mass/contact LP. Do not Boolean-cut the parent chain or enlarge AA3 armor automatically.

## Remaining failures

- Hip yaw/roll/pitch nested bridge crosses different moving material; no qualified serial load path.
- Finite load-case/motor-case/output-adapter pairs remain disconnected or intersecting; source output interface gaps are not bridged by body naming.
- Footroll arch intersects heel/fore moving support and ankle-pitch carrier even though the old seven D bearing-house targets are cleared.
- Low-foot locking tongues are omitted by inherited function for unloaded folded diagnostic; actual retractable lock motion not qualified.
- Original armor actual material intersections remain; neutral complete stock references checked against all original armor here, but upper-body dynamics and all reference clearances not closed.
- Original C15 hardware not all modeled or retained in this subgraph. No whole-robot retained-row assertion.
- Mirrored E_metadata/source labels retain some left-reference labels; mirrored coordinates/winding are correct. Metadata normalization required before canonical integration.
- Custom material 7850 model is not material/FEA/joint/drive verification; no 3t load acceptance.
- Changed E joint axes, new masses and exact root alignment require fresh full contact/drive LP; parent frozen-D LP is reference evidence only.
