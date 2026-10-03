# E2 hydraulic working points — independent neutral audit

Checked UTC: 2026-10-02T20:18:52.844648+00:00. Only candidate interface geometry is recalculated. No full model/evaluator run. Interface SHA256: `beb99c1c27cdc6b8349912d4cf3a150e9db028e04662a8ee9e7790423ad40fd7`.

Actual interface has 13 hydraulic axes /18 cylinders. Historical macro38.322 L/min at+.1 is superseded by the actual neutral geometry: waist cylinders both have J=+.12537168 (same-direction extension), ankle J=.09388110 (D macro .06410431). No D static load witness transfers to the changed E2 body tree.

## SI formulas and direction

`J=u·(axis×(B−pivot)); v=J qdot; Ac=πb²/4; Aa=Ac−πr²/4`. Extension supplies cap area and returns annular area; retraction supplies annular and returns cap. Flow conversion is60000 L/min per m³/s. `F=p_cap Ac−p_ann Aa` is positive extension. `τ_act=ΣJF`, `P_mech=ΣFv=Στ_act qdot` keep signs; pair force sharing remains unknown. Direct neutral derivatives agree with interface samples and independent central differences to max 5.74e-11 m/rad.

|Actual neutral sensitivity|Supply L/min|Return L/min|21MPa pQ kW|Equal dual-pump rpm at ηv=.97… .90|
|---|---:|---:|---:|---:|
|all13_uniform_0.1rad_s|40.381477|34.880988|14.133517|1892.3–2039.5|
|all13_uniform_-0.1rad_s|34.880988|40.381477|12.208346|1634.5–1761.7|
|all13_uniform_0.3rad_s|121.144431|104.642963|42.400551|5676.9–6118.4|
|all13_uniform_-0.3rad_s|104.642963|121.144431|36.625037|4903.6–5285.0|

Both±.3 require >3500 rpm under the declared dual-pump/ηv assumptions. At3500 the uniform-positive neutral magnitude ceiling is .171613–.184961 rad/s; negative .198676–.214128. At3000 positive .147097–.158538; negative .170293–.183538. They are flow sensitivities, not allowed task rates.

**Neither uniform sign is an admissible trajectory from neutral:** hip/fold/ankle q=0 is their upper limit; knee q=0 is its lower limit. Local inward pitch directions use hip/fold/ankle negative, knee positive. New waist sign changes the following instantaneous flow window; hip/foot-roll pairs are symmetric at neutral.

|Pitch inward magnitude|Waist sign|Supply L/min|Return L/min|
|---|---:|---:|---:|
|0.1|1|38.329341|36.933124|
|0.1|-1|36.438780|38.823684|
|0.3|1|114.988023|110.799371|
|0.3|-1|109.316341|116.471053|

These inward signs prove only the local joint-limit direction. Stance constraints, contact allocation, acceleration, motion path and actual required forces remain unknown. At+.1 uniform neutral, net chamber fill Qin−Qreturn=5.500490 L/min; reversed motion returns that differential volume. Parent owns full stroke/fluid inventory.

## Same declared pump state; oil heat remains unqualified

Z16 is11 cc/rev,700–3500 rpm,23MPa continuous;21MPa and ηv=.90–.97,ηm=.85–.90 are own assumptions. At a matched actual neutral Qin=40.381477 L/min and21MPa, hydraulic stream=14.133517kW, conditional shaft=16.189596–18.475186kW, shaft-minus-delivered-stream=2.056079–4.341669kW. These three quantities use the same Q and p; the last is pump residual, not measured oil heat. Actual useful/negative actuator work and mechanical heat paths are absent. **E2 actual oil-side heat range is unknown.**

With both pumps fixed3000rpm at21MPa, delivered flow59.4–64.02L/min and shaft25.666667–27.176471kW belong to a different explicitly fixed-speed state. Surplus over+.1 uniform demand is19.018523–23.638523L/min. IF all surplus were relieved from21MPa to zero it would dissipate6.656483–8.273483kW, but such a route is not selected or established. Do not add this surplus to the matched-speed balance. An unloaded pump, bypass, storage or pump staging has a different pressure/flow state.

Below double-pump700rpm delivered13.86–14.938L/min (ownηv), further common-speed reduction leaves the manufacturer range. A stopped/staged/unloaded circuit must be specified; this minimum flow does not prove full-pressure waste. One pump at3500rpm would deliver only34.65–37.345L/min in this sensitivity, below40.381477L/min; failure-safe performance is unproved. Joint reversal switches cylinder port conditions and does not authorize reversing the cited anti-clockwise pump rotation. Holding geometric qdot=0 implies geometric Q=0, while leakage, standby and loadholding losses remain unknown.

Negative Fv is energy from gravity/inertia/contact doing work on the actuator. It requires a defined dissipation, storage or recovery path. A capacity inequality supplies no counterbalance, make-up flow, anti-cavitation, holding or regenerative circuit proof. Pair synchronization, valve center on power loss, single-cylinder/pump failure, hose rupture and safe gravity stop remain red unknowns.

## Geometry/flow input table

|Cylinder|Bore/rod mm|Neutral J m/rad|Base → output|
|---|---:|---:|---|
|waist_pitch_pair_0|80/40|+0.125371682|waist_yaw_carrier → waist_pitch_carrier|
|waist_pitch_pair_1|80/40|+0.125371682|waist_yaw_carrier → waist_pitch_carrier|
|left_hip_roll_pair_0|63/30|+0.166989570|left_hip_yaw_carrier → left_hip_roll_carrier|
|left_hip_roll_pair_1|63/30|-0.166989570|left_hip_yaw_carrier → left_hip_roll_carrier|
|left_foot_roll_pair_0|50/25|-0.116000000|left_ankle_pitch_carrier → left_foot_roll_arch|
|left_foot_roll_pair_1|50/25|+0.116000000|left_ankle_pitch_carrier → left_foot_roll_arch|
|left_hip|50/25|+0.094868330|left_hip_roll_carrier → left_thigh|
|left_knee|80/35|+0.134928127|left_thigh → left_middle_shank|
|left_fold|63/30|+0.082169697|left_middle_shank → left_distal_shank|
|left_ankle|63/30|+0.093881097|left_distal_shank → left_ankle_pitch_carrier|
|right_hip_roll_pair_0|63/30|-0.166989570|right_hip_yaw_carrier → right_hip_roll_carrier|
|right_hip_roll_pair_1|63/30|+0.166989570|right_hip_yaw_carrier → right_hip_roll_carrier|
|right_foot_roll_pair_0|50/25|+0.116000000|right_ankle_pitch_carrier → right_foot_roll_arch|
|right_foot_roll_pair_1|50/25|-0.116000000|right_ankle_pitch_carrier → right_foot_roll_arch|
|right_hip|50/25|+0.094868330|right_hip_roll_carrier → right_thigh|
|right_knee|80/35|+0.134928127|right_thigh → right_middle_shank|
|right_fold|63/30|+0.082169697|right_middle_shank → right_distal_shank|
|right_ankle|63/30|+0.093881097|right_distal_shank → right_ankle_pitch_carrier|

## Reused primary sources

[HAWE D6820](https://productfinder.hawe.com/downloads/D6820-en.pdf), PDF pp5/7/8, version11-2022 1.1. Z16 facts above require viscosity/inlet/temperature/cleanliness conditions; continuous catalog pressure and100% pump duty do not rate the complete system. SHA256 `eb12235f90d93f9c08f1c08d7bee27427ce1338cd5429ae019420844e77307dd`.

[EMRAX188 v1.6](https://emrax.com/wp-content/uploads/2025/03/EMRAX_188_datasheet_v1.6.pdf), PDF p2. LC≥6L/min per motor, coolant inlet≤50°C, air circulation also required; enclosure restriction remains.52Nm/34kW are separate catalog references;96% is peak efficiency. Bus/winding/controllers and installed curve are unselected. SHA256 `cfa72eec662495d12eec6cafb61413b71c428cf0083019c52620a009e39631fa`.

The2 motors imply≥12L/min source LC coolant flow, independent of hydraulic oil Qin. No cross-loop thermal rating is implied. Native/source geometry, oil heat rejection, dynamic contact, pressure traces and complete safe-stop circuit are not accepted. Full input hashes, per-cylinder signed flow terms and conditional state arithmetic are in the companion JSON.
