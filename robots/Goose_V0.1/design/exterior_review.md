# Goose 外形核查：游戏鹅辨识度与工程边界

> 2026-09-30：上一卵形方案已被用户否决。当前审查[肩胸与收尾曲面候选](sculpted_exterior_review.md)，外观与工程交付均未放行。

> 2026-09-29 按用户五点反馈新增[流线型外观与器件布置候选](streamlined_exterior_review.md)。用户已授权不再逐项复刻旧图；外观仍待本轮审查，硬件布置尚非制造或物理放行。

> 2026-09-29 新增[半小时 R2 四边面重建候选](r2_quad_rebuild_review.md)：闭嘴／张嘴源文件的逐件四边面与闭合检查通过；外观仍待审查，制造、同版动力学和整机交付继续未通过。下文 v95/RC2 均为历史候选。


原交接包早已保存用户选定的 [B 步行鹅外形](concepts/history/walker_b_selected_reference.png)、[整机外观板](concepts/history/walker_r1/goose_v0.1_walker_concept.png)和[R2 尖嘴外观／并行开合板](concepts/beak_r2_review_board.png)。[交接记录](conversation_handoff.md)明确写了“B 为外形基线”；此前工程推进没有执行这一约束，是本轮外形偏离的原因。用户现已明确否决当前实物 CAD，并再次指定**以 R2 收尖鹅嘴为唯一嘴形基线**。**RC2 不再是可继续微调后放行的外观基线；先按原图重做整体轮廓，再在同一模型上审运动力学，最后处理细节。**早期宽扁鸭嘴及当前约 30 mm 可见短喙都不再是外观选项。图上的推测尺寸、自由度、载荷或电池时间仍不能当实测规格。

用户本轮再次给出的[闭嘴尖嘴参考](concepts/r2_pointed_beak_closed_reference.jpg)和[平行张开近景参考](concepts/r2_pointed_beak_parallel_open_reference.jpg)已原样保存。第二张明确显示厚度较薄但有实体体积的下喙、嘴内黑色接触垫及集中在根部的连杆；不能只根据运动示意图把下喙画成一条线。

实际模型的 [站立侧视](../images/rc2_home_side.png)、[站立斜视](../images/rc2_home_three_quarter.png) 和 [地面叼取侧视](../images/rc2_ground_grasp_side.png) 均来自同一份 MJCF 与 CAD 网格，模型 SHA-256 为 `07d4209a5a7b9322a04b9cdb62694a69cf35c97716c262909d21f039599c4cb0`。它们是当前几何，不是最终效果图。

**外形门槛未通过。** 白色椭圆躯干、橙嘴、宽脚、长颈和翼形检修门形成了基本识别，但外露叉板和电机占据了大部分颈腿轮廓；上喙可见长度仅约 30 mm，而头罩长约 104 mm。实物按现版打印会更像裸露机构，离 [goose.game](https://goose.game/) 的简洁大鹅还有明显距离。不能以早期 [概念图](concepts/index.html) 代替这项判断。

与用户参考板并排核对，当前问题是轮廓级而非配色级：机身显得过小且过于独立；颈与腿像未罩住的直线支架；头部机械体量相对嘴过重，橙色喙过短；脚是方盒而不是参考图中低矮、圆润的宽脚。只换颜色、润色渲染或加写实羽毛线条无法修复。下一版需要先用实际电机/相机/线束/关节包络建立侧、正、斜三视整体比例，再分出承力件与轻量可拆外饰，并让嘴的功能长度、机身连续面与手动翼门缝线一起成立。

独立的[外观样机脚本](../../../scripts/cad/build_goose_exterior_study.py)现可生成闭合 80 件与平行张开 94 件视觉实体的实际 3D 外观几何。可审查文件为[闭嘴 STEP](../cad/exports/goose_r2_exterior_study_closed.step)、[张嘴 STEP](../cad/exports/goose_r2_exterior_study_open.step)、[闭嘴斜视](../images/r2_exterior_study_closed_three_quarter.png)、[闭嘴侧视](../images/r2_exterior_study_closed_side.png)、[闭嘴正视](../images/r2_exterior_study_closed_front.png)、[闭嘴俯视](../images/r2_exterior_study_closed_top.png)、[闭嘴嘴部近景](../images/r2_exterior_study_closed_beak_detail.png)、[张嘴斜视](../images/r2_exterior_study_open_three_quarter.png)和[张嘴嘴部近景](../images/r2_exterior_study_open_beak_detail.png)。[样机清单](../cad/exports/goose_r2_exterior_study_manifest.json)记录来源哈希并明确 `appearance_review_pass=false`。此版的颈部先后折再前伸，腿部形成折线，尖嘴采用扁平圆角截面并保留较厚根部与圆钝尖端，翼形检修门仅以抽象的大面积轮廓表示。

本版针对前伸比例做了整体修正：颈部肘点后移，头部与尖嘴一起后收，喙尖相对躯干前缘的视觉前伸量约从 260 mm 降到 150 mm。橙色调也按用户参考板向暖橙收敛。这些数值是草模坐标的派生量，不是制造定尺或已验证的负载改善。

这仍是**未通过的外观草模**：虽然 B 步行鹅的圆机身、双腿、宽脚、长颈和 R2 收尖上下喙已在同一 3D 装配中可见，头壳、颈腿外饰及机身过渡仍比原图生硬，表面分件和材料质感不足以称为复刻。当前视觉包络约为 `500 × 268 × 781 mm`，只是为了匹配概念图轮廓的临时比例，**不能当整机定尺或外购零件适配结论**。下喙 30 mm 平行开口是视觉状态，侧连杆只表达已选拓扑；其位置、承力、装配及电机包络未验证。翼门现在只画了关闭面与缝线，尚无真实门铰链和锁扣。不得把外观样机的 STEP 当打印件或把它接入旧 RC2 动力学并声称任务通过。

**初步可落地筛查只用于发现风险。** 旧 RC2 物理模型总质量 `3.684 kg` 和现行外观草模不是同一质量模型，不能继承其站立或叼拖结论。[ROBOTIS 官方](https://emanual.robotis.com/docs/en/dxl/x/xm430-w350/)给出的 `4.1 N·m @ 12 V` 是瞬时堵转值，不是连续额定值；[旧规格](../configs/robot_spec.json)中的 `0.82 N·m` 只作初筛。现版的髋关节与躯干视觉中心均约 `x=-10 mm`、闭嘴喙尖约 `x=315 mm`，这些仍不是整机重心。[脚型与质量／动力学复核](stance_layout_review.md)用新外形的坐标、厂商电机质量和多个壳体壁厚假设重新核算，已经发现现有限力候选在站立与低头姿态均未通过，不得把图像上双脚着地当成可落地证明。

粗包络比对采用[XM430 官方本体深 34 mm](https://emanual.robotis.com/docs/en/dxl/x/xm430-w350/)和[XM540 官方本体深 44 mm](https://emanual.robotis.com/docs/en/dxl/x/xm540-w270/)，每侧暂留 3 mm 壳壁、合计 2 mm 装配间隙。所需外包深度分别至少为 `42 mm`、`52 mm`。因此视觉草模的腿上、腿下段外饰深度已改为 `42 mm`，颈下段改为 `52 mm`，颈上段为 `44 mm`；关节盖也相应加宽。**这些仍是实心视觉体，未开空腔，也未摆入电机 STEP；等于名义外包深度不等于可装配。** 圆角、输出盘/idler、支架、线束折弯及全行程扫掠都会进一步吃掉净空，必须在承力 CAD 中逐一验证。

[外观视野筛查](../evidence/exterior_vision_screen.json)的**站姿**射线从正面视觉镜片前方 `(0.236, 0, 0.737) m` 指向地面：`x=0.35、0.40、0.50、0.75、1.00 m` 的中心线先命中上喙或鼻孔装饰，到 `x=1.50 m` 才先命中地面。这个结果不能推出运动中的头部也看不到近处。后续用同一闭嘴头嘴网格绕视觉后枢轴做 1° 间隔的刚体俯仰筛查；按候选 [Waveshare 24710 原厂给出的 95° 水平／70° 垂直视场](https://www.waveshare.com/product/modules/ov5693-5mp-usb-camera-a.htm)，并暂用旧 RC2 的镜头相对头壳下俯 35° 假设，地面 `x=0.35 m` 在头部再下俯约 `40–69°` 时有未被头嘴遮挡、且落在名义视场内的射线；`x=0.50 m` 对应约 `30–60°`。镜头不预俯的替代假设也存在可见角区。**所以目前不以站姿遮挡为由增加或更换相机。**

这个纯几何可见性结果仍未验证镜头与面板的真实安装、焦距、畸变、亮度、头颈电机角度、颈罩/机身碰撞或行走时稳定跟踪。40° 头部独自俯视时，草模喙尖仍约在地面上方 0.54 m；看见近处与弯颈叼到地面是两个独立门槛。侧移 35 mm 的孔位仅保留为未批准的诊断备选。指定物自主叼取/拖拽放行前，须用同一外形在实际低头姿态中完成视野、可达与无自碰撞验证，不能沿用旧 RC2 的相机检查。

下一版外观先解决三个主轮廓，不投入羽毛刻线或焊点级细节：

1. 用可拆的轻量颈部外饰连续包住两段杆件，在每个关节预留全运动角度、线束弯曲与检修空间；不得把饰件当承力件。修改质量、惯量后重跑双足和叼拖试验。
2. 将上下喙作为一对重新定比例，形成从头部自然伸出的扁橙嘴。抓取接触区仍在嘴内，重新核算杠杆力臂和 50 g 夹取，不接受单纯延长无功能装饰尖端。
3. 用简洁的腿部遮罩和更柔和的宽脚外缘削弱裸露叉板感；脚掌接地包络须在定尺后按步行净空与防滑材料重算，不能直接沿用旧 RC2 的 `120 × 70 mm`。两侧翼形检修门继续手动开合、轮廓抽象，不能画成写实羽毛。

放行时同时看同一版 CAD 渲染的站立、低头叼取和拖拽姿态，做零件扫掠、质量/力矩、相机视野、嘴内接触和 256 mm 打印包络复查。审美目标与可落地性必须在同一版模型上成立；本轮不以修图或概念图宣称外形已交付。

## 前一轮高颈比例候选仍未过外观门槛

为纠正前一轮嘴过长、头过小，把 R2 喙长系数从 `1.60` 收回 `1.20`，头壳由原草模放大至 `1.15`；髋与机身中心继续对齐，并保留后延 50 mm 的低矮脚底。当前[侧视](../images/r2_proportion_side_candidate.png)、[斜视](../images/r2_proportion_three_quarter_candidate.png)、[平行张嘴](../images/r2_proportion_open_beak_candidate.png)、[视觉 STEP](../cad/exports/goose_r2_proportion_visual_candidate.step)与[闭嘴清单](../cad/exports/goose_r2_proportion_visual_candidate_manifest.json)提供同一几何的复核入口；清单 `appearance_review_pass=false`。视觉包络约 `525 × 268 × 788 mm`，不是用户确认的定尺。

与[原 B／R2 板](concepts/r2_pointed_beak_closed_reference.jpg)直接比，比例比前一轮接近，但头罩仍偏方盒、颈段过于直筒、机身与髋腿转接生硬，嘴部上下缘和鞋面也缺少原图那种收敛、圆润的一体感。**我不把这张渲染称为复刻，也不把视觉 STEP 称为可打印装配文件。**保持用户确认的收尖上喙、平行下喙、白色圆机身与抽象手动翼门方向；下一次外形修改应优先修正这些大轮廓，再做外饰细缝和表面质感。

同一候选的[脚底、质量、低头与单脚试验](stance_layout_review.md)已同步核算，结果仍有单脚支撑和低头失败。[第六轴踝部初筛](../evidence/ankle_roll_package_screen_r2_proportion.json)也要求抬高鞋面并开真实安装空腔；任何修改脚壳的动作，都应在三视图中与原 B／R2 外形一起复核，不能为藏电机把鞋做成厚重方盒。

## R2 整机比例候选：保留高踝轴

再次直接对照用户最后指定的[R2 尖嘴整机板](concepts/r2_pointed_beak_closed_reference.jpg)，高颈版相对机身体量仍显得瘦长。新[侧视](../images/r2_ankle_clearance_side_candidate.png)、[斜视](../images/r2_ankle_clearance_three_quarter_candidate.png)、[正视](../images/r2_ankle_clearance_front_candidate.png)、[平行张嘴](../images/r2_ankle_clearance_open_beak_candidate.png)与[低头视觉姿态](../images/r2_ankle_clearance_ground_reach_visual_candidate.png)均来自同一套 CAD 实体。[闭嘴视觉 STEP](../cad/exports/goose_r2_ankle_clearance_visual_candidate.step)、[张嘴视觉 STEP](../cad/exports/goose_r2_ankle_clearance_visual_open_candidate.step)和[生成清单](../cad/exports/goose_r2_ankle_clearance_visual_candidate_manifest.json)可复查；`appearance_review_pass=false`，不能拿去打印。

这次把机身相对地面降低 60 mm、把头颈收低，同时压缩腿中段但将踝俯仰轴保持在原 51 mm 高度；视觉包络约 `525 × 268 × 630 mm`。它更接近 R2 图中丰满机身、低重心、收尖嘴和可见双腿的总体关系，且没有把踝电机本体压进鞋底。它仍然是机械草模：白色头壳和机身连接偏方整，嘴根及翼门的表面过渡生硬，鞋壳还没有真实的电机空腔、盖板或铰链。**该候选只获得进入同版结构与物理审查的资格，没有通过用户外观复刻验收。**

同版[低头采样](../evidence/exterior_ground_reach_screen_r2_ankle_clearance.json)能把喙尖送至约 20 mm 地面目标，但下颈外饰进入机身约 `5.13 mm`，须修改承力口与外饰避让后做全行程扫掠。[条件质量与动力学](stance_layout_review.md)没有通过拾取或行走门槛；任何后续外观润色都不能继承旧 RC2 的成功证据。

## 缩小机箱与坐姿叼取的同版对照

按用户提出的 MicroDuck Max Pro 思路，下一候选保持 R2 尖嘴、头颈和高踝轴，把视觉机箱从 `350 × 205 × 230 mm` 收到 `310 × 190 × 200 mm`。可审查[站立侧视](../images/r2_compact_body_side_candidate.png)、[斜视](../images/r2_compact_body_three_quarter_candidate.png)、[正视](../images/r2_compact_body_front_candidate.png)、[平行张嘴近景](../images/r2_compact_body_open_beak_candidate.png)、[闭嘴视觉 STEP](../cad/exports/goose_r2_compact_body_visual_candidate.step)、[张嘴视觉 STEP](../cad/exports/goose_r2_compact_body_visual_open_candidate.step)和[生成清单](../cad/exports/goose_r2_compact_body_visual_candidate_manifest.json)。`appearance_review_pass=false`：机身缩小后整体更轻巧，但头壳、颈腿外饰、翼门与鞋仍是机械草模，**尚未复刻用户参考图，更不是可打印装配**。

[双腿降低 90 mm 的坐姿侧视](../images/r2_compact_body_seated_reach_side_candidate.png)和[斜视](../images/r2_compact_body_seated_reach_three_quarter_candidate.png)由同一 3D 实体按双腿逆解摆成，脚掌保持水平；[几何记录](../evidence/exterior_seated_reach_r2_compact_body_90_20.json)中机身只前俯 `20°`，颈下／上段相对俯仰约 `49.1°/35.7°`，嘴尖到 `z≈20 mm`，下颈外饰与缩小机箱的采样间隙约 `14.84 mm`，机箱最低点约 `72 mm`。把嘴尖目标抬到 `40 mm` 时，[另一姿态](../images/r2_compact_body_seated_tip40_side_candidate.png)及[记录](../evidence/exterior_seated_reach_r2_compact_body_tip40.json)的采样间隙约 `19.98 mm`，嘴壳最低点约 `37.46 mm`。这些是姿态端点采样，不是全程扫掠、机构安装或拾取证明。

当前坐姿的嘴相对水平向下约 `60°`，接近地面时有明显“啄”的外形，仍需让嘴内垫以适合夹取和拖拽的角度接近指定物；不能把视觉尖端触地当成嘴内抓握。新的物理试验发现[嘴端地面反力过大](stance_layout_review.md)，因此暂不继续细化外饰缝、羽毛或内板焊点。下一版先在同一 R2 外观上找**双脚承重、不靠嘴撑地**的低位夹取动作，并保持可以从坐姿起身、带物行走的腿脚空间。

## 短鞋、前移膝轴与较近坐姿候选

按用户提出的“机箱接近 MicroDuck 的紧凑体量、颈前段更灵活、坐下仍能够地”方向，保持 `310 × 190 × 200 mm` 视觉机箱和 R2 收尖平行嘴，收短鞋尖 40 mm，并将膝轴前移 30 mm。[新版斜视](../images/r2_forward_knee_three_quarter_candidate.png)、[站立侧视](../images/r2_forward_knee_side_candidate.png)、[坐姿侧视](../images/r2_forward_knee_seated_reach_x280_side_candidate.png)和[详细权衡](forward_knee_trade_study.md)均可对照。前移膝轴缓解此前腿线过分后折和低位受力，但头壳、颈壳、翼门、脚壳仍是未过用户外观验收的机械草模，清单保持 `appearance_review_pass=false`。

嘴尖在 `(x=280,z=40) mm` 的坐姿需颈上段约 `47.2°` 的相对俯仰；[端点采样](../evidence/exterior_seated_reach_r2_forward_knee_x280_tip40.json)给出头壳对机身约 `13.9 mm` 间隙，较近的 `x=210 mm` 则发生头壳穿插。这里的“颈前段更灵活”仍是**待实现的行程要求**，并未验证电机、线束、颈罩全程避让。嘴保持向下约 `60°`，也尚未证明其嘴内垫能以合适姿态夹取地面日用品。新版不作视觉复刻或制造放行。

后续[紧凑机箱轮廓同版审查](r2_compact_silhouette_review.md)把视觉机箱高度再收至 `180 mm`，头嘴总成后收，并让颈根与新顶面重新衔接。它有闭嘴、平行张嘴和低位姿态的同版渲染、视觉 STEP、21 点坐姿路径采样及 50 g 等效力的简化保持试验。白色颈腿壳、翼门、脚壳和机身曲面仍未达到用户原图，故外观结论继续为**未通过**；这些新试验也不构成制造放行。

进一步的[小机箱与前颈够地候选](r2_compact_front_reach_review.md)只把视觉机箱前后长度从 `310` 收至 `280 mm`。同姿态、同 15 点目标网格的几何初筛由 10 点增至 13 点，靠近身体的头壳有更多避让；盒状器件预留仍落在假设壳内。`15 mm` 嘴尖目标的短时负载代理不碰地，`10 mm` 目标却在动态保持中碰地。这更明确了前颈工作空间与接近薄物体之间的差距。新[侧视](../images/r2_compact_front_reach_v53_side_candidate.png)、[斜视](../images/r2_compact_front_reach_v53_three_quarter_candidate.png)和[坐姿](../images/r2_compact_front_reach_v53_seated_side_candidate.png)仍显示头罩、颈腿外饰、翼门和鞋壳没有复刻原图，`appearance_review_pass=false`。

随后的[尖嘴实体修正](r2_pointed_bill_mechanism_gate.md)发现上述外形的上下喙壳闭合时实体互穿，且开嘴纯下移不符合原 R2 四连杆。现用同一长尖嘴外轮廓重画上喙内侧，九点开合姿态中橙色壳不再穿插，并加入下喙最多 `5.849 mm` 的前向轨迹。新[闭嘴近景](../images/r2_nonintersecting_bill_v55_closed_detail_candidate.png)与[张嘴近景](../images/r2_nonintersecting_bill_v55_open_detail_candidate.png)仍是视觉件；头罩、相机座、翼门、颈腿过渡和鞋壳均未达到原图，外观继续**未通过**。

新增的[坐姿拾取外形／空间权衡](seated_pickup_layout_trade.md)把髋轴上移、双脚外扩和更深坐姿放在同一 R2 草模里比较：髋上移 25 mm 会与现翼门缝视觉实体重叠，深蹲时膝盖更早碰地；双脚外扩虽加宽双脚支撑，也增加单脚换重心需求。更关键的是闭嘴尖端够到地面时，下喙张开会扫向地面；需同时验证**张嘴姿态、嘴内接触与双脚承重**。这些筛查没有改变外观未通过状态，也不作为制造尺寸。

[v69 头壳包覆试样](r2_pointed_bill_mechanism_gate.md)把之前突出的嘴部电机侧颊收回头壳，直接为上下喙和连接杆留槽。[闭嘴斜视](../images/r2_head_wrap_v69_closed_three_quarter_candidate.png)、[平行张嘴](../images/r2_head_wrap_v69_open_detail_candidate.png)与[实体包络记录](../evidence/r2_head_wrap_gross_package_v69.json)可同版核查。相较先前“白牙”式外挂盖片，头嘴交界更连贯，且九点理想张合中头壳、上喙、下喙与两侧立耳不再实体互穿。**它仍是机械草模，不是用户参考图的外观复刻，更不是打印装配件。**

[v72 外观对照](../images/r2_head_wrap_v72_closed_three_quarter_candidate.png)把头罩圆角加大、翼门边与鞋底叠层压薄，并修正了上一版相机面板与固定上喙的约 `814.86 mm³` 实体重叠。[闭嘴侧视](../images/r2_head_wrap_v72_closed_side_candidate.png)、[张嘴近景](../images/r2_head_wrap_v72_open_detail_candidate.png)及[几何记录](../evidence/r2_head_wrap_gross_package_v72.json)供复核。改善集中在头嘴交界和局部比例，颈段、机身曲面与鞋面仍明显有别于用户指定图，**外观复刻未通过**；它仍是视觉 STEP，不能据此进行制造、采购或新比例动力学验收。

[v73 当前外观候选](../images/r2_slim_bill_v73_closed_three_quarter_candidate.png)把下喙外侧收薄，并给出[张嘴近景](../images/r2_slim_bill_v73_open_detail_candidate.png)与[坐姿低位侧视](../images/r2_slim_bill_v73_sit90_x300_z25_head60_open_side_candidate.png)。视觉嘴型与参考图更接近；较有余量的低位姿态通过了有限壳体／地面采样，但橙色嘴根外仍露连杆，颈杆转折、机身和脚部材质轮廓仍像机械草模。**外观未通过，低位几何筛查不等于真实夹起或拖动。**

试过在其余尺寸不变时将头嘴总成再向后收 `20 mm`；[v74 斜视](../images/r2_slim_bill_headback45_v74_rejected_three_quarter.png)与[生成清单](../cad/exports/goose_r2_slim_bill_headback45_v74_rejected_manifest.json)保存这次未采用的比例。它静态看略紧凑，但[同姿态九目标对照](../evidence/r2_head_back_trade_v73_v74.json)由 `8/9` 降至 `7/9`，`(320,15) mm` 的前方低位点失去当前平面逆解，`(300,25) mm` 点的下颈—机身采样间隙由 `11.77` 降至 `8.49 mm`。这点主观视觉收益不足以抵消前方拾取空间损失，**不采用 v74，保留 v73 作为仍未过外观门槛的工作候选**。

又试过在其他轮廓参数不变时，把视觉机箱高度从 `180` 增到 `200 mm`。这使[站姿斜视](../images/r2_body200_v75_rejected_three_quarter.png)与[侧视](../images/r2_body200_v75_rejected_side.png)的身体稍饱满，但[相同九个坐姿目标](../evidence/r2_body_height_trade_v73_v75.json)从 `8/9` 降到 `6/9`：近身 `(280,25) mm` 点的头罩—机箱采样间隙只有 `1.94 mm`，前方 `(320,15) mm` 点未找到当前平面逆解。`(300,25) mm` 的[张嘴坐姿](../images/r2_body200_v75_rejected_sit90_open_side.png)虽仍通过 41 点几何筛查，条件 `1.6 mm` 薄壳质量估算的质心高度也由约 `267.88` 上升到 `270.38 mm`。保留[闭嘴](../cad/exports/goose_r2_body200_v75_rejected_closed_manifest.json)与[张嘴清单](../cad/exports/goose_r2_body200_v75_rejected_open_manifest.json)追溯，**不采用 v75；v73 仍是未过外观和工程验收的工作候选**。这说明不能单纯把整块机箱加高，后续若要圆润的鹅身，应保护机箱前部与头颈的低位避让空间。内嵌相机黑面板另做过试样，但镜头显得孤立凸出，也未采用。

保持原机箱前缘不变、只在后上方叠加椭球的[v77 侧视](../images/r2_rear_crown_v77_rejected_side.png)和[斜视](../images/r2_rear_crown_v77_rejected_three_quarter.png)也不采用：虽避开了头颈前方空间，却在顶部留下显眼的驼峰／折线，不符合指定图的连续简洁机身。[生成清单](../cad/exports/goose_r2_rear_crown_v77_rejected_manifest.json)将此明确标作外观试样。下一次机箱改形须直接调整整片壳的连续曲面，并在改动后重查检修门轮廓、内部包络和低位颈部扫掠；不能把这个叠加实体当作外饰完成件。

连续截面放样的[v78 侧视](../images/r2_lofted_body_v78_rejected_side.png)、[斜视](../images/r2_lofted_body_v78_rejected_three_quarter.png)和[正视](../images/r2_lofted_body_v78_rejected_front.png)去掉了叠壳折线，但把前胸收成蛋形，平板检修门浮在曲面之外，顶部按钮也被新壳吞没。这三处比 v73 更远离指定整机图；[清单](../cad/exports/goose_r2_lofted_body_v78_rejected_manifest.json)保留为**外观失败记录**，不继续做这条机箱参数路线。v73 保持工作候选，仍未通过外观复刻。下一次外形动作应同时重画机身、手动翼门和颈根的接合，而非单独改变机箱外壳。

在 v73 机身、腿脚与尖嘴不变的前提下，[v79 站姿侧视](../images/r2_neck_rest15_v79_closed_side_candidate.png)和[斜视](../images/r2_neck_rest15_v79_closed_three_quarter_candidate.png)试将上颈的默认姿态向后折 `15°`，头和嘴保持水平；[闭嘴视觉 STEP](../cad/exports/goose_r2_neck_rest15_v79_visual_closed_candidate.step)、[张嘴视觉 STEP](../cad/exports/goose_r2_neck_rest15_v79_visual_open_candidate.step)及其[闭嘴](../cad/exports/goose_r2_neck_rest15_v79_visual_closed_manifest.json)／[张嘴清单](../cad/exports/goose_r2_neck_rest15_v79_visual_open_manifest.json)仅供比例比较。头嘴站姿约后移 `20.79 mm`、上升 `13.32 mm`；[同一九目标坐姿网格](../evidence/r2_neck_rest15_v79_sit90_head60_workspace_closed.json)仍为 `8/9`，指定 `(300,25) mm` 的[张嘴几何路径](../evidence/r2_neck_rest15_v79_sit90_x300_z25_open.json)保持约 `6.98 mm` 下喙离地间隙。但同一终点要求上颈相对角由约 `35.33°` 变成 `50.33°`、头相对角由 `−54.38°` 变成 `−69.38°`；工作空间不变只是理想运动学重参数化，电机行程、线束、力矩与全过程碰撞尚未验证。[条件质量估计](../evidence/exterior_mass_screen_r2_neck_rest15_v79_standing.json)的质心高度由 v73 的 `267.88` 升至约 `269.28 mm`，没有得到更低重心。它只作为**未获外观验收的对照试样**保存，v73 仍为工作候选；头壳、嘴根、机箱和翼门必须继续按原尖嘴图整体重画。

下一轮把机身与翼形检修门作为一件曲面来试。连续放样机身的[v80 斜视](../images/r2_conformal_body_v80_rejected_three_quarter.png)虽让门片贴面，却再次把前胸收成蛋形，不如指定参考图；[参数清单](../cad/exports/goose_r2_conformal_body_v80_rejected_manifest.json)留档，**不采用放样机身**。退回 v73 的原机身轮廓，仅从其曲面切分门片的[v81 侧视](../images/r2_conformal_wing_v81_closed_side_candidate.png)和[斜视](../images/r2_conformal_wing_v81_closed_three_quarter_candidate.png)使门缝更服帖，保留抽象、手动翼门方向；[视觉 STEP](../cad/exports/goose_r2_conformal_wing_v81_visual_closed_candidate.step)和[同版清单](../cad/exports/goose_r2_conformal_wing_v81_visual_closed_manifest.json)供后续重画参考。[九点低位网格](../evidence/r2_conformal_wing_v81_sit90_head60_workspace_closed.json)仍过 `8/9`，[嘴部粗包络](../evidence/r2_conformal_wing_v81_gross_package.json)和[脚底范围](../evidence/exterior_support_screen_r2_conformal_wing_v81.json)与 v73 保持一致。这些只说明视觉改门没有明显损伤已筛几何；门片还是实心视觉切片，缺少薄壳、铰链、锁止、缝隙公差和真实开合扫掠，**不能打印装配或交给用户使用**。v81 作为局部外观备选，v73 整机工作候选不变。

另将相机黑面板整体内收 `5 mm` 的[v82 近景](../images/r2_camera_bezel_v82_rejected_detail.png)与[参数](../cad/exports/goose_r2_camera_bezel_v82_rejected_manifest.json)对照：镜头依旧像独立凸出的模块，未解决头壳与嘴根的一体感；不采用。把嘴根圆盖下移、放大的[v84 闭嘴](../images/r2_root_cap_v84_rejected_closed_detail.png)／[张嘴近景](../images/r2_root_cap_v84_rejected_open_detail.png)又让圆盖悬在头壳外，连杆仍可见；[闭嘴](../cad/exports/goose_r2_root_cap_v84_rejected_closed_manifest.json)／[张嘴清单](../cad/exports/goose_r2_root_cap_v84_rejected_open_manifest.json)保存失败原因，不继续沿此参数微调。对原网格启用 MuJoCo 平滑法线后外观变化也很小，因此主要问题是**头壳、相机面板、嘴根和机身门片的整体造型**；下一步必须在指定尖嘴版上整体重画这些关系，不能靠局部移动圆盖或材质效果宣布复刻完成。

按原尖嘴参考图尝试整体放样头罩的[v85 近景](../images/r2_sculpted_head_v85_rejected_detail.png)使白壳前端变成厚直壁，相机面板局部被遮，嘴根衔接也更生硬；[生成清单](../cad/exports/goose_r2_sculpted_head_v85_rejected_manifest.json)留档，外观否决。保留原头罩而取消侧颊开槽的[v86 近景](../images/r2_continuous_cheek_v86_rejected_detail.png)仍露出下喙连杆，[九姿态实体筛查](../evidence/r2_continuous_cheek_v86_gross_package_failed.json)还发现闭嘴时两侧连杆各与头壳重叠约 `26.05 mm³`。把头壳内的嘴根避让槽向后加深到 `66 mm` 的[v87 闭嘴](../images/r2_cheek_pocket66_v87_rejected_closed_detail.png)／[张嘴近景](../images/r2_cheek_pocket66_v87_rejected_open_detail.png)清除了这处连杆重叠，但[同版筛查](../evidence/r2_cheek_pocket66_v87_gross_package_failed.json)又发现皮带粗包络有约 `22.75 mm³` 落在假设的内壳空间之外；相机仍突出、外露连杆仍破坏侧颊连续性。[v86](../cad/exports/goose_r2_continuous_cheek_v86_rejected_manifest.json)和[v87 参数清单](../cad/exports/goose_r2_cheek_pocket66_v87_rejected_manifest.json)均只作失败证据。停止沿这组局部开槽参数继续修饰，后续须在原图比例内同时重画头罩、相机窗口和内置四杆容积，再检查可装配空间。**v73 整机工作候选不变，外观和制造均未通过。**

再按[尖嘴整机参考](concepts/r2_pointed_beak_closed_reference.jpg)检查头罩与机身的大面关系：[v88 的前端相机平面](../images/r2_helmet_head_v88_rejected_detail.png)虽然能切出面板座，却把侧面变成白色方盒；[v89 的收口放样](../images/r2_tapered_helmet_v89_rejected_detail.png)仍有高而直的白色前壁，露出的嘴根连杆未消失。[v88](../cad/exports/goose_r2_helmet_head_v88_rejected_manifest.json)和[v89 参数](../cad/exports/goose_r2_tapered_helmet_v89_rejected_manifest.json)留档，不采用。与头部独立的一体机箱和贴面翼门试样 [v90 斜视](../images/r2_reference_torso_v90_rejected_three_quarter.png)／[正视](../images/r2_reference_torso_v90_rejected_front.png)又把机身前胸做成过直的盒面；[参数](../cad/exports/goose_r2_reference_torso_v90_rejected_manifest.json)留档，也不采用。这些失败说明当前视觉生成器的通用圆角盒与逐截面放样都不能直接得到原图那种圆润而有收束的机身、低小头罩及一体嘴根，继续调单个圆角或相机偏移没有意义。

下一版外形要从**整机侧视和斜视一起**建立头、颈、机身和腿脚比例，再把相机面板、嘴根空腔和手动翼门作为外形的一部分设计。参考图是透视概念图，不按其像素反推制造尺寸；但其明确的视觉要求是头罩不高耸、相机黑面融入白壳、闭嘴时四杆不悬露、脖颈在机身上方形成清楚的鹅形弧线、腿从机身下方而非远后方着地、宽脚保持低矮。髋轴上移／外扩和腿加长目前不作为默认改动：它们在[同版坐姿权衡](seated_pickup_layout_trade.md)中未显示更稳或更容易拾取的必要收益，且可能进一步改变原图腿线。任何新比例仍须用同版张嘴低位扫掠、质量与足底接触重算。**不得把 v88–v90 视为外观进步或工程版本。**

随后将头罩收低、颈段拉长，并合入贴面翼门的[v92 整机比例试样](r2_whole_proportions_review.md)，在同版低位九点和嘴部必要包络上取得可复核的局部改善；但条件重心更高，闭嘴连杆和相机模块仍破坏参考图，未进入外观验收或工程定版。

## 图生 3D 网格拒用与四边面源要求

2026-09-29 用原有 R2 外观图尝试生成整机网格，[独立拓扑记录](../evidence/r2_generated_mesh_rejection.json)检出 119,542 个三角面，没有可编辑四边面源。原始索引看似有 2,534 个断开片段，但这多数是贴图／法线接缝拆点；按相同空间位置合并后仍有 20 个连通片，整机仍不封闭。它只能帮助观察大致配色与鹅形，不作为新版外观、CAD、仿真或打印资产。用户所见的橙黑交界锯齿，主要来自诊断预览把每个三角面按贴图中心点硬分成五种颜色；这种预览方法放大了颜色边界的台阶。颈脚局部不规则和没有按活动关节整理的几何仍是建模质量问题，不能只靠抗锯齿或重新打光修好。

下一版若采用多边形外观建模，头罩、上下喙、颈段、机身与翼门、腿段和左右脚必须按真实关节分件保存可编辑四边面源，并逐件检查全四边面、单连通、无退化、封闭、流形与一致朝向；检查脚本在[这里](../../../scripts/diagnostics/check_goose_editable_quad_mesh.py)。这项要求不强迫 STEP/BREP 曲面或 STL/GLB 交换格式伪装成四边面：CAD 要验证有效实体、壁厚与装配，导出三角网格要再验证封闭、法线和公差。只有同一版外观和工程几何均过关，才可重新进入支撑、叼取和拖拽物理验证。
