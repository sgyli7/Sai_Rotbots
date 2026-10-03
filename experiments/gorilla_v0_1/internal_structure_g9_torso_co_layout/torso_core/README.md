# Gorilla G9 torso core A/B — rejected assembly probes

Frozen whole context: `07b79df0e08ffebc17ab124c4b3ac6f8bdc0a8e39f603447f2c98fc30ffad5c2`. Exactly two historical F1 torso pieces are replacement candidates; all 1792 other dictionaries/world meshes remain unchanged. `e2_upper_net_torso` (77.937 kg conditional historical steel bridge) is retained and not silently credited. AA3 and original armor changes: 0 mm. This is internal evidence, not new approved art.

| Candidate | Exact CAD steel kg | Native gate | Original-position positive probes | Armor probes |
|---|---:|---|---:|---:|
| A | 114.334853 | reject | 212 | 14 |
| B | 77.776102 | pass | 119 | 10 |

A is a full 6 mm closed box, two continuous 6 mm ribs, genuine through installation opening and finite shoulder/waist nodes. Raw STEP is valid one OCC solid, but four boundary index edges at the shoulder bore/skin tangent form a pinch. The strong native refusal is preserved; CAD/kernel acceptance does not override it. No source normalization or face deletion was performed.

B is the sole alternative: two 6 mm closed lateral load shells with continuous internal webs, upper/lower closed ties and the same historical shoulder/waist finite nodes. It has valid STEP, one actual material solid and strong native pass. Its 103875 positive tetrahedra have minimum mean ratio 0.177902 and CAD volume error +1.73624e-5. This licenses only a conditional resource probe; no strength or full assembly acceptance.

All nine whole groups are represented at exact original positions and retain full dimensions: four energy groups, two complete pump groups, HX, compute and screen. B has no intersections with the four energy/two pump/compute/screen groups; HX has two. B still conflicts with old shoulder gears/cases, historical upper bridge, waist equipment and ten original armor pieces. Its larger original shoulder cap probes are about 81.26/81.21 cm³. The old allocation is a comparison, not a restriction on new complete-group placement owned by the separate agent.

The six energy/pump gross boxes sum to 130.591499 L against the old outer box 130.152 L, before 30 L oil, HX, water, air paths and service. Gross AABBs are not free cavity, and their overlap/rotation means this is a volume challenge rather than an impossibility proof. Actual material queries and actual triangle-plane sections, not hulls, were used against original armor.

Raw positive counts are explicitly probes: gross component envelope, old finite materials, armor, nonphysical service windows and fluid inventory are separated. Coolant/oil inventory intersections cannot be classified as metal exclusion. All 249 preexisting native contract refusals remain, so a successful raw kernel operation is not a qualified true material collision for those rejected members. `service_access_probe.json` checks 90 explicitly declared access boxes and records interference with required clearance, not fabricated hardware. Intake/plenum/exhaust/radiator wall meshes were queried; lumen flow, tools, hoses and actual thermals remain open.

Historical waist: actual vertices pivot [0.230,0,1.910], axis X. Parent adapter outer/inner radii 80/30 mm and new boss 100/40 mm have a maximum common coplanar annulus r40–80 mm at X=.2475, area 0.0150796447 m². The physical-group whole plane includes neck faces and outer unsupported ring area; it is not wholly a contact/traction port. Fasteners, stress distribution and fixed/output compatibility remain unknown. Historical shoulders X=-.130,Z2.290,Y±.560 use candidate mate planes ±.51826221; neither a new full joint nor frozen robot axis.

The shoulder ports are AA3/C15 historical lines, not matched old E2 full drive interfaces: actual stock gear/motor center Z2.360 differs from candidate Z2.290 by 70 mm. Old gear Y .39825.. .52175 is 123.5 mm long, a known 8.5 mm error against the 115 mm reference. Candidate Y .51826221 came from the old pitch carrier geometry, not the gear fixed face. No axis/length/interface match passes; this requires whole shoulder drive remounting, not trimming armor.

Exact CAD mass, COM and full world inertia at COM, finite source components, source hashes, mesh receipts, classified pairs and unknowns are in report.json/cad_manifest.json. The current core mass cannot be subtracted wholesale from all previous structure: only the two exact replacement IDs are nominated. Materials remain conditional 7850 kg/m³ steel. No FEM or topology optimization was run.

Images: a/native_four_view.png, b/native_four_view.png and actual_internal_sections.png were actually viewed. They are the same-scale source geometry, with all nine modules present, and explicit internal-only hidden lists. Sections draw literal triangle-plane segments at Y=.310 and Z=2.290; no declared new exterior. Two macros are complete and stopped; B remains a rejected full assembly candidate until core/shoulder/waist/system interfaces and true material conflicts are resolved by root.

Reproduction: isolated G7 runner + build_torso_core.py --variant a|b; mesh_torso_core.py; normal .venv check_core.py; render_core_context.py. Builders refuse existing source directories to preserve frozen versions. finalize_evidence.py is a read-only checker/report generator and does not change CAD or retained geometry. New complete-group placement must be rebound and rechecked separately.
