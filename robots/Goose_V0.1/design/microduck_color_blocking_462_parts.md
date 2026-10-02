# 462 个源对象壳体固定候选的 Microduck 四色渲染

状态：**同源实际渲染候选，外观验收待定**。图片不代表制造、整机、静力、全运动范围或训练放行；相关检查由主线独立记录。

输入为 `cad/source/torso_shell_mount_fixture/assembly_scene.json`，SHA256 `dc4bd2545687f8b4d247667261abeec314291f965ca1956562db8cfd72f49876`。条件质量 `10.440894357346792 kg` 仅引用源作为版本标识。462 是场景源对象数量，含显示参考，不等于 462 个需制造或采购的零件。

本轮只设置表面材质、近似显示法线和摄影条件，不修改 CAD 几何、姿态、质量、惯量、关节、碰撞或控制参数，也不替换已交付 446 件源。

- [Cream 奶油白整机](../images/microduck_color_blocking_462_parts/cream.png)
- [Graphite 石墨灰整机](../images/microduck_color_blocking_462_parts/graphite.png)
- [Lavender 薰衣草紫整机](../images/microduck_color_blocking_462_parts/lavender.png)
- [Sky 天空蓝整机](../images/microduck_color_blocking_462_parts/sky.png)
- [Cream 头部近景](../images/microduck_color_blocking_462_parts/cream_head_detail.png)

五图使用同一源，实际 Blender 4.0.2 / Cycles 渲染，1200 × 1200、160 samples、不使用 denoising。四张整机图的镜头、灯光相同；头部近景只换用源提供的检查镜头。无需 AI 图片替代模型。

## 配色与显示

沿用 [446 件版的正确分区](microduck_color_blocking_446_parts.md)：主色壳体、中性灰检修门和脸板、深色机械、中性金属、明亮嘴脚以及次色鞋边/眼圈。Cream / Sky 为橙嘴脚与金黄辅色；Graphite 为黄嘴脚与紫辅色；Lavender 为黄嘴脚、紫鞋边和青眼圈。新源保留已修好的连续头壳，不调整其颜色家族或轮廓。

新部件的涂装映射：`torso_mounted_shell_*` 使用主壳色；内部 `torso_roof_frame_carrier_*` 为深色机械；M3 嵌件、垫片及固定螺钉采用中性金属。主线新增固定点的真实形状与位置照实导入。嘴、整只鞋罩与承载板/鞍座保持主点缀色，叉板和隔撑保持深灰/金属层次。

新前半躯干壳带内部安装凸台，几何已换源，因此本轮为 `torso_mounted_shell_left_fore` / `right_fore` 生成独立、绑定新 NPZ SHA 的近似显示法线。依据仍是已有机身轮廓导数，仅用于轮廓径向包络 0.95–1.005 范围；包络外的安装点与切口顶点保留原生 split normals，面法线与轮廓不对齐的边缘同样不套用近似法线。全部顶点和 quad 不动，不创建 modifier。这种显示处理不能证明原生 CAD 曲面质量或制造可用性。

镜圈的表面涂装仍为内半径 16.7 mm、外半径 19.25 mm；镜片和开孔不变，不添加假玻璃或覆盖真实间隙。按厂家尺寸重建的四个相机 `reference` 保持黑色机构、暗色光学或绿色 PCB 的角色，均为非打印显示参考，并非完整厂家制造 CAD。

配色来源与 sRGB/线性 RGB 转换继承 [446 件版配置](../configs/microduck_color_blocking_446_parts.json)：[Microduck 官方 Press Kit](https://pollen-robotics.com/microduck/press-kit/)、[官方四色实物合照](https://pollen-robotics.com/assets/microduck/squad.webp)及产品三维查看器。辅色是面向 Goose 的参考映射，未经耗材/喷漆色差标定；涂装质量未加入机械账本。

## 身份和历史

[渲染清单](../evidence/microduck_color_blocking_462_parts_render_manifest.json)记录源、配置、脚本、逐件几何、显示几何指纹、顶点/quad 统计及各 PNG 哈希；[验证记录](../evidence/microduck_color_blocking_462_parts_pixel_validation.json)核对源/几何依赖、分区、显示法线绑定、五图尺寸、实际逐图查看与历史完整性。每秒检查原生场景哈希，源改变即停止渲染，并在每张图前后再次校验。

446 / 419 / 344 / 314 / 292 件版本与首次被否决方案保留原图、配置、渲染脚本及哈希。早期 446 件未放行候选保留在 artifacts，不覆盖本轮或已有验收材料。

局部头壳的细条状显示明暗和三分之四视角下深置镜片的部分可见范围仍照实保留。完成像素检查只是确认交付图真实存在、分区清楚且没有混版，不代表用户已接受美感或实物已经验证。

## 复现入口

专用配置：[microduck_color_blocking_462_parts.json](../configs/microduck_color_blocking_462_parts.json)。渲染脚本：[render_goose_color_blocking_462_parts.py](../../../scripts/models/render_goose_color_blocking_462_parts.py)。近似显示法线生成：[build_goose_display_normals_462_parts.py](../../../scripts/models/build_goose_display_normals_462_parts.py)。验证入口：[validate_goose_color_blocking.py](../../../scripts/models/validate_goose_color_blocking.py)。

```bash
blender --background --threads 8 --python scripts/models/render_goose_color_blocking_462_parts.py -- \
  --scene robots/Goose_V0.1/cad/source/torso_shell_mount_fixture/assembly_scene.json \
  --live-scene robots/Goose_V0.1/cad/source/torso_shell_mount_fixture/assembly_scene.json \
  --geometry-root robots/Goose_V0.1 \
  --config robots/Goose_V0.1/configs/microduck_color_blocking_462_parts.json \
  --output robots/Goose_V0.1/images/microduck_color_blocking_462_parts \
  --manifest robots/Goose_V0.1/evidence/microduck_color_blocking_462_parts_render_manifest.json \
  --head-detail --resolution 1200 --samples 160
```
