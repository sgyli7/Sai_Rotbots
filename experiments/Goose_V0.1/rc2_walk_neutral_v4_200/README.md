# RC2 中立前馈步态 v4（失败样本）

200 轮、8 环境、每轮 32 步，共 51,200 环境步；策略观测 53 维，输出 10 维。训练和运行都使用中立刚体重力前馈，ONNX 与训练网络数值一致。

[独立回放](../../../robots/Goose_V0.1/evidence/walk_policy_200iter_v4_rc2.json)的静止、前进、后退、左转均在 0.94–1.22 秒失稳。诊断发现最初标作“普通策略站立”的[旧 1 ms 试验](../../../robots/Goose_V0.1/evidence/stand_neutral_continuous_torque_v4_rc2.json)没有按控制契约的 5 ms 更新力矩；[修正后的 5 ms 试验](../../../robots/Goose_V0.1/evidence/stand_neutral_policy_mode_v4_rc2.json)亦失稳。这个 v4 策略不得部署；v5 改变腿部阻尼并重新做两引擎站立与训练。
