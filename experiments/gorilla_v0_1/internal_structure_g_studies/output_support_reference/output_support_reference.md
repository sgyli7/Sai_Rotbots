# G：CSG-50/65-100-2UH 集成输出支承原厂复核

2026-10-02 UTC；独立、只读、有界研究。只覆盖本族已有型号与图纸，不是选型、装配或整机能力放行。G 引用 65×3（腰 yaw、左右髋 yaw）及 50×1（腰 roll）；位置、载荷和组件 owner 由主线程后续源绑定，不沿用 E2a witness。

## 原厂已知

CSG-2UH 是已包含交叉滚子输出轴承和负载法兰的完整齿轮单元；其公布质量已含该集成支承，不能将额外自建 races 再称为 OEM 必需内件。[原厂系列页](https://www.harmonicdrive.net/products/gear-units/gear-units/csg-2uh)

| 精确型号 | OEM单元质量 kg | 动基本额定 C N | 静基本额定 C0 N | 允许倾覆 Mc N·m | 平均倾覆 Km N·m/rad | 外径 / 完整轴向 mm |
|---|---:|---:|---:|---:|---:|---:|
| CSG-50-100-2UH | 8.9 | 34800 | 60200 | 759 | 1710000 | 190 / 98 |
| CSG-65-100-2UH | 20.9 | 55600 | 103000 | 1860 | 4040000 | 260 / 123.5 |

支承数值同时见 [50具体SKU](https://www.harmonicdrive.net/products/gear-units/gear-units/csg-2uh/csg-50-100-2uh)、[65具体SKU](https://www.harmonicdrive.net/products/gear-units/gear-units/csg-2uh/csg-65-100-2uh) 和本轮唯一下载的 [GENERAL目录](https://www.harmonicdrive.net/_hd/content/documents1/GENERAL-catalog.pdf) printed/PDF p50。p49 属 CSF-2UH、p51 属 CSG-2UH-LW，不能用其较低 Mc/Km 替换本表。C 的定义采用轴承一百万转基准；Km 是均值。目录 p50 的齿轮传动额定为 2000 rpm 输入、L10 10000 h（50/65 ratio100 为611/1236 N·m），这不等于输出轴承在任意外载荷下已有该寿命。C/C0 不是可独立叠加的径向、轴向允许力。

完整轴向由现有一页图纸量注组成：50 的主体90 + 左凸8 = 98；65 的主体115 + 左凸8.5 = 123.5。目录 B=90/115 不是整件最外包络。该包络不包括自建适配器、法兰螺栓、盖和检修间隙。[官方50图纸](https://www.harmonicdrive.net/_hd/Content/caddownloads/dxf/csg-2uh_gearheads/csg-50-xxx-2uh.pdf)、[官方65图纸](https://www.harmonicdrive.net/_hd/Content/caddownloads/dxf/csg-2uh_gearheads/csg-65-xxx-2uh.pdf)

## 接口及尚未证实的边界

| 图纸坐标接口 | 50图纸 | 65图纸 | 证据状态 |
|---|---|---|---|
| 左面 A | 8-M14×21，PCD84 mm | 8-M16×24，PCD110 mm | 孔位/螺纹深度已读图；OEM动静身份未核 |
| 右面 B | 14-M8 与14-Ø9，PCD174 mm | 8-M12 与8-Ø14，PCD236 mm | 孔位已读图；OEM动静身份未核 |
| 图示单元内部 | 完整齿轮壳/集成轴承/输出法兰 | 同左 | 产品集成事实；未取得分件CAD、质量/惯量归属 |

截面形状提示左侧负载法兰、右侧输入和外壳，但这是图像观察推断，不能转换成已验证的 parent/output/input owner。当前图纸与选用目录没有文字将 A/B 的每组孔与动静零件对应。网页 dp/R 分别显示 50 为0.11/0.01 m、65为0.16/0.02 m，精度不足；不得据此反算精确轴承压力中心。

该原厂集成支承形成负载法兰到壳安装的受力入口；径向、轴向及倾覆载荷路径仍需结合实际安装定义。当前已知只足以建立 Mc/Km 参照，不足以给单独 Fr/Fa 通过阈值、联合外载荷寿命或静安全系数。 selected p50 未公布组合等效载荷、寿命指数/系数、静安全系数建议、反转摆动/冲击修正、预紧或温度条件。搜索到的同族历史 engineering-data 地址本轮实际HTTP404，未采用其索引摘要。未展开第二目录或其他型号族。

未闭合：A/B动静身份；支承中心/力臂；安装螺栓等级、预紧、有效啮合与孔壁；负载法兰及自建壳刚度/平面度；组合载荷和冲击、摆动寿命/静裕量；润滑/温度；原厂内部 rotor/output/housing 质量和惯量分配。传动额定/瞬时峰值或 T0 均不能替代上述支承核查，集成支承也不是制动/保持器。

## 下一分析入口（自有计算定义，非厂家资格公式）

先取得 OEM 安装说明、精确剖面/载荷核查方法；再将 G 实际子体六维 wrench 转到真实轴承参考中心 B。自有向量恒等式为 `M_B = M_P + (P-B)×F`，按真实轴向 a 分出 `Fa=F·a`、`Fr=norm(F-Fa*a)`、`Mt=norm(M_B-(M_B·a)*a)` 与轴向传动力矩 `T=M_B·a`。Mc 仅用于倾覆分量初筛；`theta≈Mt/Km` 只是均值刚度的一阶估计，不是最坏挠度保证。Fr/Fa/Mt 的联合寿命、静安全系数及壳/螺栓强度仍需原厂对应程序和真实负载谱，不能由 `Fr<C0` 或 `T<gear rated` 放行。

额外支承是否必要由这些实际载荷、安装与变形共同决定；本研究不默认增加或删去其库存。若采用并联额外轴承，还需明确同轴公差、预紧与载荷分配，不能靠两个额定值相加形成完整承载证明。

## 来源文件、版本与复现

- 唯一新增目录缓存 `harmonic_drive_general_catalog.pdf`：5427242 bytes，SHA256 `329e507030de3d7f8fa5d02aaa27f3da1fe8d97026eec7b3116acbb5d0de8e44`；元数据创建/修改2026-07-14 UTC，88页；不以PDF生成日期充当厂家产品规格发布日期。支承表为 printed/PDF p50，本地同尺度截图 `catalog_printed_p50.png`。
- 复用50原图 `/home/ethan/Projects/Sai_Rotbots/.scratch/gorilla_internal_d_root_sources/csg50.pdf`：30418 bytes，SHA256 `9e3f4734f222b9f33aa95b2b064fc2942044c379a8cdd4dc5481030030aff527`。
- 复用65原图 `/home/ethan/Projects/Sai_Rotbots/.scratch/gorilla_internal_c_drive/csg65_drawing.pdf`：29562 bytes，SHA256 `7dc806d1b5bb4b5ca822f8e204753cf525b950d563d4473728a14545cabb1875`。
- 两图元数据创建2006-12-12、修改2017-07-27（本地显示CST）；本轮官方索引实际提供同名链接。图纸没有独立明确的当下设计修订号；现有文件hash锁定读取版本，不能宣称与未来供货一致。
- 2026-10-02实际访问的官方页面HTML缓存/URL/HTTP状态/哈希见 `source_manifest.json`。下载文件只在 ignored scratch，未注册、未提交表单、未申请CAD；未取得厂家三维内部装配CAD。本轮来源文字概括保持精简，事实表与自有分析条件分开。

复现本地读取：

```bash
pdftotext -layout .scratch/gorilla_internal_g_output_support_reference/harmonic_drive_general_catalog.pdf .scratch/gorilla_internal_g_output_support_reference/harmonic_drive_general_catalog.txt
pdftoppm -f 50 -singlefile -scale-to 2200 -png .scratch/gorilla_internal_g_output_support_reference/harmonic_drive_general_catalog.pdf .scratch/gorilla_internal_g_output_support_reference/catalog_printed_p50
sha256sum .scratch/gorilla_internal_g_output_support_reference/harmonic_drive_general_catalog.pdf .scratch/gorilla_internal_d_root_sources/csg50.pdf .scratch/gorilla_internal_c_drive/csg65_drawing.pdf
```

G root 后续必须绑定真实场景版本、轴向堆叠与载荷；此页没有宣称任一 G 关节或机器人已通过。
