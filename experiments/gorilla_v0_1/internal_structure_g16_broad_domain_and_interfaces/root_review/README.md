# G16 independent review

Reviewed actual G16 A a8a09ca0 and B 99beca60; CAD/native/source identity, SI STEP readback and complete own-frame tensor. 130 bounded checks passed; 12 direct finite-material/shoulder contact queries passed as rejection diagnostics; 124 thermal arithmetic/source checks and 12 force-origin/rank checks passed. None establishes body, whole robot, appearance or physical acceptance.

Native frame alone is 62.935417805 kg at assumed uniform 7850 kg/m³. Frame plus the two separate native polygon anchors is 93.18942896070 kg. Source anchor declared CAD metadata is 15.131277 kg per side, while native integration is 15.127006 kg: these are different curve representations, not an installed rigid assembly or robot mass. The new frame does not contain the anchors; the old G15 alias convention cannot be copied to omit them. P45B new reference rows retain source maximum70g, which is not a justified lower/nominal mass.

Both same-source four views and interface four views were actually inspected. Original armor identity does not establish assembled aesthetics. B has two thermal-group reference overlaps with shoulders, 45 finite-material overlaps and service/owner/motion unknowns. At X=.115 the new frame and anchors touch with zero positive material volume. The actual plane normal-reaction basis rank3 cannot provide gravity shear; real joining is required.

Thermal S1 consists of source-sized complete segments, six fans, and a proposed low two-EWP150 series plus hot EWP80. The actual B source has not installed that two-pump upgrade. Manufacturer hot EGW curves, conditional cold sensitivities and conditional motor thermal derating are preserved separately. A30min nameplate requirement7.475–7.757kWh at assumed SOC window exceeds the 480-cell source minimum7.44kWh; no runtime is accepted. Fluid quantities use old line-length sensitivity, not measured G16 routes.

The force basis remains G15B27141 data. The first root comparison incorrectly compared patch-origin moments with world-zero moments; its exact producer/result is preserved under before_origin_scope. Corrected integration subtracts the explicit native patch centroid and passes all9 load cases. No discrepancy was found in the author's corresponding force-origin calculation. The equivalent nodal traction is not actual bolt/bearing pressure.

Latest interface producer, native source and render are selected. The author's first5f0b98 source/producer/render bytes were not retained; historical_binding_receipt records this gap. No before bytes are invented, and original237 part fields in latest source remain identical.

Continue G17 real connected broad cage, full shoulder pitch/roll/yaw assembly and coupled thermal working point. No new FEM/SIMP/GPU, default SI or external foot artwork is accepted by this checkpoint. Final biped+bimanual autonomous native Bevy tasks remain the objective.
