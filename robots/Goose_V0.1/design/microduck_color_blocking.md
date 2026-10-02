# Microduck 色块分区重做

**历史 292 件版本。** 下文四图、配置和渲染身份保留，未经用户最终审美验收；[314 件配色候选](microduck_color_blocking_314_parts.md)亦作为历史保存，当前同版四图见 [344 件配色候选](microduck_color_blocking_344_parts.md)。不同版本图片不能混为一组。

状态：**四图配色候选，待用户验收**。这次重新划分了整机颜色面积，而不是把所有机壳、叉架和隔撑染成同一个壳色。上一版[已否决的配色](microduck_color_schemes.md)及其图片、配置、渲染哈希保留。

| 色块 | 四款共同关系 |
|---|---|
| 头部、躯干主壳 | Cream 奶油白 / Graphite 石墨灰 / Lavender 薰衣草紫 / Sky 天空蓝 |
| 翼形检修门、头部正面 | 中性灰面，与彩色主壳区分 |
| 颈部和腿的叉架 | 哑光深灰，执行器略深；隔撑及连接面保留中性金属色 |
| 嘴、整个既有脚上罩、脚承载板与鞍座 | Cream / Sky 橙色；Graphite / Lavender 黄色 |
| 鞋边、镜头圈 | Cream / Sky 黄；Graphite 紫；Lavender 紫鞋边与青蓝眼圈 |
| 接触脚底、夹持胶垫、镜片 | 黑色功能材质 |

四张 1200 × 1200 实际模型图：

- [Cream 奶油白](../images/microduck_color_blocking/cream.png)
- [Graphite 石墨灰](../images/microduck_color_blocking/graphite.png)
- [Lavender 薰衣草紫](../images/microduck_color_blocking/lavender.png)
- [Sky 天空蓝](../images/microduck_color_blocking/sky.png)

## 参考依据与调整

实际查看了 [Pollen 官方四机合照](https://pollen-robotics.com/assets/microduck/squad.webp)、[四色实物坐姿](https://pollen-robotics.com/assets/microduck/gallery/chorale-poster.jpg)、[Cream 近照](https://pollen-robotics.com/assets/microduck/gallery/closeup.webp)及[实物桌面照片](https://pollen-robotics.com/assets/microduck/gallery/desk.webp)。共同关系是深色颈腿骨架、中性连接件、彩色外壳、较完整的鲜明脚面及次色鞋底/镜头圈。此次按这些关系映射现有 Goose 零件；不复制 Microduck 的几何。

四个壳色继续采用[官方 Press kit](https://pollen-robotics.com/microduck/press-kit/)校准 swatch：`#f7e6cb`、`#6c6a68`、`#bfa9cf`、`#a9dbe8`。嘴、鞋、镜头圈等采用实物照片色彩家族的设计配色，**不称为官方准确的耗材/喷漆色号**。涂装中新增的中性检修门分区属于 Goose 本轮审美调整。

为让镜头圈存在感更明确，在既有灰色脸板上增加环形表面涂装：半径 16.7–22.5 mm。镜片、开孔和镜头实际尺寸不变；没有新增壳或假装换了更大镜头。

## 几何与显示法线

仍使用同一 292 件冻结机械快照，source scene SHA256 为 `69ee3a30d8a26b33d52c5268acdd880e0d1c5e9a84bb2f9002e9e729a9f55e74`，2,414,924 个 quad 面。每次切换配色重新核对坐标、面拓扑和物体位置指纹，四款保持一致。

旧渲染入口按角色排除曲面壳的 Weighted Normal；原生前半壳开孔后换成通用角色，导致被误加面积加权法线。新入口按壳体分组排除该 modifier。前半壳的 CAD 三角细分 quad 仍会形成中心法线分区，因此额外用原 `morphology.body_grids` 体型轮廓导数生成近似显示法线，按现有顶点映射至曲面内/外侧，切孔及安装窗口边缘保留原法线。该近似显示处理不能用来证明 CAD 没有缺陷、不能作为制造曲面验证。此项**只修显示法线，不移动顶点、不重拓扑、不改变原生 CAD/STL、碰撞或质量**。显示法线文件记录了对应几何 SHA，未来改变体型时必须重新生成，不能沿用旧场。

灯光能量、曝光与表面粗糙度也作了调整，以降低上轮高光顶白。四图同镜头、灯光和设置；没有 AI 图像生成或后期补造零件。

## 当前及后续交付

[microduck_color_blocking.json](../configs/microduck_color_blocking.json)保存新的角色映射、表面涂装、灯光和显示法线身份；[render_goose_color_blocking.py](../../../scripts/models/render_goose_color_blocking.py)是独立渲染入口。原机械脚本和物理参数不受影响。

未来改变前半壳或体型轮廓时，先运行 [build_goose_display_normals.py](../../../scripts/models/build_goose_display_normals.py) 重新生成该版近似显示法线，再渲染四色。此步骤已复现本轮相同法线/配置哈希；不会覆盖原生 CAD 或几何源：

```bash
python scripts/models/build_goose_display_normals.py
```

```bash
blender --background --threads 8 --python scripts/models/render_goose_color_blocking.py -- \
  --scene robots/Goose_V0.1/cad/source/mechanical_preview/scene.json \
  --geometry-root robots/Goose_V0.1 \
  --config robots/Goose_V0.1/configs/microduck_color_blocking.json \
  --output robots/Goose_V0.1/images/microduck_color_blocking \
  --manifest robots/Goose_V0.1/evidence/microduck_color_blocking_render_manifest.json \
  --resolution 1200 --samples 160
```

[渲染清单](../evidence/microduck_color_blocking_render_manifest.json)记录同版几何、配置、脚本与四张图的哈希。此配色候选不构成制造放行、已选商业材料或用户美感验收；涂层重量未单独计入机械账本。

[像素与身份检查](../evidence/microduck_color_blocking_pixel_validation.json)也核对当前 live scene 与冻结快照的全部零件数据相同。主线后来更新了 `source_hashes` 元数据，故 live scene 文件哈希变化；这没有改变本轮四图的几何。第一版配置、脚本、原四图的哈希保持原样。
