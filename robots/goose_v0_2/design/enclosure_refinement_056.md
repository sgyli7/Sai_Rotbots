# Goose V0.2：056 连续包覆原生 CAD

本版把已确认的横向芒果机身、完整鹅嘴、S 形颈部和侧置双腿方向落实到原生装配。目标是让实际硬件的外表完整、简洁、连贯；图像由保存后的原生面生成。冻结运行包15单独保留，不把新软罩的估计质量直接混入训练物理。

**当前脚罩的活动资格不通过。** 它的上鞋口跨踝pitch／roll与固定小腿罩，零位相减只形成零位贴合；在原轴系10°／20°姿态已有明确材料穿入证据。现版依赖未经验证的滑移和柔变，不能保证原关节范围自由通过。见[有界动作复核](../evidence/enclosure_refinement_056/ankle_motion/ankle_motion_review_056.json)与[−20°原生动作近景](../images/enclosure_refinement_056/ankle_diagnostic_ar_neg20.png)。正在独立评估分轴随动及隐藏搭接候选；未改公共b5a装配、原关节限位或冻结训练物理。

独立排除所有新脚罩后，左AP原7075承力件与原小腿承力壳在合同+1.1／−1.1 rad端点分别存在约274.576／1155.931 mm³的有效实体交集。合同、XML和原生CAD的零角度相同；XML仅将整机统一抬高5.5 mm，不改变两件相交关系。[四项原硬件检查](../evidence/enclosure_refinement_056/ankle_motion/baseline_endpoint_review_008.json)与[零位依据](../evidence/enclosure_refinement_056/ankle_motion/baseline_zero_reference_check_008.json)另存。指定的AR底板／钢集流件在±0.5 rad均有2.08 mm间隙，不能推广成全部机构通过。后续需同时解决真实承力结构与随动护罩；不得用缩限位、删除碰撞或仅修鞋面来替代。

## 查看与编辑

- [整机单色三视图](../images/enclosure_refinement_056/clay_three_views.png)
- [头颈、踝鞋与后跟细节](../images/enclosure_refinement_056/clay_interface_details.png)
- [双腿内侧、顶部与腹底](../images/enclosure_refinement_056/clay_hidden_surfaces.png)
- [MicroDuck 四套配色](../images/enclosure_refinement_056/four_colorways.png)
- [完整原生 STEP 压缩包](../cad/exports/enclosure_refinement_056/goose_enclosure_refinement_056.step.gz)：解压为同目录的 `.step` 后打开。
- [本轮修改件 STEP](../cad/exports/enclosure_refinement_056/enclosures_056.step)
- [装配身份与逐件来源](../cad/source/enclosure_refinement_056/assembly_manifest.json)
- [验收及证据索引](../evidence/enclosure_refinement_056/delivery_review.json)

完整装配保留真实内部硬件。旧罩件和已取消的独立检修门按清单退役；承力金属没有为画面整洁而隐藏。装配、分件、渲染网格和截图通过内容哈希关联，四套颜色使用同一份几何。

## 本轮改动

主体沿用真实芒果母面，保留上翘收尾。腹底闭合，髋部改为与侧置腿相配的圆形接口；尾部统一为一组双列散热格栅。原独立小门的检修职责移交给完整可拆前壳和尾盖，内部载体与必要接口保留。

颈部由刚性锚罩、连续柔性头颈外皮和内藏轴护口组成。原先分立的头后罩、过渡袖和外露接收唇并为一件连续外皮，取消抬高杯沿和月牙开口。完整相机头壳、鹅嘴、传动和真实轴系保持。内部轴护口保留名义0.8mm净隙；这不是软材料变形或夹伤认证。

四件PA12腿罩保留内部实际承力件，双膝增加独立连续TPU袖。两只鞋各使用完整TPU上罩，鞋头、侧围、后跟和踝部连成同一件，原脚底接触件保留。柔性件的安装归属及估计质量明确记录；它们不是已经标定的刚体或弹性体模型。

实际零位检查同时暴露了旧踝部钢集流件与前承座的实体干涉。前承座上板和真实输出接收件向前调整1.5mm，原脚底固定孔与承力根部保留，采用真实M3x12螺钉和垫圈；这一修改单列质量、材料及有界强度筛查。

原AB6M维护复位件移入尾盖内，以真实夹架固定在原横梁上。开盖后使用直径5mm绝缘维护推杆，核查3mm按压行程与端子弯线空间；没有声称手指可以直接伸入。原独立急停和硬隔离功能保留。原复位整件7g预算只计一次，不把采购件几何体积当成实测质量。

## 接缝与开口的用途

| 位置 | 保留理由 |
|---|---|
| 前壳／尾盖分界及少量固定点 | 拆装、器件维护与电池检修 |
| 双列尾部格栅 | 原散热通路；风量与温升尚须实测 |
| 圆形髋部边界 | 侧置髋轴的相对运动与净空 |
| 颈部接收边、膝袖和鞋口 | 相邻运动体之间的柔性过渡与装配 |
| 黑色脚底边界 | 原地面接触材料与可维护脚底 |

鞋面不增加装饰斜缝，机身不增加翼形涂色、腹部色带或零碎色块。Cream、Graphite、Lavender、Sky延续已有MicroDuck色值，主壳、头壳、深色颈腿、嘴鞋和小面积眼圈按真实完整零件分配表面处理。

## 验收范围与保留边界

交付记录区分原生拓扑、实际零位净空、有限姿态、外观和运行物理。源码成功执行不能代替保存后读回，多视图也不能代替运动检查。具体通过数、输入哈希与拒绝记录以[验收索引](../evidence/enclosure_refinement_056/delivery_review.json)为准。

PA12、TPU、硅胶与铝材质量是几何和设计密度下的估算。罩体壁厚随曲面变化，隐藏压边、粘接、预紧、公差、软罩大变形、疲劳、夹伤、热老化及真实散热仍需要制造和台架确认。踝承座采用7075-T651条件材料基础，名义截面筛查没有代替局部薄区、缺口、疲劳或材料证书。

本轮逐件质量、重心和惯量的设计估算以装配清单的`physical_estimate`为准。曲面薄罩使用按样条区间细分的自适应积分，避免默认体积低估；未改动采购件保留原有物性及整件分配。它们都不是实测值，也不覆盖冻结运行包15。

原金属膝结构在既有极端姿态约103°处仍存在实体干涉，另列原件证据；没有缩小已发布限位来掩盖它。有限罩件扫角通过不表示整机全运动范围放行。

新罩件没有热覆盖冻结15的质量、重心、惯量、碰撞或执行器合同。要把056用于新的物理机体，需要另发有明确质量分配、柔性近似与接触代理的新版本，并保留旧包。当前工作没有恢复PPO、长期训练或定时任务。

## 重建与检查

在仓库根目录运行，原生建模环境固定为cadgen 0.7.21／Python 3.13：

```sh
uvx --no-config --managed-python --python 3.13 --from cadgen==0.7.21 python scripts/cad/assemble_goose_enclosure_refinement_056.py --phase parent-mesh
uvx --no-config --managed-python --python 3.13 --from cadgen==0.7.21 python scripts/cad/assemble_goose_enclosure_refinement_056.py --phase assembly
uvx --no-config --managed-python --python 3.13 --from cadgen==0.7.21 python scripts/diagnostics/check_goose_enclosure_refinement_056.py --scope components
uvx --no-config --managed-python --python 3.13 --from cadgen==0.7.21 python scripts/diagnostics/check_goose_enclosure_refinement_056.py --scope static-neck
uvx --no-config --managed-python --python 3.13 --from cadgen==0.7.21 python scripts/diagnostics/check_goose_enclosure_refinement_056.py --scope interfaces
uvx --no-config --managed-python --python 3.13 --from cadgen==0.7.21 python scripts/diagnostics/verify_goose_enclosure_exchange_056.py
```

父装配从带哈希的原生BREP输入读取；显示缓存由原生面重新网格化，不需要历史052显示网格。生成缓存、原始日志和失败诊断留在`artifacts`，精选证据随本页链接交付。

使用Blender 4.0.2运行[实际渲染入口](../../../scripts/models/render_goose_enclosure_refinement_056.py)，参数`--views oblique front side rear top bottom feet heel neck inboard_left inboard_right --colorway clay`生成单色验收视图，包含两侧腿踝内面；四套配色只改变整件材质。渲染入口会逐一验证原生来源和网格内容哈希。不存在为修图移除硬件、手绘补面或改变物理参数的步骤。
