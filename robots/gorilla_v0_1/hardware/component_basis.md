# 器件与供电筛查依据

检索日期：2026-10-02。当前物理参数属于布局候选，目录参照与自定义总成要求分别记录。

## 已查证减速器参照

三个型号均为 **CSG-100-2UH 非 LW**。质量与额定来自官方产品页，尺寸已实际目视对应原厂图纸。

| 精确型号 | Rated Torque L10 | 质量 | 本体外径 × 轴向 | 平均输入转速上限 |
|---|---:|---:|---:|---:|
| CSG-32-100-2UH | 178 N·m | 3.2 kg | 138 × 62.0 mm | 3500 rpm |
| CSG-45-100-2UH | 459 N·m | 7.0 kg | 180 × 79.5 mm | 3000 rpm |
| CSG-65-100-2UH | 1236 N·m | 20.9 kg | 260 × 115.0 mm | 1900 rpm |

官方来源：[CSG32](https://www.harmonicdrive.net/products/gear-units/gear-units/csg-2uh/csg-32-100-2uh)、[CSG45](https://www.harmonicdrive.net/products/gear-units/gear-units/csg-2uh/csg-45-100-2uh)、[CSG65](https://www.harmonicdrive.net/products/gear-units/gear-units/csg-2uh/csg-65-100-2uh)。

本体图纸：[32](https://www.harmonicdrive.net/_hd/Content/caddownloads/dxf/csg-2uh_gearheads/csg-32-xxx-2uh.pdf)、[45](https://www.harmonicdrive.net/_hd/Content/caddownloads/dxf/csg-2uh_gearheads/csg-45-xxx-2uh.pdf)、[65](https://www.harmonicdrive.net/_hd/Content/caddownloads/dxf/csg-2uh_gearheads/csg-65-xxx-2uh.pdf)。只采用数值和独立包络，不随工程分发厂商 CAD。

L10 是减速器寿命条件，不能当成整套关节的持续热能力；平均输入转速不能和额定力矩拼成已认证同时工作点。目录质量包含减速器本体输出支承，附加独立承力支承另计，不重复添加已有支承。

## 联合总成要求

布局按额定减速器力矩的 0.8 设筛查设计值，并分别预留电机、附加轴承、壳体/固定、驱动/编码器和制动。完整总成包络、质量和设计速度为**待核设计假设**，并非这些 SKU 的官方参数。

按传动效率 0.75 假设，三档设计输出所需输入轴力矩约 1.90 / 4.90 / 13.18 N·m。效率及热功耗均需在对应工况核查。手指 16 N·m 仅是定制总成筛查要求，无现货型号证明。

真实工业电机量级对照：AKM54L 约 9.0 kg、连续堵转 14.1 N·m、320 Vdc 下额定点 11.5 N·m/2500 rpm；AKM64L 约 13.3 kg、连续堵转 21.0 N·m、320 Vdc 下额定点 18.4 N·m/1500 rpm。来自 [Kollmorgen 官方选型指南](https://www.kollmorgen.com/sites/default/files/Kollmorgen_AKM_selection_guideRevE_EN-mobile.pdf)。这些电机不是本候选已选 SKU，其电压不匹配当前低压母线假设。堵转值对应厂商温升条件，不能直接用于封闭机体。

尤其是 large 档的 6 kg 电机预留，尚无匹配订货型号和工作点证明。应将此约束保留为红线，不把 20% 质量扰动误称覆盖所有真实采购可能。稳定交接前必须以实际电机及包络替换并重算全机质量/力矩/空间。

后续补查找到 **Tecnotion QTR-A-160-34-Z（订货号 10 8160）** 的真实电磁件量级参照：15.3 N·m 连续力矩、1.613 kg、外径 160 mm、轴向最大 34.5 mm，条件为安装面 20°C、线圈 100°C；Z 绕组官方给出 48 Vdc/连续力矩/260 rpm。它支持 6 kg 电机组件预留可探索的判断，但尚未选为工程总成。[官方 brochure 2.5，20–21、35 页](https://www.tecnotion.com/wp-content/uploads/2022/05/Torque_Brochure_EN_2-5.pdf)

按 Kt=0.93 N·m/Arms、线间反电势 56 Vrms/krpm、Rph25=0.43 Ω、Lph=1.09 mH、36 极、100°C 铜温及理想 SVPWM 估算，13.184 N·m 需要约 14.18 Arms；输出 0.6/0.7/0.8/1.0 rad/s 时所需理想直流电压约 76.5/86.6/96.7/116.9 V。此计算未计逆变器、线损、公差和 SOC 余量，不能当厂家整关节通过。

该工况铜损约 336 W，输出 0.6 rad/s 时再计假设减速损耗，总成排热约 534 W。大档联合模块的 245 mm 轴向预留扣除减速器 115 mm 和电磁件 34.5 mm，剩余约 95.5 mm；290 mm 外径相对减速器每侧只有 15 mm。完整输出支承、制动、驱动、轴承固定与冷却仍需真实布局。即使电磁件有型号，封闭总成热与安装红线仍开放。

## 供电与续航

32S LiFePO4、60 Ah 是空间/能量候选：名义 102.4 V、满电 116.8 V、6144 Wh。按 80% 可用能量和任务平均输入 2/4/6 kW 假设，算术续航分别约 147/74/49 分钟。

这不是已验证续航或电池额定。电芯倍率、BMS、驱动满电窗口、线束/连接器、保护、回馈泄能和急停断电仍须闭合。8 kW 连续/20 kW 峰值是设计预算；持续输出不能由预算反向宣称已经成立。

整机 COM 下降产生的势能必须计入回馈；尤其满电或断电时，电池/BMS可能不接受回流。下一轮依据实际质量和核心姿态能量变化确定泄能需求、器件额定、空间和热预算。

## 自重反馈的备选参照

工业联合电驱初值仅驱动就约 545.8 kg，必须先核查整机自重反馈，不能以升级更重驱动掩盖失败。额外查证的 Parker HMI，40 mm 缸径/18 mm 杆径/150 mm 行程/BB 固定叉耳：干缸约 5.55 kg，缸端方形 63 mm，回缩基准 XC+行程为 322 mm（杆端附件另计）。14–21 MPa **压差**下理论推/拉力约 17.6–26.4 / 14.0–21.1 kN。[官方 HY08-1151，印刷页 8、28](https://www.parker.com/content/dam/Parker-com/Literature/Industrial-Cylinder/cylinder/cat/english/HY08-1151-2_NA_HMI.pdf)

按 0.08–0.15 m 有效力臂、0.5–0.8 rad/s，流量量级约 3–9 L/min、液压功率约 0.7–3.2 kW/轴。这只提供定制连杆的量级参照；完整质量需计连杆、承力轴承、油液/软管/阀、反馈、泵电机/蓄能/过滤/冷却。变力臂、死点、杆屈曲、侧载、保载及同时流量预算未核查，不能据此把电驱候选质量替换为干缸质量或宣称减重已经完成。

现成 Parker HTR30/90° 本体约 40 kg，20.7 MPa 非冲击输出约 3390 N·m，百万循环齿面耐久约 2226 N·m；它本身不能证明更轻。[官方 HY03-1800-2US，页 A56、A60](https://www.parker.com/content/dam/Parker-com/Literature/Literature-Files/pneumatic/Literature/Rotary-Actuator/HTR-Series_HY03-1800-2.pdf)
