# RC2 真实 5 ms 站姿控制下的 v5 步态试验（失败样本）

本目录保留 `goose_rc2_v5` 的 200 轮 RSL PPO 候选：8 个环境、每轮 32 步，共 51,200 环境步。训练与运行共用中立重力前馈、20 ms 策略及 5 ms 力矩周期，腿部阻尼为 0.10；ONNX 导出与训练网络数值一致。`checkpoint.pt`、`policy.onnx`、`metadata.json`、`runner_config.json` 属同一次试验。

[无策略的自由站立](../../../robots/Goose_V0.1/evidence/stand_neutral_policy_mode_v5_8s_rc2.json)可持续 8 秒，但[原策略独立回放](../../../robots/Goose_V0.1/evidence/walk_policy_200iter_v5_rc2.json)的静止、前进、后退、左转都在 0.98–1.34 秒跌倒；[Jolt 同一候选的静止策略回放](../../../robots/Goose_V0.1/evidence/godot_jolt_policy_v5_diagnostic_rc2.json)也失稳。作为诊断，将动作乘以 0.25 后[静止可完成 8 秒](../../../robots/Goose_V0.1/evidence/walk_policy_v5_scaled_diagnostic_rc2.json)，其余三项没有实际抬脚、前后行走或正确转向。动作缩放不是版本化策略修复，也不得部署。下一轮应先解决稳定动作和指令响应，再训练与跨引擎回放；不无限追加轮数。
