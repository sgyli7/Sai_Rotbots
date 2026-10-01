# 整机机械与物理检查点 — 2026-09-30

**结论：第三、第四阶段未完成，制造、采购、训练冻结和最终外观均未放行。** 本页是当前候选的唯一最新交接入口；历史阶段页面和试验保留，但其质量、几何及成功记录不能代替本版验证。用户追加的三小时时间盒截止 2026-09-30 17:55:02 UTC。

## 同版成果

当前装配的条件裸机质量为 **10.2707896 kg**，19 个主要刚体、18 个主动轴。物理接触版本另有 12 个理想弹性脚垫自由度，拆分脚垫时保持整机质量、重心和惯量；它们不是新增主动轴。质量包含目录件、原生实体密度估算及显式预留，不能当成实物称重或已闭合的量产 BOM。

| 资料 | 用途与边界 |
|---|---|
| [物理参数与质量依据](../evidence/body_bay_mechanical_parameters.json) | 逐体质量、重心、惯量、轴位与保留预留；不采用概念图估计惯量 |
| [中立 SI 契约](../configs/mechanical_reference_contract.json)、[逐体 CSV](../configs/mechanical_reference_bodies.csv)、[关节 CSV](../configs/mechanical_reference_joints.csv) | 后端适配的共同本体；Unity、Bevy、Godot 仍须各自验收 |
| [参考 MJCF](../models/mechanical_reference/robot.xml)、[URDF](../models/mechanical_reference/robot.urdf) | 几何、运动学和惯量参考；此目录的参考模型不提供完整碰撞 |
| [接触 MJCF](../models/mechanical_physics/robot.xml)、[URDF](../models/mechanical_physics/robot.urdf)、[接触契约](../configs/mechanical_physics_contract.json) | 9,898 个分解凸体；MuJoCo 候选接触检查。其他引擎须显式适配弹性脚垫，不可直接声称验收通过 |
| [实际装配清单](../cad/source/mechanical_preview/scene.json)、[可编辑 Blender 源](../cad/source/mechanical_preview/quad_assembly.blend) | 294 件装配显示件，2,332,948 个源四边面；仿真和 STL 导出三角化不改变编辑源 |
| [候选 BOM](../hardware/mechanical_candidate_bom.csv)、[紧固件表](../hardware/mechanical_candidate_fasteners.csv)、[清单](../hardware/mechanical_candidate_bom_manifest.json) | 322 行零件、101 行紧固件分组；未确定的 SKU、工艺、报价明确保留，不是订货单 |
| [整机斜视](../images/mechanical_preview/three_quarter.png)、[侧视](../images/mechanical_preview/side.png)、[脚部](../images/mechanical_preview/foot_detail.png)、[头部](../images/mechanical_preview/head_detail.png) | 直接渲染当前装配；不是最终制造外观，未通过的新头嘴件没有偷偷加入图片 |

新增原生 CAD/STEP/STL 在 `cad/source/` 与 `cad/exports/` 的 `body_bay_ankle_assembly`、`neck_root_assembly`、`hollow_shoe_covers`、`head_roll_envelope` 等目录；实际路径以装配/BOM 清单为准。当前鞋壳为避让实际踝机构打开了局部区域，机构外露，不能宣称保持了旧鞋罩的最终外观。

## 有限验证结果

| 检查 | 结果 | 不能据此推出的结论 |
|---|---|---|
| [整机静力参数](../evidence/body_bay_mechanical_parameters.json) | 63/63 指定接触及连续设计力矩工况通过，含质量扰动、50 g 负载和 ±2 N 拉力 | 实测热额定、冲击、疲劳、动态步行 |
| [参考一致性](../evidence/mechanical_reference_validation.json) | 39 个 FK 工况与逐体惯量一致性通过 | 全关节极限无干涉 |
| [当前 Blender 身份](../evidence/mechanical_blend_identity.json) | 294 件源身份、四边面与装配边界核对通过 | 全部显示件已可制造、最终外观已批准 |
| [踝及鞋壳](../evidence/mechanical_ankle_shoe_screen.json) | 24/24 指定原生实体姿态通过 | 轴承额定、预紧、线束及全运动包络已闭合 |
| [颈根与机壳](../evidence/neck_root_skin_screen.json) | 15/15 指定偏航姿态通过 | 全颈、线束和组合极限通过 |
| [接触与自由根站立](../evidence/mechanical_physics_rejection.json) | 7/7 指定自碰撞姿态通过；限连续力矩 PD 站立 1 秒完成，最大倾斜约 1.55° | 学会行走、转向、复杂地面或长时间稳定 |
| [低位路径](../evidence/mechanical_ground_reach_path.json) | 82/82 几何采样通过；闭嘴夹持点距地约 27.2 mm | 动态坐下、拾起贴地薄物或连续扫掠严格证明 |
| [50 g 物体保持与受拉](../evidence/mechanical_50g_hold_pull.json) | 自由物体预置于夹垫间；0.75 秒保持，后段施加 2 N 拉力，按头部坐标检查滑移通过 | 从地面捡起、拖日用品、带物行走、自主任务或新原生嘴机构通过 |

物理检查使用 MuJoCo 3.10.0，脚垫摩擦与刚度仍为假设。时间步为 **0.1 ms**；1 ms 曾产生脚垫数值不稳定，失败记录保留。使用自由根和自由物体，没有把机体或物体固定来冒充稳定。旧位置式合嘴控制曾把物体挤出，失败也保留；当前有限试验采用慢速合嘴并限制反馈力矩。当前结果不能验证新原生头嘴套件。

## 阻止三、四阶段放行的关键项

1. **头嘴承力套件未通过闭合干涉。** [新头部载荷链](../evidence/head_load_path_fit.json)的 12 个限定姿态通过，但[原生嘴传动](../evidence/beak_native_linkage_fit.json)只通过 20/23 个张合采样。闭合及 0.025/0.05 rad 附近，输出臂和按钮螺钉仍与左头壳相交。它们没有合入当前质量、主模型和图片；不能当作次要装饰细节延期后宣称完成。上下喙载荷链、轴向保持、相机固定和结构强度也未闭合。
2. **供电、回馈和实际保护未放行。** [供电检查点](../hardware/power_release_checkpoint.md)及[供应商问题](../hardware/actuator_supplier_questions.md)保留具体缺口。AK48-2405-2D-A2 是实际模组内驱动；6S 满电与钳位过冲的安全窗口尚无充分依据。实际电阻、保险、断开、散热和线束容纳未闭合；350 W 机械功率限制不能代替铜损或回馈电流核算。供应商问题未发送。
3. **本版硬件控制未实现。** [CAN 布局候选](../hardware/stage_three_can_layout.json)描述 17 个 CAN 轴与独立 TTL 头部伺服；旧 16 轴 Dynamixel 控制程序不能当作本版实现。实际协议、断线/急停、限流及接线需要落到同一版硬件。
4. **整机装配与运动仍有缺口。** 翼门铰链锁止、壳体连接、螺钉与线束扫掠、部分组合极限、OEM 输出轴承额定及结构强度未闭合。没有验证本版真实步行、转向、地面拾取、日用品拖拽、自主任务或跨引擎任务。
5. **最终外观、质量与预算未冻结。** 当前图片是可检查的机械候选。供应商额定、保护器件和头嘴改版仍可能改变质量/包络，不能向 Sai_Lab 宣告大结构已稳定，也不能保证最终实体与此图一比一。中国报价与完整加工费用未形成可采购预算。

## 复现与版本

本检查点代码与数据保存于本地 `codex/goose-stage-three-four` 工作树；打包文件如提供，只是可加载的检查包，不是制造发布包。原始图片、文档、采购表和历史失败保持。原生鞋壳 NURBS 偏移失败试样移至 `hollow_shoe_nurbs_trial`；旧失败 JSON 中的原运行路径保留历史含义。

在仓库根目录，使用已安装 build123d/OCP、NumPy、trimesh、MuJoCo 的 Python 环境执行：

```bash
PYTHONPATH=src python scripts/diagnostics/check_goose_mechanical_reference.py
PYTHONPATH=src python scripts/diagnostics/check_goose_mechanical_physics.py
PYTHONPATH=src python scripts/diagnostics/check_goose_ground_reach_path.py
PYTHONPATH=src python scripts/diagnostics/check_goose_grip_hold_candidate.py
```

以上检查会写入本机证据，范围见各文件；没有启动 PPO 扩训。更新几何、刚体归属、轴线、质量或接触以后，应重建同版参考、碰撞和物理模型，不能沿用旧哈希证据。
