# Gorilla Appearance C 外观增量记录

2026-10-02（Asia/Chongqing）。前段记录 13:16 冻结的 C9；末段追加 14:48:57 冻结的 C11 和 17:00:10 冻结的 C12，分别保留版本和失败范围。当前决定始终以 [唯一索引](current_decisions.md) 为准。**已交出可编辑真实三维增量，外观仍未通过，尚未达到用户要求的百分百还原。** 物理参数、训练和 Bevy 任务继续后置。

## 唯一原稿与冻结身份

唯一依据为 [用户确认四视图](concepts/aa3/user_confirmed_four_view.jpg)，SHA-256 `079a148340d6bb94ac2bbf5e63851c1c6bbec02acde666047c2d52385ad8bc0a`。其他 AA 图片、被否决的 B 外观及参考机器人均未参与新造型裁决。高度 2.65 m 仍是用户认可的视觉模板假设；原图比例优先，页眉宽 2.587 m 待核。

| 冻结资料 | 身份或入口 |
|---|---|
| 几何源 | [appearance_c_scene.json](../../../experiments/gorilla_v0_1/appearance_c_round_nine/appearance_c_scene.json)，SHA-256 `591996216a4c5e29d0c7c9b3f581b380588d6e7f926af9ae0d6393e65f4eb668` |
| 可编辑模型 | [Blender](../../../experiments/gorilla_v0_1/appearance_c_round_nine/appearance_c.blend)；[GLB](../../../experiments/gorilla_v0_1/appearance_c_round_nine/appearance_c.glb) |
| 四视与局部 | [中立同源四视](../../../experiments/gorilla_v0_1/appearance_c_round_nine/appearance_c_four_view.png)；[胸部](../../../experiments/gorilla_v0_1/appearance_c_round_nine/appearance_c_chest_detail.png)；[掌指](../../../experiments/gorilla_v0_1/appearance_c_round_nine/appearance_c_hand_detail.png)；[腿脚](../../../experiments/gorilla_v0_1/appearance_c_round_nine/appearance_c_leg_detail.png) |
| 复现映射 | [snapshot_manifest.json](../../../experiments/gorilla_v0_1/appearance_c_round_nine/snapshot_manifest.json)，保留原路径与冻结副本的逐项哈希 |
| 渲染与机位 | [渲染记录](../../../experiments/gorilla_v0_1/appearance_c_round_nine/appearance_c_render_manifest.json)；[机位/展示姿态](../../../experiments/gorilla_v0_1/appearance_c_round_nine/appearance_c_camera_manifest.json) |
| 资源检查 | [appearance_c_resource_check.json](../../../experiments/gorilla_v0_1/appearance_c_round_nine/appearance_c_resource_check.json) |

C9 外包络深/宽/高约 1.0677 / 1.9259 / 2.6494 m，只描述该外观候选的控制网格。深度按未校准的原稿 LEFT 前后弧重新解释，不能当作实物测绘尺寸。495 个命名分件及其完整控制网格可以编辑；这些分件数和体积不证明还原度、可制造性、承力或质量。

## 本周期实际修正

主线程逐图查看原稿、四视、胸部/掌指/腿脚近景和额外机位，PM 独立查看原稿及冻结四视。改动都来自真实几何，未用原图贴面、AI 改绘或后期补画。

| 原稿对应区域 | 本周期几何增量 | 仍须实看闭合的差异 |
|---|---|---|
| 连续白胸、冠部及背壳 | 同一闭合胸壳保留前后白甲、蓝侧面；修正重复壳造成的收腰/交叉折面；侧视前后弧按原图采样重新拟合 | 冠部嵌板与长盾的折面流向、TOP 窄尖仍不同；侧蓝面过整齐，原稿外露暗机构不足 |
| 蓝肩、白上臂与厚前臂 | 扫掠肩甲内收尖，正/侧约束的非对称包覆壳；细标与开口细线贴到实际外壳 | 原稿宽面/棱带与曲率仍未完整复原；白上臂开口、肩轴暗腔和蓝肘叉仍偏简化 |
| 双格栅 | 白支座按正/侧轮廓建立真实厚度；金边、黑井和横片按相同曲面分层，修正折扭/遮挡 | 支座上沿仍有凸尖和棱面；原稿嵌入、圆角及胸侧叠层关系继续调整 |
| 腰髋与三段腿 | 窄前黄/后白骨盆、后黄带分件；恢复暗连接；前后黄膝保留底部缺口，侧面从薄悬片改为厚护甲 | 腰/髋外露黑横件仍过规整；膝缺口下暗垫、后盖、甲面分区及连接覆盖不足 |
| 金圈与掌指 | 肘前浅圈、膝/折腿两端斜圈和薄金边；掌甲偏外、三指近节加宽、末端缩短弯入 | 关节叠层仍太统一；掌甲白/暗分区、指根铰帽大小与指尖卷曲还须对齐 |
| 足与检修盖 | 真正分离的趾甲、侧轨、黑底/后跟；背部薄切角蓝盖、上耳、把手及螺钉 | 脚仍像长平台，横宽偏窄、前后层级和斜面不足；背盖嵌入及冠部接缝仍需检查 |

所有“修正”只表示可指认的增量，不表示该部件已经百分百闭合。

## TOP 的实际证据

[标准 TOP](../../../experiments/gorilla_v0_1/appearance_c_round_nine/appearance_c_top.png) 保留整机中立姿态、真实垂直正交投影，双脚可见。它与原稿 TOP 的长白尖、双手可见及脚遮挡关系有明显差异。

[前上方机位](../../../experiments/gorilla_v0_1/appearance_c_round_nine/appearance_c_top_reference.png) 保留所有几何，但脚明显露出。[候选 A](../../../experiments/gorilla_v0_1/appearance_c_round_nine/appearance_c_top_pose_a.png) 使用近垂直透视、双完整手臂绕既有肩点前转 50°，腿脚中立，隐藏零件数为零。双手可见，但胸鼻仍偏宽平且存在脚部白缝；因此 A 也未通过。该展示变换不是已验证的关节范围、稳定姿态或控制合同。

另外的 `top_upper_assembly` 明确隐藏腿脚，仅用于解释原图可能的构图；它不能作为整机还原或自然遮挡证据。下一轮用完整躯干/腿/肩展示 FK 核查不同姿态假设，不能直接平移脚、隐零件或改图片来消除差异。原稿各视的相机与姿态尚未共同标定，TOP 构图解释仍开放。

## 验证边界与复现

实际检查了原始控制网格和导出 GLB：495 个原分件均闭合、绕序一致、正体积；多材质胸壳的 GLB 原语先按原分件组合再检查。文件绑定无错误，导出包络与源最大差约 `6.34e-8 m`。**这些结果只证明同源与网格完整，不能关闭外观门禁或任何物理红线。** C 没有质量、完整惯量、力矩/热/供电能力或碰撞合同。

工作树复现入口（从仓库根目录运行）：

```bash
.venv/bin/python scripts/models/build_gorilla_appearance_reconstruction.py
.venv/bin/python scripts/models/render_gorilla_appearance_reconstruction.py --resolution 1000 --samples 80 --views front,left,rear,top,threequarter,chest_detail,hand_detail,leg_detail,top_reference,top_pose_a,top_upper_assembly,front_reference --tag appearance_c
.venv/bin/python scripts/evaluation/check_gorilla_appearance_reconstruction.py
```

工作树后续会继续迭代。要复现本节的 C9，先在独立副本按冻结映射恢复原路径和哈希；冻结的 `.py.txt` 是原脚本字节副本，不应直接在快照目录运行。已冻结 C1/C3/C4/C5/C7 等精选候选保留各自身份；未封存的中间预览不声称可完整复现。

## C9 时的下一周期退出条件（历史）

13:20–15:20 继续外观：先修复原稿脚趾/侧轨/前护/高后跟及掌指分区，再修胸侧、腰髋、膝暗垫和壳面棱带，最后验证完整展示 FK 与 TOP 机位。脚底/甲面修复不能靠缩放踝轴承来凑宽度。至少留 24 分钟合并、重渲、逐图比对及记录剩余缺口；还有可指认差异就继续外观周期。

完整可信本体、双足/双手与自主复杂 Bevy 目标保持活动，但尚未恢复执行。当前没有 GPU/PPO 训练。

## C11：护壳构成与腿脚增量

2026-10-02 14:48:57 已冻结 [C11 输入、脚本与实图映射](../../../experiments/gorilla_v0_1/appearance_c_round_eleven/snapshot_manifest.json)，共 30 副本。几何源 SHA-256 `c0c5d8ad5553f3f22aba4b73f9977aa287e2cdb86d988be7af4a9c5307779e8c`；[Blender](../../../experiments/gorilla_v0_1/appearance_c_round_eleven/appearance_c.blend)、[GLB](../../../experiments/gorilla_v0_1/appearance_c_round_eleven/appearance_c.glb)、[完整标准四视](../../../experiments/gorilla_v0_1/appearance_c_round_eleven/appearance_c_four_view.png)及 12 机位记录属于同一源。外包络深/宽/高约 1.0677 / 1.9259 / 2.6494 m，仍是未标定的外观候选。

主线程实看标准四视、腿脚近景以及[等高正面](../images/appearance_c_round_eleven_front_comparison.png)、[侧面](../images/appearance_c_round_eleven_left_comparison.png)、[后面](../images/appearance_c_round_eleven_rear_comparison.png)。比较图只将原稿裁区等比缩放，并排显示原样完整中立正交渲染；没有修形、改色或隐藏。生成方法与身份在[比较记录](../images/appearance_c_round_eleven_comparison_manifest.json)，复现入口已作为脚本副本封存。

| 实际构成增量 | 整机实看仍失败的关系 |
|---|---|
| 冠—前盾—短背甲、蓝肩鞍与斜前翼、白肩弧盾改为薄皮/内皮/开口/翻边；移除满填彩色体和黑侧墙 | 上躯侧面大空腔及外伸后沿不贴原稿，冠部/前盾折面与蓝肩流向仍不同；白肩仍显凸块，机芯紧凑覆盖未恢复 |
| 前臂、上腿和中腿使用不同的宽面/棱带；保持完整 FRONT 高度，独立约束白肩可见区域 | 前后甲面色块与遮挡仍不齐；原稿肩肘、髋部层叠机构不足，不能靠多加细线解决 |
| 腿桥按不同端面跨度重建，膝—折腿—踝之间换为厚弧承件，添上腿斜暗壳和黄膝下小暗垫 | SIDE 膝下仍像长直颈，中腿后蓝盖与承件浮离，护甲到关节座的连续包覆仍不足；加厚没有证明承力 |
| 鞋趾、侧轨、前沿、踝盖改为有内腔及开口的独立护盖，底架和高后跟分开 | 鞋仍偏方，侧轨显墙体、脚跟/脚背层次与原稿不同。材料体闭合或有空腔不能证明形状已正确 |
| 掌指原 C10 几何完整保留 | SIDE 掌与指护几乎缺席；须先查完整手臂/掌的方向、深度与遮挡关系，再扣细节。不能让手遮住腿缺陷来冒充腿已修好 |

[实际资源检查](../../../experiments/gorilla_v0_1/appearance_c_round_eleven/appearance_c_resource_check.json)通过：478 个源分件和 478 个 GLB 原语闭合、绕序一致、正体积；绑定无误，导出与源最大包络差 `6.334e-8 m`。护甲皮厚是外观构成参数，未证明偏移自交、制造、材料或强度。**外观和物理接受标志均为 false；M1 仍失败。** 用户补充的数吨级承压是结构要求，单/双腿载荷、动载、截面、轴承与连接尚未核算。双格栅仍未闭合真实热容量及流路，不能称功能完成。

下一周期 15:20–17:20 先修胸肩与机芯、完整手臂/掌侧视关系、Z 腿—护盖—低脚连续构成，按总—分—总回到整机复核。16:56 起至少留 24 分钟冻结、重渲、看图及记录失败；掌指微细、TOP/FK、驱动/物理研究和 PPO 继续后置。完整目标活动，不因本轮有增量而放行。

新增比较复现命令（先按冻结映射恢复源/实图身份）：

```bash
.venv/bin/python scripts/evaluation/compare_gorilla_appearance_views.py --snapshot experiments/gorilla_v0_1/appearance_c_round_eleven --tag appearance_c_round_eleven
```

C11 后归因补充：侧视 `u≈963–989、v≈366–409` 的长白黑直条主要来自 edge-on 掌护板、掌载体与腕短接。白掌板 FRONT 投影约 31 px，SIDE 仅约 5 px，三指近节也在 X 上重叠；不能将此条全部当作腿部缺件。真实膝桥约在 `u970–1003、v390–431`，后弯承件约在 `v456–496`，仍需分别恢复其护甲覆盖。后蓝盖 `v437–477` 的上半区没有相应承件搭接，取主蓝壳端作锚区遗漏了这个独立护盖。下一增量据此修实际完整掌包姿态、腕连接和后盖承件锚定；外观/承力接受状态保持不变。

## C12：整机三组关系增量，仍未放行

2026-10-02 17:00:10 冻结 [30 项输入与产物映射](../../../experiments/gorilla_v0_1/appearance_c_round_twelve/snapshot_manifest.json)。源 SHA-256 `bcc54faec88c928725089f3d068781bed1c87f8da86ac7973e1b46281e358137`；[Blender](../../../experiments/gorilla_v0_1/appearance_c_round_twelve/appearance_c.blend)、[GLB](../../../experiments/gorilla_v0_1/appearance_c_round_twelve/appearance_c.glb)、[标准四视](../../../experiments/gorilla_v0_1/appearance_c_round_twelve/appearance_c_four_view.png)及 12 机位实图属于同一源。外包络深/宽/高约 1.0685 / 1.9259 / 2.6494 m，深度仍是未校准的外观重建值。

主线程实际查看冻结四视、[胸部](../../../experiments/gorilla_v0_1/appearance_c_round_twelve/appearance_c_chest_detail.png)、[掌指](../../../experiments/gorilla_v0_1/appearance_c_round_twelve/appearance_c_hand_detail.png)、[腿脚](../../../experiments/gorilla_v0_1/appearance_c_round_twelve/appearance_c_leg_detail.png)、斜视与 TOP 姿态诊断，以及[等高正面](../images/appearance_c_round_twelve_front_comparison.png)、[侧面](../images/appearance_c_round_twelve_left_comparison.png)、[后面](../images/appearance_c_round_twelve_rear_comparison.png)。比较图按统一比例缩放原稿裁区；完整模型渲染保持原样，未隐藏、改绘或拉宽，[比较记录](../images/appearance_c_round_twelve_comparison_manifest.json)绑定身份。

| 本轮完整装配增量 | 实看尚未闭合的关系 |
|---|---|
| 补薄冠侧翻边与胸壳侧返回；按原稿可见边修正正面白盾，避免盖住蓝肩内凹区；中央长盾面与侧前沿分开。蓝肩斜折面、白肩宽面使用原稿可见折线约束 | 白肩 SIDE 仍是尖帽而非宽开放弧；蓝鞍轮廓及下面暗轴座、上躯侧空腔和后沿不贴原稿。蓝颊像宽台面，腰髋护盖与外露横轴过疏 |
| 完整掌包保留原倾斜后作镜像转向，调整宽度及指根间距，并重建腕短接；正面掌宽约保留，侧面白掌与三指重新可见 | 掌与原稿分区、指形和朝向仍有差异；这是展示几何候选，不是已核实腕轴、限位或关节合同，不能靠掌遮挡把腿宣称修好 |
| 后弯承件上区锚到独立后蓝盖，内收耳沿；脚侧轨重做低平台轮廓和空腔，暗后跟降低并保留独立高层级，背面凹位落到实际跟壁 | 中腿主甲—后盖仍显分离，踝部蓝/白盖缺连续包覆；足前后斜面、横宽与侧轨终止关系仍不同。投影重叠不证明实体搭接、承力或强度 |

首次完整近景暴露白盾顶部两处尖折，来自主面宽度在两个分区行间突变；修成连续过渡后重新输出全部最终视图。旧失败近景与相应导出/检查保存在 `artifacts/gorilla_v0_1/appearance_c_crown_turn_failure/`，是部分失败诊断，未声称完整可编辑冻结候选。

[最终资源检查](../../../experiments/gorilla_v0_1/appearance_c_round_twelve/appearance_c_resource_check.json)通过：480 源分件与 480 导出原语闭合、绕序一致、正体积；绑定错误为空，导出包络最大差 `6.334e-8 m`。渲染记录 SHA-256 `3cd37550bb50ce84c15fae5284599d84bff706b2f42a34332123aeecfbe88583`，GLB SHA-256 `bf9e0f2cc036ba1ca897d3d5c26b97e7e31ed0f5a6563f74cb45c1b5bef8690b`。**文件完整性通过，外观接受与物理接受均为 false。** 薄壳内外皮不证明无自交或可制造，几何叠合不证明关节连接。双格栅仍有封闭背板，真实开口/密封风路及热能力未完成；数吨支撑只是当前结构要求，质量、截面、材料、连接、轴承、动载和驱动尚待同版核算。C 未赋予物理合同。

仅补上肩暗弧座的受限 C13 临时草稿已实看失败：弧座附着于当前错误的尖白帽母形，正面还出现阶梯暗条，不合入受控模型。下一周期先整体重建白肩宽面、侧面开放弧、蓝鞍覆盖与暗轴座；腿甲—承件—踝脚也以整体关系复核，避免继续局部补片。TOP/FK 搜索、微小装饰、物理参数、训练继续后置。完整机器人与复杂 Bevy 目标保持活动。

```bash
.venv/bin/python scripts/evaluation/compare_gorilla_appearance_views.py --snapshot experiments/gorilla_v0_1/appearance_c_round_twelve --tag appearance_c_round_twelve
```

## C13 完整装配增量与背部控制屏

封存时间：`2026-10-02T18:41:59+08:00`。本轮提前交出可复查候选，仍未关闭 M1；完整工程目标继续活动。

- [冻结清单](../../../experiments/gorilla_v0_1/appearance_c_round_thirteen/snapshot_manifest.json)保存 37 个字节一致副本，源 SHA-256 `d231d7366fc03c3f3b1cc3f20a4835b314f72f158be7aa28bd0d436481088a78`。同版 [Blender](../../../experiments/gorilla_v0_1/appearance_c_round_thirteen/appearance_c.blend)、[GLB](../../../experiments/gorilla_v0_1/appearance_c_round_thirteen/appearance_c.glb)、[参数源](../../../experiments/gorilla_v0_1/appearance_c_round_thirteen/appearance_c_scene.json)、原稿/输入/构建与渲染脚本及 13 机位全部绑定；1000 px、80 样本、Cycles CPU。标准四视完整中立，无隐藏件或装配隔离。
- [资源检查](../../../experiments/gorilla_v0_1/appearance_c_round_thirteen/appearance_c_resource_check.json)记录 535 源分件/535 导出原语全部闭合、绕序一致、正体积，绑定错误为空，最大包络差 `6.33404542e-08 m`；这不证明自交、间隙、碰撞、强度、质量、动力学或外观通过。外包络深/宽/高仍约 1.06852/1.92587/2.64938 m。
- 主线程实际查看[同版四视](../../../experiments/gorilla_v0_1/appearance_c_round_thirteen/appearance_c_four_view.png)、[正面](../images/appearance_c_round_thirteen_front_comparison.png)、[侧面](../images/appearance_c_round_thirteen_left_comparison.png)、[后面](../images/appearance_c_round_thirteen_rear_comparison.png)等高对照，以及胸、腿、手、斜视与背屏近景。原稿相机/姿态未标定；额外 TOP 参考机位、上躯隔离、展示姿态不替代标准全机四视，也没有数值还原率结论。

肩装配由七截面的尖折肩鞍/白帽改为原稿 SIDE 轮廓约束的开放蓝弧、白肩宽袖和短暗弧座，并补宽后蓝护面与薄上返边；前蓝斜折面保留。胸颊去掉旧粗轮廓形成的宽台面，白髋护盖按原稿斜面与侧返边分别建模，后腰补短白连接，中央暗骨盆载体内收。原稿侧机构当前仅是分开的短壳层候选，仍偏孤立；不是器件型号或承力链。

腿脚合入已实际三视审查的有界 revision，**没有采用把主蓝甲后点推到 u1030 的失败大蓝墙**。独立后蓝盖/后护皮、下段蓝桥、白斜踝盖与厚弯承件各自分开；主蓝甲仅新增原 SIDE 轮廓内的后角返边，不改变轴点/整机包络。斜鞋顶为薄屋面加到低侧轨的薄侧皮，脚后暗跟独立，踝下有短暗座和低底连接。SIDE 中腿/后盖搭接与踝脚层级仍不够原稿，REAR 蓝桥阶梯及 FRONT 鞋角仍不同，全部保持失败含义。数吨承压是用户要求；当前厚外形、闭合网格和开口空间均不是载荷证据。

用户新增的[背部中央控制屏](../../../experiments/gorilla_v0_1/appearance_c_round_thirteen/appearance_c_rear_panel_detail.png)使用原蓝板的板位、切角外轮廓、蓝框、四角固定点和顶部耳片。新增环形密封边、独立深蓝玻璃、约 240×312 mm 的显示窗口与 26 mm 深模组候选，背甲有实际安装开孔；框与背甲没有整片封板横穿模组空间。原顶部黑扣保留，原生网格文字方向/遮挡经实渲修正。状态、任务、本地控制均为**静态界面布局**，没有实时数据或运动控制接通的声明。供应型号/定制可标黄，模块质量、功耗、热、安装净隙、密封、线束和运行状态权限仍待后续物理/接口核查，不能通过标黄放行。

双散热口从三层满板改成有实际开孔的白/金环框、开放黑喉道及带侧出口的候选转流腔。首次近景实看发现 `blue_chest_cheek_side_return` 穿入口；[旧原生源](../../../experiments/gorilla_v0_1/appearance_c_round_thirteen/intake_before_scene.json)、[旧报告](../../../experiments/gorilla_v0_1/appearance_c_round_thirteen/intake_before_report.json)和[失败近景](../../../experiments/gorilla_v0_1/appearance_c_round_thirteen/intake_before_chest_detail.png)保留。修复将真实蓝侧返边绕到入口外侧并在口底以下过渡。

[本版原生入口检查](../../../experiments/gorilla_v0_1/appearance_c_round_thirteen/appearance_c_intake_clearance.json)直接逐三角查询完整模型：0.5 px 网格、0.7 px 口边界余量，每侧 2008 条实际格栅间隙射线在入口前 50 mm 至入口后 72 mm 中没有蓝白护甲命中。合法候选转流腔后壁在更深约 87.8–146.3 mm，分别报告。[采样图](../../../experiments/gorilla_v0_1/appearance_c_round_thirteen/intake_ray_map.png)是诊断图，不是模型渲染或空气流场。右侧仍按登记左轮廓镜像；独立原 JPG 点 `(379,204)` 位于当前镜像口之外，依旧命中金边/随后蓝主甲，属于原右轮廓还原缺口。该检查不证明全口无小尺度阻挡、倒角后间隙、风阻、换热、风机能力、侧出口连续性或独立排风；出口目前通往未核实机舱，完整散热红线仍开放。

下一完整装配优先：后上臂白护层—暗承件—肩轴座的覆盖，胸侧短机构层及髋横轴的紧凑连接；同时恢复中腿/踝白蓝盖与低脚的原稿搭接。细缝/螺栓/背屏 UI 微调、TOP/FK 搜索、物理架构和训练后置。不能再只补一块暗片、轴环或增大彩色体积。

复现入口（使用工作树时须核对冻结输入映射）：

```bash
.venv/bin/python scripts/models/build_gorilla_appearance_reconstruction.py
.venv/bin/python scripts/models/render_gorilla_appearance_reconstruction.py --resolution 1000 --samples 80 --views front,left,rear,top,threequarter,chest_detail,hand_detail,leg_detail,top_reference,top_pose_a,top_upper_assembly,front_reference,rear_panel_detail --tag appearance_c
.venv/bin/python scripts/evaluation/check_gorilla_appearance_reconstruction.py
.venv/bin/python scripts/evaluation/check_gorilla_intake_clearance.py
.venv/bin/python scripts/evaluation/compare_gorilla_appearance_views.py --snapshot experiments/gorilla_v0_1/appearance_c_round_thirteen --tag appearance_c_round_thirteen
```


## C14：内部主结构与主体受力候选

用户要求先搭主结构和主体物理受力模型，调整了此前外观完成后才恢复物理的顺序。2026-10-02T19:53:31+08:00 已冻结 [46 项输入与产物](../../../experiments/gorilla_v0_1/appearance_c_round_fourteen/snapshot_manifest.json)。源 SHA-256 `624e7a8974a8de0abf0865ad35bcfa6ee06a089de27f80627f945296cbc96f85`；[Blender](../../../experiments/gorilla_v0_1/appearance_c_round_fourteen/appearance_c.blend)、[GLB](../../../experiments/gorilla_v0_1/appearance_c_round_fourteen/appearance_c.glb)及[完整四视](../../../experiments/gorilla_v0_1/appearance_c_round_fourteen/appearance_c_four_view.png)属于同一源。外包络深/宽/高仍约 1.0685 / 1.9259 / 2.6494 m，原图比例优先、深度未标定。

本轮建立中央腰座/脊梁、肩/骨盆横梁、弯折臂梁、三段 Z 腿、空心轴座、踝和足骨架；42 梁均有有限壁厚、内孔、中心线和同源截面记录，8 框架侧轴座单独计条件毛料质量。蓝白甲保持独立薄壳，白上臂中段包覆及胸侧暗壳按原稿可见区收拢。可见梁与轴座相交处尚未装配修整，也没有连接刚度/强度证明。

[拆壳斜视](../../../experiments/gorilla_v0_1/appearance_c_round_fourteen/appearance_c_structure_threequarter.png)、[正面](../../../experiments/gorilla_v0_1/appearance_c_round_fourteen/appearance_c_structure_front.png)和[侧面](../../../experiments/gorilla_v0_1/appearance_c_round_fourteen/appearance_c_structure_left.png)展示实际内部候选，不替代整机外观证据；隐藏护盖名单明确记录。标准四视仍全部中立、无隐藏。16 个机位均从实际几何输出，没有贴图/改绘；Blender 已完成导出、全部机位和退出，但外层包装被终止，依据新鲜图像、完整机位、导出源哈希及日志执行了原渲染脚本未改动的包装段，记录在[包装恢复证据](../../../experiments/gorilla_v0_1/appearance_c_round_fourteen/wrapper_recovery.json)。

主线程实看完整四视、拆壳图及[正](../images/appearance_c_round_fourteen_front_comparison.png)/[侧](../images/appearance_c_round_fourteen_left_comparison.png)/[后](../images/appearance_c_round_fourteen_rear_comparison.png)等高对照。后上臂长撑及胸侧孤立圆层/过多镂空有所改善；冠肩折面、正面腰髋/肘组、中腿盖搭接、踝脚层级与原稿仍不同。粗梁的出现不自动关闭这些差异；**外观仍未通过**，TOP 也未共同标定。

[受力依据](structure_c14_basis.md)及[同版 SI 记录](../../../experiments/gorilla_v0_1/appearance_c_round_fourteen/structure_c14_screen.json)覆盖 181 条条件质量记录、真实脚底单向反力、关节六维载荷和名义梁应力。条件毛料与未选组件预留总质量约 1.15 / 1.42 / 1.79 吨，轴座毛料约 258 kg，是需要收敛的自重风险。每个双足工况求全部 160 组基本可行极端反力；10 个双足竖向准静力工况可平衡，两个中立单左脚工况被拒绝，没有补根部支撑或地面力矩。

42 梁中 30 件有有限截面筛查、6 护盖支撑及 6 分叉脚底梁未分析。中值自重加上躯 3 吨等效压力时，已分析截面最不利名义等效应力约 109.0 MPa；全部载荷乘 1.5 的敏感性工况约 163.5 MPa。它们只达到当前材料假设下的梁理论目标，不能证明连接、轴座、足底、屈曲/疲劳、持续驱动或动态站立。数吨压力也不是双手搬运评级；关节六维力矩范数不是某一电机的轴向额定力矩。

[源/导出检查](../../../experiments/gorilla_v0_1/appearance_c_round_fourteen/appearance_c_resource_check.json)确认 545 原生件及对应导出均闭合、绕序一致、正体积，文件绑定无错，包络误差约 6.334×10⁻⁸ m。独立复核重新积分质量/截面、求接地 LP 极值、检查相邻短梁载荷连续及力矩/应力比例，未发现新的阻断性计算缺陷；8 项数学及拒绝测试通过。这些检查均不证明装配间隙、实际连接或承载能力。双格栅的同版 2008/侧采样仍仅验证蓝白甲入口遮挡，热和全流路保持开放。

[C14 红黄线及关闭条件](../../../experiments/gorilla_v0_1/appearance_c_round_fourteen/structure_c14_gates.json)不继承 B 的证据；所有阶段放行、整机强度、稳定物理合同和仿真/实物接受均为 false。下一周期优先真实弯接/轴座/脚底装配及其载荷传递、原稿甲壳和运动空间，再闭合组件净质量与驱动轴载荷。微缝/背屏 UI/训练继续后置，完整双足/双手/自主 Bevy 目标保持活动。


## C15：正式内部设计前的复合脚基底

[阶段说明](appearance_c15_stage.md)及[31 项冻结](../../../experiments/gorilla_v0_1/appearance_c_round_fifteen/snapshot_manifest.json)保存同源 613 件、完整四视与三张脚部近景。主线程已实看全部交付图和[正](../images/appearance_c_round_fifteen_front_comparison.png)/[侧](../images/appearance_c_round_fifteen_left_comparison.png)/[后](../images/appearance_c_round_fifteen_rear_comparison.png)等高原稿对照。原板脚改为低前掌、固定足弓和独立高跟，卸载时前后段各自旋转且锁舌退出；不再有跨段整板。完整包络未变，冠肩、正面肘/腰髋、中腿搭接及脚细节仍有差异，**外观未放行**。TOP 仍未与原稿共同标定。

[原生脚检查](../../../experiments/gorilla_v0_1/appearance_c_round_fifteen/composite_foot_c15_screen.json)仅验证闭合/绕序及中立、卸载端姿态的跨组几何关系；止挡贴面明确分类，不代表有效机械连接。固定侧止挡安装仍有 35 mm 间隔，其承力、锁止、失电保持和运动接触均开放。C14 整板脚计算保留为历史，不适用于 C15。当前按用户顺序保存阶段 commit，再开始真实内部占位与宏观物理，后续再回外壳细化。
