只读数学与 scope 复核，2026-10-02 18:49 UTC 收束；未运行 screen/evaluator/main、全模型、动态轨迹或 Bevy。只独立重算一个 8 轴端点例，其他样本仅读取数量/范围与字段。

**结论。** 脚本 SI 单位、伸缩方向、cap/annular 面积、流量换算和 ΣF·dL/dt 符号正确；当前输出 108 是端点假设样本，不能据此宣称实际热、回馈或泵完整工作点成立。

51–54 行 Ac=πbore²/4，Aa=Ac−πrod²/4，均为 m²。dL/dt=(dL/dq)*qdot：arm 的单位 m/rad，qdot rad/s，所得 m/s；正值伸出由 cap chamber 供流、annular chamber 回流，负值相反。Q=A|dL/dt| 为 m³/s，乘60000为 L/min。Pa×m³/s=W，N×m/s=W。code/evidence 没把 21MPa 当21Pa或把流量 L/min直接乘Pa。

**独立一例。** deep_crouch_rejection_probe、2秒、all_lower_bounds、payload0/pressure demand0/gravity1。从 static screen 抽取该例 force/arm，从 spec 独立取 bore/rod 与角度计算，8轴每一项及总和与 power evidence 差均为0（双精度）。

| 项目 | 复算结果 |
|---|---:|
| 左 knee qdot | +0.523598776 rad/s |
| 左 knee dL/dt | +0.028853259 m/s |
| 左 knee bore/rod | 0.080/0.035 m |
| 左 knee Ac/Aa | 0.005026548/0.004064435 m² |
| 左 knee supply/return | 8.701937889/7.036332590 L/min |
| 左 knee F | -15881.643359 N |
| 左 knee signed Fv | -458.237168350 W |
| 全8轴 supply | 27.967649529 L/min = 0.000466127492 m³/s |
| 21e6 Pa×Q | 9788.677335 W |
| 全8轴 signed useful | -1340.280349 W |
| 算术 stream−signed useful | 11128.957684 W |

**neutral-to-pose 与样本数量。** 原 screen 4姿态×3mass profiles×4load cases=48 cases。power 排除12个 neutral cases，余36×2/4/8秒三种率假设=108；每例只有8 hydraulic_pitch轴。当前 neutral 腿角度全0，所以49行 angles/seconds 等于 (target−neutral)/seconds。hip+knee+fold+ankle 的角度和及 qdot和为0（浮点差≤1.4e-17），只保持所选串联矢状面的 foot pitch；不证明脚位置/零接触速度/滑移/闭链长度或 ground-normal 动态反力。脚本只用最终端点arm乘假定常角速率，未积分路径、求中途峰值、根位姿补偿或起停加速度；neutral静止时的保压/泄漏/泵耗也未由跳过neutral证明为0。

**负功范围。** 所读108个 aggregate ΣFv均为负，范围约[-6224.131,-36.490] W，代表此符号约定下机械能进入执行器的端点算术，不能当负电池功率或回馈电量。例 knee 在 v>0而F<0，是 overrunning/braking 象限；LP力假设与按速度选择的进/回流量并没有给出可同时实现该力的两腔压力、阀口/背压、卸载/储能路径。pQ−ΣFv 是待分配的能量账项，未包括真实泵效率、回油压力/阀耗、泄漏、机械摩擦、其它电驱或冷却功率。现有 scope 明确声明非 qualified heat/regeneration，措辞正确。

**固定排量泵余流。** 当前两泵11cc/rev各3000rpm ideal合66L/min，体积效率0.90–0.97仅敏感假设，得到59.4–64.02L/min；最大缸需求例仍多31.43235–36.05235L/min。若全泵流量均在21MPa，液压stream是20.79–22.407kW，绝非9.79kW；余流在同压力的stream约11.001–12.618kW。这只是明确条件下的算术，不是实测热量。余流实际去向、压力控制和实际泵rpm尚未说明，不能据缸需流低于目录流量证明泵能持续工作、低热、输入电功率或马达余量成立。也不能直接把 surplus 全按21MPa确定为热量，实际卸载压力/路径未知。

flow在相同几何/时间下不随mass/payload cases变化；因此108行也不是108次独立流量实验。其它旋转电驱、8轴动态反力、完整载荷串联、压力控制、实际thermal及Bevy均不在本表证明范围，physical_acceptance=false应保留。

JSON 保存每轴独立值、原输入hash匹配、样本计数和 pump 条件余流。绑定源SHA256：

- scripts/evaluation/screen_gorilla_distributed_power.py: `82083c27fdb02d03e8ad4029840f54274e8400f3668c54186a34555a70ba195f`

- robots/gorilla_v0_1/evidence/internal_structure_d_power.json: `607c30deacc34da907f9ec478a82171961f5abfc1d0dcc8e10277f0051aa211b`

- robots/gorilla_v0_1/evidence/internal_structure_d_screen.json: `93971c2dc05b31da4133c29a14930e1e03bfaeea7e28ed53047e81ea3d016fec`

- robots/gorilla_v0_1/configs/internal_structure_d_spec.json: `8147fef447aa3b06b59b12951f2127e4ffe3c457c24e8855bda2f4da74b9a063`

- robots/gorilla_v0_1/configs/internal_structure_d_system_spec.json: `d988ef1a248405f47f34510a4f6191f4c6ea505cc7502c62905670cab81f6ad1`

本次 finalize 所有绑定输入均未改变：True。
