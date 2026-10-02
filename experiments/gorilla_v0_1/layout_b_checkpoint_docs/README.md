# Gorilla V0.1

当前检查点：**`gorilla_layout_b`，按原图比例的探索工程布局，尚未冻结**。本轮从用户交接的 AA3 外观建立同源三维布局、质量账本、物理筛查和下一阶段入口。

唯一当前状态入口：[当前决定与门禁](design/current_decisions.md)。

| 资料 | 入口 |
|---|---|
| 唯一外观基准 | [用户再次确认的四视图](design/concepts/aa3/user_confirmed_four_view.jpg)；其他图片与粗模仅为历史资料 |
| 来源身份 | [唯一外观权威记录](source/appearance_authority.json)；[原包导入与哈希](source/appearance_import.json) |
| 当前布局参数源 | [layout_b_spec.json](configs/layout_b_spec.json)；[首轮候选评审与复现入口](design/layout_b_checkpoint_review.md) |
| 实际三维布局 | [四视图](images/layout_b_four_view.png)、[Blender 源](cad/source/layout_b.blend)、[GLB](cad/exports/layout_b/layout_b.glb)；简化代理，外观未放行 |
| 工程证据 | [SI 合同](models/full/robot.json)、[汇总](evidence/layout_b_checkpoint.json)、[质量账本](hardware/layout_b_mass_components.csv)、[静力与拒绝测试](evidence/layout_b_screen.json) |
| 历史尺寸探索参数 | [layout_a_spec.json](configs/layout_a_spec.json)；未生成模型，不能作为外观基准 |
| 任务与接口边界 | [任务和仿真交接](design/task_and_simulation_handoff.md) |
| 器件依据 | [驱动和供电参照](hardware/component_basis.md) |

首版核心为双足移动、双手操作、自主感知/规划/执行，最终在 Bevy 等游戏引擎的原生物理世界中完成搬运和环境操作。GD01 用于大型机器人方向参考；Goose 用于流程经验。两者的轴数、质量、尺寸、执行器和策略不继承。

首轮候选已生成，但首个检查点尚未达标：内部装配、空载静力、关键动作和外观仍未放行。三维布局、静力力代理和短时加载验证各有不同证据范围。此候选不能宣称已实现自主任务、持续驱动能力或制造放行。
