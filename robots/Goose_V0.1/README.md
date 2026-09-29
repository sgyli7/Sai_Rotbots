# Goose_V0.1 — 工程与原始资料入口

第二阶段交接：[嘴部传动、低位接近与供电架构](design/stage_two_parameter_handoff.md)。**当前候选为 `goose_stage_two_si_v2`，18 轴、8.854 kg；嘴部和中颈驱动升级，名义及 4 个扰动低位往返通过。** 供电窗口/回馈保护与封闭头壳热能力仍阻止硬件硬冻结。Sai_Lab 新实验请显式选择第二阶段；下方第一阶段保持历史记录。

第一阶段交接：[18 轴结构与物理参数包](design/stage_one_parameter_handoff.md)。**约 8.62 kg、MJCF + URDF + 逐体惯量 + 统一 SI 契约 + PPO 入口已提供，可启动初训；硬件硬冻结尚未通过。** 嘴持续输出、电源配套和低位拾取控制的未决项与修改边界均在交接页列明。旧 16 轴 RC2 资料不能作为本版训练输入。

执行节奏：[整机里程碑与 Sai_Lab 交接门槛](design/hardware_milestones.md)。当前先收敛大结构，再交付训练基线，制造细节随后完善。

硬件主线：[已确认外观到完整硬件交付](design/accepted_hardware_execution.md)，包含交付证明要求和同版质量／颈部负载初筛。

最新硬件增量：[脚底分层候选与嘴部传动筛查](design/foot_support_and_beak_transmission.md)；保留接地轮廓、增加金属板毛坯，条件减重约 280 g，固定接口尚未完成。

当前已确认外观入口：[饱满机身／大眼／流线鹅掌候选](design/fuller_exterior_review.md)。按最新三条反馈扩大机身并检查八组模块预留，恢复大眼表达、调整脚掌；**用户已确认这一阶段外观并授权上传 GitHub**；进入同版硬件落地，物理和制造仍未通过。

[上一版铰接嘴候选](design/hinged_beak_exterior_review.md)保留对照；约 50 N 仍为待验证目标。

[肩胸与收尾曲面候选](design/sculpted_exterior_review.md)因头嘴不协调、身体不够简约而被后续方向取代，不是获批外观。

[流线型候选失败记录](design/streamlined_exterior_review.md)：用户否决头身卵形比例，当前继续重做形体，不能进入物理放行。

本目录保留了交接包中的图片、文档、工作簿和 CSV；包内旧方案仍可完整查阅。**当前工程候选**按用户后来确认的目标推进：室内平地双足鹅、游戏般的好奇和捣蛋感、叼起与拖拽同等重要、简约手动翼形检修门、鹅叫和头颈动作。所有设计须同时满足外观方向与可制造、可运行。概念图不是尺寸或性能依据。

**当前状态：fuller 外观已获用户确认；旧 RC2 外观曾被否决，其物理结果不适用于新版。制造和采购均未放行。** 原交接包的 [B 步行鹅](design/concepts/history/walker_b_selected_reference.png) 及用户再次指定的 [R2 闭嘴尖嘴](design/concepts/r2_pointed_beak_closed_reference.jpg)、[R2 平行张嘴](design/concepts/r2_pointed_beak_parallel_open_reference.jpg) 是历史外观基线；用户随后允许按反馈与审美重新设计，最新铰接嘴候选优先。旧 RC2 虽已有可编辑 CAD 源、STEP/STL、MuJoCo 模型、统一 SI 控制/训练接口和 Godot/Jolt 接收器，但[实际外形](design/exterior_review.md)严重偏离原图；旧几何和对应的静态试验不能作为新版放行证据。初版缩壳试验曾让嘴代替双脚撑地；[短鞋与前移膝轴候选](design/forward_knee_trade_study.md)找到无物体的双脚低位保持。[小机箱与前颈够地候选](design/r2_compact_front_reach_review.md)把视觉机箱收至 `280×190×180 mm`；随后[同版尖嘴修正](design/r2_pointed_bill_mechanism_gate.md)消除了原视觉上下喙壳的实体穿插，并按 R2 四连杆的前移轨迹张嘴。修正后的简化模型通过指定坐姿 50 g 等效力保持；它仍未复刻原图、夹住物体、单脚行走或完成可装配结构。[MicroDuck Max Pro 对照](design/microduck_max_pro_baseline.md)明确了可沿用的双足方法和 Goose 必须新增的腿脚机动、真实夹取与拖拽能力；18 主动轴已有独立第二阶段训练候选，第一阶段亦保留，旧 RC2 规格仍是 16 轴历史模型。UnitySim2Sim、BevySim2Sim 仍应从引擎无关的 SI 契约适配，尚未实现或验证。

| 历史 RC2 与过渡资料入口（18 轴请使用上方交接包） | 内容 |
|---|---|
| [RC2 历史规格](configs/robot_spec.json) | 机体、16 主动轴候选、尺寸、器件、动作边界与单位 |
| [交付完整性核查](evidence/delivery_integrity_rc2.json) | 59 个交接文件、本地链接、363 个 CAD 文件哈希及现行 BOM 数量核对；仅证明资料完整 |
| [CAD 清单](cad/exports/cad_manifest.json) / [整机 STEP](cad/exports/goose_rc2_assembly.step) | 打印件、材料/质量、各 STEP/STL；清单标示制造验收状态 |
| [RC2 候选 BOM](hardware/goose_rc2_bom.xlsx) / [CSV](hardware/goose_rc2_bom.csv) / [接线装配稿](hardware/goose_rc2_wiring_and_assembly.md) | 与 CAD/规格同步的工作清单；中国报价、线束、螺钉和额定核查未放行 |
| [MuJoCo 模型](models/full/robot.xml) / [跨引擎中立数据](models/full/rigid_transfer.json) | 自由根、双腿、头颈、嘴部闭环与质量惯量，运行接口为 SI |
| [工程基线](design/engineering_baseline.md) / [整机放行判定](design/release_readiness.md) / [早期验收快照](evidence/design_review_baseline.json) | 当前门槛、已通过证据及不能下单/交付的缺口；早期记录只保留溯源 |
| [本轮抽样装配](evidence/part_clearance_sampled_rc2.json) / [叼取](evidence/grasp_50g_rc2.json) / [短距牵引](evidence/drag_short_pull_rc2.json) / [Jolt v5 站立](evidence/godot_jolt_standing_v5_rc2.json) | 同一模型哈希下的分项证据，范围见各文件；[旧叼取姿态站立失败](evidence/godot_jolt_ground_grasp_stance_failure_rc2.json)保留 |
| [游戏动作观察](design/gameplay_sources_review.md) / [行为要求](design/behavior_requirements.md) | 叼、拖、停顿、回望、鹅叫；外部视频未实际取得画面时明确标注 |
| [实际外形核查](design/exterior_review.md) | 当前 CAD 渲染与游戏鹅的差距、下一版外饰和工程复查门槛 |
| [后掌候选与物理复核](design/stance_layout_review.md) | 脚型对照、条件质量与重心、MuJoCo 限力试验；外观及动力学均未放行 |
| [MicroDuck Max Pro 对照](design/microduck_max_pro_baseline.md) | 原机质量/脚型/关节/训练方法量测；Goose 6 轴腿与 18 主动轴新候选的验证条件 |
| [R2 加长尖嘴外观对照](images/r2_pointed_max_pro_three_quarter_candidate.png) / [张嘴细节](images/r2_pointed_max_pro_open_detail_candidate.png) | 仅供 B/R2 视觉比较，未通过外观或工程放行 |
| [R2 高颈比例侧视](images/r2_proportion_side_candidate.png) / [斜视](images/r2_proportion_three_quarter_candidate.png) / [平行张嘴](images/r2_proportion_open_beak_candidate.png) | 前一轮视觉候选；仍有头、颈、脚的大轮廓偏差，未通过外观验收 |
| [六轴腿与单脚证据](evidence/physics_stance_trial_r2_proportion_ankle_roll_single_support.json) / [踝部包装筛查](evidence/ankle_roll_package_screen_r2_proportion.json) | 双脚侧移有改善，三组单脚卸载均失败；第六轴未放行 |
| [较紧凑 R2 比例侧视](images/r2_ankle_clearance_side_candidate.png) / [斜视](images/r2_ankle_clearance_three_quarter_candidate.png) / [平行张嘴](images/r2_ankle_clearance_open_beak_candidate.png) | 上一轮外观候选；踝轴保留高度，仍未通过外观和制造验收 |
| [新比例低头与单脚试验](evidence/physics_stance_trial_r2_ankle_clearance_six_axis.json) / [踝电机本体盒](evidence/ankle_roll_package_screen_r2_ankle_clearance.json) | 站立 2 秒，低头与单脚失败；鞋壳、电机承力与线束仍未闭合 |
| [缩壳站立侧视](images/r2_compact_body_side_candidate.png) / [斜视](images/r2_compact_body_three_quarter_candidate.png) / [坐姿低头](images/r2_compact_body_seated_reach_side_candidate.png) | 最新视觉对照；缩壳和双腿折低只改善几何可达性，外观复刻仍未通过 |
| [缩壳视觉 STEP 与清单](cad/exports/goose_r2_compact_body_visual_candidate_manifest.json) / [坐姿几何](evidence/exterior_seated_reach_r2_compact_body_tip40.json) / [坐姿接触试验](evidence/physics_seated_reach_r2_compact_body_tip40.json) | 视觉实体不可直接制造；嘴端受地面反力，未验证坐姿夹物 |
| [短鞋／前移膝轴对照](design/forward_knee_trade_study.md) / [候选斜视](images/r2_forward_knee_three_quarter_candidate.png) / [坐姿侧视](images/r2_forward_knee_seated_reach_x280_side_candidate.png) | 保留缩壳与 R2 尖嘴；双脚承重的无物体坐姿通过 2 秒简化试验，50 g 仅过静力初筛；外观、真实夹取和步行未放行 |
| [紧凑轮廓审查](design/r2_compact_silhouette_review.md) / [闭嘴斜视](images/r2_compact_silhouette_v51_three_quarter_candidate.png) / [张嘴近景](images/r2_compact_silhouette_v51_open_beak_candidate.png) | 机箱 `310×190×180 mm` 视觉草模；一条坐姿几何路径和 50 g 等效力低位保持通过初筛，仍无夹持、步行或制造放行 |
| [小机箱与前颈够地审查](design/r2_compact_front_reach_review.md) / [站姿斜视](images/r2_compact_front_reach_v53_three_quarter_candidate.png) / [坐姿侧视](images/r2_compact_front_reach_v53_seated_side_candidate.png) | 视觉机箱前后缩至 `280 mm`；15 点坐姿工作区几何初筛通过 13 点，嘴尖高 15／25 mm 的 50 g 外力代理保持通过，10 mm 动态碰地失败；外观和制造仍未放行 |
| [尖嘴实体与 R2 机构一致性](design/r2_pointed_bill_mechanism_gate.md) / [闭嘴近景](images/r2_nonintersecting_bill_v55_closed_detail_candidate.png) / [平行张嘴近景](images/r2_nonintersecting_bill_v55_open_detail_candidate.png) | 消除原视觉喙壳约 `9.13 cm³` 穿插，九点理想运动中两片橙色壳零穿插；同版低位外力保持仅为无物体必要初筛。旧 RC2 嘴机构型号、轴距和传动比均不符合指定 R2，不能直接换皮 |
| [小机身／高髋／前颈坐姿拾取权衡](design/seated_pickup_layout_trade.md) / [几何记录](evidence/seated_pickup_layout_trade_v55.json) | 再缩机箱没有增加已筛可达点；髋上移 25 mm 与现翼门外形冲突，更宽双脚增加单脚换重心距离；15 mm 嘴尖目标在张嘴后可能撞地，均未制造或夹取放行 |
| [内藏嘴部电机必要包络](design/r2_pointed_bill_mechanism_gate.md#内藏电机与传动带的必要包络初筛) / [几何记录](evidence/r2_internal_belt_gross_package_v61.json) | XL330 和假定 2:1 带路可在头壳／嘴根粗包络中放下；侧颊、细长立耳仍不符合指定外观，未放行制造和采购 |
| [头壳包覆 v69](design/r2_pointed_bill_mechanism_gate.md) / [闭嘴斜视](images/r2_head_wrap_v69_closed_three_quarter_candidate.png) / [张嘴近景](images/r2_head_wrap_v69_open_detail_candidate.png) / [实体核查](evidence/r2_head_wrap_gross_package_v69.json) | 收回外突大侧颊；九点理想张合的头壳／尖嘴／立耳无实体互穿。仍未复刻指定外观，也不是可装配、可采购或已验证夹拖的结构 |
| [头嘴与低鞋门 v72](design/r2_pointed_bill_mechanism_gate.md) / [闭嘴斜视](images/r2_head_wrap_v72_closed_three_quarter_candidate.png) / [平行张嘴](images/r2_head_wrap_v72_open_detail_candidate.png) / [实体核查](evidence/r2_head_wrap_gross_package_v72.json) | 修正相机面板与固定上喙干涉并保留隐藏电机／带路的假设包络；头罩更圆、翼门和鞋底更薄。仍未通过外观、装配、夹拖或采购验收 |
| [薄下喙 v73](design/r2_pointed_bill_mechanism_gate.md) / [闭嘴斜视](images/r2_slim_bill_v73_closed_three_quarter_candidate.png) / [张嘴近景](images/r2_slim_bill_v73_open_detail_candidate.png) / [坐姿侧视](images/r2_slim_bill_v73_sit90_x300_z25_head60_open_side_candidate.png) | 保留尖嘴、平行张嘴与头内藏驱动方向；一处下蹲视觉姿态通过有限几何净空筛查。仍未复刻外观，也未证实真实抓拖、步行或可打印装配 |
| [上颈默认折姿 v79](design/exterior_review.md) / [侧视](images/r2_neck_rest15_v79_closed_side_candidate.png) / [斜视](images/r2_neck_rest15_v79_closed_three_quarter_candidate.png) | 上颈向后折 15°，头嘴保持水平；同一低位九目标仍过 8/9，但拾取终点多需 15° 头颈关节转角。仅作外观对照，不替换 v73，也未通过外观或工程验收 |
| [贴合曲面的翼形门 v81](design/exterior_review.md) / [侧视](images/r2_conformal_wing_v81_closed_side_candidate.png) / [斜视](images/r2_conformal_wing_v81_closed_three_quarter_candidate.png) | 原机身轮廓上切分贴面门片，保留简约翼门方向；低位九目标仍过 8/9。门片缺薄壳、铰链和锁止，仅为局部外观备选，不能打印装配；整机仍按未通过外观的 v73 工作候选继续 |
| [低头罩与长颈比例 v92](design/r2_whole_proportions_review.md) / [闭嘴斜视](images/r2_whole_proportions_v92_closed_three_quarter_candidate.png) / [张嘴近景](images/r2_whole_proportions_v92_open_detail_candidate.png) / [坐姿侧视](images/r2_whole_proportions_v92_sit90_open_side_candidate.png) | 同版低位九目标几何初筛 9/9、嘴部粗包络通过；条件重心升高约 5.62 mm，所需头颈角度、真实夹拖与整机外观均未验收。只作为比例比较，不能打印装配或采购 |
| [连续头罩与内收四杆 v95](design/r2_whole_proportions_review.md#v95-嘴根与连续头罩的局部试样) / [闭嘴整机](images/r2_swept_head_v95_closed_three_quarter_candidate.png) / [张嘴整机](images/r2_swept_head_v95_open_three_quarter_candidate.png) | 去掉 v92 的矩形头罩缺口；开闭两端所列头罩／连杆实体不互穿，但中途只做有限采样；原头罩网格的退化面已另存清理版，仍非可装配打印件。外观与同版物理未通过 |
| [居中脚掌 v96](design/r2_whole_proportions_review.md#v96-脚掌居中站姿与低位任务一起看) / [站姿侧视](images/r2_centered_foot_v96_closed_side_candidate.png) / [坐姿张嘴](images/r2_centered_foot_v96_sit90_open_side_candidate.png) | 只把两鞋后移 `20 mm`；条件站姿余量改善，低位叼取前方余量变小，髋部负载仍未过粗筛。保留比较，不定版或下单 |
| [v95 整机对齐闸门](evidence/r2_swept_head_v95_system_alignment.json) / [放行总览](design/release_readiness.md) | 最新视觉 R2 与 RC2 模型在嘴机构轴距、电机、传动比和机身包络上不一致；旧模型试验不得用于新版放行 |
| [v73 与运行模型一致性闸门](evidence/r2_slim_bill_v73_model_alignment.json) | 明确检出当前 RC2 的 `18 mm/XC330/1:1/16 轴` 与 v73 视觉 R2 的 `14 mm/XL330/暂定 2:1` 不一致；旧模型与 CAD 不能作为 v73 的 Sai_Lab、采购或制造交付 |
| [结构/执行器核查](design/servo_mount_geometry_review.md) / [电源事实](design/power_bus_facts.md) | 原厂几何、电气限制与来源 |
| [跨引擎验收清单](design/backend_conformance_facts.md) | Godot 局部单位转换；Unity/Bevy 后续应逐项证实的适配条件 |
| [双足控制审查](design/locomotion_review.md) | 旧训练失败根因、现行站姿控制和独立步态判据；行走仍未通过 |
| [打印机与材料](design/printer_selection.md) / [采购包装核查](design/procurement_packaging_facts.md) | 当前建议 X2D 普通打印配置、P2S 为 PETG 经济选项；中国现价与供货待核 |
| [鹅叫素材](models/full/audio/honk.wav) / [音频清单](models/full/audio/audio_manifest.json) | 自制声音，用于动作表达；扬声器音量须实物验收 |

## 保留的交接包与设计历程

- [conversation_handoff.md](design/conversation_handoff.md) 和[交接时的机器人 README](source/robot_readme_handoff.md)记录原交接时的目标和决策顺序；其 18 轴/XL330 与“尚无 CAD”等表述是**当时状态**，不能覆盖此后的 16 轴/XC330 工程候选。
- [嘴部 R2 原说明](design/beak_r2.md)、[机构图复核](design/kinematic_review.md)、[整体旧结构](design/walker_structure.md) 与 [原采购工作簿](hardware/walker_r2_bom.xlsx) 都保留原始设计线索；旧工作簿不是当前订货单。
- [原嘴部采购 CSV](hardware/beak_r2_purchase.csv)、[原打印件 CSV](hardware/beak_r2_print_parts.csv)、[图片资料库](design/concepts/index.html) 和 [完整导入索引](source/asset_index.md) 可查旧版与用户补图。包内图片、文档、表格保留；仅原包 README 修复两处本地相对链接。
- 当前外形参考 [用户的翼形检修门批注图](design/concepts/wing_access_reference.png)；门手动开合、抽象曲面，不画写实羽毛、不增加翅膀电机。

构建入口位于仓库的 `scripts/cad/build_goose_cad.py`、`scripts/models/build_goose.py`、`scripts/models/export_goose_transfer.py`、`scripts/training/train_goose_rsl.py`。模型和加工验收结果必须记录所用规格与文件哈希，不能把早期失败试验的输出覆盖成成功。
