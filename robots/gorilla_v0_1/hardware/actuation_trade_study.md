# 驱动替代研究：后置来源记录

记录日期：2026-10-02。用户最新指示为先精确还原唯一原图，主任务已终止本轮驱动架构比较。**本轮没有选择新硬件、没有生成新驱动配置，也没有修改模型或参数。** 后续研究须等待主任务重新安排，不以此文档推动外观改形。

研究开始时读取的是 `gorilla_layout_b`，整机质量 890.757 kg、47 个主动关节。既有有限静力报告的单支撑空载需求包含左踝 roll 1637.4 N·m、左髋 roll 3569.9 N·m；这是失败候选中的指定姿态及接触分配，不是关节额定、行走能力或最终机器人的性能目标。该版本的输入身份见 [来源记录](../../../experiments/gorilla_v0_1/actuation_trade_study/source_basis.json)。

本轮实际打开的官方来源限定为以下三项。表格参数已读取；完整安装图、总成散热、寿命与机器人连续动作均未验证。

| 官方来源 | 已核对的有限事实 | 使用边界 |
|---|---|---|
| [Parker HMI，HY08-1151](https://www.parker.com/content/dam/Parker-com/Literature/Industrial-Cylinder/cylinder/cat/english/HY08-1151-2_NA_HMI.pdf)，印刷页 1、28 | 系列工作压力上限 210 bar；40/18 mm、B/BB/SB 安装的零行程质量 4.2 kg，每增加 10 mm 行程加 0.09 kg；既有 150 mm 行程参照的干缸质量为 5.55 kg | 干缸不含完整关节、连杆、承力支承、阀、油液、软管、泵、储能、反馈或冷却；没有形成液压整机预算或型号选择 |
| [Tecnotion Torque Brochure 2.5](https://www.tecnotion.com/wp-content/uploads/2022/05/Torque_Brochure_EN_2-5.pdf)，印刷页 20–21、35 | QTR-A-160-34-Z，订货号 10 8160；电磁件质量 1.613 kg；连续力矩 15.3 N·m，对应线圈 100°C、安装面 20°C；160 mm 外径、34.5 mm 最大轴向 | 电磁件不等于封闭安装后的电机总成或完整关节；本轮未验证母线、机械装配、持续散热与传动工作点 |
| [Harmonic Drive CSG-65-100-2UH](https://www.harmonicdrive.net/products/gear-units/gear-units/csg-2uh/csg-65-100-2uh) | 官方质量 20.9 kg，Rated Torque L10 为 1236 N·m，平均输入速度上限 1900 rpm；允许输出弯矩 1860 N·m | L10、输入速度和输出轴承数据具有各自目录条件；不能拼成机器人完整关节已认证的持续工作点 |

完整驱动质量分配、安装与扫掠空间、持续输出、供电/回馈、液压同时流量及散热仍属于红线未知。采购或定制缺口只有在对应物理范围得到验证后才能单独记黄线。此来源记录没有关闭任何红线，也没有改变当前候选的失败结论。
