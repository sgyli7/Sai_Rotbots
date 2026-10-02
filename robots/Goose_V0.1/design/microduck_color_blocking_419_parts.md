# 419 件独立制造候选的 Microduck 四套配色

状态：**制造候选的实际几何配色预览，审美验收待定**。本组不是最终实体一比一放行，也不替换默认 344 件模型。

本轮仅为 `cad/source/integrated_hardware_candidate/scene.json` 添加独立表面配色和渲染交付。其名义条件质量 `10.4024039317658 kg` 直接引用机械源，用于版本识别；没有改动几何、质量账本、关节、碰撞或控制契约。源仍标记制造、整体干涉与最终外观验收未通过，未作为训练放行版本。

四张 1200 × 1200 实际 Blender 图使用同一份完整 419 件源、同一镜头和灯光：

- [Cream 奶油白](../images/microduck_color_blocking_419_parts/cream.png)
- [Graphite 石墨灰](../images/microduck_color_blocking_419_parts/graphite.png)
- [Lavender 薰衣草紫](../images/microduck_color_blocking_419_parts/lavender.png)
- [Sky 天空蓝](../images/microduck_color_blocking_419_parts/sky.png)

## 分区与 344 件版的区别

继续采用 [344 件分区规则及官方来源](microduck_color_blocking_344_parts.md)：彩色头壳/身体主壳、中性灰翼门和相机面、深灰叉架与黑色电机、金属连接件、明亮嘴脚，以及鞋边/镜圈次色。嘴、既有完整鞋上罩、承载板与鞍座使用主点缀，骨架不随主壳全部染色。

| 方案 | 主壳 | 嘴脚 | 鞋边 | 镜头圈 |
|---|---|---|---|---|
| Cream | 奶油白 | 橙 | 金黄 | 金黄 |
| Graphite | 石墨灰 | 黄 | 紫 | 紫 |
| Lavender | 薰衣草紫 | 黄 | 紫 | 青 |
| Sky | 天空蓝 | 橙 | 金黄 | 金黄 |

原有主辅色值、哑光材料与摄影参数未改。新 `camera_open_face` 映射到中性相机面，`camera_open_eye_bezel` 映射到相应方案镜圈色；保留真实开孔与安装轮廓。既有 `camera_lens_proxy` 使用暗色光学显示材质，**仍是尺寸代理件，不能据此称为完整厂商镜片模型**。新增电源/计算载体与固定件使用既有深色结构或中性金属规则，未增添零散装饰。

419 件源相对冻结的 344 件源增加 81 件、移除 6 件，并替换 6 个同名嘴尖壳/载体/垫片的几何。这些差异全部来自主线机械候选，不由配色脚本产生。新增件主要为相机安装、电源和计算固定件；原相机脸板/镜圈/镜片显示件及两处旧承力件由主线对应候选取代。源明确说明商业 PCB 线路、接头与线束没有完整纳入显示，外壳遮挡内部新增件属于当前完整装配视角。

## 身份、验证与显示限制

冻结 scene SHA256：`bce7ee34419f7cb0898d4e5da14ceba5c6db4f4081f9b659ab00e4491d75d4ab`。

[渲染清单](../evidence/microduck_color_blocking_419_parts_render_manifest.json)记录逐件源 SHA、材质角色、完整顶点/quad/位置指纹、镜头与渲染参数、四张图片 SHA。[验证记录](../evidence/microduck_color_blocking_419_parts_pixel_validation.json)记录四图存在及同版核验、默认 344 件和历史版本哈希保护、显示法线绑定和本地链接检查。

四张完整图片均已实际查看。每图对应 419 件、5,975,202 顶点、5,976,574 quads，统一几何指纹 `951518202cc558b804e2047939210a506442e0dc2ec727452b9b7c8a34e414e7`。390 份外部几何依赖与显示法线绑定核验通过，四图均为 1200 × 1200。现行 419 件源与冻结源字节一致；默认 344 件 scene 未变，344 / 314 / 292 件及第一次被否决配色的原配置、脚本和四图哈希均未变化，本文 12 个本地链接可解析。

显示处理仅限材质和法线：躯干前半壳沿用绑定同一几何 SHA 的轮廓导数近似显示法线，切孔/安装边缘保留原法线；头壳、嘴壳、翼门及新相机脸板/镜圈排除 Weighted Normal。没有用细分、位移或网格平滑 modifier 改动顶点。近似显示法线不证明 native CAD 曲面质量或制造可用性；头壳局部法线过渡仍保留。镜圈部分视觉面积来自现有脸板环形涂装，没有扩大实体开孔或镜片。

实际预览中，新相机开孔面板相较 344 件版更外凸，头壳开口与镜片尺寸代理的间隙更可见。这是新机械源的外观差异，配色脚本没有遮盖或修补。相机面板与头壳的具体空间关系需由主线继续审查；配色交付不将它标为最终外观通过。

四套名称及主壳 sRGB 依据官方 [Press Kit](https://pollen-robotics.com/microduck/press-kit/)；色块对应关系参考 [官方四色实物合照](https://pollen-robotics.com/assets/microduck/squad.webp)与实物近景。辅色是据实物和官方 viewer 的设计适配，未标定打印耗材/喷漆实际色差。涂层质量未单独纳入机械质量账本。

## 复现与默认版保留

专用配置：[microduck_color_blocking_419_parts.json](../configs/microduck_color_blocking_419_parts.json)。独立入口：[render_goose_color_blocking_419_parts.py](../../../scripts/models/render_goose_color_blocking_419_parts.py)。

```bash
blender --background --threads 8 --python scripts/models/render_goose_color_blocking_419_parts.py -- \
  --scene robots/Goose_V0.1/cad/source/integrated_hardware_candidate/scene.json \
  --geometry-root robots/Goose_V0.1 \
  --config robots/Goose_V0.1/configs/microduck_color_blocking_419_parts.json \
  --output robots/Goose_V0.1/images/microduck_color_blocking_419_parts \
  --manifest robots/Goose_V0.1/evidence/microduck_color_blocking_419_parts_render_manifest.json \
  --resolution 1200 --samples 160
```

[默认 344 件四图](microduck_color_blocking_344_parts.md)、[314 件历史图](microduck_color_blocking_314_parts.md)及 [292 件历史图](microduck_color_blocking.md)完整保留，不覆盖原配置、原脚本或图片。本次不编辑机器人 README、计算模块文档或主线集成说明。
