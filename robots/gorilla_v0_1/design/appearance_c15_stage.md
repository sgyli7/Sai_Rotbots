# Gorilla C15 阶段保存

2026-10-02。此阶段保存现有外壳、主框架和可折叠复合脚，作为正式内部结构设计前的可回退基底。它不是外观认可、稳定物理合同、实物承载或复杂任务验收。

阶段提交 `94e0e074` 完成于21:16:53，随后正式开始内部设计。经210项合并树测试、独立安装包资源检查和两次CI通过，[PR #4](https://github.com/sgyli7/Sai_Rotbots/pull/4) 于22:12:45合入主干 `00ab3773`；见[集成记录](../evidence/appearance_c15_main_integration.json)。本页补充提交事实，冻结副本和物理缺口不变；新工作见[内部架构A](internal_architecture_a_review.md)。

## 同源候选

- [冻结映射](../../../experiments/gorilla_v0_1/appearance_c_round_fifteen/snapshot_manifest.json)保存参数、生成入口、原稿、原生场景、Blender/GLB、四视和三张脚部实渲及几何证据。原生场景 SHA-256：`7a1e49f45838303ca5fd86265dc9980c10cde85ed7626424136afd3863aa5886`。
- 613 个原生分件；深/宽/高约 1.0685 / 1.9259 / 2.6494 m。原稿比例优先，页眉宽度继续待核。标准四视为完整中立装配，没有隐藏本体或修改截图。
- 脚部包含独立前掌、固定足弓、独立高后跟、分开的接地垫、有限壁厚局部梁、轴/衬套/叉件及候选止挡/可退出锁舌。没有跨前后活动组的一整块底板或刚性梁。上踝两侧各 10 件原网格保留。
- [原生脚检查](../../../experiments/gorilla_v0_1/appearance_c_round_fifteen/composite_foot_c15_screen.json)验证 132 个脚组件闭合、绕序一致、正体积。两侧中立各四对候选止挡贴面明确分类；卸载前掌 −15°、后跟 +10°、锁舌退 32 mm 后无额外跨组相交。这是两个离散端姿态，尚未覆盖连续扫掠、同组接口、完整机器人或带载折叠。
- [实际四视](../../../experiments/gorilla_v0_1/appearance_c_round_fifteen/appearance_c_four_view.png)、[中立脚](../../../experiments/gorilla_v0_1/appearance_c_round_fifteen/appearance_c_foot_left.png)、[卸载折叠](../../../experiments/gorilla_v0_1/appearance_c_round_fifteen/appearance_c_foot_folded_left.png)与[机制拆壳](../../../experiments/gorilla_v0_1/appearance_c_round_fifteen/appearance_c_foot_mechanism_left.png)来自同一实际几何。折叠与机制图是明示的局部隔离。

## 下一阶段必须关闭

[接口交接](../../../experiments/gorilla_v0_1/appearance_c_round_fifteen/composite_foot_c15_interfaces.json)记录全部保留件、分组及缺口。前止挡支架顶面 Z=0.052 m 与固定轴座底面 Z=0.087 m 有 35 mm 安装间隔；固定侧安装、叉件与局部梁的连接、轴/支承、锁止保持及失电安全尚未成为连续承力链。它们属于物理红线，不能因可定制标黄而放行。外观细节仍有差异，后续按真实内部占位做有依据的小幅调整。

本阶段没有修改历史 B 的运行模型或 C 的 SI 参数；显示活动组不代表新物理关节。C14 的整板脚静力和条件毛料账本仅保留历史含义，不能移植到 C15。数吨测试压力与双手搬运载荷分开。

提交后首先建立整机质量/空间/力矩/功率/供电/回馈/热预算，再比较完整旋转电驱、线性电驱与液压/电液路线，把真实参数依据及简化模块放进现有壳体。采购明细、装饰细节和 PPO 后置。

## 复核入口

```bash
.venv/bin/python scripts/models/build_gorilla_appearance_reconstruction.py
.venv/bin/python scripts/models/render_gorilla_appearance_reconstruction.py --resolution 800 --samples 24 --views front,left,rear,top,foot_left,foot_folded_left,foot_mechanism_left
.venv/bin/python scripts/evaluation/check_gorilla_appearance_reconstruction.py
.venv/bin/python scripts/evaluation/check_gorilla_composite_foot.py
```

冻结源须按映射恢复到独立工作树，历史源码副本的 `.py.txt` 后缀在恢复时去除。持续状态以[当前决定](current_decisions.md)为准。
