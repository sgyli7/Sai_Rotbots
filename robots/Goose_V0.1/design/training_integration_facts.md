# Goose 训练集成：本机事实与接入缺口

**历史调查快照。** 本文下述 17 轴候选、缺失训练依赖、尚无 Goose 模型/任务等结论仅描述调查时状态。现行 [RC2 规格](../configs/robot_spec.json)为 16 主动轴，[Goose 训练入口](../../../scripts/training/train_goose_rsl.py)已完成有限 RSL PPO/ONNX 冒烟验证，结果见[精选记录](../evidence/train_smoke_rc2.json)。已导出策略仍为实验样本，尚无步行、带物拖行或跨引擎策略验收；本文的接口风险和既有 Sai_Lab 事实仍可作后续复核线索。

核查时间：2026-09-28 02:47，Asia/Chongqing。核查方式：读取工程和已安装包源码、查询包版本、导入依赖、执行一个最小 CUDA 张量求和。未安装依赖、未启动训练、未运行历史实验、未修改 Sai_Lab。本文只记录接入事实；不决定结构、观测/动作契约、控制参数或训练效果。

本轮输入为 **17 个主动关节候选：10 腿 + 6 颈 + 1 嘴**。这不是已验证的 MJCF `nu`、`nq`、`nv` 或策略输出维度。自由基座、嘴部被动连杆、对象状态可以增加状态维度；动作空间还取决于后续明确的控制分工。

## 1. 工作副本与环境

| 简称 | 实际路径 | 核查时 HEAD |
|---|---|---|
| Goose 工作树 | `/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved` | `4af28a4f94fae968d5f9ba21cc78f175ecad3bdc` |
| Sai_Lab Godot 工程 | `/home/ethan/Projects/Sai_Lab/Godot_Sim2Sim` | `eae2f98fb95e6cc58b7be98ae21c157693ec7e0c` |
| 本机 MicroDuck 上游副本 | `/home/ethan/Projects/Sai_Lab/upstream/pollen-robotics-microduck_rl` | `5946fd9cdbc58956424420153e51975af3b30d77` |

存在未提交内容，HEAD 不代表完整工作区快照。执行前仍应记录实际源文件和模型哈希。以下环境均使用 Python **3.12.14**。

| Python 可执行文件 | MuJoCo / NumPy / SciPy | 训练与导出依赖 |
|---|---|---|
| Goose 工作树 `.venv/bin/python` | 3.10.0 / 2.5.3 / 1.18.1 | ORT 1.24.4；**未安装** Torch、ONNX、MuJoCo-Warp、Warp、mjlab、RSL、TensorDict |
| `/home/ethan/Projects/TempWorktree/Sai_Lab/local-main-wip/Godot_Sim2Sim/.venv-sai/bin/python` | 3.10.0 / 2.5.2 / 1.18.1 | ORT 1.24.4；同样缺少上述训练包 |
| `/home/ethan/Projects/TempWorktree/Sai_Lab/legacy-godot/.venv/bin/python` | 3.10.0 / 2.5.2 / 1.18.1 | Torch 2.9.1+cu129、ONNX 1.22.0、ORT 1.24.4、RSL 5.0.1、TensorDict 0.14.1；无 mjlab / MuJoCo-Warp / Warp |
| MicroDuck 上游副本 `.venv/bin/python` | 3.10.0 / 2.4.1 / 1.18.0 | Torch 2.9.1+cu129、ONNX 1.22.0、ORT 1.24.4、RSL 5.0.1、TensorDict 0.10.0、mjlab 1.3.0、MuJoCo-Warp 3.8.1、Warp 1.12.0 |

版本通过各 Python 的 `importlib.metadata.version()` 读取，不以锁文件代替已安装事实。MicroDuck 环境的 `mujoco`、`warp`、`mujoco_warp`、`mjlab`、`rsl_rl`、`onnx`、`onnxruntime` 导入全部成功，进程退出码 0；尚未创建 Warp 模型或执行物理内核。

本仓库 [pyproject.toml](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/pyproject.toml:5) 要求 Python `>=3.12,<3.13`；第 13 行的 `train` extra 已声明 Torch 2.9.1、MuJoCo-Warp 3.8.1、Warp 1.12.0、RSL 5.0.1、ONNX 1.22.0。第 34–40 行为 Linux aarch64 指定 `pytorch-cu129` 源。当前 Goose 环境只是基础运行环境，不能直接执行现有 GPU 训练脚本。没有在此次核查中补装依赖。

### GPU 与推理的实际验证边界

- `nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader` 返回 `NVIDIA GB10, [N/A], 580.173.02`。`[N/A]` 不能解释为没有显存或容量为零。
- `nvcc --version` 返回 CUDA toolkit **13.0 / V13.0.88**，可执行文件 `/usr/local/cuda/bin/nvcc`。Torch 自身报告 CUDA **12.9**，两者是不同来源的版本。
- legacy-godot 和 MicroDuck 环境均报告 `torch.cuda.is_available() == True`、1 张 GB10、capability `(12, 1)`；`torch.tensor([1,2,3], device='cuda').sum()` 与同步成功，结果 `6.0`。
- 两者均有 Torch 警告：设备 capability 12.1 超出其列出的 12.0 上限。小张量成功是有限证据，**不构成 PPO、Warp 接触/闭环内核或整轮训练的通过记录**。
- 两者 ORT provider 列表均为 `AzureExecutionProvider`、`CPUExecutionProvider`，没有 `CUDAExecutionProvider`。ORT 导入伴随 DRM 设备探测警告，但 CPU provider 可用。现有导出一致性检查也明确使用 CPU provider。

## 2. 现成入口分别能做什么

| 入口和源码依据 | 当前用途 | 对 Goose 可复用部分 | 必须替换或新增的部分 |
|---|---|---|---|
| 本仓库 [scripts/training/train.py](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/scripts/training/train.py:19) | MuJoCo-Warp GPU PPO，支持 001/002 的 flat/stairs | 有时限的训练循环、种子、检查点、源文件快照、非有限状态捕获、训练后保持 unvalidated 状态 | CLI 第 42 行只接收 001/002；第 65/72 行固定加载轮腿 `locomotion.xml` 和专用 env；第 109 行固定写 `82/16/50Hz` 元数据；小残差初始化依赖既有解析控制器 |
| Sai_Lab [src/sim2sim/train/runner.py](/home/ethan/Projects/Sai_Lab/Godot_Sim2Sim/src/sim2sim/train/runner.py:338) | **GodotVecEnv + OnPolicyRunner** 的 Jolt 训练入口，第 357 行明确 | 训练生命周期、恢复/导出/一致性检查的组织方式 | 它不是可直接替代的 MuJoCo GPU runner；Godot env、控制器、观测和导出仍专用 MicroDuck |
| MicroDuck [pyproject.toml](/home/ethan/Projects/Sai_Lab/upstream/pollen-robotics-microduck_rl/pyproject.toml:53) 的 `train` | wrapper 转到 `mjlab.scripts.train`；[README](/home/ethan/Projects/Sai_Lab/upstream/pollen-robotics-microduck_rl/README.md:35) 的现成任务是 `Mjlab-Velocity-Flat-MicroDuck` | 已安装的 mjlab / MuJoCo-Warp / RSL 栈；manager 框架、任务注册方式、带 normalizer 的 ONNX 导出方式 | 必须有 Goose entity、task、动作映射、传感器、reset/终止/奖励及运行配置；现有 MicroDuck 实体和任务不是 Goose 训练任务 |
| Sai_Lab [MujocoBackend](/home/ethan/Projects/Sai_Lab/Godot_Sim2Sim/src/sim2sim/backends/mujoco_backend.py:19) | 单实例 CPU MuJoCo 读模、步进、状态采集 | 第 56–61 行按实际 `model.nu` / actuator joint 地址取 q/qd，适合作为模型适配思路 | 默认 base `trunk_base`、IMU `imu_ang_vel`；第 42 行覆盖 timestep；第 44–48 行可用 XL330 常数统一覆写所有执行器力限。需显式 Goose 参数，且不能据此得到 vector PPO env |

本机已安装的 mjlab 本体可以从 action manager 取总维度；[RslRlVecEnvWrapper](/home/ethan/Projects/Sai_Lab/upstream/pollen-robotics-microduck_rl/.venv/lib/python3.12/site-packages/mjlab/rl/vecenv_wrapper.py:21) 使用 `action_manager.total_action_dim`。上游 [task 注册](/home/ethan/Projects/Sai_Lab/upstream/pollen-robotics-microduck_rl/src/mjlab_microduck/tasks/__init__.py:81) 和 [entity 配置](/home/ethan/Projects/Sai_Lab/upstream/pollen-robotics-microduck_rl/src/mjlab_microduck/tasks/microduck_velocity_env_cfg.py:266) 是机器人专用层；通用框架可读作参考，原任务不能只改名字使用。

### 上游现成环境的额外耦合

本次 `import mjlab` 实际加载了 MicroDuck 插件，并打印 NaN 补丁与 passive joint 导出补丁。源码 [tasks/mdp.py](/home/ethan/Projects/Sai_Lab/upstream/pollen-robotics-microduck_rl/src/mjlab_microduck/tasks/mdp.py:30) 第 40 行全局替换 `RewardManager.compute`，第 58 行替换 `PPO.compute_returns`，把部分非有限结果归零；第 79–109 行全局替换 ONNX base metadata 生成器，要求 `joint_pos` action，并按 `passive_` 名称前缀过滤关节。

因此这个 venv 的包版本齐全，也带机器人插件副作用。使用它运行 Goose 不能自动视为干净的通用训练环境；尤其不能让非有限状态被归零后当作模型稳定的证据。Goose 的 active/passive/actuator 顺序应以显式映射为依据，不依赖名称前缀碰巧匹配。此核查没有卸载插件或更改补丁。

## 3. 固定维度与关节布局在哪一层

| 模块 | 已查明的硬编码 | 接入影响 |
|---|---|---|
| 本仓库 [control.py](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/src/sai_agent/control.py:12) | 82 观测 / 16 动作；每四个关节的第四个是轮；静止命令时输出全零残差 | 改一个维度常量不足以接入双足、六颈、嘴 |
| 本仓库 [runtime.py](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/src/sai_agent/runtime.py:6) | 四腿 haa/hip/knee/wheel 名称和 SO101 手臂名称 | Goose 需要独立命名映射和控制适配，原 runtime 会查找不存在的关节 |
| 本仓库 [env.py](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/src/sai_agent/env.py:26) | 16 动作/previous；第 85–106 行构造轮腿观测与目标；reward/终止也是轮腿特定 | 需要 Goose task env；不能用填零、截断或第 17 维追加的方式继承语义 |
| 本仓库 [gpu_backend.py](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/src/sai_agent/gpu_backend.py:12) | kernel `joint % 4 == 3` 是轮；`qpos[joint+7]` / `qvel[joint+6]` 假定连续主动轴；第 39/62/100 行固定 16；力限/gain 固定两类 | 需按 actuator→joint→qpos/dof 地址映射，支持被动轴和对象自由关节，读取逐执行器控制类型/参数；接触容量 `96/384` 也不能无依据作为 Goose 验收值 |
| 本仓库 [export_policy.py](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/scripts/training/export_policy.py:20) | dummy `(1,82)`、actor 输出 16、随机一致性输入 82 | 输入/输出长度必须来自实际契约/检查点；第 34 行的 batch 17 只是批大小，不是 17 个动作 |
| Sai_Lab [train/vec_env.py](/home/ethan/Projects/Sai_Lab/Godot_Sim2Sim/src/sim2sim/train/vec_env.py:29) | actor 61 / critic 70 / action 14；home 必须长 14，step/state slices 固定 14 | 原 Godot 训练 env 不能直接加载 Goose 17 候选 |
| Sai_Lab [train/manifest.py](/home/ethan/Projects/Sai_Lab/Godot_Sim2Sim/src/sim2sim/train/manifest.py:90) 与 [export.py](/home/ethan/Projects/Sai_Lab/Godot_Sim2Sim/src/sim2sim/train/export.py:168) | manifest 写 61/14、MicroDuck/XL330；导出 `check_dims(14)` | 不能沿用旧 manifest 内容或旧验收维度 |
| Sai_Lab [pickup_env.py](/home/ethan/Projects/Sai_Lab/Godot_Sim2Sim/src/sim2sim/pickup_env.py:24) | 76 观测 / 15 动作；模型仅接受 15 或 16 执行器 | pickup pilot 不是 Goose 通用接收器；其真值输入和抓取 assist 也不能标作视觉自主拾取 |
| 已安装 [RSL PPO.construct_algorithm](/home/ethan/Projects/TempWorktree/Sai_Lab/legacy-godot/.venv/lib/python3.12/site-packages/rsl_rl/algorithms/ppo.py:473) | **没有 14/16 的固定动作长度**；第 493/501 行使用 `env.num_actions` | PPO 算法层可复用；必须先给它语义正确的 env 和 observation groups |

已有 14/16 轴策略、normalizer、home、gain、奖励及日志不能通过张量扩展直接变成 Goose 策略。闭环嘴的被动关节不应按主动轴排列。四连杆还需在物理和转换接收层独立验证；“成功导出 ONNX”不验证闭环机械模型。

## 4. 最小训练接入接口与元数据

以下是接入所需字段类别，不是已经选定的 observation/action contract。

### 模型与控制适配器

1. 稳定 `robot_id`、完整 MJCF 及 include/mesh/textures 相对资源、模型/资源哈希、编译得到的 `nq/nv/nu/njnt/neq`。显式区分 free base、主动、被动关节与任务对象。
2. 有序 active joint / actuator 名称、actuator transmission 类型、关节 ID、`jnt_qposadr`、`jnt_dofadr`、动作→执行器映射。主动轴候选列表和实际策略动作列表需分别记录；只在全部 17 轴确实逐轴受策略控制时，`num_actions` 才能设为 17。
3. 基座 body、IMU/sensor、双脚接触 site/geom、嘴端/夹持 site 名称；角度、角速度、长度、力、力矩的单位；世界/局部坐标、四元数顺序、轴方向和零位。
4. physics timestep、整数 decimation 和 control timestep；动作控制模式、scale/offset/home、gain/damping、控制/力限和动作裁剪顺序，逐执行器记录。源码里的 0.02 s 与轮腿 gain 不是 Goose 默认验收依据。
5. 被动闭环/equality 的对象和初始闭合状态；对象质量/摩擦/接触参数、辅助约束开关和任务 reset 条件。训练记录必须标明是否使用真值、weld/adhesion/抓取 assist。

### RSL 环境边界

已安装 [VecEnv 定义](/home/ethan/Projects/TempWorktree/Sai_Lab/legacy-godot/.venv/lib/python3.12/site-packages/rsl_rl/env/vec_env.py:21) 要求/声明 `num_envs`、`num_actions`、`max_episode_length`、`episode_length_buf`、`device`、`cfg`，以及：

```python
get_observations() -> TensorDict
step(actions) -> (observations, rewards, dones, extras)
# actions: [num_envs, num_actions]
# rewards / dones: [num_envs]
# observation groups 的名称与结构由任务契约确定
# extras 包括 time_outs；log 提供标量/张量指标
```

`obs_groups` 明确指定 actor/critic 使用哪些 TensorDict groups。必须记录每组长度、各项名称/顺序/slice、dtype、单位/scale、历史长度、噪声/延迟、normalization 和输入来源；actor 的部署可用输入与 critic/teacher 的特权信息应可识别。这里不指定 Goose 观测长度。

已有本仓库 [env.step 返回值](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/src/sai_agent/env.py:131) 符合上述四元组。可复用该边界和 timeout 区分；轮腿任务内容需另建。PPO 读取真实 observations 和 `num_actions` 创建网络/存储，而不是由 17 主动轴自动推导观测。

### 训练与交付记录

- 模型、控制契约、观测/动作契约和任务配置版本/哈希；源文件/提交与脏工作区状态；Python/包/GPU/驱动版本；seed、并行环境数、时限/步数、训练统计与失败记录。
- reward/reset/终止/timeout/randomization/curriculum 的完整配置；checkpoint 的 actor/critic/normalizer/optimizer/RNG；resume 所用模型与契约兼容性。
- ONNX 输入/输出名称、长度/dtype、normalization 是否包含、opset、checkpoint/ONNX 哈希、PyTorch↔ORT 一致性结果、训练和独立验收状态。
- MuJoCo 与 Godot/Jolt 使用同一套明确的关节和动作语义。资源路径、轴变换、步长和闭环支持应单独验收；策略尺寸一致不等于物理一致。

本仓库 [export_policy.py](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/scripts/training/export_policy.py:24) 的 `actor.as_onnx()` 包含 observation normalization，第 29–41 行执行 ONNX checker 和 CPU ORT 一致性检查。这套流程可保留，固定 82/16 改为读真实元数据。该检查只验证同输入下网络输出一致性。

## 5. 必需新增与可保留模块

| 必需工作 | 可保留依据 | 新建/适配范围 |
|---|---|---|
| Goose 资源登记与可加载模型 | [paths.py](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/src/sai_agent/paths.py:19) 的 catalog/resource 定位 | 当前 [catalog](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/robots/catalog.json:4) 只有 001/002；模型/config/policy/manifest 应归 Goose，wheel force-include 须显式补充。核查时 `Goose_V0.1/models`、`configs` 尚不存在 |
| 名称和地址驱动的物理适配器 | MuJoCo CPU backend 的实际 `nu` 和地址取法；Warp 的批量/stream 组织方式 | Goose 映射、逐执行器参数、passive/对象/闭环处理；不能继承 `joint+7` 与每四轴一轮的 kernel |
| Goose task env | RSL VecEnv/TensorDict 通用边界 | Goose command/observation/action adapter、reset、reward、终止、对象和技能阶段；不得覆写旧 001/002 或 MicroDuck task 语义 |
| Goose 训练入口与配置 | 现有 bounded runner 的循环、保存、有限性检查和来源记录；RSL PPO 本体 | 接受 Goose 模型/任务/契约；真实维度元数据；缺失训练依赖补齐与 GPU 物理小步验证应另记证据 |
| Goose 导出/部署适配 | normalizer 随 actor 导出、checker、ORT parity | 动态读取维度和映射、Goose metadata；Godot/controller/state adapter 和资源部署需对应同一契约 |
| 可复现实验与验收 | `artifacts/<robot_id>/<run_id>` 与精选 `experiments`/`evidence` 的工程规则 | 先分开记录依赖导入、模型编译、有限单步、reset、短训练、导出一致性、跨引擎验收的结果；未完成项明确未验证 |

此文档提供实现前沿事实。当前没有现成的 Goose 17 轴训练任务、对应策略或已通过的 MuJoCo↔Godot 训练交付。依赖存在、CUDA 小张量成功、旧任务能训练，均不能代替新 Goose 模型/行为的验证。
