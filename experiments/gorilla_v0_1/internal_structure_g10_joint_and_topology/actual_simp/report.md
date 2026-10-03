# G10 actual 3D SIMP tool experiment

Real source: frozen G8 B, 401748 tetrahedra, 104847 nodes, original material mass 37.295406 kg. Only existing B material is designable; the original voids and seven load/interface surfaces remain. This is conditional stiffness exploration of this component, not a whole robot or tonne-load qualification.

All42 original literal balanced nodal loads remain, reconstructed from the same8 actual load columns. Their original ±25°/neutral poses, CoPs, 1/1.5 factors and reaction hypotheses are retained without force projection. Six gauge DOFs remove rigid modes only; they are not bearings or robot supports.

Uniform steel E=210GPa, nu=.3, SIMP p=3, Emin/E=1e-6, exact volume-weighted conic centroid filter15mm, OC move=.1. Non-design material is 21.779781% of the baseline volume: all actual loaded/interface cells and a deliberately conservative10mm surface neighbourhood. The radius is a numerical filter, not a manufacturing minimum wall guarantee.

Variable-element modulus assembly vs independent scikit-fem numerical cube: relative matrix error 5.885e-16. Real B full-material iteration0 uses G8 fields as an already-converged warmstart: U relative difference 1.134e-14; it is not a new independent cold solve. Actual filtered-direction FD relative gradient error 1.141e-06.

The pilot x=1 first move could not satisfy cap=.85; its incomplete first-step density is retained as rejected history. Adopted initialization solves the exact filtered affine volume equation, x_uniform=0.803095645, giving total volume .85. That same-inventory uniform model is ersatz, not a manufactured same-mass solid.

| State | Density inventory kg | True binary kg | p8 relative compliance |
|---|---:|---:|---:|
| Original B full steel | 37.295406 | — | 1.000000 |
| Feasible uniform ersatz | 31.701095 | — | 1.541617 |
| Final optimized ersatz | 31.701095 | — | 1.125144 |
| Fixed-preserving rho>.5 true void | — | 32.966108 | not solved: material admission/timebox rejection |

Completed 12 OC steps; change convergence=False. No extra iterations, island deletion, bridge repair, threshold tuning, added material or OEM movement. Binary actual mass is 88.391874% of B, independently checked against the cap: False. Face-connected components and boundary gate are in binary_native_gate.json. Strict oriented-boundary/kernel result is Error.NoError; kernel conversion NoError/same-volume=True, original native source resource admission=False. Constructor output topology is separately counted and never adopted as a repair of the original36 bad edges or2 face-connected components. A successful numerical solve would not close real bearing/pin/stop contact, pressure distributions, fit, yield, fatigue, buckling or manufacturing.

The projection PNGs use actual tetra boundary triangles at the same scale, with approximate face-depth occlusion. They are neither AI exterior concepts nor CAD qualification. Physical density is virtual modulus and inventory, not actual wall thickness. The full density/true-void meshes, histories, all42 compliance/field diagnostics and unchanged source hashes are stored separately.

Formula references: [DTU Andreassen et al.2011, equations1–10](https://www.topopt.mek.dtu.dk/-/media/subsites/topopt/apps/dokumenter-og-filer-til-apps/topopt88.pdf); [scikit-fem official docs](https://scikit-fem.readthedocs.io/en/stable/). Selfwritten 3D adaptation; no copied third-party optimization source.
