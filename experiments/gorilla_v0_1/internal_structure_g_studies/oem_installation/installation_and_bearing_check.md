# G1：CSG-50/65-100-2UH 安装身份与联合支承核查

2026-10-02 UTC。只读补齐；只新增一份原厂 CSF/CSG 工程安装文档。没有改 G、旧研究、模型或配置，没有进行选型或整机放行。

## 本次补齐的安装事实

唯一原始来源：[CSF & CSG Component Sets / Housed Units](<https://www.harmonicdrive.net/_hd/content/documents1/CSG-CSF_GearUnits.pdf>)，封底明确 `TI-26024 REV 1 CSF-CSG Catalog 072026`、July 2026；52页，printed页码与PDF一基页码一致。p5 标注 case/circular spline、input/wave generator、flexspline/output flange；p6 标准减速配置固定 CS、输入 WG、输出 FS。p33 明确轴承内圈形成输出法兰。p36 剖面直接标明左面为输出法兰、右外壳为 case，p37 接口表与现有图纸孔距对应。

| 现有图纸接口 | CSG-50-100-2UH | CSG-65-100-2UH | 现已可采用的机械身份 |
|---|---|---|---|
| A：左面小节圆负载孔 | 8-M14×21、PCD84 mm | 8-M16×24、PCD110 mm | 输出法兰 / OEM bearing inner race / FS输出侧，绑定输出负载体 |
| B：右侧大节圆安装孔 | 14-M8及14-Ø9、PCD174 mm | 8-M12及8-Ø14、PCD236 mm | 固定 case / circular spline侧，绑定parent安装壳 |
| 右侧中心输入接口 | 具体加工尺寸须绑定对应drawing | 同左 | wave generator输入，绑定电机转子/联轴器，不能并入fixed壳 |

这是原厂标注与精确孔距相互校准的接口身份。它没有提供 OEM内部每片材料、旋转件拆质量或惯量；一个完整gear envelope仍不能全部作为固定刚体或全部作为输出体。OEM轴承由完整8.9/20.9 kg单元质量涵盖，不能再重复计为附加races；自建额外支承是否必要仍由真实载荷/安装评估决定。

p37 Table33 的50壳侧写12×M8，然而同文p33 Table29 明确区分 CSF12 / CSG14，且现有CSG50图纸为14。故 B身份可用，12孔那行的整组传扭容量不能直接套给CSG14孔。现有50/65裸包络仍按原图 Ø190×98 / Ø260×123.5 mm；所有适配板、密封、螺栓和维修间隙另计。

## 支承平面、已公布参数

同文 p33 Table30 与先前标准CSG-2UH原厂SKU/p50目录能力相符；不得混CSF/LW/GH版本。

| 尺寸 | dp m | R m | C N | C0 N | Mc N·m | Km N·m/rad（平均） |
|---|---:|---:|---:|---:|---:|---:|
| 50 | .119 | .0180 | 34800 | 60200 | 759 | 1710000 |
| 65 | .160 | .0225 | 55600 | 103000 | 1860 | 4040000 |

p34 Fig6：dp是输出轴承滚子节圆直径；R为负载安装法兰基准面至轴承节圆中心平面的轴向偏置，朝case内部。Lr从同一法兰基准面向外量到径向力作用位置，La为轴向力作用线的径向偏距。不能把R当几何圆柱中心距，也不能将已经转到真实轴承中心的wrench再重复加一次R。宏观圆柱若尚未具备原厂法兰安装基准面，仍需用该drawing显式定义，不能只依中心猜位置。

## 原厂计算入口与条件

以下均为该唯一原始文档 p34–35 的字段/公式；单位 Fr/Fa为N、长度为m、M为N·m、速度为rpm、寿命为h。

- p34 最大倾覆筛查：`Mmax = Frmax*(Lr+R) + Famax*La`，核 `Mmax ≤ Mc`。这是图示同平面、最大值标量相加入口；任意六维力旋量先按真实轴承平面变换，不能把轴向传动扭矩代入Mc。
- p34 Eq11/12：`Fav = (Σ(n_i*t_i*|F_i|^(10/3))/Σ(n_i*t_i))^(3/10)`，分别用于径向/轴向荷载；原图用每时段最大值，不是任意时间均方根。反向运动的转数权重应采用非负累计转数；这是实现时的自有解释，原文没有给任意矢量旋转/符号转换程序。静止时段仍应接受静力核查。
- p34 List2：令 `Mav = Frav*(Lr+R) + Faav*La`，`q=Faav/(Frav+2*Mav/dp)`；q≤1.5 时 X=1/Y=.45，q>1.5 时 X=.67/Y=.67；零分母应单独处理。
- p35 Eq17/19：`P0=Frmax+2*Mmax/dp+.44*Famax`，`fs=C0/P0`。一般条件下的下限表为：不旋转轻摆 .5、冲击1–1.5；旋转正常1–2、冲击2–3。该表不是 Gorilla 高难度任务的自动安全系数选择。
- p35 Eq15：`L10=1e6/(60*Nav)*(C/(fw*Pc))^(10/3)`；fw参考稳态无冲击1–1.2、正常1.2–1.5、冲击振动1.5–3。
- p35 Eq18：往复摆动 `Loc=1e6/(60*n1)*(90/phi)*(C/(fw*Pc))^(10/3)`，phi为摆动总角度的一半、单位度；n1为每分钟往复数。小于5°摆动存在润滑不能充分循环/微动腐蚀条件；不能用摆动寿命式忽略该边界。Nav/n1或phi为零时不使用除零公式“证明”无限寿命。

### 原始公式的实际印刷缺陷，不能静默修正

p35 Eq16 在真实PDF图像中印为 `Pc_printed = X*(2*Mav/dp)+Y*Faav`，没有 Frav 项；但 p34 List2 分母明确是 `Frav+2*Mav/dp`。一个非零纯径向荷载、轴承中心倾覆为零的例子会令印刷Pc=0，与基本径向额定载荷定义矛盾。p34 Eq13 的速度平均分母也印为相邻 `t1 t2 ... +tn`，缺少求和连接符。以上均已实际读取PNG，不是OCR误识。

可供探索的自有条件修补为 `Pc_candidate=X*(Frav+2*Mav/dp)+Y*Faav` 和 `Nav_candidate=Σ(n_i*t_i)/Σ(t_i)`，但尚未取得厂家勘误或确认，本页不将其称为已证原厂公式。机器数据同时保留印刷式、候选式、零径向反例；不得从候选式生成正式寿命放行。静态Eq17/19可作本族参考筛查，但依然需要真实安装中心、最大组合载荷、冲击类别和结构约束。

## 安装传扭条件与未闭合事项

p37 Table32：50输出侧8×M14，拧紧205 N·m/螺钉、表列传扭3070 N·m；65输出侧8×M16，319 N·m/螺钉、5480 N·m。65壳侧8×M12，128 N·m/螺钉、表列6310 N·m。50壳侧Table33的12×M8、37 N·m/螺钉、3040 N·m仅保存为与CSG14孔不符的表行，不能直接采用。所有这些是安装连接传扭参照，既不是输出bearing Mc，也不是整个关节持续电驱能力。

表列条件为 JIS B1176螺钉、文中JIS B1051强度12.9或以上、扭矩系数K=.2、clamp coefficient A=1.4、结合面摩擦系数 .15，且螺纹材料必须承担夹紧力；p32警告螺钉啮合不得超螺孔深度。没有提供自建壳的螺纹拉脱、偏载剥离、弯剪、疲劳或实际摩擦认证。p36精度表正文写CSF-2UH，因此其具体公差数值不自动作为当前CSG制造合格依据；接口公差仍要最终供应drawing确认。

本族装配资料允许 root 明确 A/B/WG机械接口身份并开展条件探索/仿真，不证明真实制造与热连续能力。仍待关闭：①真实法兰/支承平面与G轴位绑定；②全任务受载与冲击/摆动谱及厂家公式勘误；③螺栓预紧、螺纹/承载壳/局部结构；④润滑、密封、温度；⑤OEM内部输入/输出/固定件质量与惯量分配。Root给出的880.424 kg上身及471 N·m重力倾覆只是敏感性输入，本页未代入并放行，也没有沿用E2a负载见证。

## 缓存与复现

原PDF只在 ignored `.scratch/gorilla_internal_g1_oem_installation/csg_csf_gear_units.pdf`：1374130 bytes，SHA256 `517160deff3bc6272980fef807212d29ee2301ce819b4388df540fcd3ce7d97b`；PDF元数据2026-07-14，封底正式版本另已读。原图50/65路径与哈希继承 G receipt，没有重新下载图纸；详见 `source_manifest.json`。没有注册/表单/CAD下载或第二工程目录。

实际查看的页面PNG：5、6、32–37；源内容未修改。复现命令：

```bash
pdftotext -layout .scratch/gorilla_internal_g1_oem_installation/csg_csf_gear_units.pdf .scratch/gorilla_internal_g1_oem_installation/csg_csf_gear_units.txt
pdftoppm -f 32 -l 37 -scale-to 2200 -png .scratch/gorilla_internal_g1_oem_installation/csg_csf_gear_units.pdf .scratch/gorilla_internal_g1_oem_installation/doc_page
sha256sum .scratch/gorilla_internal_g1_oem_installation/csg_csf_gear_units.pdf
```
