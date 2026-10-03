# Gorilla V0.1

当前工作：**G9实际主躯与完整系统两布局已封存，整装仍拒绝；G10接回肩驱动并运行真实子件三维拓扑优化。** 壮硕体积用于宽厚承力与系统共同设计。用户指定「Gorilla 设计」重画腿脚，完成后通知；这里继续可适配的内部工程。C15 已先提交并合主干，AA3仍为审美权威。完整质量/驱动热/稳定SI尚未放行，双足、双手与自主复杂Bevy目标继续推进。

唯一当前状态入口：[当前决定与门禁](design/current_decisions.md)。

| 资料 | 入口 |
|---|---|
| 唯一外观基准 | [用户再次确认的四视图](design/concepts/aa3/user_confirmed_four_view.jpg)；其他图片与粗模仅为历史资料 |
| 来源身份 | [唯一外观权威记录](source/appearance_authority.json)；[原包导入与哈希](source/appearance_import.json) |
| C 工作输入（迭代中） | [appearance_c_spec.json](configs/appearance_c_spec.json)；[原稿轮廓与分区点](source/appearance_c_reference_landmarks.json)；[可见护甲区域约束](source/appearance_c_front_shape_constraints.json) |
| C15 阶段基底 | [提交说明与缺口](design/appearance_c15_stage.md)；[冻结映射](../../experiments/gorilla_v0_1/appearance_c_round_fifteen/snapshot_manifest.json)；[Blender](../../experiments/gorilla_v0_1/appearance_c_round_fifteen/appearance_c.blend)、[GLB](../../experiments/gorilla_v0_1/appearance_c_round_fifteen/appearance_c.glb) |
| C15 实际复合脚 | [中立](../../experiments/gorilla_v0_1/appearance_c_round_fifteen/appearance_c_foot_left.png)、[卸载折叠](../../experiments/gorilla_v0_1/appearance_c_round_fifteen/appearance_c_foot_folded_left.png)、[机制拆壳](../../experiments/gorilla_v0_1/appearance_c_round_fifteen/appearance_c_foot_mechanism_left.png)；[原生几何检查](../../experiments/gorilla_v0_1/appearance_c_round_fifteen/composite_foot_c15_screen.json) |
| 内部 B 历史拒绝候选 | [改变、粗算与拒绝评审](design/internal_structure_b_review.md)；[原生源](cad/source/internal_structure_b_scene.json)、[Blender](cad/source/internal_structure_b.blend)、[GLB](cad/exports/internal_structure_b/internal_structure_b.glb)；原护甲保留但匹配未通过 |
| 内部 D 历史拒绝候选 | [同版评审/复现](design/internal_structure_d_review.md)；[整机native源](cad/source/internal_structure_d_scene.json)、[Blender](cad/source/internal_structure_d.blend)、[GLB](cad/exports/internal_structure_d/internal_structure_d.glb)；[冻结清单](../../experiments/gorilla_v0_1/internal_structure_d/snapshot_manifest.json) |
| 内部 D 同源图 | [四视](images/internal_structure_d_four_view.png)、[拆壳斜视](images/internal_structure_d_cutaway_threequarter.png)、[侧拆壳](images/internal_structure_d_cutaway_left.png)；原111甲壳不改，冲突没有隐藏 |
| 内部 D 参数/证据 | [统一参数](configs/internal_structure_d_spec.json)、[全机模块](configs/internal_structure_d_system_spec.json)；[质量/接触/空间](evidence/internal_structure_d_screen.json)、[功率/流量](evidence/internal_structure_d_power.json)、[红黄线](evidence/internal_structure_d_gates.json) |
| G2 安装检查点 | [实际源/范围/下一动作](../../experiments/gorilla_v0_1/internal_structure_g2_modules/README.md)；全部安装未放行，隐藏几何可新源重建 |
| G3 功能链与新末端 | [实际源/粗算/完整图/失败](../../experiments/gorilla_v0_1/internal_structure_g3_functional_chains/README.md)；未组成新整机，新粗甲不采用 |
| 新末端参考与授权 | [六图来源清单](design/concepts/leg_terminal_references/source_manifest.json)；可重设计末端，参考不提供承载认证 |
| G/G1 历史研究 | [实际结果/复现](../../experiments/gorilla_v0_1/internal_structure_g_studies/README.md)；原生材料、原厂安装、腰/下腿/手部源及整体资源粗算；未组成新整机 |
| 最近完整 E2a 研究 | [整机源/同源图/拒绝](../../experiments/gorilla_v0_1/internal_structure_e2/README.md)；未合格历史账本，不作定型质量 |
| 内部 E 开局诊断 | [完整轴参考](../../experiments/gorilla_v0_1/internal_structure_e_constraints/README.md)；[串联腿、全关节热路与独立复核](../../experiments/gorilla_v0_1/internal_structure_e_probes/README.md)；实际失败分支，未组成整机或换审美基准 |
| 分置线性/泵阀一手依据 | [型号事实/有限几何/电热条件](hardware/distributed_internal_component_references.md)；参照、假设与联合资格分别报告 |
| 内部 C 历史拒绝探针 | [同版评审/复现](design/internal_structure_c_review.md)；[净材料/组件源](cad/source/internal_structure_c_scene.json)；[联合接触/驱动](evidence/internal_structure_c_screen.json)、[空间拒绝](evidence/internal_structure_c_space.json)、[门禁](evidence/internal_structure_c_gates.json)；[冻结清单](../../experiments/gorilla_v0_1/internal_structure_c/snapshot_manifest.json) |
| 内部 B 同源图 | [整机正](images/internal_structure_b_front.png)、[左](images/internal_structure_b_left.png)、[后](images/internal_structure_b_rear.png)、[拆壳斜视](images/internal_structure_b_cutaway_threequarter.png)、[脚近景](images/internal_structure_b_foot_mechanism_detail.png)；新模块与冲突没有隐藏 |
| 内部 B 参数/证据 | [参数](configs/internal_structure_b_spec.json)、[真实姿态/静力](evidence/internal_structure_b_statics.json)、[正体积冲突](evidence/internal_structure_b_space.json)、[独立脚复核](evidence/internal_structure_b_foot_review.json)、[资源/端点力矩检查](evidence/internal_structure_b_resource_check.json) |
| Tesla / Figure / GD01 参照 | [一手共同设计研究](hardware/internal_co_design_references.md)；区分代际、公开事实与推断，不继承联合额定或未公开 CAD |
| 包装授权与共同设计方法 | [历史 C 任务依据](design/internal_co_design_c_brief.md)；C/D 已有实际候选与拒绝图，下一方案以当前决定为准 |
| 紧凑电驱部件参照 | [原厂组件事实与条件](hardware/compact_electric_component_references.md)；包含支承的齿轮组件和精确绕组电机仍需整套匹配 |
| 内部架构 A 前一候选 | [粗算、装配与红黄线评审](design/internal_architecture_a_review.md)；[两路线同尺度实图](images/internal_architecture_a_route_comparison.png)；四路线仍未通过 |
| 内部架构 A 参数与证据 | [预算配置](configs/internal_architecture_a_spec.json)、[布局配置](configs/internal_architecture_a_layout.json)；[宏观预算](evidence/internal_architecture_a_budget.json)、[空间/重心/接地筛查](evidence/internal_architecture_a_space.json) |
| 内部研究输入与真实 CAD | [真实驱动/能源/热/感知模块依据](hardware/internal_module_research.md)；原厂参考网格仅本地忽略保存，受控模型为自有模块包络 |
| 历史 C14 可编辑模型 | [Blender 源](../../experiments/gorilla_v0_1/appearance_c_round_fourteen/appearance_c.blend)、[GLB](../../experiments/gorilla_v0_1/appearance_c_round_fourteen/appearance_c.glb)、[参数化几何源](../../experiments/gorilla_v0_1/appearance_c_round_fourteen/appearance_c_scene.json)；外观/物理仍未通过 |
| 历史 C14 实际对照 | [同源四视](../../experiments/gorilla_v0_1/appearance_c_round_fourteen/appearance_c_four_view.png)；[阶段实渲审查](design/appearance_c_checkpoint_review.md)；[渲染身份](../../experiments/gorilla_v0_1/appearance_c_round_fourteen/appearance_c_render_manifest.json) |
| 内部主结构实渲 | [拆壳斜视](../../experiments/gorilla_v0_1/appearance_c_round_fourteen/appearance_c_structure_threequarter.png)、[正面](../../experiments/gorilla_v0_1/appearance_c_round_fourteen/appearance_c_structure_front.png)、[侧面](../../experiments/gorilla_v0_1/appearance_c_round_fourteen/appearance_c_structure_left.png)；同一实际几何，隐藏的护盖逐项记录 |
| 主体受力入口与结果 | [计算依据](design/structure_c14_basis.md)；[同版受力记录](../../experiments/gorilla_v0_1/appearance_c_round_fourteen/structure_c14_screen.json)、[红黄线](../../experiments/gorilla_v0_1/appearance_c_round_fourteen/structure_c14_gates.json)；有限准静力筛查，不是稳定动力学合同或吨级认证 |
| 当前工作树几何 | [可编辑控制网格](cad/source/appearance_c_scene.json)；后续增量须完成实渲/导出检查后才成为冻结候选 |
| C 外观增量与复现（历史） | [历轮冻结评审](design/appearance_c_checkpoint_review.md)；[历史 C14 冻结映射](../../experiments/gorilla_v0_1/appearance_c_round_fourteen/snapshot_manifest.json)（46 副本）；网格/文件身份通过，外观仍未通过 |
| 历史 C14 等高整机对照 | [正面](images/appearance_c_round_fourteen_front_comparison.png)、[侧面](images/appearance_c_round_fourteen_left_comparison.png)、[后面](images/appearance_c_round_fourteen_rear_comparison.png)；原图相机未校准，图像不能证明物理能力 |
| 用户新增背部控制屏 | [同版背屏近景](../../experiments/gorilla_v0_1/appearance_c_round_fourteen/appearance_c_rear_panel_detail.png)；原蓝板外框/固定点保留，状态/任务/本地控制为静态界面候选 |
| 散热入口原生几何复核 | [同版入口检查](../../experiments/gorilla_v0_1/appearance_c_round_fourteen/appearance_c_intake_clearance.json)；每侧 2008 个当前格栅间隙样本无蓝白甲遮挡，仅验证采样入口，不代表完整排风或热能力 |
| 持续排期与 PM | [滚动排期](design/project_schedule.md)；当前聊天每两小时检查实际产出 |
| 被否决的 B 与复现入口 | [layout_b_spec.json](configs/layout_b_spec.json)；[首轮候选评审](design/layout_b_checkpoint_review.md) |
| 历史 B 三维代理 | [四视图](images/layout_b_four_view.png)、[Blender 源](cad/source/layout_b.blend)、[GLB](cad/exports/layout_b/layout_b.glb)；仅作失败对照 |
| 历史 B 工程证据 | [SI 合同](models/full/robot.json)、[汇总](evidence/layout_b_checkpoint.json)、[质量账本](hardware/layout_b_mass_components.csv)、[静力与拒绝测试](evidence/layout_b_screen.json)；不代表 C |
| 历史尺寸探索参数 | [layout_a_spec.json](configs/layout_a_spec.json)；未生成模型，不能作为外观基准 |
| 任务与接口边界 | [任务和仿真交接](design/task_and_simulation_handoff.md) |
| 器件依据 | [驱动和供电参照](hardware/component_basis.md) |

首版核心为双足移动、双手操作、自主感知/规划/执行，最终在 Bevy 等游戏引擎的原生物理世界中完成搬运和环境操作。用户将功能目标定位为 Figure / Tesla Bot 的 MAX PRO，GD01 用于大型体量参考；Goose 用于流程经验。各参照的轴数、质量、尺寸、执行器和策略不继承。

C15 将前掌、足弓与后跟分开，取消跨段连续底板；卸载端姿态有界几何检查通过，固定侧止挡安装和锁止承力仍开放。尚未建立新脚 SI 合同，C14 整板脚的质量/接触/受力结果不适用于 C15。

历史 C14 已建立实际有限壁厚框架和条件质量/受力账本，包含当时脚底单向反力、关节六维载荷和限定截面应力。42 梁中 30 梁有有限筛查、12 梁未分析；条件毛料及组件预留总质量约 1.15–1.79 吨。完整惯量、轴向/驱动、连接/轴承/脚底、运动接触和热仍未闭合，外观也未放行。B 的失败记录保留，两版证据不混用；首个完整工程检查点仍未达标。

早期内部基底：[G4 单关节／拓扑比较](../../experiments/gorilla_v0_1/internal_structure_g4_joint_study/README.md)与[G5 CPU 拓扑工具链](../../experiments/gorilla_v0_1/topology_g5_toolchain/README.md)。前者是未放行的实际内部bench，后者只校验数值工具；完整三维骨架和整机能力仍由[当前决定](design/current_decisions.md)继续推进。

[G6 实际三维输入与网格拒绝证据](../../experiments/gorilla_v0_1/topology_g6_3d_inputs/README.md)：宽厚承力域与同源节点载荷入口；当前网格不适用于结构FEM，没有机器人减重或强度放行。

[G7 实际CAD与三维条件基线](../../experiments/gorilla_v0_1/topology_g7_cad_baseline/README.md)：合法宽厚承力件、两档体网格及独立数值核验；已识别压撑顶墙传力风险，尚无骨架优化、强度或整机资格。

[G8 宽厚内部传力路径对照](../../experiments/gorilla_v0_1/topology_g8_material_paths/README.md)：两真实CAD及完整42条件工况；连续内肋显著改善压撑刚度，驱动/接触/全机资格仍开放。接续G9整体主结构与机电空间共同安排。

[G9 宽厚主躯与完整系统实际共布](../../experiments/gorilla_v0_1/internal_structure_g9_torso_co_layout/README.md)：两真实主core、九组两实际摆位、切面和宏观质量/翻转力矩；整装失败保存，接续完整肩接口与有界真实三维优化。
