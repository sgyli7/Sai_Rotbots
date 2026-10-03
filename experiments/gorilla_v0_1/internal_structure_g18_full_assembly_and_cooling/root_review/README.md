# G18 full-source integration review

Gorilla V0.1 internal engineering checkpoint, 2026-10-03. Full-source assembly, physical capability, styling and stable SI remain rejected. This checkpoint retains actual improvements and explicit failures; it does not install a model or change training/control contracts.

## Bound sources and current composition

Body B `7102db0e…` plus shoulder/arm A `bd94b65f…` or B `7425523c…` yields 2583 part records in each actual composed scene. Current composed sources are A `61825d70…` and B `9873e9db…`. Each present record is assigned once to the mass/functions inventory or explicitly excluded as service/fluid alias. Old lower-body geometry is a historical placeholder: user supplied two new lower-body art revisions, still being corrected. After art acceptance this project reconstructs the common engineering geometry; external CAD delivery is not a mandatory dependency.

The original 111 armor records remain byte-identical, for comparison only. Actual source-rendered bare and armor FRONT/LEFT/REAR/TOP were inspected. Complete drives and cooling stocks visibly extend beyond the existing skin, especially rear/top, shoulder and elbow. This is not a proposed accepted exterior, and shell identity cannot prove internal fit or preservation of assembled silhouette. No new lower-body art is represented in these views.

## What improved and what blocks installation

Body B has one continuous own cage/receiver material root, conditional native mass 94.691083 kg at assumed steel density 7850 kg/m³, with COM and full tensor independently checked. Real pack ports and mounting holes are incorporated; local pack finite-material queries have no positive intersections in their limited scope. The current receiver face and holes are actual geometry, but the hole at PCD270/r135 opens into the Ri132 bore (inner ligament -1.3 mm); washer, bolt preload, threads and reaction path are unqualified.

Frozen body's local finite-material classification omitted three original load-hold metal guards because it relied on flags and density fields. Their material role and independently closed positive-volume meshes confirm they are real hardware. The full-source check reproduces waist guard×cage 3.811523 and 4.341835 cm³, right hip guard×oil shell 1.678561 cm³, plus guard×working oil 1.457624 cm³. The frozen author report is preserved; independent classification correction is explicit, not an erased failure or same-owner exemption.

Shoulder/arm A and B retain full motor, gear, brake, feedback, controller, cooling and connectors. B still has four rejected native material resources and own load-path CAD roots 2/3/1/2 for pitch/roll/upperarm/forearm on each side. The valid right yaw keeper also intersects the valid upperarm housing by 3.048684 cm³. Complete service extraction groups fail. The new shoulder×body-only neutral query returning zero does not certify the rest of the assembly.

Root B changed/moved-versus-all neutral diagnostic tests 5061 AABB candidate pairs and preserves 955 positive results with separate armor/reference/fluid/rejected-resource classes. There are four valid finite–finite positives and one finite–fluid positive. Unchanged-versus-unchanged pairs, motion sweeps and assembly paths are not newly qualified. Kernel construction alone does not legitimize the four rejected source resources.

## Mass and actual axis loads

1447 retained historical mass rows transport only through indexed proper rigid transforms. Complete OEM mass is never divided among artificial subparts or treated as uniform material. Partially retired own unions are recomputed only where legal density/material geometry is known; otherwise remaining functions stay unknown. 480 cells keep only their 70 g each upper bound: low/nominal masses are null, upper total 33.6 kg. Rejected material and missing four hydraulic cylinders remain unknown, not zero.

Conditional known/proxy subset sums are A 1538.542/1721.022/2026.113 kg and B 1520.180/1702.660/2007.751 kg. These are not total robot mass or credible upper bounds: absent/unplaced functions remain, fluids are one global budget proxy with unknown distribution/COM, and old lower legs remain historical. B's lower partial sum partly reflects more invalid uncounted material, not weight reduction. Whole mass, COM and inertia are null.

Eight actual candidate axes have independently recomputed six-component gravity resultants for the three numeric subsets. Maximum independent residual is 2.05e-12. All 422 unmapped-owner rows are explicitly listed globally and at every joint, including retained forearm armor and unsplit drive/bearing owners. Numerical subsets exclude them and cannot be called complete joint loads. Payload, dynamic/contact loads, hydraulic reactions and tonne pressure are not certified by this check.

## Complete cooling and same-task energy

Final thermal source is v3 `f3a08516…`. Body inventory binds to the complete split-loop layout: 6 ES0707, 1 ES0714, 8 full fans and 2 WP32 stocks, with original series-pump functional group explicitly retired. Geometry remains a full installation stock, not OEM net-material CAD. New actual routes, TIM, pump feet/eye location and air sealing are absent. Source-required flooded 25.4 mm suction is unproven; stock-centre height is not NPSHa. Cold-fluid pump/core curves, NPSHr and case pressure remain unknown.

At 35°C ambient, original duty and source-upper auxiliary input, sensitive EMRAX supply conditional ROM is 41.40–46.85°C; high concurrency can reach 51.29°C. Other motor mounting/coldplate temperature requirements remain unclosed. Same air-point theoretical fan head is 186.742 Pa; worst shared rotor branch needs 215.137 Pa. The 28.395 Pa shortfall and absent real sealed duct remain red. Theory is not a measured PWM point and no 53 W fan energy credit is taken.

Complete auxiliary source upper is 3.1575 kW at 28 V (3.2775 kW at 32 V). The 480-cell 7.44 kWh lower nameplate reference cannot close the original 30-minute duty plus 10% reserve: requirement 9.111–9.469 kWh at 28 V; conditional duration 24.50–23.57 min. Actual pump input at 12/47 L/min is unknown; source upper is conservative, not an achieved rating. No endurance promise or new cells are silently adopted.

Root independently checks 133 identity/conservation/pressure/air/energy/ROM arithmetic conditions. This is numerical scope only. An initial evaluator wrongly applied 0.5 h to a 1 h sensitivity mission; exact producer/results are preserved, and final evaluator reads actual source duration. Geometry was unchanged by the owner-list correction; exact before sources/reports and invariance receipt are retained. No FE, CFD, GPU or historical expensive rerun.

## Next architecture exit

Both shoulder macros are stopped. Next comparison must address a complete pitch→roll→yaw→upperarm reaction and installation chain, actual input/output ownership, full drive stocks and skin envelope together. Compare a directly integrated load-bearing actuator/housing with a proximally concentrated drive/remote transmission route, preserving all functions and bounded physical requirements. Do not add a third patch to the failed housings or claim topology optimization can fix drives, energy and service space by itself. Uncertain custom capability stays a red evidence gap until credible mechanical/thermal ranges exist; only procurement absence may remain yellow.

Root outputs are frozen by `freeze_manifest.json`; selected byte restoration is separate from geometry regeneration, omitted publication retrieval and physical qualification.
