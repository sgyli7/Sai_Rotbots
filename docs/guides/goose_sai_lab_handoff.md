> 新版 18 轴初训请使用 [第一阶段结构与物理参数交接](../../robots/Goose_V0.1/design/stage_one_parameter_handoff.md)。本页以下保留旧 RC2 的历史接入说明；旧 16 轴模型/策略不适用于新版。

# Goose_V0.1 → Sai_Lab 接入入口（RC2 工程候选）

本页说明怎样从 Sai_Rotbots 工作区接入 Goose 的模型和训练接口。**当前只有站立和若干预设接触单项通过，尚无可交付的行走/拖拽自主策略，不能将它设为 Sai_Lab 默认机器人。** 完整门槛见[机器人放行判定](../../robots/Goose_V0.1/design/release_readiness.md)。

当前可加载资产属于 **RC2 历史工程候选**。用户指定的尖嘴 v73 外形与它不是同一具机器人：[候选一致性检查](../../robots/Goose_V0.1/evidence/r2_slim_bill_v73_model_alignment.json)检出 R2 嘴的支点距 `14 vs 18 mm`、电机 `XL330 vs XC330`、传动 `2:1 vs 1:1`，且 v73 的外形清单没有与 RC2 的模型／制造清单建立同版来源。可运行不等于适合拿去训练当前外形；这项检查是必要门槛，通过后仍须另验夹取、拖拽、步行和跨引擎行为。

## 可直接读取的资产

- 机器人 ID `Goose_V0.1` 已登记在 [catalog](../../robots/catalog.json)，源码和安装包均可通过 `sai_agent.paths.model_root('Goose_V0.1')` 找到 `models/full/robot.xml`。现行模型 SHA-256 `07d4209a5a7b9322a04b9cdb62694a69cf35c97716c262909d21f039599c4cb0`。
- [rigid_transfer.json](../../robots/Goose_V0.1/models/full/rigid_transfer.json)是后端中立 SI 交换包，含质量/完整惯量、几何、关节与被动件、点闭环、相机/任务点及 `standing`、`ground_side_grasp` 两个具名姿态。Godot 的坐标转换和质量缩放只在 [Godot 接收器](../../integrations/godot/goose_robot/goose_adapter.gd)内部。UnitySim2Sim 与 BevySim2Sim 应各自按[一致性核查清单](../../robots/Goose_V0.1/design/backend_conformance_facts.md)实现，不复制 Jolt 私有参数。
- `goose_rc2_v5` 控制契约：53 维仅传感/指令观测、10 维腿部动作、16 维有序执行关节力矩；20 ms 策略周期、5 ms 扭矩周期。动作目标为 `standing` 腿角 `+ 0.30 rad × clip(action,-1,1)`；`q-home` 只用于观测字段。训练与接收器都使用中立刚体重力前馈，腿部阻尼按真实 5 ms 更新周期复测；策略元数据必须与模型、规格、名字顺序和契约版本匹配。[v4 失稳原因和 v5 站立结果](../../robots/Goose_V0.1/design/locomotion_review.md)单独记录。

## 工作区验证入口

在此仓库根运行：

```sh
uv run pytest -q tests/test_goose_interfaces.py tests/test_goose_imu_audio.py tests/test_goose_transfer_contract.py
uv run python scripts/diagnostics/check_goose_delivery.py
uv run python scripts/evaluation/evaluate_goose_stand.py --standing-pose --shared-controller --no-double-support --output artifacts/Goose_V0.1/stand_policy_mode.json
uv run python scripts/evaluation/evaluate_goose_bridge.py --output artifacts/Goose_V0.1/godot_policy_mode
```

Godot 回放的 `--output` 每次选一个新的目录名，防止覆盖上次证据。

在将某个新外形候选交给 Sai_Lab 前，运行 `uv run python scripts/diagnostics/check_goose_candidate_alignment.py --evidence artifacts/Goose_V0.1/candidate_alignment.json`。当前 v73 对 RC2 **预期返回非零**；不能通过跳过此检查或沿用 RC2 的通过记录来放行。

RSL 训练入口是 `scripts/training/train_goose_rsl.py`，输出检查点、ONNX、元数据与精确输入快照；策略回放入口是 `scripts/evaluation/evaluate_goose_walk.py`。这些入口适合实验，但训练能跑通、ONNX 数值一致或自由站立通过都不代表游戏任务成功。[v5 原策略](../../robots/Goose_V0.1/evidence/walk_policy_200iter_v5_rc2.json)和[低探索对照策略](../../robots/Goose_V0.1/evidence/walk_policy_calm_init_v5_200_rc2.json)四项回放均失败；失败策略只在 `experiments/Goose_V0.1/` 供诊断，禁止默认装载。正式策略需通过步行、带物、拖拽和跨引擎验收，并另做用户定义的实物门槛。

安装包已做[独立解包加载检查](../../robots/Goose_V0.1/evidence/wheel_load_rc2.json)：Goose 和原有 Sai_Agent_001/002 模型可加载，默认机器人仍为 001。安装包只含运行所需模型/配置，不含 CAD、采购表和历史验证；完整工程资料以[Goose 导航](../../robots/Goose_V0.1/README.md)为准。
