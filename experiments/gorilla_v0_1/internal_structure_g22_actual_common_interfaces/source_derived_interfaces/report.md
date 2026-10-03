# Gorilla G22 source-derived interface receipt

This is a read-only interface extraction from frozen rejected candidates. It
does not create a new shoulder, adopt an exterior, change the SI/control contract,
or qualify material, assembly, drive, bearing, cooling or mass replacement.

The stable machine contract is `source_derived_interfaces.json`, SHA256
`a021be1dae460bda190717c9bceb289265e2a895a5080988a754886ffc0c90aa`.
Its `input_bindings` contain exact paths and hashes. Principal sources:

- G21 joint B: `6652a6669b6922e74f3faaaaf96c94dcc876eb8da35c8e6fea66952ed4f2645f`, 110 parts, 65 finite material candidates.
- G21 whole-body B: `683da8b329db49bdd25a36725a71619eb92b4646f090da033e3430840e0d94cb`, 3003 parts.
- G21 functional review: `a1e2f8f5406f0793328d167d18f3b445e7f51a75dcd4ac100a8682f8bcd828e2`.
- Original erroneous geometry producer is preserved byte-for-byte in
  `preserved_input_producers/joint_producer.py`, SHA256
  `99ad7ce1f82e221a2b18b6552a3620918ae35b4f2c7fd10ec1c3d0f6232fb028`.
  The material-gate producer `d41f644a…` is the checker, not this geometry producer.

## Actual geometry versus planned interface fields

The signed axes below are explicit G21 scene design datums. Scene
`joint_interfaces` and the corresponding `interfaces.json` axes agree. Circular
native geometry corroborates the **unsigned axis line**, not encoder/action sign.

| Joint | Source pivot, m | Source signed axis | Input center spacing, m | Actual output centers, m | Actual output spacing, m |
|---|---|---|---:|---|---:|
| pitch | (−.040, .515, 2.405) | (0,−1,0) | .0645 | (−.04,.565,2.405); (−.04,.625,2.405) | .060 |
| roll | (−.080, .700, 2.235) | (1,0,0) | .0645 | (−.13,.7,2.235); (−.19,.7,2.235) | .060 |
| yaw | (.020, .740, 2.030) | (0,0,−1) | .0475 | (.02,.74,2.08); (.02,.74,2.14) | .060 |

The stale `output_bearings.geometric_spacing_m=.063` and its old center pair are
preserved separately from the actual .060 native center separation. Neither
separation is a bearing pressure-center separation. Preload, arrangement,
pressure-center locations and reaction/load split are unresolved.

`actual_native_mount_bolt_and_bore_groups` contains all 48 native CS bolt
centerlines, PC195/150/150 mm groups, native shaft/head radial levels and 192
matching bore vertices per receiving hole. Pitch receiving material passes its
inherited resource check; roll/yaw receivers retain their two source resource
rejections. These remain prototype smooth bolts, not established threads,
preloads, OEM internal mounts or qualified contact.

`part_native_envelopes` gives all 110 native bounds and individual CAD-row
correspondence. `actual_vs_planned_installations` distinguishes their larger
actual principal-plus-reference envelopes from the old plan boxes; swept bounds
are only plan queries, not an installation/removal pass. Brakes, feedback,
controllers, fluid/power loops remain complete gross reserves or incomplete CAD.

## Core attachment and waist boundary

The actual joint X=.115 terminal plane is an unbored rectangle:
Y=.345..565, Z=2.275..2.535, area .0572 m². The existing body plate surfaces are
X=.112 and .124. Projected common area is only .0091 m² at either surface, with
plane offsets −3 and +9 mm. Combining the actual finite native solids gives
44.681414 cm³ material overlap. Common-owner labels and projection cannot turn
this into a joint.

The six existing body holes have native R8 mm, Y=±.300 and Z=2.280/2.400/2.520;
64 native bore vertices corroborate each datum. None matches a hole on the joint
X=.115 terminal face or falls inside its left-side common strip. A subsequent
jointly designed receiver/core needs actual material and fastener/seat interfaces,
not loads spread over the entire planned rectangle.

The current cage's waist annular producer datum is center (.238,0,1.91), axis X,
R145/R72 mm, axial .020 m. Actual partial terminal surface patches are at
X=.228/.248, each area .044059293 m². They differ from the old adapter/interface
assumptions. **No waist-roll rotating output adapter is present in this whole
source.** `f1_ds_waist_roll_gear_load_shell` belongs to fixed
`waist_pitch_carrier`; it is not an output adapter. Its finite mesh query with
the new cage is 30.832815 cm³, with source qualification unresolved. Actual
rotating-output mating patch is null. No legacy .2475 plane, full annular mate,
fixed-shell alias or load/pressure allocation is inherited.

## Bilateral insertion, retirement and downstream FK

The 3003-part body contains **zero** of the actual 110 joint part IDs. It contains
six mirrored planned protection boxes plus both old shoulder function chains.
The 110-part joint source is one **left** three-axis source. Its single
`g21_b_core_fixed_receiver_continuous_candidate` occupies positive Y only and has
own CAD material inventory 13.994230 kg; it is not already a bilateral receiver.
The body `g21_wide_closed_load_cage_net` has bilateral plate occupation and must
be counted once (114.239508 kg conditional own steel inventory). A mirrored
reaction receiver creates more actual material; a new shared union must be
generated/measured, rather than silently supplying a second shoulder with the
left receiver's single mass.

`bilateral_replacement_contract.conditional_geometry_probe_retire_ids` is the
exact, unique 290 **source-present** nominated IDs, partitioned as:

| Scope | Count |
|---|---:|
| Original G13 complete bilateral pitch assembly | 186 |
| Old roll/yaw complete module sets | 28 |
| Old pitch/roll/yaw cooling cases and ports | 18 |
| Old pitch→roll / roll→yaw compact transition housings | 4 |
| Old roll/yaw output bearings, keepers and FS attachment bolts | 48 |
| Six planned new-joint boxes | 6 |

This is a **conditional geometry-probe replacement list**, not authorized
functional or mass retirement credit. `qualified_function_retire_ids=[]`:
brake, feedback, driver, true cooling ports, FS attachment/keepers and interface
closure remain unresolved. The six planned protection boxes add no hardware
mass. Old elbow/forearm/hand function is not retired. The exact retained rebind
set has 112 parts; strict direct `left_upper_arm` / `right_upper_arm` sets each
contain 23 IDs, including 7 complete elbow modules, cooling, harnesses, arm
housing and existing visible armor. All original 111 visible armor IDs remain
listed for preservation/context, not appearance acceptance.

For a reflected right candidate, S=diag(1,−1,1): points use S, angular axes use
det(S)S for the same abstract joint angle, and triangle winding reverses. This
produces candidate right pitch (0,−1,0), roll (−1,0,0), yaw (0,0,1). It does not
adopt right actuation/encoder signs or an old FK convention. Right native
instances have not been generated in this task.

`actual_output_terminal_interfaces` gives source-terminal planes and triangle
IDs. The yaw terminal is Z=2.207, X=−.0275...0675, Y=.671...809, area .01311 m²,
normal +Z, no implemented terminal mounting holes. New yaw output body is
`left_shoulder_yaw_carrier`; old yaw directly owns `left_upper_arm`. Adding the
new carrier requires an explicit fixed rest transform to the full downstream
arm, actual attachment geometry, then dependent FK/COM/inertia/wrench/limit/sign
rebuild. Elbow (.02,.74,1.740) is a design datum only, not a connected arm.

## Preserved shaft error and minimal next source correction

The producer unions a Ø24.9 mm primary input shaft across WG engagement, then
adds a reduced cylinder inside it. Adding an inner cylinder does not remove the
existing larger shaft. Actual radial intrusion is .45 mm at the pitch Ø24 bore
and 2.95 mm at the roll/yaw Ø19 bores. Queries against protected WG gross meshes
are .828977 / 4.878739 / 4.878739 cm³. They indicate an envelope/interface sizing
error; gross rings are not evidence of actual OEM internal-material collision.

The minimal correction boundary is the producer's primary shaft axial interval
and true reduced WG engagement before union, jointly with the key and transitions
to 25 mm bearing/rotor-holder seats. Recheck retained dimensions, material
continuity, torque/key, keeper, initial assembly and extraction. No OEM bore is
enlarged, no datum or bearing pressure center is fabricated, and no source repair
was made here.

## Reproduction and limits

```bash
.venv/bin/python .scratch/gorilla_internal_g22_source_derived_interfaces/extract_interfaces.py
.venv/bin/python .scratch/gorilla_internal_g22_source_derived_interfaces/draw_native_interface_sections.py
```

The extractor verifies expected frozen hashes and part/CAD/checker identity,
preserves producer bytes, projects original triangles, measures vertex radial
levels, and makes local Manifold material or protected-envelope queries with no
mesh normalization or repair. Face IDs refer to source triangles; areas are
native discretizations, not certified effective contact areas. The section image
was actually viewed and shows literal source planes/sections. `finite_validation`
keeps three expected plan-vs-geometry mismatches false rather than normalizing
them. Geometry extraction is not an independent whole-source material gate,
motion/maintenance pass, connection design, electrical rating or physical
admission. The old lower body is still historical context. All physics decisions
remain with the parent task.
