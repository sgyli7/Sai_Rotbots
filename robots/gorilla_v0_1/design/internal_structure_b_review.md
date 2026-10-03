# Gorilla 内部 B：支承、复合脚与布局拒绝记录

2026-10-03。B 是 C15 上独立的内部结构试验，与曾被用户否决的外观 `layout_b` 不同。**整机匹配、结构、驱动、接触与热均未放行。** 本轮保留可复查的源、实际渲染和失败证据，随后转向原形体约束下的完整总成共同设计；不继续用更多大工业模块或包壳隐藏冲突。

唯一外观仍为 [AA3 原稿](concepts/aa3/user_confirmed_four_view.jpg)。C15 阶段提交 `94e0e074` 已先于内部设计保存，并随 PR #4 合入主干。B 的 111 个原护甲行、4 个主地面垫及其世界几何原样保留；这证明未暗改基底，**不能证明内部适配原稿**。实际 8 个 CPU 视图均已打开审查，整机正、侧、后图仍明确看见旧肩、腰、髋及腿驱动探针穿出壳；膝近景受真实手部及旧模块遮挡，不能用它证明完整膝装配已可检查。

## 实际改变与身份

| 资料 | 结果与范围 |
|---|---|
| [参数](../configs/internal_structure_b_spec.json)、[原生源](../cad/source/internal_structure_b_scene.json) | 629 分件；521 个 C15 留存源行逐项不变，108 个新原生件，92 个原件被独立替代。source SHA `7a6186594f2a47067fe9c38e4cc52833b1c930c93568e5b215a520d195e7621f` |
| [Blender](../cad/source/internal_structure_b.blend)、[GLB](../cad/exports/internal_structure_b/internal_structure_b.glb) | 与上述源同版，真实原生网格导入；新件无倒角或 OEM 网格替换。16 个轴承只是目录外形/质量标尺 |
| [实渲清单](../cad/exports/internal_structure_b/internal_structure_b_render_manifest.json) | Blender 4.0.2 / Cycles CPU，600 px、16 samples，8 视图。拆壳仅隐藏明确原护甲和旧腿关节视觉代理；新驱动、支承及其冲突不隐藏，无后期修形 |
| [质量与静力](../evidence/internal_structure_b_statics.json) | 18 个独立刚体的真实有限材料并集；8 个成对输出支承；4 个姿态、16 个整机重力工况及真实脚垫单向反力极点；没有隐藏根部约束 |
| [体积检查](../evidence/internal_structure_b_space.json) | 原生封闭材料和完整模块预留的正体积相交拒绝；只检查列明角色及 4 个姿态，不是完整连续扫掠 |
| [资源和独立数学检查](../evidence/internal_structure_b_resource_check.json) | 629 源/导出名称一致；108 个新件的双向顶点误差 < 0.3 μm；8 个端点力矩解析 Jacobian 与有限差分一致；C15 的 31 个原件/冻结副本哈希不变 |

8 个腿支承使用 100 mm 外径、60 mm 内孔、264 mm 长的自研输出轴候选、成对 32020 轴承外形、有限壁厚轴承壳/叉架和输出连接框。旧毛料轴座实际删除，旧框架在轴位作真实切除，各同运动体材料作布尔并集；不按任意百分比减重。右上臂框从左侧真实反射，修复原弯四边面三角划分造成的两侧体积差异；原护甲不改。并集只代表名义连续材料，焊缝、紧固、轴肩和密封没有因此合格。

复合脚保留原前掌、足弓和独立后跟，在 35 mm 止挡安装断续处增加有限侧叉候选。前后各自增加 6 mm 金属托盘与短局部肋，托盘不跨脚段之间的缝。原 7/11 mm 接地垫至钢框空气隙已在名义材料几何上接续；前后托盘 X 向仍有 129 mm 分离缝。新金属实际增加质量，不能因“接通”而免计。脚垫密度 1100/1250/1500 kg/m³ 为假设，4 垫中值 34.297 kg，已明确计入。

## 宏观物理边界

真实净钢几何为 **505.361 kg**，16 个轴承目录质量合计 **31.04 kg**。原护甲密度、脚垫密度、仍待重设计的完整模块，以及缸端安装/接头质量范围共同形成 **1617.515 / 2072.755 / 2738.613 kg** 条件账本。模块仍相交且组件归属有假设，这不是可制造整机净重，也不是 Gorilla 目标重量。完整逐体惯量、转子/反射惯量与稳定物理合同尚未建立；记录的完整 3×3 惯量仅属于净框架材料。

| 核查 | 当前结果 | 必须关闭的问题 |
|---|---|---|
| 双足重力平衡 | 4 姿态 × 空载、100 kg 假设载荷、全重力×1.5、3 t 外压，各有可解的有限单向反力 | 只有水平、共面脚垫的准静力法向模型；真实摩擦、弹性、动态步态与带物接触仍未知 |
| 中立至关键姿态 | 围绕 C15 原腿轴点实际变换，脚面法向仍竖直；躯干绕 Z=1.74 m 的假设 Y 轴，臂轴为简化姿态 | 不是完整多轴拓扑、可执行连续动作或自由根仿真；所有未移重心的单左脚平衡均拒绝 |
| 短缸分置 | 4 个 CHD80/45 T/4M/S100 目录尺寸探针，基座放在中腿；末段与脚缸跨折叠/踝两轴，使用真实长度与 `τ=Jᵀf` | 不是独立两轴恒定力臂；自研眼端额外 50 mm 是安装假设，缸体/杆质量分配、支座和软管未闭合 |
| 行程/输出 | 4 姿态及各 21 个长度采样在 290–390 mm 条件眼距内；100 kg、×1 条件载荷的有限反力需求可落入假设压力范围 | 16 MPa 供压、1 MPa 回压、0.85 力损系数不是持续/瞬态评级。×1.5 的中立/蹲姿踝退向需求超出假设；3 t 各姿态均至少一缸失败 |
| 支承/轴 | 实际缸端力加入折叠/踝轴承径向载荷，目录静力与名义空心轴联合应力有限筛查 | 压力中心、预紧、配合、轴肩/焊缝集中、屈曲/疲劳、真实传扭路径仍未知；轴承不提供轴向保持力矩 |
| 复合脚固定路径 | 名义材料空气隙接续、各独立金属体连通；有限钢体中立/卸载 −15°/+10°端点无足弓穿透 | 甲/钢仍相交，锁导向尚无实际固定钢安装接合，带载折叠/锁止没有证明 |

4 个真实姿态下，中立左折叠/踝缸在 100 kg 假设载荷、×1 条件下的含力损有符号需求分别约 **−31.070…43.822 kN**、**−34.405…36.909 kN**；推/拉容量假设分别 **76.989 / 49.951 kN**。独立反向轴力矩组合另算并保留，不能只用有利同向轴载。名义轴应力仍保守保留轴上传扭需求，不因驱动力矩把外部合力矩抵消为零而删去扭转项；该传扭路径未制造核验。

独立 [脚部复核](../evidence/internal_structure_b_foot_review.json)按最新 B 质量重算 64 个局部工况。3 t 外压的最大前掌止挡总需求 **533.373 kN**，条件平均每侧止挡 **266.687 kN**，低脚铰链销的竖向需求 **507.398 kN**；它不能转移给 Z=.285 m 的腿踝轴承标尺。×1.5/100 kg 条件下反向保持需求最大 **215.052 N·m**。这些都是需求，不是能力。30/25 mm 的短止挡力臂导致强烈放大，下一轮须宏观重设中立承载路径/有效支承臂，不能只继续加厚小止挡。

## 真实空间拒绝

检查阈值为 1×10⁻⁹ m³ 正体积；单纯贴合面不算穿透。同一刚体内的不同材料重叠仍拒绝。完整模块包络冲突意味着安装预留不成立，不能全部称为厂家内部材料穿透。未分析的旧显示机构、线束、安装工具、完整软管扫掠不算通过。

| 实际姿态 | 跨运动体钢材 | 框架/轴承预留 | 框架/护甲 | 完整模块预留相关 | 合计 |
|---|---:|---:|---:|---:|---:|
| neutral | 9 | 16 | 44 | 258 | 327 |
| crouch | 9 | 24 | 44 | 259 | 336 |
| forward_manipulation | 9 | 32 | 44 | 257 | 342 |
| deep_crouch_rejection_probe | 9 | 24 | 44 | 255 | 332 |

新增轴承座的叉臂/腔体仍侵占部分轴承预留，新脚托盘还与外侧低轨及暗跟壳相交；内低轨有继承的更高框架冲突，不能全归因新增托盘。旧腰多轴、肩多轴完整模块互相叠放及长腿工业缸仍是整机主要拒绝热点。上述结果阻止 B 装配放行，不能靠拆壳图、材料连通或软件测试关闭。

## 来源、复现与下一入口

原厂 [Parker/Miller CHE/CHD 目录](https://www.parker.com/content/dam/Parker-com/Literature/Miller-Fluidpower/miller/cat/HY08-M1137-7NA-CHE-CHD.pdf)给 CHD80/45 钢缸 T/4M、S100 的 114 mm 方体、178 mm 缸体、240 mm 裸缩至杆螺纹端、13.89 kg 裸缸；100 mm 行程和安装眼端不是关节角度或完整关节质量保证。[Schaeffler TPI241](https://www.schaeffler.es/remotemedien/media/_shared_media/08_media_library/01_publications/schaeffler_2/tpi/downloads_8/tpi_241_de_en.pdf)、[TPI245](https://www.schaeffler.es/remotemedien/media/_shared_media/08_media_library/01_publications/schaeffler_2/tpi/downloads_8/tpi_245_de_en.pdf)与 [TPI205](https://www.schaeffler.es/remotemedien/media/_shared_media/08_media_library/01_publications/schaeffler_2/tpi/downloads_8/tpi_205_de_en.pdf)用于目录支承尺寸/质量与有条件静力公式；成对 O 形压力中心 ±116 mm 需符合对应安装方向及 no-play/no-preload 假设，非实体中心 ±99 mm。S355J2H 条件材料来源在参数文件，不能替代加工轴、焊接和成品料证。

```bash
# 在仓库工程 Python 环境中运行；此外需要 trimesh 4.11.1、
# manifold3d 3.5.4、shapely 2.1.2、Pillow 12.3.0。
.venv/bin/python scripts/models/build_gorilla_internal_structure.py
.venv/bin/python scripts/evaluation/evaluate_gorilla_internal_structure.py
.venv/bin/python scripts/evaluation/check_gorilla_internal_structure.py
.venv/bin/python scripts/models/render_gorilla_internal_structure.py
.venv/bin/python scripts/evaluation/check_gorilla_internal_structure_resources.py
```

受控 B 源已通过另一路径重建，SHA 完全相同。渲染运行需本地 Blender 路径；参数脚本有明确环境入口。构建默认会写 B 工作文件，冻结后的 B 只读复查应在独立 checkout 运行或用 `--output` 指向忽略产物，后续改形另起 C；不要覆盖本失败记录。仓库回归 **210 passed / 89.06 s**，无共享运行模型、轴/驱动合同、策略或 observation/action 修改。它只证明已有软件回归，不构成此处任何物理放行。

下一轮采用 [Tesla / Figure / GD01 一手共同设计研究](../hardware/internal_co_design_references.md)：把原胸背、厚肩臂、髋与长腿段作为布局约束，重建完整载荷壳—输出支承—传动—电机/制动—驱动/热总成，减少重复独立壳体与支承。优先肩/腰/髋多轴及远置传动、复合脚中立载荷旁路，而非对短末腿再塞大成品。外观甲与内部载荷壳分清，能共用的结构只有在真实连接/材料核算后才计一次质量；原壳小调展示冲突和修改量。能量、回馈与热按任务工况重新分摊，暂不选择液压或电驱路线，不将两吨账本、100 kg 假设载荷或 3 t 外压当作产品指标。双足、双手、自主复杂 Bevy 闭环目标继续活动。
