# 344 件机械候选的 Microduck 四套配色

状态：**实际模型的配色预览，待用户审美验收；不是制造最终外观**。

本轮使用主线包含可替换夹持垫匣与上喙安装紧固件的 344 件模型。名义条件质量 `10.35785617008905 kg` 仅引用机械源以标识版本。配色任务没有修改 CAD 几何、轴位、质量、惯量、碰撞或控制契约。

四图均为实际 Blender 渲染，使用同一份源几何、同一镜头和灯光，输出 1200 × 1200 PNG：

- [Cream 奶油白](../images/microduck_color_blocking_344_parts/cream.png)
- [Graphite 石墨灰](../images/microduck_color_blocking_344_parts/graphite.png)
- [Lavender 薰衣草紫](../images/microduck_color_blocking_344_parts/lavender.png)
- [Sky 天空蓝](../images/microduck_color_blocking_344_parts/sky.png)

## 色块关系与参考

本轮重新实际查看官方 [Microduck 四色实物合照](https://pollen-robotics.com/assets/microduck/squad.webp) 与 [Cream 近景实物](https://pollen-robotics.com/assets/microduck/gallery/closeup.webp)。保留共同关系：彩色壳、中性面、深色机械、显眼的嘴脚主点缀，以及鞋边和镜头圈次色。四款名称及主壳色来自官方 [Press Kit](https://pollen-robotics.com/microduck/press-kit/)，完整资料来源及线性 RGB / sRGB 处理沿用配置中的 `sources` 与 [历史配色研究说明](microduck_color_blocking.md)。

| 部位 | Cream / Sky | Graphite | Lavender |
|---|---|---|---|
| 头壳与身体主壳 | 奶油白 / 天空蓝 | 石墨灰 | 薰衣草紫 |
| 翼形检修门、相机脸板 | 中性灰 | 中性灰 | 中性灰 |
| 颈腿叉架、内承力骨架、电机 | 深灰 / 黑 | 深灰 / 黑 | 深灰 / 黑 |
| 嘴壳、全幅既有鞋罩、鞋鞍座及承载板 | 橙色 | 黄色 | 黄色 |
| 鞋边 | 金黄 | 紫色 | 紫色 |
| 镜头圈及脸板环形涂装 | 金黄 | 紫色 | 青色 |
| 金属连接件 / 橡胶夹持垫和接地层 | 中性金属 / 黑 | 中性金属 / 黑 | 中性金属 / 黑 |

新增 `upper_grip_shell` / `lower_grip_shell` 归嘴部主点缀；载体与上夹持骨架归深色结构，下夹持金属骨架保留金属色，橡胶垫保持黑色，安装螺钉螺母保持金属色。四套配色没有将所有结构直接染成主壳色，也没有遮去实际机械件。

本轮不增加碎片化装饰。大色块与清晰镜头圈用于保留亲和表情；萌感仍由用户验收。为看清暗色结构，将统一侧前补光由 12 W 增至 20 W，主光、曝光及哑光材质保持原值，避免以高光烫白来换取明亮。

## 源身份与显示限制

冻结 scene 的 SHA256：`bcaf85208c96d55d563cc659a48732ab4326210a0a8849d8eb6870022e6f7cb7`。逐件几何 SHA、颜色角色及每张图片 SHA 见 [渲染清单](../evidence/microduck_color_blocking_344_parts_render_manifest.json)；源和历史完整性、像素尺寸、本地链接及角色检查见 [验证记录](../evidence/microduck_color_blocking_344_parts_pixel_validation.json)。

四图均为 344 件、5,765,656 顶点、5,766,994 quads，几何指纹 `a4d0374ef276f8d238a85778f536e1a60edc0f71c353743303d02d8e1ed4a295` 一致。现行 scene 与冻结源完全相同，311 份外部几何依赖及显示法线绑定已核验，四张原图均已实际查看；314 件、292 件及第一次被否决配色的配置、原入口、四张 PNG 哈希均保持不变，46 个本地资料链接可解析。

躯干前半壳沿用绑定原几何 SHA 的轮廓导数**近似显示法线**；切孔和安装窗口保留原边缘法线。头壳、喙壳与翼门排除 Weighted Normal，仅作显示平滑，不使用改变顶点的平滑、细分或位移。这类显示处理不能证明 native CAD 没有曲面缺陷；头壳局部原曲面法线过渡仍需后续制造曲面审查。

镜头可见彩圈的一部分是既有脸板环形涂装，没有扩大实际镜片或镜头开孔。主壳外的辅色是参考实物照片及官方 viewer 后的设计适配，未经耗材或喷漆实物色差标定；涂层质量未单独加入机械账本。

## 复用与历史

本轮独立配置：[microduck_color_blocking_344_parts.json](../configs/microduck_color_blocking_344_parts.json)。入口：[render_goose_color_blocking_344_parts.py](../../../scripts/models/render_goose_color_blocking_344_parts.py)。

```bash
blender --background --threads 8 --python scripts/models/render_goose_color_blocking_344_parts.py -- \
  --scene robots/Goose_V0.1/cad/source/mechanical_preview/scene.json \
  --geometry-root robots/Goose_V0.1 \
  --config robots/Goose_V0.1/configs/microduck_color_blocking_344_parts.json \
  --output robots/Goose_V0.1/images/microduck_color_blocking_344_parts \
  --manifest robots/Goose_V0.1/evidence/microduck_color_blocking_344_parts_render_manifest.json \
  --resolution 1200 --samples 160
```

[314 件历史四色图](microduck_color_blocking_314_parts.md)、[292 件历史四色图](microduck_color_blocking.md)和[被用户否决的第一次配色](microduck_color_schemes.md)继续保留，原图与原配置不覆盖。后续机械模型继续沿用相同表面角色，在对应版本生成独立四图及源身份；形状改变时不得直接套用旧几何绑定的显示法线。
