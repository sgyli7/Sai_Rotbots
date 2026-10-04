# Sai_Rotbots

面向真实世界互动与任务的开源机器人工程。保留轮腿机器人 **Sai_Agent_001**、后备箱平整的 **Sai_Agent_002**，并开发 **Goose V0.1** 与大型双足双手机器人 **Gorilla V0.1**。仓库由 `Sai_Agent_001` 直接改名，提交历史和旧版本发布均保留。

| Robot | Cargo bay | Guide |
|---|---|---|
| Sai_Agent_001 | Original powered opposed pads and belt mechanism | [001](robots/Sai_Agent_001/README.md) |
| Sai_Agent_002 | Continuous flat floor, no moving clamp mechanism | [002](robots/Sai_Agent_002/README.md) |
| Goose_V0.1 | Long-neck biped with a gripping beak; initial training checkpoint | [Goose](robots/Goose_V0.1/README.md) |
| gorilla_v0_1 | AA3 appearance; C15 segmented-foot stage, physical gates open | [Gorilla](robots/gorilla_v0_1/README.md) |

## Gorilla V0.1：AA3 外形与复合脚阶段

Gorilla 以用户确认的 AA3 四视图为唯一外观基准，原图比例优先、高度暂取 2.65 m；目标是双足移动、双手操作与自主复杂任务。当前 [C15 阶段基底](robots/gorilla_v0_1/design/appearance_c15_stage.md)保存实际外壳、有限壁厚主框架和分段前掌/足弓/后跟；已提供同源可编辑模型、七机位实渲及有界几何检查。

![Gorilla C15 actual source geometry](robots/gorilla_v0_1/images/appearance_c_four_view.png)

这是一份可回退的探索候选，外观、完整内部装配、锁止承力和稳定物理合同仍未放行。历史 B 的运行模型与 C15 显示几何分别保留版本；Gorilla 不使用现有轮腿控制器或策略，Bevy 原生物理任务尚待后续验证。下一阶段先闭合真实内部模块的质量、空间、输出、供电与热预算，再细化壳体。

## Goose V0.1：一只幽默又实用的机器人鹅

Goose 的初衷来自 [Untitled Goose Game](https://goose.game/)：把鹅的好奇、探头、歪头、回望、动作停顿和叫声带进真实世界，也让它能帮人做小事。**叼起物品和拖拽物体同等重要**；目标包括指定轻量日用品、布边、空拖鞋、轻篮及小车，支持遥控和“叼过来／拖到指定位置／放下”的指定物自主任务。这些是设计目标，完整任务能力仍待验证。

我们将它视作 [MicroDuck](https://github.com/pollen-robotics/microduck) 的“Max Pro”方向：借鉴双足互动机器人的经验，增加头颈活动范围、真实嘴部夹持和腿脚机动。外观追求简约的鹅感，以可打印曲面、大眼、橙色嘴脚和两侧手动检修门表达角色；检修门不画写实羽毛。最终外观须与实际制造装配一一对应。

### 当前工程装配

![Goose V0.1 当前手动翼门候选实际装配渲染](robots/Goose_V0.1/images/microduck_color_blocking_manual_wing_service/cream.png)

上图直接来自当前 **478 件候选源装配**，不是实物照片或最终制造验收图。单件打印主头壳、相机面板、夹嘴和深色承力结构分别承担实际功能。当前候选有 **18 个主动轴、约 10.40 kg 条件质量**；闭合零位包围尺寸约 **43.4 × 26.7 × 64.2 cm**（长 × 宽 × 高），姿态变化会改变外部包围尺寸。质量含设计预留，尚非实物称重。两侧检修门已加入实际手动铰链和关闭保持；上沿接缝和外露支臂仍待最终审美与制造资格。

| Cream 奶油白 | Graphite 石墨灰 |
|---|---|
| ![Cream](robots/Goose_V0.1/images/microduck_color_blocking_manual_wing_service/cream.png) | ![Graphite](robots/Goose_V0.1/images/microduck_color_blocking_manual_wing_service/graphite.png) |
| Lavender 薰衣草紫 | Sky 天空蓝 |
| ![Lavender](robots/Goose_V0.1/images/microduck_color_blocking_manual_wing_service/lavender.png) | ![Sky](robots/Goose_V0.1/images/microduck_color_blocking_manual_wing_service/sky.png) |

四款使用同版几何、同镜头与灯光，分别配置主壳、中性检修门／脸板、深色骨架、嘴脚及眼圈／鞋边辅色；见[配色与源身份记录](robots/Goose_V0.1/design/manual_wing_service_checkpoint.md)。

### 设计图与外观演进

| 早期 R2 尖嘴概念 | 已确认的阶段性外观基线 |
|---|---|
| ![R2 尖嘴概念图](robots/Goose_V0.1/design/concepts/r2_pointed_beak_closed_reference.jpg) | ![饱满机身、大眼与鹅掌外观基线](robots/Goose_V0.1/images/fuller_closed_three_quarter.png) |

这些图保留设计意图和演进过程。右侧[外观基线](robots/Goose_V0.1/design/fuller_exterior_review.md)曾获阶段性确认；之后按真实器件、承力和装配需求继续调整。概念图上的旧尺寸与性能不作为当前工程参数，当前手动翼门候选仍需最终审美与制造验收。

### 当前交付与下一步

当前 Sim2Sim 入口是[11 个碰撞体的任务代理](robots/Goose_V0.1/design/task_proxy_11_v1.md)，绑定[同版入口与契约](robots/Goose_V0.1/configs/task_proxy_11_v1_entry.json)。硬件 CAD、打印源、BOM、质量与完整惯量保持独立；MuJoCo 与原生 Rapier 各完成 2,500 次实际积分，通过冷启动、站立、有限关节动作、嘴部行程和负载／摩擦检查。18 项动作、65 项基础观测及 82 项指定物扩展可供 Sai_Lab 绑定新策略；这不代表已学会行走、转向、拾取／拖拽或适应复杂地面。Godot/Jolt、Unity 仍需各自验证。

当前[478件结构检查点](robots/Goose_V0.1/design/manual_wing_service_checkpoint.md)有独立CAD/SI与采购增量；003运行模型继续绑定原来的10.430690821kg参数，不混用新版硬件质量。[精确驱动资料及18轴端点](robots/Goose_V0.1/hardware/power_release_checkpoint.md)已补齐电压、插头及型号协议范围；新增[绝对阈值制动电路候选](robots/Goose_V0.1/hardware/absolute_brake_chopper_checkpoint.md)通过原生连通、条件角点和实际NGSPICE行为/故障对照，仍未取得PCB、热与完整安装资格。完整安装与线束、翼门连续开合和接缝、供电保护和独立急停、真实电机额定及热／载荷检查仍未闭合，**不能直接按候选 BOM 下单装机；第三、第四阶段和硬件冻结尚未完成**。原交接图片、文档、采购表以及成功／失败记录均保留，历史模型的结果不替代当前版本验证。

从[Goose 资料入口](robots/Goose_V0.1/README.md)、[新版独立接收器与复测命令](integrations/bevy/goose_task_proxy/README.md)、[历史 460 件训练交接](robots/Goose_V0.1/design/training_checkpoint_handoff.md)、[单件头壳结构](robots/Goose_V0.1/design/one_piece_head_checkpoint.md)、[行为要求](robots/Goose_V0.1/design/behavior_requirements.md)继续；[原始资料图片库](robots/Goose_V0.1/design/concepts/index.html)与[导入记录](robots/Goose_V0.1/source/workspace_import.md)保留溯源。大型 Blender／OBJ 资产须按 [Git LFS 拉取说明](docs/guides/large_asset_checkout.md)获取完整内容。

## Project organization

Robot-specific design, models and evidence live under `robots/<robot_id>/`.
Shared policies and configurations live under `shared/`; common software lives
under `src/sai_agent/`, with categorized command entrypoints in `scripts/`.
Local generated runs belong in `artifacts/<robot_id>/<run_id>/` and are not committed.

Read the [engineering rules](sai_robots_engineering_rules.md) before adding or
moving files. The [migration record](docs/guides/directory_migration.md) maps old
paths to their new locations without rewriting historical experiment records.

Both variants retain the front SO101 arm, four wheel-legs, camera mounts and
rear touchscreen layout. Hardware has not been built or calibrated.

![Sai_Agent_002 actual model](robots/Sai_Agent_002/images/front.png)
![Sai_Agent_002 cargo surface](robots/Sai_Agent_002/images/cargo-top.png)

## Run in Godot

Python 3.12, Godot 4.7.2 and `uv`:

```sh
uv sync
uv run sai-agent godot --robot Sai_Agent_002
uv run sai-agent godot --robot Sai_Agent_001
```

W/S 前进后退，A/D 左右转向，按住 Shift 下蹲、松开恢复，R 重启。
Omitting `--robot` preserves the original 001 default.

```sh
uv run sai-agent godot --robot Sai_Agent_002 --task cargo
uv run sai-agent godot --robot Sai_Agent_002 --stairs .04
```

002 uses contact-only pickup → placement → passive transport. It has no
clamping stage or cargo attachment constraint. Objects can slide or fall;
this variant does not promise automatic load restraint. Camera images are
available but the current tasks use model-state IK and terrain raycasts,
not VLA. The touchscreen remains a hardware layout, not implemented firmware.

## Models, training and integrations

[`robots/catalog.json`](robots/catalog.json) maps stable robot IDs to separate
model directories. Shared controllers/policies are retained; new robots can add
catalog entries and their own model directory. The `sai-agent-001` Python
package name and `sai_agent` import remain for existing integration compatibility.
The repository name is `Sai_Rotbots` as requested, including that spelling.

```sh
uv sync --extra test --extra cad --extra assets --extra hardware
uv run pytest -q
uv run python scripts/evaluation/evaluate_flat.py --robot Sai_Agent_002 --policy shared/policies/flat-v1.onnx --full-robot --out artifacts/002-flat --require-pass
uv run --extra train python scripts/training/train.py --robot Sai_Agent_002 --worlds 256 --seconds 300 --name my-002-trial
```

The variant reuses existing trained actors and is checked on its changed
mass/contact model. It is not presented as a newly trained policy. GPU training
accepts `--robot`; each run records the selected model hash and robot ID.

See [002 scope and evidence](robots/Sai_Agent_002/README.md),
[game integration notes](docs/guides/integrations.md),
[001 historical acceptance](robots/Sai_Agent_001/design/simulation_guide.md),
[variant plan](robots/Sai_Agent_002/design/agent_002_plan.md), and [third-party notices](THIRD_PARTY_NOTICES.md).
Old alpha.3 results describe 001, not 002. Unity editor validation remains pending.

SO101 and Raspberry Pi derivatives retain their upstream licenses. Supplier
CAD with unconfirmed redistribution rights is represented by independent
nominal display envelopes. Physics parameters are documented estimates, not
measured hardware values. Inspired by [MicroDuck](https://github.com/pollen-robotics/microduck)'s
functional design philosophy; the wheel-leg cargo chassis is an independent design.
