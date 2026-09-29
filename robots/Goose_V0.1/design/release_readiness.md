> 最新候选（2026-09-30）：[饱满机身／大眼／鹅掌](fuller_exterior_review.md)。仅完成外观迭代、静态预留盒及源网格筛查，同版动力学与制造仍未放行。

> 最新候选（2026-09-30）：[简约头嘴／铰接鹅嘴](hinged_beak_exterior_review.md)。外观待用户验收；约 50 N 仅为初算目标。新增头部质量与新嘴机构尚未进入同版物理验证，旧试验不能用于放行。

# Goose_V0.1 整机放行判定

> 2026-09-30：上一卵形方案已被用户否决。当前审查[肩胸与收尾曲面候选](sculpted_exterior_review.md)，外观与工程交付均未放行。

> 2026-09-29 按用户五点反馈新增[流线型外观与器件布置候选](streamlined_exterior_review.md)。用户已授权不再逐项复刻旧图；外观仍待本轮审查，硬件布置尚非制造或物理放行。

> 2026-09-29 新增[半小时 R2 四边面重建候选](r2_quad_rebuild_review.md)：闭嘴／张嘴源文件的逐件四边面与闭合检查通过；外观仍待审查，制造、同版动力学和整机交付继续未通过。下文 v95/RC2 均为历史候选。


本页截至 2026-09-29 按同一候选版本判定交付门槛。下表中历史 RC2 的规格 SHA-256 为 `c3b9f885ebbe854c47a3f0dbecdbef190b7fcb39f3b412c980561e3c838be62e`，MuJoCo 模型 SHA-256 为 `07d4209a5a7b9322a04b9cdb62694a69cf35c97716c262909d21f039599c4cb0`。**结论：RC2 外观已被用户否决；v95 外观与 v96 居中脚掌试样都尚未获外观验收，工程交付未通过。现有 BOM 不是订货单，视觉 STL 不是最终承力打印件。** 先按原有 B 步行鹅与 R2 尖嘴图重做整机外观，再对同版质量、支撑和任务能力做物理核查，最后闭合采购装配。实物打印、温升和地面带载步行是之后的独立实测门槛。

## 当前 v95 外形与 v96 脚掌试样：先看整机，再看分项，最后回到整机

| 整机条件 | 同版事实 | 判定 |
| --- | --- | --- |
| 外观与动作形象 | [原尖嘴图](concepts/r2_pointed_beak_closed_reference.jpg)与[v95 闭嘴整机](../images/r2_swept_head_v95_closed_three_quarter_candidate.png)、[张嘴整机](../images/r2_swept_head_v95_open_three_quarter_candidate.png)已能直接并排审查；头部相机面、颈腿整体曲面与机身转接仍有明显偏差，`appearance_review_pass=false`。 | **未通过** |
| 可编辑网格与导出质量 | [图生 3D 失败记录](../evidence/r2_generated_mesh_rejection.json)确认新尝试只有三角化 GLB，没有可编辑四边面源；原始索引有 2,534 个连通片，其中多数是贴图／法线接缝拆点，按空间位置合并后仍有 20 片、整体不封闭。用于预览的逐三角面离散上色又造成明显橙黑锯齿。该 GLB 不进入 CAD、仿真或打印。后续凡以多边形建模的可打印分件，须逐件通过[四边面、单连通、闭合与面朝向检查](../../../scripts/diagnostics/check_goose_editable_quad_mesh.py)；BREP/STEP 另查实体，STL/GLB 的三角化导出另查封闭性与尺寸。 | **未通过，拒用图生网格** |
| 版本一致的物理基础 | [v95 与运行模型对齐记录](../evidence/r2_swept_head_v95_system_alignment.json)检出视觉 R2 与 RC2 规格的嘴机构轴距 `14/18 mm`、电机 `XL330/XC330`、暂定传动比 `2:1/1:1` 不一致；视觉机箱与 RC2 机身名义包络亦不同。[同版脚底范围](../evidence/r2_swept_head_v95_support_geometry.json)与[条件质量筛查](../evidence/r2_swept_head_v95_conditional_mass.json)仅按薄壳及继承器件估算双脚投影；单脚还需至少约 `42.77 mm` 横向移重心。没有真实同版质量／惯量、驱动、关节和接触动力学模型。 | **未通过** |
| 双足与任务 | v95 的 `9/9` 坐姿嘴尖目标只证明有限几何可达；没有同版站稳、下蹲夹物、携物起身、移动拖拽、行走及 MuJoCo↔Godot/Jolt 试验。历史 RC2 的单项成功和失败均不能移植为 v95 结论。 | **未通过** |
| 制造与采购 | v95 头罩原 STL 含 18 个零面积面；[拓扑清理记录](../evidence/r2_swept_head_v95_mesh_topology.json)证明清理后网格封闭，但未给出可装配分件、紧固、壁厚和强度。CAD、BOM、接线仍属于 RC2。 | **未通过** |
| 脚掌前后位置 | [v96 同版权衡](../evidence/r2_centered_foot_v96_trade_screen.json)只后移视觉鞋 `20 mm`：条件站姿最近前后余量增约 `17.44 mm`。[坐姿腿质量重摆复核](../evidence/r2_seated_whole_mass_repose_v95_v96.json)修正了旧质心高度近似后，v95／v96 低位最近前后视觉余量仍为 `76.70/59.25 mm`，差 `17.45 mm`；髋矩粗筛也未过。不能只以站姿居中冻结脚型。 | **未通过，保留两版比较** |
| 坐姿整体姿态 | [v95 较少前俯的张嘴路径](../evidence/r2_swept_head_v95_sit90_torso15_x300_z25_open.json)在同一嘴尖目标的采样净空通过；`15°` 前俯相较 `20°` 将单髋条件重力矩约从 `0.989` 降至 `0.940 Nm`，仍高于 `0.82 Nm` 粗筛值，且下颈到机身的采样净空缩小。几度姿态优化不能代替同版承力布局与任务动力学。 | **未通过** |

下一轮只推进整机主矛盾：先用同视角整机姿态确认尖嘴鹅的轮廓和动作表达，再将这套外形映射到同版质量／惯量／驱动包络，检查双脚支撑与坐姿叼拖；最后用同一个候选的 CAD、物理模型、任务证据和采购表作整机回查。相机小倒角、焊点、装饰分缝等可在这些门槛之后细化。

## 历史 RC2 与视觉候选分项记录

以下记录按产生顺序保留；旧段落中“最新”只指当时的局部试样。每项通过仅属于其记录中的候选、假设和测试范围，不提升上方 v95 整机结论。

| 门槛 | 当前证据与边界 | 判定 |
| --- | --- | --- |
| 交接资料 | [导入核查](../source/workspace_import.md)保存原 ZIP、图片、文档和四本 Excel；原机器人 README 另存为[历史快照](../source/robot_readme_handoff.md)。 | 已保留 |
| 可编辑几何与交换文件 | [CAD 清单](../cad/exports/cad_manifest.json)含 121 件 BREP/STEP/STL 和整机 STEP。 [三姿态](../evidence/part_clearance_sampled_rc2.json)、[正常站姿](../evidence/part_clearance_standing_rc2.json)、[电机包络](../evidence/motor_clearance_check.json)、[设计视野](../evidence/camera_clearance_check.json)分项通过；未完成全行程扫掠、螺钉/线束可达、打印层向承力验证。 | 部分通过 |
| 外观与检修 | 实际 [RC2 CAD 渲染](../images/rc2_home_side.png)与原有 [B 步行鹅／R2 尖嘴外观](exterior_review.md)严重不符，用户已否决现版。新增[闭合／平行张开 3D 外观草模](../cad/exports/goose_r2_exterior_study_manifest.json)供对照，仍未通过外观复刻；[近场视野筛查](../evidence/exterior_vision_screen.json)显示站姿中心线被尖嘴遮挡，头部俯视存在纯几何可见角区，但装配、碰撞和自主任务均未验证。后续须先闭合外观与动作姿态，再回算质量、运动和叼拖能力。 | **否决，重做** |
| 采购和拼装 | [现行工作 BOM](../hardware/goose_rc2_bom.xlsx)列 30 项采购/材料行和 121 件打印切割行；[接线装配稿](../hardware/goose_rc2_wiring_and_assembly.md)有拓扑和顺序。人民币报价、保险/继电器额定、完整紧固件规格、线束长度与干涉、材料试件仍未闭合。 | **未通过** |
| MuJoCo 机制 | [正常站立](../evidence/stand_neutral_rc2.json)、预设姿态 [50 g 叼取/释放](../evidence/grasp_50g_rc2.json)、静足 [0.3 kg 样块短距牵引](../evidence/drag_short_pull_rc2.json)通过。未覆盖携物步行、移动拖拽、指定日用品和小车、失败恢复。 | 部分通过 |
| 训练入口与策略 | [RSL-RL 冒烟训练和 ONNX 导出](../evidence/train_smoke_rc2.json)可运行，接口为 53 维观测/10 维腿策略/16 维执行器力矩；[v5 200 轮原策略](../evidence/walk_policy_200iter_v5_rc2.json)四项步态回放均约 1 秒跌倒。[低探索对照](../evidence/walk_policy_calm_init_v5_200_rc2.json)将训练期跌倒次数从 877 降至 255，但独立回放仍在 2.78–4.16 秒跌倒，未形成有效步态。零动作站立虽可 8 秒，[缩小动作的诊断](../evidence/walk_policy_v5_scaled_diagnostic_rc2.json)也只会原地站立。失败候选已保存；无已验收行走策略或自主任务策略。 | 部分通过 |
| MuJoCo ↔ Godot/Jolt | 同一具名站姿在[MuJoCo v5 真实 5 ms 控制模式](../evidence/stand_neutral_policy_mode_v5_rc2.json)与[Godot/Jolt v5 同模式](../evidence/godot_jolt_standing_v5_rc2.json)分别自由站立 4 秒通过，无额外双脚支撑补偿。但[Jolt v5 原候选策略](../evidence/godot_jolt_policy_v5_diagnostic_rc2.json)失稳；[低探索候选](../evidence/godot_jolt_policy_calm_init_v5_200_diagnostic_rc2.json)静止 4 秒未摔倒，站姿误差、倾角及根部位移仍超标，不能声称跨引擎策略通过。此前[MuJoCo v4 的 5 ms 站立失败](../evidence/stand_neutral_policy_mode_v4_rc2.json)及[侧叼接触起姿失败](../evidence/godot_jolt_ground_grasp_stance_failure_rc2.json)均保留。Jolt 叼取、拖拽、行走未过门槛。 | 部分通过 |
| 后续 Unity/Bevy | [中立 SI 刚体包](../models/full/rigid_transfer.json)与统一控制协议不含 Jolt 私有尺度；[B01–B09 核查清单](backend_conformance_facts.md)已列。UnitySim2Sim、BevySim2Sim 接收器和实测均未完成。 | 可接续，未适配 |
| 游戏行为与自主 | [行为定义](behavior_requirements.md)覆盖探头、回望、鹅叫、拾取和拖拽；[游戏来源](gameplay_sources_review.md)明确哪些画面没有实际观看。[合成视觉定位](../evidence/vision_pixels_check.json)和具名任务接口不能代表真实相机自主完成。 | **未通过** |

接下来的顺序按用户最新决定执行：先用原有 B 步行鹅与 R2 尖嘴图建立可检查的真实 3D 外观，并对比多视角闭嘴、张嘴和动作姿态；外观过关后再重新设计与验证承力机构、质量、运动、拾取和移动拖拽；最后闭合供电保护、紧固件、线束与含税采购清单。现有 RC2 的力学与采购记录只作为旧候选问题清单，不能反过来逼迫新外观贴合旧机构。每次涉及物理模型的改动须按模型/规格哈希重跑相应证据，不能沿用旧通过结论。

后续[比例修正外形](exterior_review.md)与[MicroDuck Max Pro 六轴腿初筛](stance_layout_review.md)没有改变以上放行判定：新视觉 STEP 仍未复刻用户 B／R2 图；双脚侧移改善，但三组单脚换重心／抬脚均失败，低头姿态也失稳；[踝电机包装](../evidence/ankle_roll_package_screen_r2_proportion.json)仅为本体包络初筛。新增两踝轴和 18 轴总数均保持候选身份，不能更新采购单或宣称 Goose 已具备比 MicroDuck 更强的实际行走／夹拖能力。

最新[较紧凑 R2 外观候选](../cad/exports/goose_r2_ankle_clearance_visual_candidate_manifest.json)虽把脚踝电机本体移出鞋底，并降低条件重心，仍有颈根外饰穿插、低头失稳、三组单脚卸载失败及踝部承力壳和线束未设计。[对应动力学证据](../evidence/physics_stance_trial_r2_ankle_clearance_six_axis.json)和[包装筛查](../evidence/ankle_roll_package_screen_r2_ankle_clearance.json)均为失败或必要条件记录；本页的**未放行**结论不变。旧 RC2 的 MuJoCo↔Godot/Jolt 站姿结果也不能代表新比例的跨引擎验证。

随后按用户的 MicroDuck Max Pro 补充做了[缩壳与坐姿候选](exterior_review.md)：机箱视觉包络缩至 `310 × 190 × 200 mm`，双腿降低后的嘴尖有几何可达解，但[同版物理记录](../evidence/physics_seated_reach_r2_compact_body_tip40.json)显示嘴端仍承受大量地面反力，三组单脚试验也未通过。该版本仍未获用户外观验收，CAD 仍是视觉实体，无可采购承力结构、夹取和拖拽闭环；**制造、采购和工程交付继续不放行**。

再往后，[短鞋与前移膝轴候选](forward_knee_trade_study.md)消除了**一个特定无物体低位保持动作**的嘴端撑地：[2 秒接触试验](../evidence/physics_seated_reach_r2_forward_knee_x280_tip40_ff.json)双脚承重、嘴无地面反力；50 g 等效载荷仅有[静力必要条件初筛](../evidence/foot_only_equilibrium_r2_forward_knee_50g_sweep.json)，未动态夹物。外观没有获用户确认，视觉 STEP 无真实制造结构，单脚／步行、带载起身、移动夹拖和新比例跨引擎验证均未通过。RC2 旧版分项成功不得移植到此候选；**制造、采购和工程交付仍不放行**。

最新[紧凑轮廓候选](r2_compact_silhouette_review.md)进一步对齐头、嘴与机箱的大比例。[站姿到低位的采样路径](../evidence/exterior_sit_sweep_r2_silhouette_v51_x280.json)以及[50 g 等效外力低位保持](../evidence/physics_seated_reach_r2_silhouette_v51_x280_50g_proxy.json)通过各自的有限初筛，但这仍是视觉实体和无物体接触的负载代理。真正的 R2 嘴夹物、连续下蹲／起身、带物步行与拖拽、全行程装配、连续扭矩／温升及新比例跨引擎验证均未完成；**外观、制造、采购和工程交付继续不放行**。

同版踝部尺寸复核又发现，上一低位动力学候选使用的 XM540 踝俯仰本体[侵入鞋底约 `7.25 mm`](../evidence/ankle_package_screen_r2_silhouette_v51_xm540_hub.json)，因此不能据其短试验订货。改用较小 XM430 后，[50 g 等效力低位保持](../evidence/physics_seated_reach_r2_silhouette_v51_x280_ankle_xm430_50g_proxy.json)仍过简化筛查，但[现有黑色踝罩的名义径向余量](../evidence/ankle_package_screen_r2_silhouette_v51_xm430_hub.json)只有 `2.36 mm`，尚无可制造的空腔、支架与线束。该尺寸纠错不改变未放行结论。

[280 mm 小机箱候选](r2_compact_front_reach_review.md)扩展了前颈的采样坐姿可达区域，并在嘴尖 `15／25 mm` 目标通过两项 `50 g` 等效力的双脚低位保持试验；`10 mm` 目标则[发生嘴端碰地](../evidence/physics_sit_r2_compact_front_v53_x280_z10_50g_proxy_failure.json)。器件盒只通过视觉壳内的[必要空间筛查](../evidence/body_reservations_r2_compact_front_v53.json)。该候选没有真实抓物、可拼装中空壳、步态和新比例跨引擎验证，且原图外观仍未通过；**外观、制造、采购和工程交付继续不放行**。

最新[指定 R2 尖嘴一致性审查](r2_pointed_bill_mechanism_gate.md)又排除了一个实体制造故障：旧视觉闭嘴上下喙互穿约 `9.13 cm³`，现视觉壳九点开合抽样无交集，并按 R2 下喙前移运动显示。新外形在[15 mm 低位外力代理](../evidence/physics_sit_r2_nonintersecting_bill_v55_x280_z15_50g_proxy.json)仍能短时保持双脚承重，但旧 RC2 是 `XC330 / 18 mm / 1:1` 直驱，指定 R2 是 `XL330 / 14 mm / 约 2:1`；二者的 CAD、BOM、接触动力学不能混用。长尖嘴的[薄壳质量代理](../evidence/r2_pointed_bill_v55_mass_screen.json)也提示早期 `65 g` 嘴部目标须重审。[XL330 同轴安装](../evidence/r2_pointed_bill_v55_xl330_coaxial_package_rejected.json)会明显露出当前头嘴轮廓，必须重排轴位或做内置远程传动。整机外观与可装配嘴部都未放行。

按最新“小机箱、前颈灵活、高髋长腿”建议做的[同版权衡](seated_pickup_layout_trade.md)显示：`270 × 190 × 170 mm` 继续缩壳没有增加固定网格中的可达点；髋轴上移 `25 mm` 与翼门外形重叠，并让深蹲膝罩更早碰地；双脚外移增加单脚换重心距离。现 `280 × 190 × 180 mm` 外形在一种 90 mm 下蹲、较陡的头姿下通过无物体 50 g 等效力短时保持，但[下喙张开扫掠](../evidence/seated_pickup_layout_trade_v55.json)显示同一低位不能安全使用 30 mm 全开。**地面物体夹取、起身和拖拽未通过，髋轴与站距不冻结。**

[内藏 XL330／2:1 传动带占位初筛](../evidence/r2_internal_belt_gross_package_v61.json)在 `2.7 mm` 假定壳壁下通过电机盒、33 个带路截面和九个理想嘴部位置的必要几何检查；[该版闭嘴](../images/r2_internal_belt_v61_closed_rejected_candidate.png)与[张嘴](../images/r2_internal_belt_v61_open_rejected_candidate.png)的侧颊和立耳依然不符合选定外观。**这不解除嘴部制造、真实夹取与整机外观阻断。**

[v69 头壳包覆试样](r2_pointed_bill_mechanism_gate.md)移除外突大侧颊，并通过[头壳、固定上喙、运动下喙及立耳的九点实体不互穿检查](../evidence/r2_head_wrap_gross_package_v69.json)。传动带与电机仅在假设包络内放得下；真正内框、舵盘、轴承、打印分壳和带载动作未完成。外观仍未按用户参考图验收，**工程、采购和 Sai_Lab 新比例 Sim2Sim 交付继续不放行**。

[v72 头嘴和低轮廓鞋门候选](r2_pointed_bill_mechanism_gate.md)进一步修正相机面板与上喙的实体干涉，使两者最近距离约 `3.43 mm`；[同版必要包络](../evidence/r2_head_wrap_gross_package_v72.json)保持九个理想张合样点无已检查避让件互穿。圆角头罩和较薄翼门／鞋底是可比较的外观试样，尚未达到用户指定的整机形象，也未生成可拼装中空头架、真实传动和可验收步态。**外观、制造、采购与工程交付仍不放行。**

[v73 薄下喙候选](r2_pointed_bill_mechanism_gate.md)使指定的 `90 mm` 下蹲、`(300,25) mm` 嘴尖、`60°` 头俯姿态在[41 点视觉路径](../evidence/r2_slim_bill_v73_sit90_x300_z25_head60_open.json)中保留约 `6.98 mm` 的全开下喙离地间隙和 `26.04 mm` 的头罩—机身采样间隙；原先更靠近身体的低位姿态仍失败。这只找到一处有余量的**视觉姿态**，没有证实嘴内抓住目标、双脚动态承重、带物起身、移动拖拽或新比例步行。削薄下喙还须验证真实承力。**外观、制造、采购和工程交付继续不放行。**

[v92 整机比例试样](r2_whole_proportions_review.md)把头罩视觉高度收至 `104 mm`、拉长颈段后，同姿态的九个低位几何目标由 v73 的 `8/9` 增至 `9/9`，假设的内部电机／带路粗包络也通过；[张嘴路径](../evidence/r2_whole_proportions_v92_sit90_x300_z25_open.json)下喙最低约 `6.98 mm`。但按 `1.6 mm` 薄壳代理的站姿重心比 v73 高约 `5.62 mm`，目标姿态需约 `58.91°` 上颈相对俯仰和 `−70.07°` 头相对俯仰，实际电机行程、线束和力矩均未验证。相机外观、嘴根遮蔽、可装配结构、夹拖和单脚步行仍缺失；**外观、制造、采购及 Sai_Lab 新版训练交付继续不放行**。

[v95 连续头罩局部试样](r2_whole_proportions_review.md#v95-嘴根与连续头罩的局部试样)把四杆收至嘴根内侧，并为活动件切出采样运动避让；开、闭两端所列头罩与连杆实体交集为零，闭嘴的显眼矩形缺口缩小。原头罩 STL 含退化三角面，另存的拓扑清理版可封闭加载；没有连续扫掠或完整电机／带路／轴承装配验证，也没有可制造分壳。**这不改变上述四项不放行结论。**
