# E 一体检修头壳的 Microduck 四色实际渲染

状态：**单件打印头壳的同源配色候选**。完整安装、制造、训练和用户审美验收均未由本任务放行。

[当前场景](../cad/source/one_piece_head_service_fixture/assembly_scene.json) SHA256 为 `1a05dc55c66f96bee59f8cdb50d2f15942fdcf201e91c8d2e72140ba30be25de`，460 个源对象、18 个主动轴；[整机参数](../evidence/one_piece_head_service_parameters.json)的条件质量 `10.430762602736852 kg` 仅标识版本。[主头壳原生 CAD](../cad/source/one_piece_head_service/head_integral_print_shell.brep)保持单一实体。主线将底部开口扩大到 110 × 70 mm、上缘抬高 4 mm 并连通后口；上部连续曲面、1.8 mm 内部容纳余量和光学面沿用 D。配色任务没有修改几何、孔洞、顶点、姿态或物理参数。

- [Cream 奶油白整机](../images/microduck_color_blocking_one_piece_head_service/cream.png)
- [Graphite 石墨灰整机](../images/microduck_color_blocking_one_piece_head_service/graphite.png)
- [Lavender 薰衣草紫整机](../images/microduck_color_blocking_one_piece_head_service/lavender.png)
- [Sky 天空蓝整机](../images/microduck_color_blocking_one_piece_head_service/sky.png)
- [Cream 头部近景](../images/microduck_color_blocking_one_piece_head_service/cream_head_detail.png)

五图为同一冻结源的实际 Blender 4.0.2 / Cycles 渲染：1200 × 1200、160 samples、无 denoising，近景优先，四色整机同镜头/灯光。D 的材质、相机和主辅配色全部保持：主壳、中性检修门/脸板、深色机械、明亮嘴脚、次色鞋边/眼圈，分区依据见已提交的 [462 配色说明](microduck_color_blocking_462_parts.md)。Cream / Sky 用橙嘴脚、金黄辅色；Graphite 用黄嘴脚、紫辅色；Lavender 用黄嘴脚、紫鞋边和青眼圈。颜色家族来自已核对的 [Microduck 官方四色资料](https://pollen-robotics.com/microduck/press-kit/)，耗材与喷漆色差尚未标定。

主头壳只用原生 split normals；没有补片、modifier、近似头部法线、假玻璃或遮缝涂装，真实扩大后的下后装配口和黑色内部保留。机体前半壳沿用几何 SHA 绑定的 462 版近似显示法线，切口/内部安装面保持原生法线；这不能证明 CAD 曲面或制造质量，后壳端部既有的轻微径向明暗过渡也保留。

[配置](../configs/microduck_color_blocking_one_piece_head_service.json)、[渲染清单](../evidence/microduck_color_blocking_one_piece_head_service_render_manifest.json)、[像素与身份报告](../evidence/microduck_color_blocking_one_piece_head_service_pixel_validation.json)记录完整几何指纹、顶点/quad、网格/材质分区、源与图片 SHA 和逐图实看。每秒及每张图前后监测源 SHA，变化即停。独立 [渲染入口](../../../scripts/models/render_goose_color_blocking_one_piece_head_service.py)沿用选项 `--head-detail --head-detail-first --resolution 1200 --samples 160`，只指定 E 的场景、配置及输出目录。

五张实际图片已逐张检查：扩大后的下后开口与黑色内部清楚可见，上部头壳在该近景视角保持连续，四款主辅分区沿用 D；这个观察不替代原生曲面或制造检查。

冻结快照在 `artifacts/Goose_V0.1/color_blocking_one_piece_head_service_snapshot`。D 及更早图片/配置/证据保留，本轮没有重写旧报告或共享 validator，也没有编辑 README、CAD、物理、供电或工程里程碑，没有 Git 提交。失败历史由主线统一保存。有限原生姿态、直线拆装采样、静力和实际制造验证均由主线负责，图像完成不能代替完整安装或用户审美验收。
