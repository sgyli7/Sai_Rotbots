# RC2 高增益、模型内部前馈步态试验（失败样本）

本目录保留 `goose_rc2_v3` 的 200 轮 RSL PPO 候选：8 个环境、每轮 32 步，共 51,200 环境步。`checkpoint.pt`、`policy.onnx`、`metadata.json` 与 `runner_config.json` 是同一次训练输出；模型和规格 SHA 见元数据。

此版训练每个扭矩周期使用 MuJoCo 内部 `qfrc_bias`，运行接收器则只能从引擎中立刚体包计算重力前馈。[仅作失配诊断的回放](../../../robots/Goose_V0.1/evidence/walk_policy_v3_on_v4_receiver_rc2.json)把该策略注入当前中立 MuJoCo 接收器，静止、前进、后退、左转都约 1 秒跌倒。诊断特意绕过版本护栏；正常运行应拒绝 v3 策略。不能把这份结果当作原 v3 训练环境回放，也不能部署。后续 v4 重新使用与运行时一致的前馈训练。
