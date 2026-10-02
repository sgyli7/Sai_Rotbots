# Layout B 首轮工程候选评审

本记录对应 `gorilla_layout_b`，是失败候选的可复查交付。**首个检查点尚未达标，外观、内部装配和物理均未放行。** 原图是设计基准；以下网格是用于暴露冲突的工程代理，不能替换原设计或称为制造 CAD。

## 实际交付

- [原图](concepts/aa3/user_confirmed_four_view.jpg)与[比例依据](../evidence/appearance_constraint_review.json)。高度暂取 2.65 m，按用户选择保留原图比例，页眉宽度待核。
- 可编辑[场景数据](../cad/source/layout_b_scene.json)、[Blender 源](../cad/source/layout_b.blend)、[GLB](../cad/exports/layout_b/layout_b.glb)及 [OBJ](../cad/exports/layout_b/layout_b.obj)。外包络按 +X 深、+Y 宽、+Z 高约为 1.093 × 1.918 × 2.650 m；深度为工程重建假设。
- 实际[四视图](../images/layout_b_four_view.png)和[三分之四视角](../images/layout_b_threequarter.png)。[渲染身份记录](../evidence/layout_b_render.json)绑定原图、参数、场景、MJCF、姿态和脚本。
- [胸前持物手位](../images/layout_b_pose_chest_hold.png)、[前伸](../images/layout_b_pose_front_reach.png)、[低位触达](../images/layout_b_pose_low_reach.png)、[门把手位](../images/layout_b_pose_door_handle.png)、[单腿支撑](../images/layout_b_pose_single_support.png)：均为同版模型的 FK 渲染，图中没有实际搬运物体，也未通过接触和动作验收。
- [SI 物理契约](../models/full/robot.json)、[可加载 MJCF](../models/full/robot.xml)、[逐组件质量账本](../hardware/layout_b_mass_components.csv)、[内部包络筛查](../evidence/layout_b_internal_screen.json)和[静力/拒绝测试](../evidence/layout_b_screen.json)。
- [汇总证据](../evidence/layout_b_checkpoint.json)和[同版审计清单](../evidence/layout_b_audit_manifest.json)。加载与哈希通过只说明资源一致，物理拒绝结论同时保留。

更早的 B 拒绝输入、运行模型与报告保留于 `experiments/gorilla_v0_1/layout_b_initial_rejection/`；`layout_b_manual_pose_rejection.json` 和 `layout_b_reach_limit_rejection.json` 是历史筛查，不绑定本次最终几何。A 参数未产生模型。原包的其他图片只作历史来源，不与用户再次确认图竞争外观权威。

## 外观比对结果

主 Agent 已实际查看原图、四视、三分之四及六个姿态。保留了无独立头颈的象牙楔形躯干、蓝肩/前臂、双竖格栅、三段 Z 腿、腿外展、低宽脚和后背蓝检修面板；没有为容纳器件把整体横向拉宽到 2.587 m。

仍有明显代理偏差：蓝肩甲曲面偏圆，胸侧和顶部连接过于简化；格栅为突出挂载盒，原图更接近嵌入式；髋/膝黑色机构、手掌及脚趾的分层细节不足。低位动作还显示手/膝及腿部遮挡与碰撞风险。**这些偏差没有被批准为新设计，也不因四视图已生成而关闭外观门禁。** 下一版应利用原图进行局部曲面和分区复原，并保持工程源与实际渲染一致；先解决阻断内部方案的体量问题，避免把失败总成精修成定稿。

## 质量、负载和动作需求

完整工业电驱假设约 545.8 kg，框架、电池、散热、线束及功能组件预留 180 kg，3 mm 铝薄壳估计约 165 kg，合计 **890.76 kg**。质量采用薄壳表面积积分和显式组件汇总，并回读编译后的逐体完整惯量。外壳强度、真实传动部件运动及电机转子反射惯量没有因此得到证明。

驱动 ±20%、其他分配/薄壳 ±30% 只覆盖已声明的估计；约 678–1103 kg 的范围不是所有实际采购、缺失结构或热系统的覆盖保证。中立 COM 约为 (0.0024, −0.0017, 1.432) m，重力约 8.74 kN。

静力采用自由根六维平衡、真实足底箱体角点、非负法向力和内接摩擦锥，优化各轴相对设计力矩的最大利用率。载荷为虚拟手部力，不能证明夹持。下表是代表性解与限值之比；不是逐关节独立额定或实测力矩。

| 姿态 | 空载最小最大利用率 | 20 kg 力代理 | 代表性最紧轴需求 | 结果 |
|---|---:|---:|---|---|
| 中立 | 1.085 | 1.135 | 折叠轴约 399 N·m，假设限值 367.2 | 超限；腕部接触代理也重叠 |
| 胸前手位 | 1.619 | 1.834 | 空载折叠轴约 595 N·m | 超限和碰撞 |
| 前伸 | 1.935 | 2.164 | 空载踝滚转约 711 N·m | 超限和碰撞 |
| 低位触达 | 1.698 | 1.851 | 空载踝俯仰约 624 N·m | 超限和大量碰撞 |
| 门把手位＋150 N 反力 | 1.249 | 1.376 | 踝滚转约 459 N·m | 超限和碰撞 |
| 单腿支撑 | 4.459 | 4.529 | 空载踝滚转约 1637 N·m | 超限和碰撞 |

全部 42 个静力样本未通过联合门禁。若仅保持该质量分布和姿态、均匀缩放全部质量，在不计外力及碰撞的理想力矩条件下，中立的质量临界值约 821 kg，单腿约 200 kg；这是解释自重反馈的数学对照，**不是可以只把机器人改成 200 kg 的设计方案**。现有驱动总质量已超过后者，不能仅升级更多同类重驱动来宣称闭合。

几何手位：胸前目标 (0.70, ±0.32, 1.58) m；前伸 (0.75, ±0.32, 1.50) m；低位 (0.50, ±0.32, 0.90) m；右侧门把 (0.65, −0.45, 1.30) m。IK 位置误差约 0–0.004 mm，但只有离散位置核查，未约束抓取朝向、连续扫掠或真实物体。操作安全包络、额定载荷和行走速度目前不能成立。

2 ms 和 20 ms 的 MuJoCo 自由根短时拒绝测试均在第一步因约 27 mm 接触穿透停止。腕部壳网格与稀疏前臂代理发生接触，需用实际腕部承力/轴承间隙几何区分连接界面和真实干涉，不能盲目禁掉该对碰撞。20 ms 结果仍是 MuJoCo 诊断，绝不是 Bevy 验收。

6.144 kWh 电池、80% 可用量、平均输入 2/4/6 kW 时，算术续航约 147/74/49 分钟。任务功率、BMS、电机持续工作点、冷却、回馈/泄能和急停均未闭合，不能将这些分钟数写成产品续航。

## 承力链、手部与感知

完整内部包络初筛包含 47 个驱动圆柱、22 个功能/框架预留箱体，共 2346 对。25 对独立完整驱动包络具有严格重叠证书，其中 23 对同轴位中心；另两对为左右第一指近节与拇指远节。腰俯仰/滚转及髋滚转/俯仰的重叠交集下界达 7.700 L。因此，现有“每轴中心放一套完整模块”不能作为装配方案。

这些是所声明的排他包络冲突，不是已确定的实体材料相交。82 对预留箱体共占以及两对折叠轴/中段框接触或未知仍保持开放；薄壳内腔、真实中空框、工具、线束和连续扫掠尚未验证。默认 20 mm 维护间隙只用于筛查，不代表维护设计标准已满足。

承力需求路径为地面 → 足底/脚框 → 双轴踝 → 低位折叠轴 → 中段 → 膝 → 大腿 → 三轴髋 → 骨盆框 → 腰 → 躯干/肩框；手部任务载荷沿手指/掌框 → 腕 → 前臂 → 肘 → 上臂 → 肩 → 躯干返回支撑足。已有质量分配及关节树，尚无截面、法兰、轴承载荷、紧固与疲劳证明。

每手三根双关节长指加双关节拇指，均为探索自由度。手掌及手指采用同源凸组合接触网格；抓取闭合、持物和释放尚未完成。主双目及腕部位姿/FOV 只写在物理合同，MJCF 内只有安装标记，没有实现相机、视锥遮挡筛查或感知服务。

## 下一轮入口与放行条件

1. 在现有外包络内比较多轴联合总成、错位安装或远置传动，并用完整模块质量与轴承/制动/冷却空间重新核算。并行比较液压等候选时计全系统，不用干缸重量替代整机。暂不改变原图主体或缩放硬件。
2. 区分腕部接触界面与真正干涉，用同源真实间隙几何重建碰撞；检验髋/膝/折叠轴和手/腿的连续动作。保留本轮失败模型与证据。
3. 闭合结构、质量归属、传动惯量、供电/回馈和持续热工作点，重新做静力范围及自由根、限力拒绝测试。仅在这些门禁通过后提出额定载荷和速度。
4. 身体/接口稳定后接入 Bevy/Rapier 的 50 Hz、20 ms、一次原生积分，先身体、再真实双手取放、持物行走、环境操作和长任务恢复。每层独立验收；GPU PPO 不是本轮退出条件。

复现入口：

```bash
.venv/bin/python scripts/models/build_gorilla_proportion_layout.py
.venv/bin/python scripts/models/build_gorilla_proportion_physics.py
.venv/bin/python scripts/evaluation/evaluate_gorilla_layout.py
.venv/bin/python scripts/models/render_gorilla_proportion_layout.py \
  --screen robots/gorilla_v0_1/evidence/layout_b_screen.json \
  --model robots/gorilla_v0_1/models/full/robot.xml
.venv/bin/python scripts/evaluation/check_gorilla_internal_layout.py
.venv/bin/python scripts/evaluation/summarize_gorilla_checkpoint.py
.venv/bin/python -m pytest -q
```

实际渲染入口依赖本机 Blender 和库路径；参数说明见脚本帮助。入口重新生成同名候选，修改设计前应先保存新实验 ID，不能覆盖已发布候选。
