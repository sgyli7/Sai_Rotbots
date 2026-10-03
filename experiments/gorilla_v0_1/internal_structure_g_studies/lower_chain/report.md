# Gorilla G1 finite lower-chain candidate — rejected

Frozen candidate SHA `bf3f81c5dd813a79b51c7557dfd16e81e2a73d8505a0954ce758dd8b0215e460`. One complete left lower-chain geometry attempt, 43 native parts including 4 full cylinders, 3 actual恒材料姿态 and 121-point per-actuator length/J data. No second local-patch geometry adopted.

新源由有限 CSG 生成，未修旧F2绕向。G资源早门禁拒绝 `g1_arch_net` 的6个小于1e-16 m²/退化三角；其他42件通过此有界资源先验，但不等于几何或物理通过。门禁拒绝后保留整候选诊断，未自动修面、放宽容差、fix_normals或compose。涉及arch的材料交是kernel诊断值，不能作合格实材证据。

## Actual rejection

- neutral: different-owner intersections 26 (17 candidate-pair resource-valid / 9 invalid-arch diagnostic), original armor 34; max constant-material volume drift 0 m³.
- lower_negative_endpoint: different-owner intersections 33 (23 candidate-pair resource-valid / 10 invalid-arch diagnostic), original armor 27; max constant-material volume drift 8.24e-18 m³.
- unloaded_split_endpoint: different-owner intersections 40 (31 candidate-pair resource-valid / 9 invalid-arch diagnostic), original armor 29; max constant-material volume drift 6.94e-18 m³.

最大中立resource-valid对为roll_1 barrel与distal主承件60.059 cm³，roll_-1对应42.086 cm³；不是旧F2内皮符号导致。roll barrel与其固定carrier也各39.025 cm³。完整后置roll双缸沿中段后空间延伸仍撞中腿/下腿承壳；需要整组重新安排缸/固定支承/输出承壳，不能再在现图补叉。中立original armor冲突最大forefoot tray与内低轨141.785 cm³；8mm inset原pad footprint仍不足以容纳原低轨内皮。此候选选位失败，不证明AA3必须改形。

Middle/ankle_carrier各2个真实材料roots：单一body名称未当作刚接证据。固定journal/转轴、销/眼/叉为分件设计的名义接触，不因分件自动判断链，亦无承载接合资格；具体根bounds在JSON。

## Scope and finite sizes

- fold: eye 0.290368–0.373631 m, stroke 0.103262 m, shortest finite zero 0.273262 / used zero 0.280368 m; J 0.233921..0.240208 m/rad. 63/30×5 mm, pin40 mm; pressure21 MPa is not a qualification.
- ankle_pitch: eye 0.550091–0.568852 m, stroke 0.038761 m, shortest finite zero 0.208761 / used zero 0.540091 m; J -0.108854..-0.105528 m/rad. 63/30×5 mm, pin40 mm; pressure21 MPa is not a qualification.
- roll_-1: eye 0.430892–0.458973 m, stroke 0.048081 m, shortest finite zero 0.218081 / used zero 0.420892 m; J 0.076094..0.083390 m/rad. 63/30×5 mm, pin40 mm; pressure21 MPa is not a qualification.
- roll_1: eye 0.430892–0.458973 m, stroke 0.048081 m, shortest finite zero 0.218081 / used zero 0.420892 m; J -0.083390..-0.076094 m/rad. 63/30×5 mm, pin40 mm; pressure21 MPa is not a qualification.

Candidate finite-metal net mass at conditional steelρ7850 is 173.753 kg; actual pad volume×ρ900/1100/1400 gives total [186.0994575510912, 188.8431910260462, 192.9587912384787]. Resource-rejected arch contribution remains explicitly unqualified, not credit toward whole robot mass.
Four-axis illustrative synchronized0.5rad/s neutral supply positive/negative {'positive': 42.90500137342798, 'negative': 40.18233732189054} L/min. Not full-robot flow or continuous heat capability.

Fore/heel new candidate axes [-.05,.5,.124]/[-.18,.5,.124], separate trays/pads preserve original ground gap. Stop lever fore .20 m, heel .14 m; caps retract up65/40mm and pins +X110mm unloaded. No full-length sole or beam crossing both segments. Neutral/endpoint interferences persist, so this lock/arch arrangement is rejected despite actual withdrawal transforms.

Roll moved rear to[-.205,.5,.245] axis+X, anklepitch original[-.075,.5,.285] unchanged; new FK/LP needed. Upstream thigh/knee actuator and complete torso/hip chain omitted scope. Right mirror not built; this is single-left candidate.

Native painter projections (850px/m) use actual source triangles and same cameras, no shape manipulation. Eight bare/original-armor neutral views plus2endpoint left views. Actual visual inspection shows posterior barrels/carrier stand beyond blue rear shank, rear foot/arch crowded; original armor unchanged0mm cannot visually or materially close this arrangement. Views are diagnostics, not new four-view aesthetic baseline.

## Re-run / integration

`python build_chain.py` regenerates the same source; `python check_chain.py` computes the bounded gate/Boolean/actual projections; `python freeze_candidate.py` adds compact receipt/interface/manifest. Need numpy/trimesh/manifold3d/shapely/Pillow. Do not resolve .venv/python symlink.

Read `interface.json`; native neutral parts and actual pose arrays are in chain_scene.json; body ownership for barrels/rods is endpoint-driven, not base-body transform. All root shifts zero. Source remains rejected, no canonical/Git change.

Final actual lock note: nominal cap/segment compression planes have zero positive-volume penetration, but each cap has5.108711 cm³ fixed-arch kernel diagnostic overlap. This design is rejected before pin load or strength qualification. AA3 was actually viewed alongside all4 candidate bare/armor native projections; source overlay does not imply user aesthetic acceptance.
