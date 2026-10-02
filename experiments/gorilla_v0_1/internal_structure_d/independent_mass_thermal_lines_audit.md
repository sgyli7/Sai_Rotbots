质量完整性只读审查，2026-10-02 18:38 UTC 收束；未跑 evaluator 或整机模型，只对 coolant fill/shell 两局部实体作一次有限材料交。本文不能作物理放行。

**可核实的账目事实。** system spec 的 670 个 modules 与 master.system_module_rows 完全相同；每 ID 唯一、均有同名 native part、body 字段一致、质量三点皆非零且有序。没有查实 ID 层面漏记或确定重复。所有 module 都是 component_module_envelope，所有 inertia_scope 都明确 proxy。原系统 mass_excludes 是根负责的 8 pitch-cylinder 结构、C15 甲壳/框架和 D 分段脚钢件，属于集合分工，不能当整机质量漏项。

299 个 d_* 散热/管线/连接件条目总量 [14.7553915,24.7016632,41.4539734] kg；这只是所列自估子集，并非 complete manufactured thermal/lines mass。各类如下：

| 子集 | 数量 | low / nominal / high kg |
|---|---:|---|
| connector_fastener_plate | 20 | 1.511846 / 2.351846 / 3.991846 |
| connector_manifold_reserve | 18 | 2.880000 / 5.760000 / 10.800000 |
| coolant_inventory | 1 | 0.473821 / 0.518710 / 0.548635 |
| coolant_line | 14 | 0.445781 / 0.669890 / 0.996303 |
| coolant_pump | 1 | 0.400000 / 0.750000 / 1.200000 |
| coolant_reservoir | 1 | 0.219845 / 0.287814 / 0.409767 |
| electrical_harness | 58 | 1.650276 / 2.970497 / 4.950828 |
| fan | 2 | 0.320000 / 0.600000 / 1.000000 |
| hydraulic_case_drain_line | 58 | 0.660110 / 1.072679 / 1.732789 |
| hydraulic_pressure_line | 58 | 1.485248 / 2.310387 / 3.630608 |
| hydraulic_return_line | 58 | 1.815303 / 2.887983 / 4.538259 |
| radiator_core | 2 | 1.242800 / 1.997050 / 3.402700 |
| sealed_air_duct | 8 | 1.650360 / 2.524808 / 4.252238 |

三类液压管线和 electrical harness 各 58 段，供回油/泄油 dry mass 按长度分别计；所有几何长度与端点距离一致，质量公式只有小数舍入误差。各 arm 每类 12 段、1.8206566 m，各 leg 每类 17 段、2.3050335 m，左右镜像。液压管线明确 hydraulic_oil_mass_excluded，root 的 oil inventory 是单一 owner，不能在本子集再加油；本次不核 root 油账。coolant_line 则明确含液体，14 段合计约 0.130016 L；radiator 各含 [0.03,0.05,0.10] kg 工质，约 0.499 L reservoir fill 独立计量，pump package 排除工质。未查实这些 coolant 字段重复计入。

**必须保留的红色 unknown。** 14 段 coolant_line 全在 torso，仅连接小泵/小箱及两 radiator，function 明示 heat-source cold plate path not closed。23 个 motor_cooling_case/connector 已有壳体及服务预留质量，但未列到肢体 motor cooling case、inverter 或 compute cold plate 的真实供回路径、接头、增量管长和增量液量；其完整装机质量与热能力不能据当前子集认为已覆盖。

232 段 limb routing 是安装占用圆柱及干质量估计，不是实心材料。例 system_spec:29073 的 d_left_arm_electrical_harness_06 写明 upstream body 仅供 neutral visualization，both-end kinematics/deforming geometry 未表示。当前相邻段 06 在 left_upper_arm、07 在 left_forearm，共用 neutral 点 [-0.27,0.82,1.73]；两个 body 发生相对转动时，整体刚体变换不能保持路线连接。需要保留跨关节的两端运动、弯曲/夹持/应力释放、conductors/insulation/oil 各自分布未知；不得把圆柱均匀密度惯量当真实 hose/cable 惯量。改变姿态的质量分配同样只是 body proxy，不能用此归属证明真实关节重力载荷。

23 个 ds_*_wire_coolant_connector service reserves 与 18 个 d_*_routing_connector_block、20 个 connector_fastener_plate 都有非零质量，但未明确逐项 BOM 边界。例左脚分别有 0.25 kg service connector、0.32 kg mixed block、0.1173248 kg clamp/fastener plate nominal。功能含接头/线缆/安装件，可能有 allowance 重叠；目前没有证据能作确定双计修正，也不能据名称相异认完整总成。须保留 item ownership 未闭合。

compute、network switch、back screen nominal 为 2.0/0.45/1.7 kg；23 关节 controller 各 1.1 kg，2 pump inverter 各 1.8 kg；8 EA coil、HV distribution、LV converter 也有独立非零 reserve。这些是 own packaging 包括 enclosure/thermal/connectors 的估计，功率/电压/截面/热连接和选型未闭合。compute/system_spec:22508 的“complete”只是预留范围描述，不能当厂商完整持续系统额定或质量实测。

脚 roll 每侧明确列 gear/motor、壳、输入 hub、output adapter、brake/encoder/controller/service connector、2 carrier 等 12 个 modules，共 24 项；与根的 D 分段脚钢 arch/tray/brace/pins 是不同明确范围，没有查实重复 ID。系统 body 全归 left/right_foot 是 C15 packaging ownership，proposed serial output carrier 未重建，不能用于最终 foot roll 的父子惯量合同。锁销防脱、拔销/锁止执行或人工维护接口的实际安装件未独立选型，不能隐含零质量或自动锁止能力。

**可核实的局部几何缺口。** d_coolant_reservoir_fill（system_spec:24638）与 reservoir shell 的真实材料交为 1.6354029e-5 m³，z=[1.97500002,1.97800004]，即 fill 占用从外底面起而进入 3 mm 底盖。native fill 体积约 0.490617 L，mass basis 则是独立 nominal 0.498759 L 假设。contained_in / allowed_overlap_with 标签不证明液体在内腔，不能把其装机容量/COM 当事实；本审查未调整任何质量。这个小项不能代替整个冷却闭环缺口。

本次未发现明确可直接删除的重复质量，也未为缺口补编未知质量。需要保留所有质量区间、安装包络和非均匀 inertia 的 unknown，完整 BOM/实际管件分布/最终父子所有权再闭合。详细 per-ID 字段、system spec 行号、路线公式复算和 snapshot hash 见 JSON。

绑定源哈希：

- robots/gorilla_v0_1/cad/source/internal_structure_d_scene.json: `2933318e60dfe786f5cae61d88682519589f1eb5f8a23c999e6f7c6566cdd280`

- robots/gorilla_v0_1/configs/internal_structure_d_spec.json: `8147fef447aa3b06b59b12951f2127e4ffe3c457c24e8855bda2f4da74b9a063`

- robots/gorilla_v0_1/configs/internal_structure_d_system_spec.json: `d988ef1a248405f47f34510a4f6191f4c6ea505cc7502c62905670cab81f6ad1`
