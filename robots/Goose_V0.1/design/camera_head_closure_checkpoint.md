# 头壳连续后缘与相机闭合检查点

本轮处理用户在 419 件 Cream 图中指出的两处实际结构问题：相机面板与头壳之间有大缺口，头壳后缘采用网格逐格裁切而形成台阶。修正保存在独立 **446 件显示装配候选**；原 419 件候选和默认 344 件模型保留。该检查点完成局部修补，不代表第三、第四阶段或最终制造外观通过。

## 修正与同版参数

- 左右头壳改为连续原生切边，后部开口位于原生坐标 X=100.75 mm，边缘圆角 0.4 mm，保留检修与颈部通道。
- 新增连续空心鼻罩，连接旧头壳和倾斜相机面板，主体名义壁厚约 2.2 mm；独立面板采用实际螺钉固定，不用渲染补面遮住缺口。
- 根据完整厂家相机叠层重建承力架，修正 PCB 螺钉方向和绝缘垫片位置，保留原厂角部柱件。支架梁绕开鼻罩和嘴部电机。
- 保留 18 个主动轴、原光学方向与嘴部结构。19 个刚体的闭合姿态质量、质心、完整惯量重新计算；条件整机质量 **10.4046964 kg**，比 419 件版增加 **2.29248 g**。25 g 相机预留仍保留，未重复加入显示参考的质量。

[装配源](../cad/source/camera_closure_fixture/assembly_scene.json) SHA256 为 `6dae191d4172ccb2aa3ca9faca8b15ce12cb29dac6e19c4bc45d1d35735de02e`。446 是显示源对象数，包含四件按厂家尺寸重建的零质量显示参考，不是可打印实物件数。本轮自研/名义五金共 29 件，其中五件主要结构、八颗 M2×10 螺钉、十六片尼龙垫片；螺钉和 OEM 螺纹仍需以实际采购规格确认。

## 交付与验证

| 内容 | 文件 |
|---|---|
| 原生 BREP、闭合 quad 源、STEP/STL 及逐件哈希 | [原生件清单](../cad/exports/camera_head_closure/manifest.json) |
| 446 件同源显示装配及导出 | [装配清单](../cad/exports/camera_closure_fixture/manifest.json) |
| 完整质量、质心、惯量与版本边界 | [参数 JSON](../evidence/camera_head_closure_parameters.json)、[19 体 CSV](../hardware/camera_closure_body_parameters.csv) |
| 七行、29 件名义增量采购表 | [XLSX](../hardware/camera_head_closure_bom.xlsx)、[CSV](../hardware/camera_head_closure_bom.csv)、[JSON](../hardware/camera_head_closure_bom.json) |
| 原生几何与同源静力复核 | [检查记录](../evidence/camera_head_closure_fit.json) |
| 渲染、CAD、参数、采购表和本地链接一致性 | [检查点审计](../evidence/camera_head_closure_checkpoint.json) |
| 同版四色实际渲染及头部近景 | [四色与复现说明](microduck_color_blocking_446_parts.md)、[头部近景](../images/microduck_color_blocking_446_parts/cream_head_detail.png) |

29 件新增/替换件通过原生实体有效性、STEP 回读、STL 闭合和四边面源检查。十个闭嘴头部姿态的有限几何筛查均无碰撞失败或未判定项。四处自研框架和四处 OEM 名义螺纹接触分别记录；没有把整个相机组或细小交集直接忽略。有效厂家实体保留完整子实体；复杂组布尔计算超时时，以完整子实体的扩大包围盒证明分离，不能证明分离的部分继续精确检查。一个厂家非实体组仍采用完整扩大包络保守筛查，不能据此称原厂 CAD 全部有效。

新质量和逐体惯量重新进行嘴尖 20 N、嘴中部 50 N 各 63 个静力工况，接触与名义力矩筛查通过。嘴尖工况的右膝最小余量约 **0.05944 Nm**，筛查依赖尚未实测确认的驱动/热能力边界；这不是充足动态余量或行走能力的证明。没有新增 PPO 或把旧动态成功结果移植到新装配。

过程中发现并修正的 [螺钉方向失败](../evidence/camera_head_closure_initial_failure.json)、[叠层/鼻罩失败](../evidence/camera_head_closure_stack_failure.json)、[支架梁失败](../evidence/camera_head_closure_beam_failure.json)保留。完整失败候选在本地忽略目录 `artifacts/Goose_V0.1/`，不作为本轮验收图。

## 当前边界与下一步

四色图均直接来自上述几何，未新增封孔、替代镜片或修改器。后缘台阶已去除，前部大缺口已由原生鼻罩闭合；零件装配缝、实际镜片深度及源显示法线的细条明暗仍保留。审美验收待用户确认，不能称实体与电子版已一比一落地。

完整头壳/框架固定、实际相机版本与连接器、线束活动余量、材料强度与工具路径仍需确认；整机供电保护、完整装配、同版动力学/任务及跨引擎验证尚未完成。本轮到此收束头部局部修补，下一步回到整机供电/驱动与装配关键路径，不继续围绕鼻罩细雕或 PPO 扩训。

复核入口为 [原生检查脚本](../../../scripts/diagnostics/check_goose_camera_head_closure.py)和 [一致性审计脚本](../../../scripts/diagnostics/check_goose_camera_closure_checkpoint.py)。从 GitHub 拉取超过 100 MiB 的历史模型资产时遵循 [Git LFS 拉取说明](../../../docs/guides/large_asset_checkout.md)。
