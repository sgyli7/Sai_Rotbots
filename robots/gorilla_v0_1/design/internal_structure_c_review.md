# Gorilla 内部 C：组件实布置与联合反力诊断

2026-10-03，Asia/Chongqing。**此版保留为拒绝探针，不是完整内部方案，也不请求接受其外观。**它将八个腿部矢状轴的减速器、电磁套件、有限壳体和输出桥实际拆开布置，以排除直接工业组件叠栈。原 AA3 审美基准不变；原外形非改不可尚未得到证明。完整机器人、双手操作、行走及自主复杂 Bevy 目标继续推进。

## 同版源与真实图

[可编辑 JSON](../cad/source/internal_structure_c_scene.json)、[Blender](../cad/source/internal_structure_c.blend)、[GLB](../cad/exports/internal_structure_c/internal_structure_c.glb)、[参数](../configs/internal_structure_c_spec.json)与[渲染绑定](../cad/exports/internal_structure_c/internal_structure_c_render_manifest.json)属于同一候选。scene SHA-256 `e7281d2bf5ece116e6a88b8c8fc5e7c4c16c8e5ab230fb0ad3b9bd8427cac3bc`；spec `ecbe6ad64d8c968f913b14998b69b7f14080d2b950b526813309c34c8f6b873d`。

[正](../images/internal_structure_c_front.png)、[左](../images/internal_structure_c_left.png)、[后](../images/internal_structure_c_rear.png)、[顶](../images/internal_structure_c_top.png)及[拆壳左](../images/internal_structure_c_cutaway_left.png)、[拆壳斜](../images/internal_structure_c_cutaway_threequarter.png)均为实际原生模型 Cycles CPU 渲染，600 px、16 样本，3.04 m 统一正交尺度，未后期修穿透。主线程已实际查看六图。TOP 使用完整中立姿态，不等同 AA3 的展示姿态；本套是空间诊断图，不是改壳审美提案。

542 个分件中保留 C15 的449件，包括全部111件护甲与四主足垫；移除164件旧框架/矢状轴装饰，用18个净承件、24个组件/辅助预留和51个其它模块预留替换。保持的原生网格、变换和材质指纹逐项一致；93件新增几何与 GLB 世界顶点独立比较通过。源、图、导出以及 C15/B 冻结输入的身份检查见[资源记录](../evidence/internal_structure_c_resource_check.json)。检查通过只证明资源一致，不能关闭装配或物理红线。

## 实布置排除什么

髋/膝各四套 RV380N R117＋QTL230-85-N，fold/踝各四套 RV160N R81＋QTL230-65-N。目录主体尺寸、目录质量、Ts/Tc和速度点分别保留，支承质量不重复加旧16只轴承。输入齿轮、保持、驱动、出线/液冷密封及维护只是明确的未合格辅助预留，不能称完整关节。

| 同版项 | 实际结果 | 结论边界 |
|---|---:|---|
| 净名义钢材料 | 464.377 kg | 按有限网格净体积×7850；不含制造/连接资格 |
| 八个减速器＋八个电磁套件 | 330.000 kg | 目录组件质量；不等于整组驱动质量 |
| 八组辅助预留 | 64 / 112 / 176 kg | 无完整接口或能力资格 |
| 51个继承A的其它模块预留 | 706 / 989 / 1431 kg | 包含其它轴、能源/热等；旧粗分配仍须全机重做 |
| 护甲密度假设对应质量 | 115.373 / 177.497 / 248.496 kg | 表面模型皮厚及材料均未制造定案 |
| 足垫密度假设对应质量 | 30.181 / 34.297 / 41.156 kg | 名义接触件，不证明摩擦或局部压强 |
| 条件整机账本 | **1709.931 / 2107.171 / 2691.029 kg** | 非定型净重、目标重量或能力承诺 |
| 四姿态正体积冲突 | **323 / 322 / 322 / 320 对** | 中立、蹲、前向操作、深蹲；范围内未知布尔0，未核线束/工具/连续扫掠 |

数据见[质量与力矩](../evidence/internal_structure_c_screen.json)和[逐对空间拒绝](../evidence/internal_structure_c_space.json)。C 与 B 的角色筛选/组件定义不同，冲突总数不能直接作改善分数。腿轴不是完整多轴总成；肩、腰、髋yaw/roll、踝roll、腕手与其它51预留还未共同匹配。

独立[原生审查](../../../experiments/gorilla_v0_1/internal_structure_c/native_layout_review.md)确认具体断路：RV380 case内半径148.5 mm，所谓连接颈外半径126 mm，**径向相隔22.5 mm**；切除后的父侧框材没有固定侧接合。左右大腿和中腿各3个正体积分量、末腿各2个、骨盆5个、主足座各2个。左主足座的两正材料岛至少相隔57 mm。把材料岛写成同一body不能产生刚性连接；闭合网格不是闭合承力链。这些失败不通过标黄或遮甲处理。

独立[原壳空间审查](../../../experiments/gorilla_v0_1/internal_structure_c/skin_space_review.md)与[截线图](../images/internal_structure_c_skin_sections.png)采用 C15 真实内外皮，不拿 AABB 当空腔。16个肩/膝目录主体探针在0/5 mm余量下均交甲；5 mm余量、104 mm轴长时，原视觉肩轴中心最大离散无交直径约39.2 mm，轴向外移60 mm约176.7 mm；膝中心104/131 mm轴长约144.1/133.8 mm。这些仅是指定轴/长度、离散搜索的材料不交界，不是完整封闭安装容纳证明。旧 `joints` 显示分组坐标与实际 `points_world_m` 肩/膝相差100/321.6 mm，本版只按后者建立临时轴；仍没有稳定 SI 轴合同。

## 同时求接触分配与关节力矩

有限准静力模型以所有真实触地顶点的竖直反力 `f_i≥0` 满足整体力/矩平衡。同一组反力进入八个腿轴的 `τ_j=c_j+K_j f`，最小化最大归一化力矩 `t`。容量比较为 `min(Tgear, ηR×Ts或Tc×factor)`；η=.55/.7/.85与factor=.9/1只是敏感性假设，静态η映射也不是已证保持能力。

任意自由接触极值超载只说明潜在需求，不证明全部受驱动约束的共同分配都不成立。因此本版同时保留自由极值和独立 minimax，避免由过于保守的自由角点盲目放大驱动。

| 姿态 | 自重 | 加100 kg，g×1 | 加100 kg，g×1.5 | 自重＋3000 kg竖直压力 |
|---|---:|---:|---:|---:|
| 中立 | 0.294166 | 0.324812 | 0.487218 | **1.397414** |
| 蹲姿 | 0.280680 | 0.296451 | 0.444677 | 0.674807 |
| 前向操作 | 0.668695 | 0.892465 | **1.338697** | **2.495847** |
| 深蹲拒绝探针 | 0.401936 | 0.444328 | 0.666491 | **1.293565** |

表内数值为最小峰值利用率。大于1由独立dual下界支持在**当前代数模型内排除**；小于1仅证明该模型中有共同反力。100 kg是虚拟双掌负载假设，×1.5是重力敏感性，不是惯性模型或额定负载；3吨外压是单列需求，不能等同搬运能力。四姿态全部未移重心的单左脚法向平衡均拒绝，需要真实移重心与全轴/摩擦/动态验证。

独立[接触复核与dual证书](../../../experiments/gorilla_v0_1/internal_structure_c/contact_lp_review.md)覆盖288解/16 case：216解具有有效primal存在证据，72解具有大于1的dual下界；最大力残差7.28×10⁻¹² N、矩残差1.33×10⁻¹¹ N·m，dual残差/gap≤4.45×10⁻¹⁶。未调用原 evaluator 的LP/结构静力函数。全部18个速度/η/factor情景的容量被齿轮T0截断，数值一致；**这不是18种速度、供电或热能力通过**。求解失败应解释为未知，本批未触发。

机械功率只按 `τ ω` 比较，传动损耗只是η敏感性；零速度不表示零保持发热。电机完整 T–n 曲线、实际母线、20°C安装面实现、回馈、制动和热系统仍开放。参数与边界来源见[紧凑电驱原厂参照](../hardware/compact_electric_component_references.md)及[组件兼容核算](../../../experiments/gorilla_v0_1/internal_structure_c/compatibility_screen.md)。

## 惯量已知项与源的限制

厂家已公布85-N定子7.2 kg、转子2.4 kg、`Jr=.014 kg·m²`；65-N定子5.2 kg、转子1.6 kg、`Jr=.009 kg·m²`。本版16 kg转子全部随parent粗分配，只适用于此处静态质量诊断；builder把输入转子惯量统称未知的文字过宽，以本项明确纠正。轮毂、完整COM、减速器内部转动分配和全组惯量仍未知。

R117/R81下理想反射惯量分别191.646/59.049 kg·m²，仅为运动学推导，不额外添加固定质量。`body_mass_and_inertia_proxies`混用真实净框材料张量与均匀组件包络代理，不能交给 Bevy/WBC 当物理契约。下一候选必须区分定子/相对输入转子和传动关系，不继承本版粗body惯量。

## 下一周期退出条件

主线程保留路线最终决策；包装Agent按已核红线改稿的授权持续有效。下一原生候选要共同组织完整承力壳、支承、驱动、保持、反馈、连接与热，比较关节整组集成和沿厚腿/厚臂分置动力的真实传动；不能仅修22.5 mm空隙或继续保留989 kg粗预留当完整本体。

下一候选单独命名为内部D，不覆盖本C探针。先交一整条连续腿（含髋多轴carrier、复合脚中立压缩路径和卸载折叠）与全机其它模块分配，按同版质量/几何/工作点回算并回看整机。主线程选择优先验证沿腿段分置的线性传动几何，同时保留完整整组/偏置旋转作为比较，尚未锁定电驱或液压能源路线。线性路线必须由实际端点长度、行程、Jacobian及推/拉力闭合，不能把远置动力画成细杆而省略传动/反力路径。

独立[下一布局宏观约束](../../../experiments/gorilla_v0_1/internal_structure_c/c2_macro_constraints.md)保留同一LP反力的逐工况相关性。仅统计12个条件可行案例，髋/膝/fold/踝的所选反力分配需求包络约1.235/2.513/1.428/1.334 kN·m；这不是每轴必要下界或实际额定。初步二维耳轴线在四姿态对应推力峰12.64/46.97/17.07/20.43 kN，眼距变化50.4/81.5/29.4/11.4 mm。杆线未证明任何完整执行器可装入；真实缸/丝杠、耳轴、壳体、行程余量与强度/热占位须在D实际建立，质量/COM变化后重新求共同反力。989 kg其它预留须同步重排，不能用旧账给新传动作固定需求。

仍不能容纳时，再由包装Agent给出实际内皮/外表面差额和新同源四视，保持审美并由用户认可；本探针没有证明AA3必须扩大或改比例。

## 复现与验证

```bash
.venv/bin/python scripts/models/build_gorilla_internal_co_design.py
.venv/bin/python scripts/models/render_gorilla_internal_co_design.py --views front,left,rear,top,cutaway_left,cutaway_threequarter --resolution 600 --samples 16
.venv/bin/python scripts/evaluation/evaluate_gorilla_internal_co_design.py
.venv/bin/python scripts/evaluation/check_gorilla_internal_co_design_resources.py
uv run --no-sync pytest -q
```

实际全量软件回归：**210 passed，83.67 s**。工程脚本使用已安装trimesh/manifold/scipy；Blender来自配置的本地安装。C15/B源及助手脚本保持冻结，所需输入和只读复核的字节副本见[C冻结清单](../../../experiments/gorilla_v0_1/internal_structure_c/snapshot_manifest.json)。只读审查临时路径按清单恢复后可重算；未把版权未明OEM CAD或抓取资料加入仓库。此版不修改共享运行模型、控制时序、observation/action或发布策略，不运行GPU/PPO；CI另行报告。门禁及关闭条件见[C机器可读记录](../evidence/internal_structure_c_gates.json)。
