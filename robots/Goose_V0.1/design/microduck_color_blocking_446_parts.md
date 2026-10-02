# 446 件头部闭合候选的 Microduck 四套配色

状态：**修正后的制造候选，实际模型渲染，审美验收待定**。不替换 419 件冻结版，也不代表实体一比一制造放行。

输入为 `cad/source/camera_closure_fixture/assembly_scene.json`，源 SHA256 为 `6dae191d4172ccb2aa3ca9faca8b15ce12cb29dac6e19c4bc45d1d35735de02e`。名义条件质量 `10.404696411680682 kg` 仅从源引用以标识版本。原厂相机柱件叠层、螺钉方向、支架和鼻罩的修改均由主线处理；配色任务没有修改 CAD、质量、惯量、碰撞、关节或控制契约。主线完整原生复核与外观验收另行记录。

五张图片均由这一份 446 件源实际 Blender 渲染：

- [Cream 奶油白整机](../images/microduck_color_blocking_446_parts/cream.png)
- [Graphite 石墨灰整机](../images/microduck_color_blocking_446_parts/graphite.png)
- [Lavender 薰衣草紫整机](../images/microduck_color_blocking_446_parts/lavender.png)
- [Sky 天空蓝整机](../images/microduck_color_blocking_446_parts/sky.png)
- [Cream 头部近景](../images/microduck_color_blocking_446_parts/cream_head_detail.png)

四张整机图使用相同几何、镜头、灯光和 1200 × 1200 分辨率。近景仅采用源提供的 `head_detail` 镜头，零件形状、位置和装配位移不变。

## 配色分区

沿用 [419 件版的官方参考与四套主辅色](microduck_color_blocking_419_parts.md)：彩色主壳、中性灰检修门和脸板、深灰骨架/黑电机、中性金属、明亮嘴脚及鞋边/眼圈次色。整只前后鞋罩和承载板/鞍座保持主点缀色，叉板和隔撑不喷成整机壳色。Cream / Sky 为橙嘴脚与金黄鞋边/眼圈；Graphite 为黄嘴脚与紫鞋边/眼圈；Lavender 为黄嘴脚、紫鞋边与青眼圈。

| 新部件 | 显示角色 |
|---|---|
| `head_camera_access_shell_left` / `right`、`head_camera_nose_shroud` | 四款主壳色 |
| `camera_fastened_open_face` | 中性灰脸板与环形涂装 |
| `camera_open_eye_bezel` | 四款对应的辅色眼圈 |
| `camera_catalog_barrel_reference`、`camera_autofocus_case_reference` | 黑色机械显示参考 |
| `camera_catalog_glass_reference` | 暗色光学显示参考 |
| `camera_sensor_board_reference` | 绿色 PCB 显示参考 |

环形涂装外半径 19.25 mm、内半径 16.7 mm，让中性脸板更清楚；实体镜圈和镜片不改。四件 `reference` 均为按厂家尺寸重建的显示参考，非打印或制造件。源给予这些显示参考零附加质量，不能据此推断实物相机无质量或这是完整厂家 CAD。

主辅色关系依据 [Microduck 官方实物合照](https://pollen-robotics.com/assets/microduck/squad.webp)、[Press Kit](https://pollen-robotics.com/microduck/press-kit/) 及官方产品三维查看器。壳色沿用官方 sRGB 色卡，辅色为实物照片与查看器材料参数指导的 Goose 映射，非原厂耗材或喷漆的精确规格。sRGB 按标准分段传递函数转换为 Blender 线性 RGB，已经声明为线性 RGB 的材质不重复转换；来源和完整材料值保存在专用配置。

## 身份验证和失败历史

[渲染清单](../evidence/microduck_color_blocking_446_parts_render_manifest.json)记录源、配置、脚本、逐件几何、全部 quad/顶点、各 PNG、同镜头和近景镜头身份；[验证记录](../evidence/microduck_color_blocking_446_parts_pixel_validation.json)检查图像、分区、法线绑定、历史完整性和本地链接。

三轮先前候选均保留在本地 `artifacts/Goose_V0.1/`，没有留在本轮图片目录供验收：

- `color_blocking_446_pre_fix_snapshot` / `color_blocking_446_pre_fix_preview`：源 `179ccafba274b1a9646501e43674e92c0bc6b9dbe1b938af7316df72888b321e`，4 颗 PCB 后侧螺钉名义方向错误；仅有 700 像素 Cream 小样。
- `color_blocking_446_stack_failed_snapshot` / `color_blocking_446_stack_failed_images`：源 `4bed5a8b7a5cfe9ee939163ef753a66aeabef0b6f5e4e45294c0c90a72ae7e8d`，原厂角部柱件与新增五金冲突，以及鼻罩/支架交集；5 图均标为失败候选，不放行。

- `color_blocking_446_pre_final_collision_snapshot` / `color_blocking_446_pre_final_collision_images`：源 `2ddd642031d5f66ca356f89ed71d9e7539b200c6349e44d96123b43a46e1904e`，内部支架斜梁与嘴部电机有 3.66 mm³ 交集，完整 OEM 组检查尚未结束；5 图保留为不放行候选。

新源由主线纠正上述实体装配问题，并将螺帽预留由 1.6 mm 调整为 2.0 mm；可见外壳轮廓未改。配色脚本每秒检查原生场景字节哈希，发生变更即停止 Blender；每张渲染前后再次检查。冻结场景、几何 NPZ 和法线字段逐一验证哈希，避免混用版本。419 / 344 / 314 / 292 件版及首次被否决的单色方案原图、配置、脚本和哈希保持完整。

## 显示和验收限制

本轮不创建 modifier，不添加平移、替代玻璃或封孔几何。全部输入 quad 和原坐标保留。躯干前半壳沿用绑定该几何 SHA 的轮廓导数近似显示法线，切孔和安装边缘保留原法线；这不是 native CAD 曲面质量或制造可用性的证明。

图像保留真实相机开孔、镜片深度和候选装配状态。当前三分之四视角不能看到整片深置镜片，不用假玻璃遮盖。头部局部仍可能有源 quad 平滑法线带来的细条状明暗过渡，需结合原生源和其他视角评审。涂装质量未加入机械账本，喷涂/耗材色差尚未标定。完成实际渲染与像素检查，不代表用户已认可美感或实体已放行。

## 复现

专用配置：[microduck_color_blocking_446_parts.json](../configs/microduck_color_blocking_446_parts.json)。独立渲染入口：[render_goose_color_blocking_446_parts.py](../../../scripts/models/render_goose_color_blocking_446_parts.py)。身份/图像验证入口：[validate_goose_color_blocking.py](../../../scripts/models/validate_goose_color_blocking.py)。

```bash
blender --background --threads 8 --python scripts/models/render_goose_color_blocking_446_parts.py -- \
  --scene robots/Goose_V0.1/cad/source/camera_closure_fixture/assembly_scene.json \
  --live-scene robots/Goose_V0.1/cad/source/camera_closure_fixture/assembly_scene.json \
  --geometry-root robots/Goose_V0.1 \
  --config robots/Goose_V0.1/configs/microduck_color_blocking_446_parts.json \
  --output robots/Goose_V0.1/images/microduck_color_blocking_446_parts \
  --manifest robots/Goose_V0.1/evidence/microduck_color_blocking_446_parts_render_manifest.json \
  --head-detail --resolution 1200 --samples 160
```

本轮只写配色、独立渲染脚本、图片、验证和说明，不编辑 README、CAD、质量台账或主线计算/集成文档。
