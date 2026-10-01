# 314 件机械候选的 Microduck 四种配色

**历史 314 件版本。** 本文原图、配置及渲染身份保留；当前夹持垫匣与安装紧固件候选的同版四图见 [344 件配色候选](microduck_color_blocking_344_parts.md)。不能将不同版本的图片混为一组。

状态：**实际机械候选的配色预览，待用户审美验收；不是制造最终外观**。

主线将原生上下喙骨架及轴向锁固候选合入后，本次使用同一份 314 件 scene 重渲染四种配色。条件质量 `10.342345692378164 kg` 来自该 scene 的机械账本，仅用于版本识别；此配色任务没有计算或变更质量、惯量、碰撞、轴位、控制参数或 CAD 几何。

四张实际 Blender 图均为 1200 × 1200、160 samples，使用同一镜头、灯光和几何：

- [Cream 奶油白](../images/microduck_color_blocking_314_parts/cream.png)
- [Graphite 石墨灰](../images/microduck_color_blocking_314_parts/graphite.png)
- [Lavender 薰衣草紫](../images/microduck_color_blocking_314_parts/lavender.png)
- [Sky 天空蓝](../images/microduck_color_blocking_314_parts/sky.png)

沿用 [292 件版本的色块关系及官方实物参考](microduck_color_blocking.md)：彩色主壳、中性灰检修门/脸板、深灰颈腿骨架、中性金属连接件、橙/黄嘴脚，以及黄/紫鞋边和黄/紫/青镜头圈。之前近乎单色且被用户否决的[第一次配色](microduck_color_schemes.md)仍保存为历史。

| 当前新增或替换部件 | 本次表面角色 |
|---|---|
| `head_retention_access_shell_right`、`head_bill_access_shell_left` | 四款主壳色 |
| `upper_bill_retention_shell`、`lower_bill_backbone_shell` | Cream / Sky 橙色，Graphite / Lavender 黄色 |
| 喙骨架、头部承力框及保持盖 | 深色结构或原有中性金属色 |
| 原翼形门、脸板、嘴脚及镜头圈 | 保留相应的主/辅色分区 |

## 同版源身份与显示处理

本轮冻结 scene 的 SHA256 为 `2757ef91a6c7f40d98106d5fd9b067c9ca709c246dded3cdae3bac83e967926c`。[渲染清单](../evidence/microduck_color_blocking_314_parts_render_manifest.json)逐件记录几何源 SHA、表面角色、完整顶点/quad 拓扑/位置指纹及每张图片的 SHA。

四图均为 314 件、5,074,940 顶点、5,076,268 quads，几何指纹 `e4f51a9b5f13f3c0312017f2bb954e6c169d4cfe6bd9ce55ab5aeab4b6c2557e` 相同。[像素与身份检查](../evidence/microduck_color_blocking_314_parts_pixel_validation.json)核验了现行源与冻结源一致、279 份外部几何依赖、各图 1200 × 1200 尺寸、新部件的表面角色，以及历史 292 件配置/入口/四图哈希均未改变。四张原图均已实际查看；局部头壳仍可见原曲面的法线分区，本次未修改其几何。

新头壳和喙壳均排除面积加权法线，只保留曲面 smooth 与边缘法线；没有通过平滑、细分或位移 modifier 改变顶点。躯干前半壳沿用原体型轮廓导数产生的**近似显示法线**，其对应源几何未变，因此场文件未重写。切孔及安装窗口边缘继续保留原法线。

这类近似显示处理不能证明 CAD 无缺陷，也不构成制造曲面验证。镜头圈的可见扩展仍是既有脸板的环形涂装，未改变镜片、开孔或壳尺寸。涂层重量未单独计入机械账本，商业喷漆/打印耗材色号尚未选定。

## 复用与历史

本轮独立配置为 [microduck_color_blocking_314_parts.json](../configs/microduck_color_blocking_314_parts.json)，入口为 [render_goose_color_blocking_current.py](../../../scripts/models/render_goose_color_blocking_current.py)。历史 292 件版本的配置、原渲染入口和四图原样保留，历史渲染哈希不覆盖。

```bash
blender --background --threads 8 --python scripts/models/render_goose_color_blocking_current.py -- \
  --scene robots/Goose_V0.1/cad/source/mechanical_preview/scene.json \
  --geometry-root robots/Goose_V0.1 \
  --config robots/Goose_V0.1/configs/microduck_color_blocking_314_parts.json \
  --output robots/Goose_V0.1/images/microduck_color_blocking_314_parts \
  --manifest robots/Goose_V0.1/evidence/microduck_color_blocking_314_parts_render_manifest.json \
  --resolution 1200 --samples 160
```

后续机械版本继续使用相同的表面角色规则，并建立该版独立四图及源身份记录。若改变躯干形状，先用 [build_goose_display_normals.py](../../../scripts/models/build_goose_display_normals.py) 针对该版 scene/config 重建显示法线；源 SHA 不符时不得直接套用旧场。
