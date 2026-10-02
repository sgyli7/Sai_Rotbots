# Gorilla E2 first selective hybrid structure candidate — REJECTED

Source `baf16ef2e19272f18ae95aa9d94d7e0416e583bcca32c98fefe5abb1ca787618`. Native geometry identity `2d1ad3a757845ae21259cc66b83e0ccd5847efec093ad3b9e1d540a186700856`. Metadata-only pad-ID correction preserves every vertex/face/name/body/role in all five poses.

Actual CAD contains587parts per pose, serial waist yaw→pitch→roll and pelvis→hip yaw→roll→pitch→knee→fold→ankle pitch→foot roll→independentfore/heel. Complete4rotary reference kits are unscaled;18hydraulic cylinders include actual barrel/caps/rods/eyes, moving crank mounts and support envelopes. This is finite material CAD, not qualified bearings/fasteners/welds/actuation or a stable SI contract.

| Pose | material pairs | armor pairs | disconnected frame groups | metal kg | endpoint max error m |
|---|---:|---:|---:|---:|---:|
| neutral | 167 | 129 | 13 | 661.475 | 1.39e-17 |
| crouch | 167 | 135 | 13 | 661.476 | 0 |
| forward_manipulation | 169 | 131 | 13 | 661.476 | 1.39e-17 |
| small_lateral_tilt | 165 | 121 | 13 | 661.475 | 5.55e-17 |
| unloaded_independent_fold | 171 | 141 | 13 | 658.114 | 1.39e-17 |

The first candidate fails. Neutralhiprollfixedcylinder↔thigh86.57cm³, distalframe↔ankleoutputcarrier45.37cm³. Thirteen framegroups have2–12positive materialcomponents; fork ownership/bodytree does not create a material bridge. Pins and bearing clearance candidates are separately represented; all positive pairs, including same mass-owner body and presumed connections, remain in checks.json.

Neutral actual metal net661.475kg plus reference constituent ranges[80.973,92.663,118.463]kg givesbranch[742.448,754.138,779.938]kg. This excludes14armkits,16hand/upper,energy/heat/line/fluid/originalskins/mainpads and retained20unresolvedcontroller/encoder/brake/connector rows[8.600,15.250,28.250]kg. Exactdensity7850kg/m³ assumption; steel net isunion perphysicalassembly, not sum of overlappingpieces. Unqualifiedstructural dimensions/material/joints remainred.

Eighteencylinder finite eyes haveallfiveposeerrors≤5.6e−17m and no designatedworkingmarginfailure. This does not prove force/torque, zero-length vendorcompatibility, holdcapacity, hydraulicflow/heat, or jointcouplingfeasibility. Axis/anchor changes invalidate macro/D LP mapping; rootmust solvewholecandidatewithnewmassesandaxes.

Fold endpoint brace nativeplunger reconstruction loses3.361kg vsneutral. All16locksremain andwithdraw110mmY; loss isnotunlockmassdeletion. Fold material identity isfailed andmust not be treated as a constant-mass motion proof. Existingnative defect is preserved for audit.

Original111armor meshes are reference-only and unmodified. Neutralnet-material×armor129pairs differs frompackagingprimitive289pairs; neither isunique armorcount. Knowntraywall contacts include9mmsteelpadtray underrail/heelhousing; arbitrarily clipping originalarmor or acceptingoverlapisprohibited. Fourmainpadsareunchangedcomparison; forepadupperedge2nonarmorproxies are explicitlyreplaced. The sourcefields now nameactualleft/rightfore/heelpads.

Raisedhipyaw[−.250,±.354,2.025] and waist[0,0,1.87]/[0,0,2.07]/[.125,0,2.30] conflictwitholdinstalledpackaging. Old30Loiltank→waistpitchcarrier1.815L and oldleft/rightlowerHVpacks→pelvis603.217cm³ each. These conflicts require coordinatedrear/waist/hipandenergy relocationor newcarrierconcept, notisolatedpatches. Actualmaterialintersectionbounds inreport/checks definewhere. Conservativeoneaxis AABB separationnumbers inreport are sufficientbox probes, not minimaltruegeometryor AA3-requiredouterdelta. A nextsinglewholecandidate must rebuildfullreactionpathandwholepackageplacement, not deletecontroller/energybulk orblindcutparentchain.

Fourfullstockelectricgroups areuniquelyreplaced. Fivehydraulicconvertedgroups removegear/motor/housing/input/output/carriers only;20oldbrake/encoder/controller/connectors retainmass withunresolvedmounting. Newholdvalves do not automatically replaceoldbrakes. Newhydangularandlinearsensorcoverage remainsred.

Neutraloriginalarmorwiredprojection andeachposebare3views aregenerated fromactualnativecoords. Bodyassemblydiagnostics explicitlyshowpieceownershipanddiscontinuities; no componentcount provesratedstructuralcontinuity. Posedarmorwithunmappedupperbodies islistedandnotdeclaredcompletewholemotion. Actualoldcontextcheckonlyneutral; referencecomponent-vsarmor/newmaterialfullfitcheckstillunknown.

Nofourthphysicalgeometryvariant wascreated. This branchisfrozen asfailedcandidate. AA3necessaryouterchange,aestheticapproval,3tpressure/carrycapacity,manufacturing,stablecontract andcomplex-taskcapability arenotestablished.
