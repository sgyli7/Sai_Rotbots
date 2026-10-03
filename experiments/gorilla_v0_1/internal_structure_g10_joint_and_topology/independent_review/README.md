# Gorilla G10 independent numerical review

This review tests the actual G8 B three-dimensional material mesh and G10 SIMP
implementation. It does not authorize a robot structure, a 3 t motion/load
capability, or a manufactured optimized carrier. The input B is a standalone
carrier bench; the whole Gorilla still requires actual shared spatial and
mechanical interfaces.

## Independent method and observations

`verify_actual_operator.py` implements Tet4 gradients from each native 3×3
coordinate Jacobian, tensor small strain, isotropic stress, and stress·gradN
nodal-force scattering. It imports no producer/root stiffness, engineering
Voigt strain matrix, sensitivity or solve functions. Producer displacement
fields are test inputs; this audit does not claim an independently solved state.
The implementation computes 8×8 internal energy, reconstructs all 42 original
case compliances with their individual rank-8 coefficients, and forms the p8
baseline-normalized adjoint weights and actual density sensitivities.

| Actual snapshot | Independent p8 | Total density volume | Maximum 8-basis original-force residual |
|---|---:|---:|---:|
| original full B material | 0.9999999999985 | 1.0 | 9.5953e−10 |
| corrected feasible uniform start | 1.5416165924441 | 0.85 | 9.4970e−10 |
| completed optimization step 4 | 1.1847710259829 | 0.85 | 9.8288e−10 |
| final completed step 12 | 1.1251440424841 | 0.85 | 9.8228e−10 |

For the baseline, feasible uniform and fourth-step fields, all 42
internal/external compliance differences are at most 1.9490e−11 relative.
The independently reconstructed baseline design directional derivative is
−0.6286564822584. The producer's independently executed ±0.001 state re-solves
give −0.6286571996846, a 1.1412e−6 relative difference. The positive branch above
density 1 is a derivative test only. The audit also performs its own central
finite difference of the material operator with frozen displacement; this
second check is not described as a re-equilibrated compliance solve.

Two hundred actual filter rows are rebuilt from native SI centroids and signed
tetra volumes using 15 mm cone weights. Neighbour IDs agree and weight relative
errors are below 1.9e−15. A random forward/adjoint dot-product check differs by
5.79e−15. Fixed-cell contributions stay on the filter right hand side; they
are not renormalized away. The affine volume derivative is separately checked.

`domain_constraint_review.json` checks all eight input hashes, actual 42-case
force reconstruction (8.4560e−15), rank-8 coefficients, and all seven original
interface tags. The conservative fixed band is reproduced without mismatches;
no tetra touching an interface vertex is designable. This is the documented
10 mm + largest loaded triangle edge + individual cell extent superband,
not an exact 10 mm CAD-distance band. It fixes 247,672 of 401,748 elements but
only 21.7798% of material volume. Existing walls are not all permanently fixed.

## Important corrections and limits

The full-density pilot is a material baseline, not a feasible 85% optimization
start: a move of 0.1 cannot reach that cap. Its incomplete first step was
explicitly retired by the producer. The corrected uniform design variable is
0.8030956454667, derived from the actual filtered affine volume map. The fixed
neighbour/filter constant contributes 23.8209% of baseline volume, which differs
from the direct 21.7798% fixed volume. The unfiltered shortcut 0.8082337 is not
the adopted initialization. Completed steps 0–12 retain fixed density 1,
the original forces, move limits and the filtered total cap (roundoff near
1e−14 is reported, not converted into false exact decimal equality).

The six QR gauge rows remove rigid modes in a balanced conditional free body.
They are not bearing clamps, static robot supports, or qualification of the
actual interface traction distribution. The audit checks the original full
operator, including those rows, rather than accepting only reduced equations.
Actual fits, contact, support preload, gravity, dynamics, yield, fatigue,
buckling, stress convergence and manufacturing remain outside these checks.

The density field is an ersatz continuum with p=3 and E_min/E=1e−6. Its virtual
31.7011 kg at 85% volume is not a true-void CAD mass. The objective minimizes
normalized compliance; it imposes no direct yield, buckling, minimum-wall,
tool-access, casting or manufacturing constraints. A p8 decrease and a bounded
12-step run are not a converged design or KKT/optimality certificate.

The improvement is measured against the feasible uniform-density start, not
against the full-material B. With material only removed, modulus never above
the original, and the same forces, compliance cannot improve beyond the
full-material baseline. The normalized objective starts at 1 for that baseline.
Any specific-stiffness proxy using mass and compliance is not a yield or load
capacity certificate.

The design domain is **only the existing B material**. It preserves all original
cavities and cannot allocate new ribs/material inside previous voids or use
the full thick-body volume requested for Gorilla. A future domain may do so
with real drive, energy, thermal, wiring, moving-interface and tool exclusions.
An exterior AABB is not an available internal cavity.

Binary thresholding is a different geometric candidate. Source code keeps all
islands and original loaded nodes and performs no repair/deletion. Its separate
connectivity, manifold, real-void mass and fresh force solve must be read on the
actual output when available; an 85% density cap does not guarantee a binary
85% material cap. Binary cell surfaces still need discrete/thickness quality,
remeshing/refinement and fresh mechanical checks before a CAD proposal.

## Actual final binary result: rejected

Final density SHA `b6d5a931e03f33aba07c0933be53f3261e4d9377c232e9485e970f333a157b12`
was independently checked against the original full 42 forces. Its largest
all-case operator residual is 3.3774e−9; internal/external compliance differs by
at most 4.2109e−11. All 13 completed snapshots satisfy the filtered total cap
within roundoff and the move limit within 3e−17. The twelfth maximum design
change is still 0.1: this run is not change-converged.

Binary SHA `0e2347c3ceb01a8dd184ed7cefab2250566c81f3641e62466fcd1879ba477dd6`
contains exactly the original cells with final rho > 0.5, plus every fixed cell.
Coordinates, tetra connectivity and positive-tet outward boundary inventory
agree with their original source arrays. All interface/loaded nodes are kept.
Independent actual material volume is 4.1995042193 L, or 32.9661081215 kg
conditional steel: **88.39187357%** of full B, exceeding the separate 85% binary
material target. This is distinct from the 31.7010951 kg virtual density field.

The 381,869 tetra / 100,597 nodes have two face-connected material components
of 381,868 and 1 tetra. The isolated cell is original element 255479, centroid
[0.0948410, 0.7459071, 0.3635882] m, conditional mass 0.0001929 kg. Thirty-six raw
boundary edges have degree 4. These original failures are preserved; there is
no island deletion, threshold adjustment, source replacement or true-void solve.

The raw Mesh64 kernel import unexpectedly returns NoError. Its exported
coordinate-triangle inventory is identical, but it changes the boundary's
75,837 used vertices to 75,879 (+42), makes all exported edges degree 2, and
reports one kernel component. That kernel topology normalization is not a
source-identity proof or permission to replace the raw mesh. The raw tetra
face-connectivity and edge gate still fail. Both query results and exact failed
edge locations are retained in `binary_strict_boundary_review.json`; the
kernel export is used only for this diagnostic comparison, never FE/CAD.

## Artifacts and reproducibility

- `baseline_actual_operator_review.json`: actual full-material operator/energy/filter/gradient comparison.
- `feasible_uniform_actual_operator_review.json`: actual corrected variable-E initial state.
- `optimization_04_actual_operator_review.json`: completed fourth-step variable-E state.
- `optimization_04_gauge_actual_operator_review.json`: the same snapshot with all 42 residuals and explicit rank-6 gauge-row residuals.
- `domain_constraint_review.json`: immutable source hashes, port band, volume map and completed-field constraints.
- `final_density_actual_operator_review.json`: final actual variable-E 42-case check.
- `binary_output_review.json`: actual raw true-cell inventory, mass, connectivity and interface retention.
- `binary_strict_boundary_review.json`: strict import/kernel comparison and unrepaired failure locations.
- `*_independent_sensitivity.npz`: independently recomputed physical/design derivatives and case energies.
- `verify_actual_operator_initial.py.txt`: exact earlier producer bytes matching the first three numerical reports; current script adds explicit 42 residual/gauge diagnostics.

The two initial audit-script exceptions are preserved in stdout logs: native
element IDs were initially mistaken for design-variable positions, and a
hash helper initially expected a Path rather than a string. Those auditor
implementation issues were corrected; they are not failures of source geometry
or physics. No old CAD, source mesh, exterior, producer density, frozen report,
Git or canonical robot data were changed.
