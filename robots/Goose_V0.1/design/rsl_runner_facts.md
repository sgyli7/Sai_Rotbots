# Goose / RSL 5.0.1 runner 接口事实

核查日期：2026-09-28。**以下是当时只读调查快照**：当时只运行纯张量 runner 初始化与确定性网络前向，没有 MuJoCo step、PPO learn/update、模型导出或文件保存。后续 RC2 已有 RSL 训练与 ONNX 导出，并把动作中心从未通过站立测试的 `home` 改为具名 `standing`，再将训练力矩前馈改为与运行接收器相同的中立刚体计算。现行控制契约为 `goose_rc2_v5`：v4 在真实 5 ms 力矩周期下失稳后调整了腿部阻尼；见[现行控制](../../../src/sai_agent/goose/control.py)、[训练入口](../../../scripts/training/train_goose_rsl.py)和[步态审查](locomotion_review.md)。下文代码只是历史接入骨架，不是当前训练或物理通过记录。

## 1. 核查环境与 Goose 当前边界

使用 Python：`/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/.venv/bin/python`。

已安装：RSL **5.0.1**、Torch **2.9.1+cu129**、TensorDict **0.14.2**、ONNX **1.22.0**、ORT **1.24.4**、onnxscript **0.7.2**、onnx-ir **1.0.0**、GitPython **3.1.62**。**没有 tensorboard 或 wandb**；此次没有安装包。版本来自 `importlib.metadata`。

已安装 RSL 根：`/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/.venv/lib/python3.12/site-packages/rsl_rl/`。核心 runner/PPO/MLP 等九个审查文件与 legacy-godot 环境的同版本包逐文件一致。本轮导入中没有加载 `mjlab_microduck`，也未使用它的全局 NaN 或 exporter 补丁。

- [Goose control.py](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/src/sai_agent/goose/control.py:8) 为 `goose_rc2_v1`、53 观测 / 10 动作 / 0.02 s；[robot_spec.json](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/robots/Goose_V0.1/configs/robot_spec.json) 现有 16 个 encoder joints：10 locomotion、5 neck、1 beak。16 encoder 不等于 16 policy actions。
- [LocomotionEnv](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/src/sai_agent/goose/locomotion.py:35) 的 `observations()` 返回 NumPy `[N,53]`；`step()` 返回 `(numpy_obs, numpy_rewards, numpy_dones, info_list)`，done 后已 reset；`age` 是 episode 长度，超时为 600 步。
- 现有环境还不是 RSL VecEnv：缺少 `get_observations()`、Torch/ TensorDict 包装、`num_actions/device/cfg/max_episode_length/episode_length_buf` 属性和 dict extras；薄 adapter 足以表达这些边界，无需添加 root velocity 或改关节/观测顺序。
- 环境首行 docstring 残留 `55/10`，实际常量和 metadata 为 **53/10**；此文只记录，未改源码。
- 自研 [train_goose.py](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/scripts/training/train_goose.py:23) 是独立 ActorCritic/PPO。它的 checkpoint 格式/网络参数名不是 RSL checkpoint；不能直接用 `runner.load()` 当作兼容迁移。

## 2. 真正需要的配置 dict

RSL 5.0.1 使用独立 `actor`、`critic`、`algorithm` 字典；不是旧版 `policy/actor_hidden_dims/critic_hidden_dims` 配置。runner 的 [初始化第 26–52 行](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/.venv/lib/python3.12/site-packages/rsl_rl/runners/on_policy_runner.py:26) 调 `get_observations()`，PPO [第 473–504 行](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/.venv/lib/python3.12/site-packages/rsl_rl/algorithms/ppo.py:473) 由 TensorDict 推断输入长度、从 `env.num_actions` 推断输出长度。

下面的 dict 已通过本机 **构造与前向** 检查。它使用 RSL 自身默认超参，只说明最小接入字段；不是 Goose 超参/网络架构推荐，也不复用 MicroDuck14 或轮腿16配置。

```python
MIN_CFG = {
    "num_steps_per_env": 32,
    "save_interval": 10,
    "obs_groups": {"actor": ["policy"], "critic": ["policy"]},
    "actor": {
        "class_name": "rsl_rl.models:MLPModel",
        "distribution_cfg": {
            "class_name": "rsl_rl.modules.distribution:GaussianDistribution",
        },
    },
    "critic": {"class_name": "rsl_rl.models:MLPModel"},
    "algorithm": {"class_name": "rsl_rl.algorithms:PPO"},
}
```

| 字段 | 实际要求 |
|---|---|
| `num_steps_per_env` | rollout storage 和 learn 循环使用；上例 32 是骨架用值 |
| `obs_groups` | 明确 actor/critic 各读哪些 TensorDict keys；每个 list 非空且 key 存在 |
| `actor.class_name` / `critic.class_name` / `algorithm.class_name` | callable 或合法名称；上例明确定位 RSL 类，避免模糊发现 |
| `actor.distribution_cfg` | PPO 要采样、log probability、std/entropy；仅确定性 actor 不满足这条 PPO 路径 |
| `save_interval` | writer 非 None 时 learn 的自动保存使用；writer=None 时该分支不执行 |
| `multi_gpu` | 单进程 OnPolicyRunner 会注入 None，所以构造 runner 时可不传；直接调用 `PPO.construct_algorithm()` 则须显式提供 |
| `rnd_cfg` / `symmetry_cfg` | 此骨架未启用；resolver 自动补 None，logger/learn 随后会读 `rnd_cfg` |

可选模型字段为 `hidden_dims`、`activation`、`obs_normalization`；Gaussian 的 `init_std`、`std_type`。最小 dict 默认是 `[256,256,256]` / ELU / 不归一化 / Gaussian std=1、scalar 参数化；与当前自研 Goose PPO 的 `[128,128]` / Tanh / log-std 不同。真实实验应显式记录选择，不能把最低字段数误当行为等价。依据：[MLPModel 第 30–76 行](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/.venv/lib/python3.12/site-packages/rsl_rl/models/mlp_model.py:30)、[Gaussian 第 139–159 行](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/.venv/lib/python3.12/site-packages/rsl_rl/modules/distribution.py:139)。

PPO 其他键有构造默认值；例如 epochs=5、mini-batches=4、lr=0.001、schedule=adaptive、desired_kl=0.01，见 [PPO.__init__ 第 35–60 行](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/.venv/lib/python3.12/site-packages/rsl_rl/algorithms/ppo.py:35)。`max_iterations`、`seed`、`experiment_name`、`run_name`、`runner_class_name` 不是此直接 OnPolicyRunner 构造路径的必需 cfg 键；迭代数由 `learn(num_learning_iterations=...)` 参数传，device 由构造参数传，seed 在调用侧设置。

**必须 `copy.deepcopy(cfg)`**：PPO 构造会 pop 三个 `class_name`，MLP 构造也 pop distribution `class_name`，并注入/修正 obs groups、RND、symmetry、multi-GPU。不要让多个 runner 共享同一份可变配置，也不要只保存被改写后的 `runner.cfg` 作为完整可重建配置。

## 3. TensorDict 与 VecEnv 的最小边界

本例两种网络都读同一个现有 53 维观测，不额外引入 critic 特权观测：

```python
TensorDict({"policy": obs_tensor}, batch_size=[num_envs])
# obs_tensor.shape == [num_envs, 53], float32
# obs_groups == {"actor": ["policy"], "critic": ["policy"]}
```

若 TensorDict keys 使用 `actor` / `critic`，则 config 要对应为 `{"actor":["actor"],"critic":["critic"]}`。名字是 group 选择，不能靠改名字改变输入语义。MLP 按列表顺序拼接 group，要求每项 rank=2；不需要手写 `num_actor_obs/num_critic_obs`。依据：[resolve_obs_groups 第 225–272 行](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/.venv/lib/python3.12/site-packages/rsl_rl/utils/utils.py:225)、[MLP 第 110–119、180–190 行](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/.venv/lib/python3.12/site-packages/rsl_rl/models/mlp_model.py:110)。

[VecEnv 定义第 21–91 行](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/.venv/lib/python3.12/site-packages/rsl_rl/env/vec_env.py:21) 声明：`num_envs`、`num_actions`、`max_episode_length`、`episode_length_buf`、`device`、`cfg`；方法 `get_observations()` 和 `step(actions)`。step 返回四元组：TensorDict、float rewards `[N]`、done flags `[N]`、dict extras。`log` 指标用 `/` 命名空间；`time_outs` 区分时限截断与失败。

RSL [PPO 第 174–179 行](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/.venv/lib/python3.12/site-packages/rsl_rl/algorithms/ppo.py:174) 会对 `time_outs` 对应项加 `gamma * transition.values`。适配器不要再次手动给 reward 加 bootstrap。当前 Goose 的 info 可能同时标记 failure 和 timeout；下方骨架只把没有 failure 的 timeout 传入 `time_outs`。这是按现有失败原因做 RSL 截断分类；它没有改变观察/动作，但与现有自研 PPO 把所有 done 都截断的 return 处理并不完全相同。

runner 自带 `check_for_nan` 默认 True，但 [check_nan 第 275 行起](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/.venv/lib/python3.12/site-packages/rsl_rl/utils/utils.py:275) 用的是 `torch.isnan`，不等于全面的 isfinite 检查。骨架保留显式有限性拒绝，不把 Inf/NaN 归零。

## 4. 可执行的 Goose adapter / runner 调用骨架

将上节 `MIN_CFG` 与本节代码放在同一 Python 文件可执行。执行需本仓库 `src` 可导入；默认只构造 runner/检查输入，训练函数由调用侧显式调用。此段没有在核查中执行真实 Goose 环境；构造已用同维度的纯张量 stub 核验。

```python
import copy
from pathlib import Path

import numpy as np
import torch
from tensordict import TensorDict
from rsl_rl.env import VecEnv
from rsl_rl.runners import OnPolicyRunner

from sai_agent.goose.control import ACTION_SIZE, OBS_SIZE, metadata
from sai_agent.goose.locomotion import LocomotionEnv


class GooseRslVecEnv(VecEnv):
    def __init__(self, base):
        self.base = base
        self.num_envs = base.num_envs
        self.num_actions = ACTION_SIZE  # current Goose: 10
        self.device = "cpu"  # base MuJoCo/NumPy physics stays CPU
        self.max_episode_length = 600  # current base.step timeout
        self.episode_length_buf = torch.as_tensor(base.age.copy(), dtype=torch.long)
        self.cfg = {
            **metadata(base.mapping.spec),
            "model_sha256": base.source_model_sha256,
            "episode_length_steps": self.max_episode_length,
        }

    def _pack(self, array):
        tensor = torch.as_tensor(array, dtype=torch.float32)
        if tensor.shape != (self.num_envs, OBS_SIZE):
            raise ValueError("Goose observation shape mismatch")
        if not torch.isfinite(tensor).all():
            raise FloatingPointError("Non-finite Goose observations")
        return TensorDict({"policy": tensor}, batch_size=[self.num_envs])

    def get_observations(self):
        return self._pack(self.base.observations())

    def step(self, actions):
        actions = actions.detach().to("cpu")
        if actions.shape != (self.num_envs, ACTION_SIZE):
            raise ValueError("Goose action shape mismatch")
        if not torch.isfinite(actions).all():
            raise FloatingPointError("Non-finite Goose actions")
        obs, rewards, dones, rows = self.base.step(actions.numpy())
        rewards = torch.as_tensor(rewards, dtype=torch.float32)
        dones = torch.as_tensor(dones, dtype=torch.bool)
        if not torch.isfinite(rewards).all():
            raise FloatingPointError("Non-finite Goose reward")
        # base has already reset completed environments; synchronize its ages.
        self.episode_length_buf.copy_(torch.as_tensor(self.base.age, dtype=torch.long))
        extras = {
            "time_outs": torch.tensor(
                [row["timeout"] and not row["failure"] for row in rows],
                dtype=torch.bool,
            ),
            "log": {"/goose/failure_rate": float(np.mean([r["failure"] for r in rows]))},
        }
        return self._pack(obs), rewards, dones, extras


def build_runner(num_envs=8, seed=20260928, policy_device="cpu"):
    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.set_num_threads(2)
    base = LocomotionEnv(num_envs=num_envs, seed=seed)
    env = GooseRslVecEnv(base)
    runner = OnPolicyRunner(env, copy.deepcopy(MIN_CFG), log_dir=None, device=policy_device)
    # Makes writer=None available for later manual save; no writer or files.
    runner.logger.init_logging_writer()
    return env, runner


def train_and_save(env, runner, output, num_iterations):
    # Calling this function starts training; not called by this fact check.
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    runner.learn(num_learning_iterations=num_iterations, init_at_random_ep_len=False)
    runner.save(str(output / "model.pt"), infos={
        "environment": env.cfg,
        "train_cfg": copy.deepcopy(MIN_CFG),
        "status": "training_complete_unvalidated",
    })
    runner.export_policy_to_onnx(str(output), filename="policy.onnx")


if __name__ == "__main__":
    env, runner = build_runner()
    print(env.get_observations().get("policy").shape, env.num_actions)
    # For an independently configured bounded experiment, call train_and_save
    # with a new artifacts/Goose_V0.1/<run_id> directory and chosen iterations.
```

注意：这里不启用 `init_at_random_ep_len`。runner 在启用时直接替换 `env.episode_length_buf`，不会自动改变 NumPy base 的 `age`；要启用它必须另做同步，否则两个 episode 时钟会分叉，见 [runner 第 59–62 行](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/.venv/lib/python3.12/site-packages/rsl_rl/runners/on_policy_runner.py:59)。`policy_device="cuda:0"` 只改变网络/rollout tensor 设备，不能把此 CPU MuJoCo 循环变成 GPU 物理。

## 5. learn / save / load / export 的具体限制

| 操作 | 真实要求与行为 |
|---|---|
| `learn(num_learning_iterations, init_at_random_ep_len=False)` | 每轮采 `num_steps_per_env`，step 返回值迁到 runner device；没有 wall-seconds 参数，时间上限由调用侧管理。`learn` 会初始化 logger |
| 日志 | 非 None `log_dir` 默认选择 TensorBoard，首次 learn 时导入 `torch.utils.tensorboard`；当前包缺 TensorBoard。仅支持 tensorboard/wandb/neptune，没有 `logger="none"` 选项 |
| `log_dir=None` | writer=None，既不写训练指标，也不执行自动周期/最终 checkpoint 保存；需显式 save 和另记运行指标。不要把无日志当作已保存 |
| 首次手动 save | `Logger.__init__` 尚未建立 writer 属性；构造后、learn 前保存，要先 `runner.logger.init_logging_writer()`。log_dir=None 时这个调用不创建文件 |
| `save(path, infos=None)` | path 父目录应已存在。保存 actor/critic/optimizer states，加 `iter`、`infos`；normalizer 若启用则在模型 state_dict 内。不自动保存 pristine train_cfg、Goose 契约/模型哈希、seed、RNG 或 env state |
| `load(path, load_cfg=None, strict=True, map_location=None)` | 用 RSL checkpoint keys；默认恢复 actor/critic/optimizer/iteration 等，返回 infos。不能直接读取当前自研 Goose 的单个 `state_dict` 格式 |
| `get_inference_policy(device=...)` | 返回确定性 actor，输入仍是 TensorDict；会把 **live actor** 移到指定设备，不是 deepcopy。不要移动到 CPU 后继续假定原 GPU runner 未变 |
| `export_policy_to_onnx(path, filename="policy.onnx", verbose=False)` | path 是目录，opset=18；MLP wrapper 深拷贝 normalizer/MLP 并导出确定性输出。默认 names=`obs` / `actions`，dummy `[1,53]`，未设置动态 batch |

依据：[runner 第 56–201 行](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/.venv/lib/python3.12/site-packages/rsl_rl/runners/on_policy_runner.py:56)、[logger 第 63–86、266–307 行](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/.venv/lib/python3.12/site-packages/rsl_rl/utils/logger.py:63)、[PPO checkpoint 第 432–466 行](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/.venv/lib/python3.12/site-packages/rsl_rl/algorithms/ppo.py:432)、[MLP ONNX wrapper 第 227–257 行](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/.venv/lib/python3.12/site-packages/rsl_rl/models/mlp_model.py:227)。`iter` 是最近执行的零基迭代索引，不是物理步数；累计环境步数需另记。

本机 Torch 2.9 的 `torch.onnx.export` 默认 `dynamo=True`（[本机源码第 59–72 行](/home/ethan/Projects/TempWorktree/Sai_Rotbots/goose-v01-preserved/.venv/lib/python3.12/site-packages/torch/onnx/__init__.py:59)）；RSL export 没有显式覆盖它。当前 onnxscript/onnx-ir 已安装，但本轮没有实际导出验证。若实施时需要 legacy exporter、动态 batch 或与现有 Goose 的 `observation` / `action` names 对齐，可用 `actor.as_onnx(verbose=False)` wrapper 在调用侧显式传 `dynamo=False` / names / dynamic_axes，随后核 ONNX/ORT 一致性；无需 monkey-patch RSL 模块。

## 6. 本轮实际验证与未验证边界

纯张量 stub 为 `N=2`、policy zeros `[2,53]`、num_actions=10，step 方法一旦被调用就抛错。实际结果：

```text
OnPolicyRunner 初始化成功；actor input_dim=53，critic input_dim=53
确定性 actor 输出 [2,10]，全部 finite
writer=None；multi_gpu/rnd_cfg/symmetry_cfg 被补为 None
actor/critic/algorithm class_name 被 pop
alg.save() 的内存 dict keys：actor_state_dict、critic_state_dict、optimizer_state_dict
as_onnx wrapper：input_names=[obs]、output_names=[actions]、dummy=[1,53]
没有 mjlab_microduck 模块；learn/env.step/update/export/save 文件调用均未发生
```

未验证：真实 Goose adapter step、timeout/reset 生命周期、CPU/GPU训练步、优化器更新、checkpoint 文件恢复、RSL 实际 ONNX 导出/ORT parity、任何行走/稳定性或跨引擎行为。此文提供接口事实，不替代这些验证。
