# 整机机械与物理检查点 — 原生头嘴合入

**第三、第四阶段仍未完成，制造、采购、训练硬冻结和最终外观均未放行。** 本页是当前候选的最新交接入口；[前一检查点](mechanical_checkpoint_pre_native_head.md)对应本地提交 `00b686a`，旧数据与失败证据保留。用户追加三小时时间盒截止 2026-09-30 17:55:02 UTC，已经超时；后续进展不重写该时间盒未完成的事实。

## 同版成果

当前条件裸机质量 **10.2794142 kg**，比前一检查点增加约 **8.625 g**，仍为 **18 个主动轴、65 维观察和 18 维动作**。原生头部支承、真实规格的头部伺服及嘴部曲柄连杆已合入质量、惯量、装配、渲染与运行模型。头部仍保留 80 g 内部结构预留，没有把未建成的喙骨架、相机和轴向保持件偷偷扣掉。

静力台账以闭嘴姿态归并为 19 个主要刚体；运行参考则拆出实际转动曲柄和移动连杆，共 **21 个刚体、2 个传动从动坐标**。带接触模型另拆出 12 个弹性脚垫，共 **33 个移动刚体、14 个从动/被动自由度**，不是增加 14 个电机。拆分保持闭合姿态的整机质量、重心和完整惯量张量。条件质量来自目录件、原生实体密度估算及明确预留，不等于实物称重。

| 资料 | 当前内容与边界 |
|---|---|
| [质量与静力参数](../evidence/body_bay_mechanical_parameters.json) | 逐体质量、重心、惯量、轴位与预留；闭嘴静力归并与张嘴运动模型的区别明确保留 |
| [中立 SI 契约](../configs/mechanical_reference_contract.json)、[逐体 CSV](../configs/mechanical_reference_bodies.csv)、[关节 CSV](../configs/mechanical_reference_joints.csv) | 后端共同坐标和传动关系；Unity、Bevy、Godot 须各自落实从动约束并验收 |
| [参考 MJCF](../models/mechanical_reference/robot.xml)、[URDF](../models/mechanical_reference/robot.urdf) | 21 刚体，`nq=27/nv=26/nu=18`；此参考版本不提供完整碰撞 |
| [接触 MJCF](../models/mechanical_physics/robot.xml)、[URDF](../models/mechanical_physics/robot.urdf)、[接触契约](../configs/mechanical_physics_contract.json) | 10,526 个凸体，`nq=39/nv=38/nu=18`；2 个嘴传动从动坐标及 12 个理想弹性脚垫 |
| [实际装配](../cad/source/mechanical_preview/scene.json)、[可编辑 Blender](../cad/source/mechanical_preview/quad_assembly.blend) | 292 件、2,414,924 个源四边面；运行/STL 三角化不改变编辑源 |
| [候选 BOM](../hardware/mechanical_candidate_bom.csv)、[紧固件表](../hardware/mechanical_candidate_fasteners.csv)、[清单](../hardware/mechanical_candidate_bom_manifest.json) | 316 行零件、101 行紧固件分组；未确定 SKU、工艺和报价不是订货依据 |
| [当前整机斜视](../images/mechanical_preview/three_quarter.png)、[当前头部细节](../images/mechanical_preview/head_detail.png) | 实际装配渲染；其他旧视图未随本次头嘴重建，不作为本版外观证据 |
| [MicroDuck 四色色块重做](microduck_color_blocking.md) | 同版 Cream、Graphite、Lavender、Sky 四图已重做，等待用户验收；主壳、检修门、骨架、嘴脚分区，机械参数不变；第一版被否决且保留 |

原生新增件位于 `cad/source/` 与 `cad/exports/` 的 `head_load_path`、`beak_native_linkage`、`head_linkage_clearance_skins`；踝、颈根和鞋壳增量仍在原目录。各件路径、源哈希及归属以装配与 BOM 为准。当前机构和鞋罩仍为制造候选，不能承诺最终实体已经与本图一比一。

## 本次解决的两个干涉

闭嘴输出臂和螺钉原先撞到头壳下颊，单纯加宽侧颊没有解决底面交叠。本版保持内外壳同向变化，局部下颊降低最多 4 mm，未靠删面修网格。原生实体嘴传动检查由 20/23 变为 **23/23**；[原失败定位](../evidence/beak_native_linkage_cheek_floor_failure.json)保留。名义螺纹交叠仍单独量化，不能称为净空或螺纹强度通过。

头嘴合入后的首次整机回归另检出头部支架与前机壳相撞，原低位成功记录没有沿用。[失败路径](../evidence/mechanical_native_head_ground_path_first_failure.json)和[失败姿态](../evidence/mechanical_native_head_low_reach_first_failure.json)保留；[局部姿态搜索](../evidence/mechanical_native_head_reach_search.json)找到可行折姿，不称为全局最优体型。当前[任务姿态](../configs/mechanical_task_poses.json)先准备头颈，再下蹲 70 mm，最后开嘴。闭嘴夹持点约为 `[200.0, 0, 24.2] mm`，与站姿采用相同身体、腿脚和头嘴几何。

## 有限验证

| 检查 | 当前结果 | 不能推出的结论 |
|---|---|---|
| [静力参数](../evidence/body_bay_mechanical_parameters.json) | 63/63 指定接触与连续设计力矩工况，含质量扰动、50 g 等效负载及 ±2 N 拉力 | 所有张嘴姿态的移动质量已归并、实测热额定、冲击、疲劳或动态步行 |
| [参考一致性](../evidence/mechanical_reference_validation.json) | 39 个 FK 工况与逐体惯量通过；21 刚体 | 全运动范围无干涉 |
| [Blender 身份](../evidence/mechanical_blend_identity.json) | 292 件源身份、quad 与位置边界通过 | 全部显示件已可制造 |
| [原生嘴传动](../evidence/beak_native_linkage_fit.json) | 23/23 张合采样通过，并核对已安装的原生套件 | 连续扫掠、轴销强度、螺纹预紧、实体咬合力或热能力 |
| [头部支承](../evidence/head_load_path_fit.json) | 12/12 限定原生姿态通过 | 全头、喙骨架、相机和线束已闭合 |
| [整机接触与站立](../evidence/mechanical_physics_rejection.json) | 7/7 指定自碰撞姿态；限连续力矩的自由根 PD 站立 1 秒，最大倾斜约 1.56° | 步行、转向、复杂地面或长时间稳定 |
| [低位路径](../evidence/mechanical_ground_reach_path.json) | 82/82 全模型几何采样，夹持点距地约 24.2 mm | 动态坐下、拾起贴地薄物或严格连续扫掠 |
| [低位原生复核](../evidence/mechanical_low_reach_native_pair.json) | 原碰撞支架与两片前机壳，82/82 原生实体采样零交集 | 其余零件、线束或全机连续运动均通过原生 CAD 核对 |
| [50 g 保持和受拉](../evidence/mechanical_50g_hold_pull.json) | 预置自由物体，0.75 秒保持；后段施加 2 N 拉力，头部坐标系滑移检查通过 | 地面拾取、拖日用品、带物行走或自主任务 |
| [四色当前身份](../evidence/microduck_color_current_model_identity.json) | 四张原渲染与当前全部零件源、顶点、quad 和位置指纹相同 | 实物耗材颜色、最终制造外观或涂装重量已确定 |

[移动连杆质量影响](../evidence/mechanical_native_linkage_static_bound.json)在七个任务姿态、161 个张嘴点中核算：全机重心变化最多约 0.005 mm，颈部重力修正最大约 0.000323 N·m，计入原生质量不确定性后仍在现有余量内。它只关闭闭嘴归并的这一项误差，不证明结构强度或热能力。

新增 4 项机构与运行测试，加既有质量和运行测试，共 **23 项通过**：真实两端销孔在张合过程保持同心、移动体拆分守恒质量/重心/全惯量、颈部重力补偿与 MuJoCo 一致、当前弹性脚垫模型保持 65/18 接口。修正了把世界基准高度为零误判成倒地的运行入口问题。未启动 PPO 扩训。

接触检查使用 MuJoCo 3.10.0，0.1 ms 时间步；脚垫材料、摩擦和控制刚度仍为假设。模型仅对真实第二连杆销处的相邻机械配合增加过滤，与第一销处默认相邻过滤对应；其几何另由原生检查约束。没有删除不相关机体碰撞、放宽路径判据、固定根部或固定物体。历史 1 ms 脚垫数值失败和旧合嘴物体挤出失败继续保留。

## 独立喙壳候选与发现

[原生空心喙壳清单](../cad/exports/bill_shells/manifest.json)保存上下喙 STEP/BREP/STL 与 quad 源，分别约 29.29 g、23.10 g，**尚未替换运行模型**。[支承交集核查](../evidence/native_bill_shell_support_screen.json)证实当前旧实心上喙显示包络与支架、两侧轴承分别交叠约 581.5、402.6、187.7 mm³；不能因为它们属于同一仿真刚体就称为装配无穿插。空心候选及局部轴承窗口对所列支承零交集；下喙 STL 需 0.003 mm 细分才使体积误差降至约 0.31%。这只关闭所列支承的实体交集与交换检查，真正法向最小壁厚、骨架/轴连接、螺钉、运动扫掠和制造仍未通过。当前整机条件质量未因此减去任何预留。

[金属喙骨架七件套](../cad/exports/bill_backbones/manifest.json)是独立原生候选，包括框架安装耳、上喙连接板、下喙双 D 孔钢骨架、上下空心喙壳及两片局部开窗头壳。首次壳壁／轴承干涉、随后头壳干涉、固定安装接口交叠分别保留在[首轮失败](../evidence/native_bill_backbone_first_fit_failure.json)、[头壳失败](../evidence/native_bill_backbone_head_skin_first_failure.json)与[固定接口失败](../evidence/native_bill_fixed_interface_first_failure.json)。本轮恢复被安装耳填占的轴承座、给上喙壳建实际安装口，并修正固定横梁的宽度；没有靠过滤这些实体碰撞使检查通过。

当前[闭嘴实体核查](../evidence/native_bill_backbone_initial_fit.json)通过 **45/45 项所列配对**，其中包含七件套全部 21 个闭嘴配对和框架对电机／轴承的检查。[限定张嘴检查](../evidence/native_bill_backbone_sweep.json)通过 **23/23 个采样点**，检查下喙骨架与壳、输入／输出曲柄对所列固定骨架、支架和头壳的实体交集；仍不是连续净空证明或整个头部装配验收。[新件 quad 核查](../evidence/native_bill_backbone_quad_gate.json)通过七件、2,913,036 个四边面，核对闭合、绕序、源身份及相对原生实体的体积／重心误差。它们是 CAD 细分得到的四边面显示源，BREP/STEP 为可编辑工程实体，不是专门为艺术细分设计的控制笼。

[承力初筛](../evidence/native_bill_load_screen.json)使用这版实际 STEP 的 104 个薄截面，包括垫片安装孔，按现有 4.5 N·m 设计峰值和 80 mm 作用臂计算等效 56.25 N。理想固定端变截面梁给出上／下喙板名义最大弯曲应力约 **50.65 / 75.75 MPa**，板的理想弯曲挠度约 **0.498 / 0.317 mm**；固定端、材料模量、应力集中系数及安全系数均是明示假设。连杆销理想最大受力约 **406 N**、当前候选轴套平均投影压力约 **20.3 MPa**。这些数值不包括 D 孔耳、轴的扁位与过渡、轴承座、螺钉／螺纹和实际夹持垫安装，不能用作全头强度或实测 50 N 夹力通过证据。矩形截面与均匀梁闭式解的数值校核也保存在报告中。

七件套条件质量约 **219.48 g**，替换当前五件对应件时、不扣除任何内部预留的名义增量约 **46.45 g**。它尚未合入整机质量、显示或运行模型；当前四套配色图仍对应 292 件、10.2794 kg 的已集成候选，不是这套新喙装配。80 g 头部内部结构预留继续保留。下一步优先完成真实夹持垫／壳连接、轴承及轴的轴向保持和载荷路径，再按同版源重建整机与回归检查。

## 三、四阶段仍须完成

1. **闭合实际承力与装配。** 上下喙薄壳/骨架与输出轴连接、轴向保持、相机安装、翼门铰链与锁止、壳体连接和完整螺钉/线束扫掠未闭合。轴销、支架、OEM 轴承的额定、疲劳与热占空仍待依据；不能把关键承力当装饰细节延期后宣称完成。
2. **供电保护与回馈。** [供电检查点](../hardware/power_release_checkpoint.md)及[供应商问题](../hardware/actuator_supplier_questions.md)仍有效。实际 AK48-2405-2D-A2 驱动的持续电压与回馈安全窗口未充分证实；6S 满电、钳位过冲、实际电阻、保险、断开和散热/线束布局未放行。供应商问题未发送。
3. **本版硬件控制。** [CAN 布局](../hardware/stage_three_can_layout.json)为 17 个 CAN 轴及独立 TTL 头部伺服候选；旧 16 轴 Dynamixel 程序不能当成当前固件。[新原厂手册适用范围核查](../hardware/ak_manual_applicability_audit.json)记录 V3.2.0 通用手册仍未列入本机小型驱动的电压窗口和 MIT 参数档案，不能照抄其他电机的数值。真实协议、急停、断线及限流仍须实现与验收。
4. **整机任务和后端。** 当前真实步行、转向、地面拾取、日用品/小车拖拽、自主任务及 Godot/Unity/Bevy 同版任务未验证。从动传动和弹性脚垫须由每个后端实际适配；中立 SI 与 URDF mimic 不等于所有引擎自动实现。
5. **制造外观、质量和预算冻结。** 保护硬件和未建成承力件仍可能改变质量/包络，中国报价和完整加工费未形成可采购预算；当前四种颜色用于验收机械候选表面方案，不是最终制造放行。

## 复现

本地工作树：`codex/goose-stage-three-four`。交付检查包只用于检查与加载，不是完整制造包；原始资料、图片、采购表和历史失败保留，旧检查包不覆盖。

```bash
PYTHONPATH=src python scripts/diagnostics/check_goose_mechanical_reference.py
PYTHONPATH=src python scripts/diagnostics/check_goose_mechanical_physics.py
PYTHONPATH=src python scripts/diagnostics/check_goose_ground_reach_path.py
PYTHONPATH=src python scripts/diagnostics/check_goose_low_reach_native.py
PYTHONPATH=src python scripts/diagnostics/check_goose_beak_native_linkage.py
PYTHONPATH=src python scripts/diagnostics/check_goose_grip_hold_candidate.py
PYTHONPATH=src python -m pytest -q tests/test_goose_native_linkage.py tests/test_goose_stage_one.py tests/test_goose_mass_properties.py
```

Python 需 build123d/OCP、NumPy、trimesh、MuJoCo；Blender 入口见[四色分区方案](microduck_color_blocking.md)。改变几何、归属、质量或接触后重建并验证同版模型，不能沿用旧哈希或把失败覆盖成成功。
