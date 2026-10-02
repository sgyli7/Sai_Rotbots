# 第三、第四阶段追加两小时

用户于前一时间盒结束后授权继续两小时。追加时间盒从 2026-09-30 05:11:01 UTC 起至 07:11:01 UTC；不重写前次未完成的判定。目标仍是完整机械与电气工程交付，最终外观必须来自实际同版装配。

追加要求：脚底使用刚性承力底板与弹性、可更换的接触层。材料硬度不等于实际贴地能力；须给出接触分区、压缩行程、受力和适应地形的范围。足部接触轮廓或层厚变化须作为新物理版本处理，保留第二阶段文件。

优先次序：实际双片叉架及独立后支承 → 全机承力/装配回归 → 电源回馈、保护、接线和采购 → 同版质量/接触参数与最终外观。PPO 不扩训。尚未取得的厂商电压限值不得填入假数值来使门槛通过。

本页是追加授权与工作边界，**不代表任何阶段验收通过**。阶段事实继续由同版 CAD、物料和验证记录给出。

## 首次制造叉架回归

六组带孔原生叉架共156件，配备输出转接盘、独立静止后支座、SKF61800、轴承盖、螺钉孔和可加工连接桥；相邻叉架错开安装平面，后支承与前一段的电机壳体连接使用同一螺钉堆叠。13个抽样姿态未发现这些部件之间的实体交叠。全机跨轴连接、内部框架、嘴部轴系与线束仍不在此证据范围。

首版减重叉板杆身3.5mm。与同版整机63静力工况关联的378组空间梁筛查，在单脚支撑下出现约170.8MPa名义等效应力、4.11mm挠度；2倍缺口敏感性取值下超过假设200MPa材料屈服下限，**失败**。这不是孔位接触FEA，但足以拒绝直接放行减薄方案。该失败版本先保存，再补强；不得调整通过标志来掩盖。

软底增加两个同版铝板M3孔图及两件可更换TPU90A底。每脚6个开口弹性叶片、1.5mm几何行程；材质数据见[厂家TDS](https://store.bblcdn.eu/s8/default/8140c9d50a6049a3b634fa1387518d8d/Bambu_TPU_90A_Technical_Data_Sheet_582bf8f6-1f0a-474c-aeda-9e72af3689dc.pdf)，其拉伸模量不能直接当作实物打印弹簧标定。24组导向压缩夹具仿真通过数值平衡，但包含触底案例，不能称复杂地面行走通过。初试0.5ms步长在高刚度、小运动质量下出现数值不稳定；改为0.1ms，要求无数值警告且完整运行6s，不能把MuJoCo自动重置后的有限数值冒充稳定。

包含上述薄板候选的整机条件质量9.175566kg，比第二阶段增加321.938g；63静力接触与力矩工况通过，但部分逐体参数超出旧范围。第二阶段模型没有改动，新接触轮廓不能继续沿用旧训练版本。

## 补强、紧固件与整机结果

薄板失败版本保存在提交`01b8d0b30ee874734132092914be2b6dc5835286`及[失败记录](../evidence/manufacturing_fork_frame_thin_failure.json)。当前杆身24mm宽、5.5mm厚，安装平面与轴线未变。[156件实际STEP回读](../evidence/manufacturing_pitch_assembly.json)在13个抽样姿态中无超过0.01mm³的交叠；不包含真实电机实体、全部跨轴、线缆和螺钉实体。

[160件四边面检查](../evidence/manufacturing_increment_quad_gate.json)包含156件叉架部件和4件脚底/承力板，共522,144个四边面，闭合、绕向、非退化、单位、文件身份及世界重心与CAD比较通过。四边面是编辑源；STL按格式为三角面。拓扑检查不是装配或强度放行。

[螺钉堆叠](../hardware/native_pitch_fastener_stacks.json)与[CSV候选清单](../hardware/native_pitch_fastener_bom.csv)含174枚螺钉，长度、有效啮合与共享壳体螺钉按实物堆叠核算通过；未放行具体供应商头型/垫片、预紧、孔位接触、疲劳和长支柱螺钉弯曲。螺钉/垫片完整包络的保守质量估算约305.980g，不能继续用原小件预留替代；这是局部候选清单，不是整机采购BOM。

加入上述保守质量、保留未闭合框架/线束预留后，[条件整机台账](../evidence/manufacturing_component_parameters.json)为**9.607808kg**，比第二阶段增加754.180g。保留预留可能部分重叠，此数不是最终硬件名义质量。63组静态接触及原连续力矩边界均通过；最差右膝6.291Nm，对6.4Nm设计限值只余0.109Nm，不能据此证明动态步行/温升合格。部分逐体参数超旧范围，接触轮廓也改变；**不能沿用旧冻结版本**。

[378组空间梁筛查](../evidence/manufacturing_fork_frame_screen.json)与当前条件质量关联，最差名义56.51MPa、两倍缺口敏感性113.01MPa、最大节点位移1.259mm；在所列120MPa敏感性筛查线以内。电机输出按无限刚、后轴承只承径向，孔/肩台/长螺钉接触FEA和疲劳未完成，不等于结构放行。独立解析测试检查空间旋转后的轴向、两个弯曲方向、扭转、六个刚体模态与过短/触底螺钉。全仓库回归86项通过。

## 弹性脚底范围

采用4mm铝承力板和可更换TPU90A接触件，**不使用裸硬板接地**。每脚6个开口叶片、1.5mm几何行程；刚性整机统一抬高3.7mm，支撑采用六个接触块的实际凸包，未沿用旧整片脚底边界。原生CAD、STEP/STL、材质与螺孔见[脚底清单](../cad/exports/compliant_foot/manifest.json)。打印力曲线、摩擦、疲劳和耐久须实物验证。

[24组导向压缩测试](../evidence/manufacturing_compliant_foot.json)通过，但含触底。使用当前条件质量加50g载物的[自由单脚测试](../evidence/manufacturing_free_foot_fixture.json)覆盖半/满载、三种偏心及两种地面，**23/24组通过，整体未通过**。未通过组：满载、横向偏心12mm、名义刚度、1mm起伏；倾斜约0.33°，6秒末广义速度最大约0.00173，未达预设1e−4阈值。50/25µs步长复核也未达原判据。该单脚试验使用假设惯量/载荷高度与未标定材料，不能代替全机粗糙地面行走。

首次自由脚场景只有六块地面小块，中间空隙导致滑出后落入空处，不能称“平地倾倒”；[错误场景失败](../evidence/manufacturing_free_foot_sparse_ground_failure.json)保留。改成连续基础地面与凸起块后重新运行，未降低通过标准。

[实际候选整机图](../images/pitch_foot_candidate/three_quarter.png)、[脚部图](../images/pitch_foot_candidate/foot_detail.png)与[Blender源](../cad/source/pitch_foot_preview/quad_assembly.blend)直接引用当前原生四边面。239部件、1,414,164四边面通过[保存文件回读](../evidence/manufacturing_pitch_foot_preview_quad_gate.json)。其他跨轴、嘴、盖体、线束和螺钉仍未完整制造，图上标候选，**不是最终一比一制造外观**。

## 转向要求

用户补充：必须具备像MicroDuck一样的转弯能力。每腿保留6个主动轴：髋yaw/roll/pitch、膝pitch、踝pitch/roll；髋偏航绕Z轴，候选范围±0.6rad约±34.4°，不是整机转向角或转弯半径。髋侧倾/踝侧倾支持横向换重心；不能拿颈部偏航充当整机转弯。

[有限固定脚转向检查](../evidence/manufacturing_turning_screen.json)使用当前质量和接触轮廓。四组左右单脚支撑、机身转±15°的逆运动学达到脚位姿误差阈值，并通过静力接触/连续力矩筛查。固定机身位置转±30°时两组触膝部限位，约2.7mm/1°位姿残差；另两组达到阈值。**全部8组运动学检查未通过，真实转向步态未通过。** 不能宣称单次30°或任意原地转向。

正确任务路径是换重心→卸载摆动脚→髋偏航改变落脚朝向→落地并调整躯干→另一脚接续，避免靠高摩擦脚底硬拧。接下来必须核真实跨轴支架/插头扫掠、摆脚净空和左右重复90°/180°转向轨迹；记录偏航速率、最小转弯空间、滑移和稳定性。当前端点测试没有抬起另一脚，也不是轨迹控制器或PPO步态，不能把静力端点通过写成转弯能力已实现。

## 退出判定与主线

| 要求 | 当前结果 |
|---|---|
| 六组平行轴制造候选 | 带孔原生CAD、堆叠、局部干涉及梁筛查通过；完整局部强度未放行 |
| 弹性脚底 | 有可更换候选；自由单脚未全通过；整机地形未放行 |
| 第三阶段完整机械 | **未完成**：跨轴连接、主框架、嘴部轴系和全机真实附件未闭合 |
| 第四阶段完整电气 | **未完成**：[供电检查点](../hardware/power_release_checkpoint.md)记录候选及拒绝理由；电压、保护定值、线束、散热未闭合 |
| 新硬件冻结/Sai_Lab交接 | **未通过**：超旧参数范围、接触和制造重量变化；旧第二阶段原样保留 |
| 最终实体/电子版外观 | **未通过**：须待同版整机制造装配完成后出图 |

非承力圆角、装饰涂装和焊点优化可以后置；承力连接、动态容量、回馈和接触不能用“细节后置”替代。下一步回到整机：闭合跨轴/主框架/嘴部载荷链并控制增重，再闭合母线额定与实际保护、线束、散热，然后重发同版物理版本、全机装配和最终外观。本轮PPO未扩训。

## 增量复现入口

在固定提交工作区依次运行：

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/cad/build_goose_pitch_forks.py
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/cad/build_goose_compliant_soles.py
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/diagnostics/check_goose_pitch_assembly.py
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/diagnostics/check_goose_native_fastener_stacks.py
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/diagnostics/check_goose_manufacturing_parameters.py
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/diagnostics/screen_goose_fork_frames.py
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/diagnostics/check_goose_native_increment_meshes.py
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/diagnostics/check_goose_compliant_foot.py
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/diagnostics/check_goose_free_foot_fixture.py
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/diagnostics/check_goose_turning_kinematics.py
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q
```

自由单脚与转向入口当前应返回非零，拒绝全项放行。工程缺口未闭合，不得把这些正确拒绝的退出码伪装成全部验收成功。
