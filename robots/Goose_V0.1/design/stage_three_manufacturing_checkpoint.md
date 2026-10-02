# 第三、第四阶段：制造几何首个检查点

本轮时间盒开始于 2026-09-30 02:10:11 UTC，截止 05:10:11 UTC。此页是约 90 分钟的中途检查点，**不是第三阶段完成，也不是第四阶段完成**。最终目标仍为完整工程交付；物理实测另设门槛。

## 总体判定

已建立原生曲面制造基础和实际电机接口事实输入。全机实际支架、承力连接、供电保护和装配扫掠仍未闭合，硬件冻结与最终外观均未通过。第二阶段物理模型没有被这些未完成制造件替换，不能把本增量当成新 Sai_Lab 冻结版本。

用户新增的[实体与电子版外观一致门槛](manufacturing_appearance_acceptance.md)已并入最终交付：最终多视图只能由实际同版制造装配生成，必须呈现真实外露零件、接缝、插头和走线，并记录制造与涂装公差。

## 可复现增量

- 六件机身/手动翼形检修盖与两件头部半壳已生成闭合原生 NURBS 实体，保留 BREP、STEP、STL 和四边面源。此处仅为外壳基础，固定接口尚未完成。
- [制造基础清单](../cad/exports/manufacturing_skins/manifest.json)关联源、单位、材质、体积、质量、惯量与文件哈希。薄曲面采用原生几何的自适应体积分计算质量、重心与惯量，避免默认非自适应积分造成偏差。调整头部安装口后，全密度 PETG 壳体合计约 **0.597kg**，未加紧固件/加强筋；不能直接在 8.854kg 整机上再加此数，必须替换原有壳体估算后回算。
- 848,260 个闭合四边面保存在八份压缩 NPZ 中（`vertices` 为 m，`faces` 为整数四元组）。源场景记录每份身份和哈希；STL 使用同一原生曲面直接采样形成的共享四边面三角化，单位 mm。五点/格的采样中，源网格与原生曲面偏差最大约 **0.096mm**；这是采样结果，不是连续曲面的严格 Hausdorff 证明。
- [STEP/STL 回读](../evidence/manufacturing_skin_stl_gate.json)八件通过有效单实体、闭合、一致绕向、正体积、零退化面和体积比较。原生 OCCT 高细分设置曾出现退化三角形/小开口，保留[失败记录](../evidence/manufacturing_skin_stl_raw_gate.json)。未通过填洞或法线修补冒充成功；改变网格生成路径后重新检查实际交付文件。
- [外观一致性检查](../evidence/manufacturing_appearance_gate.json)核验部件身份、文件哈希、四边面拓扑、mm/m 尺度及世界重心位置；当前完整性通过，最终外观放行失败。11 个独立回归测试覆盖篡改 STEP/NPZ、单位混淆、重复/缺件、路径越界、保持体积却平移的错误位姿，以及虚假的全机放行标记。另有测试证明旧装配审核不能用于当前场景，且制造 CAD 变化即使没有改显示场景，也必须重新取得同版审核；装配标识绑定实际场景字节与全部原生部件记录。
- [电机安装事实](../hardware/stage_three_actuator_mounts.json)来自三份官方 2D 图和 STEP 的圆柱面位置；区分各型号的孔数、螺纹、插入深度、前后安装面、文件原点和输出方向。AK45-36 突出定位销端不等同其输出安装面；AK45-10/AK40-10 文件输出端方向相反，不能直接按包络中心套同一变换。

## 已发现、必须处理的装配问题

对新头部原生实体与候选硬件做 CAD 布尔检查：

| 检查对象 | 两侧各自结果 | 处理边界 |
|---|---|---|
| AK45-36 的 55×56.5mm 保守整圆柱包络 | 无实体相交；最小间隔约 0.572mm | 装配/打印误差后余量偏紧，尚未放行实际插头与冷却 |
| 头部 XC330 箱体 68–94mm X、±10mm Y、561–595mm Z | 每侧约 832mm³ 交叠 | 新头部半壳必须开真实后下方轴/机体安装口，不能直接打印当前封闭壁面 |
| 18×40mm 摄像头 PCB，当前放置中心 Z606mm | 每侧约 2.15mm³ 交叠 | 调整光学模块真实安装位姿或内腔，核实当前 SKU 孔图；不能沿用先前 30mm 高代理包络 |
| 摄像头镜头 18mm 外径、19.69mm 长 | 无实体相交 | 尚无完整固定与配套线缆检查 |

以上为修正前真实 CAD 检查，保留失败原因。后续已按侧倾 ±0.6rad 的机体、支架及连接器包络开后部安装口，移除开口留下的孤立塑料片，先在 CAD 构造域保持单个连通半壳，再生成原生实体；没有在 STL 上填洞或修法线。[头部安装回读](../evidence/manufacturing_head_installation.json)对两侧壳体各做 7 组 ×49 个侧倾样本，所有列出的包络均无实体交叠；其中前壳最小间隔约 2.086mm、叉架约 2.800mm。摄像头整个光学组统一下移 1.5mm 后，板包络最小间隔约 1.152mm。嘴部电机间隔仍仅约 0.572mm，实际插头、散热与制造公差尚未放行。这是局部包络检查，不能代替实际相机组件和完整头部装配。

三种电机共六件[带孔原生接口原型](../cad/exports/actuator_interfaces/manifest.json)已按实际孔图生成：输出转接盘与静止前环分开，避免把转动端锁死；AK45-36 的定位销、18mm 定位插口和螺钉深度均纳入。回读实际 STEP 后逐孔用实体探针检查，并核螺钉/垫片/有效插入长度，六件均通过[部件检查](../evidence/manufacturing_actuator_interfaces.json)。这些接口仍未完成与叉板、后侧独立支承、线缆及预紧的整体装配，因此不是完整关节。

新增[安装候选三分之四图](../images/manufacturing_skin_candidate/three_quarter.png)、[头部图](../images/manufacturing_skin_candidate/head_detail.png)、[侧视图](../images/manufacturing_skin_candidate/side.png)直接使用本次八件原生曲面的四边面与一致的光学位姿；其余部分仍为第二阶段候选结构，图中明确标候选。可编辑 Blender 文件为 [quad_assembly.blend](../cad/source/manufacturing_preview/quad_assembly.blend)，绝不是最终全机制造外观。[实际 Blender 回读](../evidence/manufacturing_preview_quad_gate.json)确认 101 个部件、902,084 个四边面，均闭合、零退化面、正体积；这不证明部件之间没有碰撞。当前全仓库回归共 **75 项通过**，其中 Goose 相关为 60 项。

[壳体物理参数增量](../evidence/manufacturing_skin_parameter_delta.json)用原生实体的质量、世界重心与惯量替换旧七项外壳估算，并一致移动相机质量点，逐体采用平行轴定理回算。仅此增量的整机名义值为 **8.825363kg**，比第二阶段低 **28.264g**；逐体质量、重心位移和广义惯量比例均落在原训练参数范围内。新接口、框架、紧固件、散热和电源仍未冻结，因此此数不是最终称重，也不能据此宣告硬件收敛或策略可迁移。旧第二阶段模型与契约保持原哈希。

[通信安装候选](../hardware/stage_three_can_layout.json)把 17 个 CAN 轴具体分为 9/8 两组，单独保留头部 5V TTL 轴；考虑两件 Waveshare USB-CAN-A #23635，USB 串口 2Mbps、CAN 1Mbps，不假定其支持原生 SocketCAN或电气隔离。[解析预算](../evidence/manufacturing_can_budget.json)含每秒 100 帧诊断，CAN 占用 59.2%/52.8%，固定 20 字节主机协议的 8N1 串口占用 37%/33%。厂家资料确认 Linux 演示和这些接口能力，但本机尚无持续丢包/延迟验证；此处没有放行实际尺寸、USB 电流、极性、接地或电池接法。来源见 [Waveshare 商品页](https://www.waveshare.com/product/usb-can-a.htm)、[官方 Wiki](https://www.waveshare.com/wiki/USB-CAN-A)。

## 下一段工作的关键路径

1. 先完成实际电机输出/静止壳体接口、叉架和框架承力连接，再核对整机质量变化与主要姿态。不能把未开孔毛坯当成装配。
2. 处理上述头部安装口、光学模块和实际嘴部轴系/固定；沿用同一套几何做碰撞、夹力路径和外观回归。
3. 完成电源与回馈硬件、完整 BOM/接线/装配资料。[厂商确认问题稿](../hardware/actuator_supplier_questions.md)已经备好，尚未发送。公开资料缺 AK48 电压/回馈额定，目前仍阻止电池接法和保护定值的最终放行；已向用户集中询问现有采购渠道/规格链接。
4. 制造装配和关键物理参数通过后再生成最终整机外观与版本交付。PPO 保留为有限验证，不在此检查点增加训练轮数。

## 复现入口

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/cad/build_goose_manufacturing_skins.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/diagnostics/check_goose_native_skins.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/diagnostics/check_goose_manufacturing_appearance.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/cad/build_goose_actuator_interfaces.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/diagnostics/check_goose_actuator_interfaces.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/diagnostics/check_goose_head_installation.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/models/build_goose_manufacturing_preview.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/diagnostics/compare_goose_native_skin_parameters.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/diagnostics/check_goose_can_layout.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q tests/test_goose_manufacturing_appearance.py
```

`check_goose_manufacturing_appearance.py --require-final` 当前应返回非零，明确拒绝把八件局部原型壳体发布为最终整机。环境为 build123d 0.11.1、OCP 7.9.3.1、trimesh 4.11.1、NumPy 2.5.3；曲面与交换格式证明均与实际清单哈希绑定。
