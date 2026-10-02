# 四片固定机壳到内部框架的连接检查点

四片固定机壳现在有独立的内部框架支架、壳内螺母柱和紧固叠层，外部体型与主关节位置保持原方案。新增30件名义CAD/五金替换446件源中的14个对象，形成独立462个显示对象、18轴、19体闭合姿态参数候选。条件整机质量 **10.440894357kg**，相对446件版增加 **36.197946g**；原30g未闭合机壳五金预留继续保留，用于尚未建成的接缝、门和端部固定，没有提前当成已实现结构扣除。

本检查点解决固定外壳悬空的四处连接。它没有完成翼门铰链、锁扣、接缝支承、端部封盖、整机强度或电气放行；三、四阶段完整目标仍未完成，也不宣布训练硬冻结。已修正的[连续头壳与相机闭合](camera_head_closure_checkpoint.md)保持不变。

## 同版文件

| 文件 | 用途 |
|---|---|
| [装配源](../cad/source/torso_shell_mount_fixture/assembly_scene.json) | 462个同源显示对象；四个OEM相机尺寸参考不是打印件 |
| [CAD与交换文件清单](../cad/exports/torso_shell_mounts/manifest.json) | 30件原生BREP、STEP、STL、闭合quad源及哈希 |
| [结构输入](../configs/torso_shell_mounts.json) | 四个真实框架锚点、屋顶曲面位置和紧固叠层 |
| [完整SI参数](../evidence/torso_shell_mount_parameters.json) | 同版逐件质量、重心、惯量和19体闭合姿态聚合 |
| [逐体参数表](../hardware/torso_shell_mount_body_parameters.csv) | kg、m、kg·m²；保持18轴顺序，不修改Jolt/Unity/Bevy接口 |
| [候选采购表CSV](../hardware/torso_shell_mount_bom.csv)／[XLSX](../hardware/torso_shell_mount_bom.xlsx) | 30件替换增量与19体参数；不是可直接下单的整机BOM |
| [装配与静力证据](../evidence/torso_shell_mount_fit.json) | 全输入/输出哈希、18个有限闭嘴姿态、名义线程/热熔装配量及两组63个静力工况 |
| [同源四色与头部近景](microduck_color_blocking_462_parts.md) | 实际装配渲染；不以渲染遮盖内部装配缺口 |

装配源SHA256：`dc4bd2545687f8b4d247667261abeec314291f965ca1956562db8cfd72f49876`。此前344默认模型、419整机候选和446头壳修正源保留；这版尚未生成同版新碰撞/动力学模型，不能拿旧模型的站立或夹取结果替它放行。

## 结构与安装关系

后部两处使用已有计算板框架M3锚点：X−96mm、Y±34mm。新增支架压在原框架法兰上，顶部垫片/螺母提高2mm，原M3×12换成名义M3×16。前部两处使用颈根/电源框架锚点：X52mm、Y±34mm；顶部垫片提高2mm，原M3×18换成名义M3×20。已有板件、底部垫片与前部螺母保持原位。新后部名义螺栓突出量5.6mm、前部2.6mm，尚须核对实际工具与拆装顺序。

每个候选支架是一体6061加工件：19×16×2mm底部法兰、8×3mm支杆、直径12×2.5mm屋顶压板。斜支杆接到压板外侧，保留直径8mm的螺丝工具通道；螺母柱上方另留0.25mm径向间隙。后部底法兰曾与电池框架柱发生干涉，已缩短并重新核对，没有删除原框架柱或把正交集当成“允许接触”。加工工艺、圆角、预紧、局部强度和疲劳仍待验收。

四片PETG候选壳体内部增加直径9.2mm、长8mm的盲孔柱，热熔插入件从内侧安装，外表没有新增贯穿螺孔。候选为 **Ruthex RX-M3×5.7**：厂家标注M3、长5.7mm、最大名义外径4.6mm；2022-08-15图表给出4.0mm预孔与至少1.6mm径向壁厚。来源：[厂家产品页](https://www.ruthex.de/products/ruthex-gewindeeinsatz-m3-100-stuck-rx-m3x5-7-messing-gewindebuchsen)、[厂商RX系列图表](https://www.igo3d.com/mediafiles/Sonstiges/Ruthex/ruthex_Datenblatt_RX-Serie.pdf)。显示/参数中使用自建保守包络，不把它标成可打印零件或精确原厂螺纹CAD。

内侧名义M3×8与0.5mm垫片形成5.0mm螺纹啮合，离插入件端部还有0.7mm。4.0mm打印预孔与4.6mm热熔件的正交集是明确测量的热熔安装量，**不是刚体已装配状态的无干涉证明**。打印收缩、热熔工艺、拉脱、壳内柱强度和实际螺丝SKU仍未通过。

## 复查结论与边界

- 30件原生实体各为有效单一实体；STEP回读体积误差不超过1e−5。全部自研显示源由闭合quad组成，STL回读闭合且绕序一致；相对原生体积差均低于0.5%。原生CAD继续作为尺寸和质量依据。
- 18个有限闭嘴姿态包括站立、不同下蹲/够地、左右单脚支承、单侧髋偏航/侧倾组合与颈偏航；新增结构相对保留的完整目标几何/保守包络 **0个正交集碰撞、0个未决项**。不是连续关节扫掠或完整旧装配验收。
- 六个新件内的名义螺纹接触、两个与保留框架螺母的名义接触、四个热熔预孔安装量分别量化通过；没有通用碰撞排除表掩盖干涉。
- 更新后的全部质量、重心、完整惯量进入新静力筛查。嘴尖20N／中部50N分别63个工况的承重约束与条件力矩检查通过。嘴尖工况的右膝最小余量 **0.050541N·m**，中部工况 **0.066937N·m**；右膝相对6.4N·m筛选上限只余约0.79%，不能据此宣称动态步行容量充足。
- 力矩上限仍是继承的设计筛选假设，不能替代实际驱动电压、电流、封闭安装温升、输出支承或实物负载能力。供电与额定资料由设计Agent继续核实，不转交给用户负责。

部分目标只有保守完整包络，检查中保留了这些包络及来源身份；没有用包络的零交集宣称真实连接器、配对插头或线束已经合格。闭嘴姿态中的输入转子/连杆保留全部几何，采用明确的19体闭合姿态变换；张嘴的完整运动链仍是另一项验收。

## 失败保留与可复现入口

[初版原生干涉记录](../evidence/torso_shell_mount_initial_native_fit_failure.json)保留十个失败接触及当时的条件静力结果。另保留[支架被工具通道切断](../evidence/torso_shell_carrier_initial_failure.json)、[二进制精度失败](../evidence/torso_shell_binary_precision_failure.json)、[布尔输入精度失败](../evidence/torso_shell_boolean_input_precision_failure.json)、[网格精度比较](../evidence/torso_shell_mesh_precision_comparison.json)和[原生差集运算恢复](../evidence/torso_shell_delta_operation_recovery.json)。失败候选完整本地副本位于忽略的`artifacts/Goose_V0.1/torso_shell_*_failure/`，不覆盖历史默认模型。

薄壳网格布尔运算全程使用双精度，保留原曲面采样，仅局部增加柱和预孔。表面简化位移上限0.00001mm；右前壳的二进制STL合并短边后不闭合，交付经回读验证的全精度ASCII STL。不是改变壁厚、补洞遮盖或人工美化渲染。大曲面整壳原生重网格产生的资源膨胀尝试也保存在本地，没有把被中止的导出当作制造失败或成功。

在已配置的依赖环境中运行：

```bash
env PYTHONPATH=src .venv/bin/python scripts/cad/build_goose_torso_shell_mounts.py
env PYTHONPATH=src .venv/bin/python scripts/diagnostics/check_goose_torso_shell_mounts.py
env PYTHONPATH=src .venv/bin/python scripts/diagnostics/build_goose_torso_shell_mount_bom.py
env PYTHONPATH=src .venv/bin/python scripts/diagnostics/check_goose_torso_shell_mount_checkpoint.py
```

首个构建需要按配置中的厂商URL取得原厂插入件STEP和图表，存入指定本地`artifacts`路径并满足记录哈希；供应商原件不随自研CAD包重分发。最后一项检查还需要同版四色渲染和实际像素复核。大型历史资产的拉取见[Git LFS指南](../../../docs/guides/large_asset_checkout.md)。

下一段返回整机：翼门/接缝/端部固定与可拆装路径、当前电机套装的供电和保护要求、同版完整运动模型及任务回归。非承力外观雕琢与焊点继续后置；不再扩训PPO。
