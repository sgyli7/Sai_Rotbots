# R2 整机比例试样：低头罩与长颈段

以用户指定的 [R2 尖嘴整机图](concepts/r2_pointed_beak_closed_reference.jpg)及[平行张嘴图](concepts/r2_pointed_beak_parallel_open_reference.jpg)为外观方向，在 v73 的机身、双腿、低鞋和尖嘴坐标上，只将白色头罩视觉高度从 `116` 收至 `104 mm`，把颈部竖向比例从 `0.645` 改为 `0.8`，保持颈根位置不变，并采用 v81 的贴面手动翼门。头嘴总成视觉上升约 `41.34 mm`，整机视觉包络高从约 `601.5` 增至 `638.84 mm`。这些是外观试样尺寸，**不是用户确认的整机定尺**。可直接对照[闭嘴侧视](../images/r2_whole_proportions_v92_closed_side_candidate.png)、[斜视](../images/r2_whole_proportions_v92_closed_three_quarter_candidate.png)、[头嘴近景](../images/r2_whole_proportions_v92_closed_detail_candidate.png)、[张嘴近景](../images/r2_whole_proportions_v92_open_detail_candidate.png)与[坐姿张嘴侧视](../images/r2_whole_proportions_v92_sit90_open_side_candidate.png)。[闭嘴 STEP](../cad/exports/goose_r2_whole_proportions_v92_visual_closed_candidate.step)、[张嘴 STEP](../cad/exports/goose_r2_whole_proportions_v92_visual_open_candidate.step)及[闭嘴](../cad/exports/goose_r2_whole_proportions_v92_visual_closed_manifest.json)／[张嘴清单](../cad/exports/goose_r2_whole_proportions_v92_visual_open_manifest.json)可追溯生成参数与参考图哈希，**STEP 仍是相交的实心视觉件**。

第一版 v91 虽改善了头颈比例，却让相机环与黑面板在实体上断开，且输出端皮带粗包络有 `17.93 mm³` 超出假设头壳内空间，见[失败记录](../evidence/r2_whole_proportions_v91_gross_package_failed.json)和[参数](../cad/exports/goose_r2_whole_proportions_v91_rejected_manifest.json)。v92 仅向下补 `2 mm` 头罩内部空间，并让相机环与面板实体相接；[按清单横向位置重算的九姿态头嘴与 33 点皮带粗包络筛查](../evidence/r2_whole_proportions_v92_gross_package_manifest_center.json)的必要几何条件通过。早期[同项记录](../evidence/r2_whole_proportions_v92_gross_package.json)把皮带横向中心硬编码在 `18 mm`，与清单中的 `20 mm` 不一致；已改为读取清单重算，保留旧记录供追溯。此筛查没有实际皮带齿形、轴承、薄壳、张紧器、螺钉、线束或可装配支架，不是嘴部结构放行。

| 同版筛查 | v92 结果 | 边界 |
| --- | --- | --- |
| [90 mm 下蹲九目标](../evidence/r2_whole_proportions_v92_seated_workspace.json) | 指定 `x=280/300/320 mm`、嘴尖 `z=15/25/40 mm` 的 `9/9` 个采样几何点通过；v73 为 `8/9` | 只测一条关节插值路径，未测机械限位和线束 |
| [张嘴坐姿 41 点路径](../evidence/r2_whole_proportions_v92_sit90_x300_z25_open.json) | 目标 `(300,25) mm` 时，下喙离地最小约 `6.98 mm`、头壳离机身约 `26.62 mm`、下颈外饰离机身约 `19.15 mm` | 颈下／上段相对俯仰约 `51.16°/58.91°`，头相对俯仰约 `−70.07°`；实际关节行程、受力和拾取未验证 |
| [脚底必要范围](../evidence/r2_whole_proportions_v92_support.json)与[条件质量](../evidence/r2_whole_proportions_v92_standing_mass.json) | 双脚视觉支撑范围未变；按 `1.6 mm` 均匀 PETG 薄壳代理，站姿质心高约 `273.50 mm`，比 v73 的 `267.88 mm` 高 `5.62 mm` | 未包含真实完整承力件、所有踝轴、紧固件及实测打印质量，不能推断能站、走或拖 |

## 髋轴上移、外移与腿长的取舍

针对“髋更高、更靠两侧，腿也更长，是否更稳且更容易坐下捡物”的设想，按[同一 v92 几何试样的对照记录](../evidence/r2_whole_proportions_v92_hip_layout_trade.json)分别移动髋轴、脚和理想腿段，不把它们混成一个未做出的新外壳。以机身和脚不动为前提，髋轴上移 `10 mm` 会使髋膝轴距由 `100.86` 增至 `110.57 mm`；`130 mm` 下蹲时原膝罩离地由 `14.75` 降为 `9.65 mm`，翼门接缝与髋轮毂的名义竖向间隔由 `20.62` 降为 `10.62 mm`。单独把大腿和小腿轴长各加 `10 mm`、而机身和脚不升高，深蹲同样使原膝罩离地代理从 `14.75` 降为 `10.07 mm`。更长的腿容许在站姿保持机身高度时多弯曲，却不自动降低站姿质心，也不能直接证明能蹲得更低。

把两侧髋轮毂各外移 `6 mm` 而脚保持原位，足底支撑范围不变，髋至踝的横向偏角在 `130 mm` 下蹲时从约 `1.17°` 增至 `5.82°`；现有轮毂已比翼门外表面突出约 `12.35 mm`，外移还会增加突起。若把脚各外移 `6 mm`，双脚支撑半宽由约 `133.23` 增至 `139.23 mm`，但单脚站立时质心至少要横移到支撑脚内边缘的距离也由约 `42.77` 增至 `48.77 mm`。只把假设的六个髋电机升高 `10 mm`，`1.6 mm` 薄壳代理的质心高度约增加 `1.41 mm`；若整个机身随腿升高，升幅还会更大。因而当前不把“髋上移／外移＋加长腿”当作定版；应先保持参考图的紧凑机身、髋腿外观和低鞋，在后续同一结构版对比轻微髋轴调整、蹲姿自碰、真实质量与单脚控制。

这个比例比方盒头试样更接近参考图的低头罩、清晰颈弧，但**用户外观验收仍未通过**：相机仍像凸出的模块，闭嘴时嘴根连杆悬露，机身和翼门、腿罩与鞋面也未达到原图的整体表面质量。v92 暂作整机比例比较，v73 仍是先前工作候选；当前 RC2 模型、BOM、旧 CAD 和 Sim2Sim 结果不能继承 v92 的变化。下一外形动作应同时重画相机窗口、头罩侧颊与隐藏四杆的空腔，并核算较长颈部的行程、线束、力矩和带物起身；在同一装配版完成前，**外观、制造、采购和训练交付都不放行**。

## v95 嘴根与连续头罩的局部试样

为去掉 v92 闭嘴时显眼的矩形头罩缺口与外露侧杆，试用名义 `2.7 mm` 薄壁头罩，把成对四杆从 `y=±30 mm` 收到 `±20 mm`，暂定传动带从 `y=20 mm` 移到中心 `y=0`，按上喙和下喙的运动轨迹在白壳上切避让。对照[原尖嘴图](concepts/r2_pointed_beak_closed_reference.jpg)，可查看[闭嘴整机](../images/r2_swept_head_v95_closed_three_quarter_candidate.png)、[闭嘴近景](../images/r2_swept_head_v95_closed_detail_candidate.png)、[张嘴近景](../images/r2_swept_head_v95_open_detail_candidate.png)和[张嘴整机](../images/r2_swept_head_v95_open_three_quarter_candidate.png)。[闭嘴视觉 STEP](../cad/exports/goose_r2_swept_head_v95_visual_closed_candidate.step)、[张嘴视觉 STEP](../cad/exports/goose_r2_swept_head_v95_visual_open_candidate.step)及各自的[闭嘴](../cad/exports/goose_r2_swept_head_v95_visual_closed_candidate_manifest.json)／[张嘴清单](../cad/exports/goose_r2_swept_head_v95_visual_open_candidate_manifest.json)保存同版参数与脚本哈希，**仍不可作打印装配图**。

这次没有只靠白壳遮住穿插的杆件。第一轮保留原 `±30 mm` 四杆时，闭嘴的两根下喙连接件各穿入头罩约 `166.57 mm³`；收至 `±20 mm` 后仍在闭嘴各穿入约 `87.64 mm³`，张嘴时每侧下摆杆与移动立杆分别约 `48.76/81.41 mm³`。v95 再按九个四杆角度样点切局部运动避让，按十七个下喙角度样点切嘴壳避让；[同版实体记录](../evidence/r2_swept_head_v95_sampled_geometry.json)显示，开、闭两端所列连杆／连接件与头罩的布尔交集均为 `0 mm³`，头罩仍为一个有效 BREP 实体；九个上、下橙嘴采样点也无实体互穿。沿用 v92 的 `90 mm` 下蹲和九个嘴尖目标，[同版几何路径](../evidence/r2_swept_head_v95_seated_workspace.json)仍过 `9/9`；指定 `(300,25) mm` [张嘴坐姿 41 点路径](../evidence/r2_swept_head_v95_sit90_x300_z25_open.json)下喙最低约 `6.98 mm`。新中心带路另做[名义内腔 33 截面筛查](../evidence/r2_swept_head_v95_nominal_drive_core.json)：假设电机盒和带路均在头内，所测截面超出量为零，电机与 `±20 mm` 四杆的横向名义间隔为正。这些仅证明**所列实体和采样位置的必要几何条件**，没有连续扫掠、真实轴承／横轴、输出盘、皮带齿形、张紧器、机械限位、紧固件或强度核算。

视觉上的嘴根缺口缩小了，但原图的内嵌相机面、颈腿曲面和机身转接仍未复刻；张嘴时连杆仍显得生硬。原导出的[头罩 STL](../cad/exports/goose_r2_swept_head_v95_visual_shell_raw.stl)在网格封闭性检查中 `is_watertight=false`；定位为 18 个零面积三角面。只删除这些退化面后的[拓扑清理版](../cad/exports/goose_r2_swept_head_v95_visual_shell_topology_cleaned.stl)重新载入后 `is_watertight=true`，体积与包围盒不变，见[原件／输出哈希和检查记录](../evidence/r2_swept_head_v95_mesh_topology.json)。这解决了视觉网格的拓扑错误，**仍没有可打印的分件、安装柱、局部壁厚与强度验收**。v95 只作为下一轮头嘴结构与外观比较的局部候选，`appearance_review_pass=false`，不替换原 RC2 物理模型、BOM 或 Sai_Lab 训练模型。

## v96 脚掌居中：站姿与低位任务一起看

针对用户提出的“脚掌相对于小腿尖再后移一些”，v96 **只把两只鞋整体后移 `20 mm`**，保留 v95 的机身、腿轴、头颈及 R2 尖嘴。可并排看 [v95 侧视](../images/r2_swept_head_v95_closed_side_candidate.png)、[v96 侧视](../images/r2_centered_foot_v96_closed_side_candidate.png)、[v96 闭嘴斜视](../images/r2_centered_foot_v96_closed_three_quarter_candidate.png)、[张嘴斜视](../images/r2_centered_foot_v96_open_three_quarter_candidate.png)与[坐姿张嘴](../images/r2_centered_foot_v96_sit90_open_side_candidate.png)。[闭嘴](../cad/exports/goose_r2_centered_foot_v96_visual_closed_candidate.step)／[张嘴 STEP](../cad/exports/goose_r2_centered_foot_v96_visual_open_candidate.step)及[闭嘴](../cad/exports/goose_r2_centered_foot_v96_visual_closed_candidate_manifest.json)／[张嘴清单](../cad/exports/goose_r2_centered_foot_v96_visual_open_candidate_manifest.json)是可复核的视觉候选，**不是承力鞋设计**。

[同版权衡记录](../evidence/r2_centered_foot_v96_trade_screen.json)逐一核对闭嘴／张嘴各 `98` 个视觉网格，确认仅两鞋的 `12` 个网格改变；[v96 坐姿采样](../evidence/r2_centered_foot_v96_sit90_x300_z25_open.json)仍保留原 `(300,25) mm` 嘴尖目标及所查头颈／嘴壳离地净空，但现有采样器**不查膝盖与鞋的实体接触**。按 `1.6 mm` 均匀 PETG 薄壳与继承器件质量的条件代理，双脚站姿的前后最近支撑余量从 v95 的 `75.21 mm` 增至 v96 的 `92.65 mm`；同一 `90 mm` 下蹲叼取姿态却从 `73.01 mm` 降至 `55.56 mm`。这一低位计算还把腿质量保留在站姿位置，只能表示趋势。两版低位的单髋重力矩代理均约 `0.989 Nm`，超过试用的 `0.82 Nm` 粗筛值；把 `50 g` 当作已提起的嘴尖点载荷后代理约 `1.065 Nm`，**并非真实夹取或连续额定核算**。

因此不把 v96 脚掌定版：后移改善站姿居中，却削弱核心的低位叼取前方余量，也没有解决髋部负载、单脚换重心与行走。[v96 与运行模型对齐闸门](../evidence/r2_centered_foot_v96_system_alignment.json)依然失败；整机外观仍未获验收，v95/v96 都不能继承 RC2 的物理、制造或采购放行。

针对上述“腿质量仍在站姿”的近似，[同版重摆质量复核](../evidence/r2_seated_whole_mass_repose_v95_v96.json)让两腿按该视觉坐姿弯曲，并把躯干整体下降 `90 mm`；理想脚踝位置与原位偏差小于 `0.001 mm`。在仍然假定 `1.6 mm` PETG 均匀薄壳和继承器件质量的条件下，v95／v96 坐姿整机质心高度都约为 `165.36 mm`，前后最近视觉脚底余量分别为 `76.70/59.25 mm`，v96 依旧少 `17.45 mm`；单髋重力矩仍约 `0.989 Nm`。这修正了旧估算的坐姿重心高度，**没有**把视觉脚底范围变成实测接触面，也没有解除髋负载或夹拖能力缺口。

## 低位叼取姿态的整机权衡

仍用 **v95 张嘴整机**，仅将 `90 mm` 下蹲、嘴尖 `(300,25) mm` 的机身前俯从 `20°` 改为 `15°`。[41 点路径记录](../evidence/r2_swept_head_v95_sit90_torso15_x300_z25_open.json)中的有限外壳净空检查通过，下喙最低约 `6.98 mm`，颈下外饰对机身的采样间隙从 `19.15` 减至 `12.76 mm`；腿部平面反解的髋角从 `13.78°` 增至 `18.78°`，踝角仍为 `52.79°`。按同一 `1.6 mm` 均匀薄壳和继承器件位置的条件质量代理，单侧髋部静态重力矩约从 `0.989` 降到 `0.940 Nm`，仍高于试用 `0.82 Nm` 筛查值；把 `50 g` 视为已经提起的嘴尖点载荷后约为 `1.016 Nm`。此处腿质量仍按站姿摆放，且没有实测额定力矩、腿部自碰、连续扫掠、足底载荷和抓取接触，**不能据此认定坐下捡物可行**。

这组整机权衡说明微调前俯角不足以解除当前负载警报，不继续围绕几度姿态或鞋面细节迭代。先把用户指定的尖嘴、内嵌相机、小头罩、颈弧、紧凑机箱与低脚的**整机外观**做到可并排验收；随后在同一候选上重新确定承力质量、关节行程和双足／叼拖动力学，最后回到整机 CAD、BOM、接线和跨引擎任务复核。
