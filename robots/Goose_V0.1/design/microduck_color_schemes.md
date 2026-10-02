# Goose V0.1 四种配色

**历史第一次配色，已被用户否决。** 用户指出整机近乎单色、没有学到 Microduck 的完整色块关系。以下配置和图片原样保留以便追溯，不再作为当前推荐方案。新一轮见 [Microduck 色块分区重做](microduck_color_blocking.md)，仍待用户验收。

四张图来自同一份实际机械模型、同一灯光与机位；只切换表面颜色。此项用于配色验收，机械制造与物理任务验收仍以主线记录为准。

| 方案 | 头、躯干及原白色叉架表面 | 嘴、脚前罩 | 镜头圈 | 脚侧细边 |
|---|---|---|---|---|
| [Cream 奶油白](../images/microduck_color_schemes/cream.png) | `#f7e6cb` | 橙色 | 暖金橙 | 黄色 |
| [Graphite 石墨灰](../images/microduck_color_schemes/graphite.png) | `#6c6a68` | 黄色 | 紫色 | 紫色 |
| [Lavender 薰衣草紫](../images/microduck_color_schemes/lavender.png) | `#bfa9cf` | 黄色 | 青蓝色 | 紫色 |
| [Sky 天空蓝](../images/microduck_color_schemes/sky.png) | `#a9dbe8` | 橙色 | 暖金橙 | 黄色 |

黑色执行器、镜片、夹持胶垫、柔性脚底和裸露金属紧固件保持原有功能材质。原白色叉架采用对应配色的表面涂装，未改变其基材、尺寸、质量、关节位置或控制参数。涂层重量尚未单独计入质量账本。

## 来源与色彩转换

[Pollen Robotics 官方 Press kit](https://pollen-robotics.com/microduck/press-kit/)明确列出四个名称及上表四个校准壳色，说明 Cream / Sky 搭配橙色、Graphite / Lavender 搭配黄色。原来的白＋橙作为 Cream 方案延续，并采用官方壳色稍微调暖。

[官方产品页](https://pollen-robotics.com/microduck/)的[四机合照](https://pollen-robotics.com/assets/microduck/squad.webp)及[官方 3D viewer 材质配置](https://pollen-robotics.com/_next/static/chunks/2guekqpch1ejk.js)还提供了镜头圈和脚底的次要配色关系。镜头圈的线性 RGB 为：Cream / Sky `[0.93, 0.30, 0.002]`，Graphite `[0.28, 0.15, 0.55]`，Lavender `[0.32, 0.73, 0.86]`。这是暖金橙、紫与青蓝，合照中的暖金橙在受光处接近黄色。

配置查阅于 2026-09-30 UTC。官网脚本可能换名，其哈希已记录在[配色配置](../configs/color_schemes.json)中；没有引入 Microduck 的模型、商标或网站源码。

壳色输入为 sRGB hex，渲染器按标准分段函数转换为线性 RGB：`c <= 0.04045` 时 `c / 12.92`，否则 `((c + 0.055) / 1.055)^2.4`。官网 viewer 的数值已经是线性 RGB，直接用于 Blender 的 Principled Base Color。AgX 色调映射、光照与显示设备会影响图片观感；这些数值是配色基准，未定义商业耗材色号或保证实物色差。

## 当前及后续交付的使用方式

[color_schemes.json](../configs/color_schemes.json)是这四种表面配色的唯一配置。材质语义映射到壳、主点缀、次点缀、镜头圈等角色；新机械版本保留这些角色后可直接重用。渲染入口是 [render_goose_color_schemes.py](../../../scripts/models/render_goose_color_schemes.py)，不修改主线构建脚本或默认物理模型。

在工作区根目录运行（`blender` 指向现有 Blender 4.0.2 安装）：

```bash
blender --background --threads 8 --python scripts/models/render_goose_color_schemes.py -- \
  --scene robots/Goose_V0.1/cad/source/mechanical_preview/scene.json \
  --geometry-root robots/Goose_V0.1 \
  --config robots/Goose_V0.1/configs/color_schemes.json \
  --output robots/Goose_V0.1/images/microduck_color_schemes \
  --manifest robots/Goose_V0.1/evidence/microduck_color_scheme_render_manifest.json \
  --resolution 1200 --samples 192
```

每次交付先重建该版机械 scene，再运行四色入口。不要把历史版本的一张图与新版的其他三张图混为同组。渲染器逐件核对源 NPZ 哈希，检查 quad 面，并在每款配色前核对顶点、拓扑和物体位置指纹；未知的新材质会要求显式补入角色映射。

本次使用冻结的 292 件几何快照，原渲染 scene SHA256 为 `69ee3a30d8a26b33d52c5268acdd880e0d1c5e9a84bb2f9002e9e729a9f55e74`。[渲染清单](../evidence/microduck_color_scheme_render_manifest.json)记录源配置、脚本、模型及每张图的哈希。随后低位姿态与源台账的元数据更新改变了 scene 文件哈希，原渲染记录保持不变；[当前几何身份核对](../evidence/microduck_color_current_model_identity.json)另行确认当前全部零件源哈希、Blender 顶点、quad 拓扑和位置指纹仍与这四张渲染一致。四张 1200 × 1200 图片的几何完全相同；镜头与灯光相同，192 samples，无 AI 图像生成或后期补造结构。
