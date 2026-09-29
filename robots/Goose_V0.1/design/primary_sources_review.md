# Goose V0.1 一手资料核对

检索日期：**2026-09-28（Asia/Chongqing）**。本记录核对已引用器件与 Microduck 上游的公开文档、源码和实际下载响应；不冻结 Goose 的结构、供电、关节接口或 RL 方案，不作为实物性能验收。

## 范围与证据口径

- **事实**：本轮实际读取的官方页面、固定提交源码或文件内容。尺寸单位换算、文件数量及摘要是可复算结果。
- **估算**：供应商明确标为 estimated 的数值，保留其条件和计算方法。
- **假设／未取得**：尚未取得完整图纸、版本、许可或实测依据；不得把候选器件、索引页、渲染图、STEP 下载入口当成已完成的制造交付。
- 上游代码只做文本读取，未运行训练、推理或控制代码。供应商文件只在内存中读取或解析，未复制到本项目正式 CAD、mesh 或采购交付目录。

本地背景已读：[beak_r2.md](beak_r2.md)、[walker_structure.md](walker_structure.md)、[conversation_handoff.md](conversation_handoff.md)。当前本地候选为 12 个 XC330-M288-T、6 个 XL330-M288-T，共 18 个执行器；两腿各 5 个，颈／头 7 个，嘴 1 个。这是本地设计上下文，不是上游 Microduck 的配置。

| 本地输入 | 本轮读取时 SHA-256 |
|---|---|
| `beak_r2.md` | `80603f26cccc69fb4f6b82be0d4e792bf5272df4789d158fad531bc785d873a7` |
| `walker_structure.md` | `2c020be82132ddf129dbfda9f5507982950aa0600f8a10e9c97c8f7f19dbda9e` |
| `conversation_handoff.md` | `d47c540d6ba669d053f0a6a6ef3a7eb01d7a64280aa92ac749e85ba2aa5b99e8` |

这些摘要只标识本轮事实核对的输入版本；其他评审可能继续更新本地文档。

## 对工程构建影响最大的已核差异

1. **Microduck 的源码交付并不是完整制造 CAD 包。** 固定提交中确有 MJCF 和真实 STL；未找到 URDF 或 STEP／原生装配 CAD。导出配置引用一个 Onshape 工作区，但本轮没有取得其可编辑 CAD、固定版本或独立制造资产许可。
2. **Microduck 与 Goose 的执行器／策略接口不同。** 上游是 15 个总线关节、策略控制 14 个关节、嘴另控，观测 61 维、动作 14 维；当前 Goose 候选是 18 个执行器。上游的顺序、关节限位和策略权重不能默认为 Goose 的接口。
3. **官方标准供电与上游实现存在明确差异。** XL330-M288-T 和 XC330-M288-T 官方输入为 3.7–6.0 V、推荐 5 V；Microduck 的代码使用 2S 电池电压，电池显示常量为 6.6–8.2 V，且关闭输入电压错误触发的 shutdown。该上游做法不等于供应商批准的标准工作范围。
4. **堵转力矩、供应商估算连续力矩与实测连续能力必须分开。** 5 V 下 XL330 为 0.52 N·m／1.47 A，XC330 为 0.93 N·m／1.80 A，均为堵转项。官方商店另外给出 0.10／0.186 N·m 的 estimated rated torque，注明按堵转的 20% 估算；不是本机器人工况下的热稳定实测。
5. **B0292 页面已混入不同 SKU。** 原始 B0292 数据表是 38 × 38 mm、5 V 最大 200 mA；当前选择器包含 B0292-1 与 B029202，后者是 32 × 32 mm 板尺寸、功率和镜头参数不同。近焦距离、麦克风描述也有来源差异，不能只按“B0292”名称冻结外壳。
6. **Pololu #3417 与 VL53L5CX 的配对正确。** 需要处理的是 VIN／I²C 电平和准确板图，不是型号误配：该板 SDA、SCL 上拉到 VIN，不能因为板有稳压器就假定 5 V 供电时与 Radxa 的 3.3 V GPIO 直接兼容。
7. **已有部分真实器件几何文件，但尚有装配版本／许可缺口。** ROBOTIS 的单个 STEP、DWG、参考 PDF 已实际读取；Radxa 的 ZIP、Pololu 的 STEP 也已读取。Arducam STEP 未取得；igus 精确 SKU 的 CAD 未取得。所有“可下载”和“可再分发”状态应分列。

## 1. Microduck 当前公开工程

### 1.1 固定提交与许可证

| 官方来源 | 本轮固定提交 | 提交日期（UTC） | 检索日期 |
|---|---|---|---|
| [pollen-robotics/microduck](https://github.com/pollen-robotics/microduck)；默认分支 `main` | `a9ec4b2079ef8ee7904014089c885bb07d57d63c` | 2026-09-23 12:51:05 | 2026-09-28 |
| [pollen-robotics/microduck_rl](https://github.com/pollen-robotics/microduck_rl)；默认分支 `develop` | `cb70b792312d559a4da09064d92009079671815f` | 2026-09-14 12:22:01 | 2026-09-28 |

两个仓库根目录的实际 LICENSE 均为 Apache-2.0：[microduck LICENSE](https://github.com/pollen-robotics/microduck/blob/a9ec4b2079ef8ee7904014089c885bb07d57d63c/LICENSE)、[microduck_rl LICENSE](https://github.com/pollen-robotics/microduck_rl/blob/cb70b792312d559a4da09064d92009079671815f/LICENSE)。这是仓库层面的许可事实；本轮没有核实链接到 Onshape 的可编辑制造 CAD 是否适用同一许可。

### 1.2 实际交付结构和几何资产

| 项目 | 实际读取的交付结构／文件 | 检索日期 |
|---|---|---|
| Microduck 运行端 | Rust Cargo workspace，含 `robotd`、`duck-control`、`duck-ipc-proto`、`kinematics`、`odometry`、`btd`、`configd`、`mediad`、`padd`、`tof`、`updater`、`robotctl`、`duckctl` 等。另有设计、部署和 policy manifest 文档。见 [Cargo.toml](https://github.com/pollen-robotics/microduck/blob/a9ec4b2079ef8ee7904014089c885bb07d57d63c/Cargo.toml) 和 [architecture.md](https://github.com/pollen-robotics/microduck/blob/a9ec4b2079ef8ee7904014089c885bb07d57d63c/docs/design/architecture.md)。 | 2026-09-28 |
| Microduck 几何文件 | 完整递归树 371 个 blob；0 个 `.urdf`；1 个 `.xml`：`kinematics/assets/alpha/robot_walk.xml`；0 个 `.stl/.step/.stp/.obj/.dae/.fcstd`。该结论只覆盖这个仓库的固定提交。见 [完整树](https://api.github.com/repos/pollen-robotics/microduck/git/trees/a9ec4b2079ef8ee7904014089c885bb07d57d63c?recursive=1)。 | 2026-09-28 |
| Microduck RL | Python 项目；MJCF、机器人资产、环境配置、训练／评估／实机工具。完整递归树 239 个 blob；0 个 `.urdf`；27 个 `.xml`；54 个 `.stl`（43 个 Microduck 机器人资产，11 个 XL330 测试台资产）；0 个 STEP／STP／FCStd。见 [完整树](https://api.github.com/repos/pollen-robotics/microduck_rl/git/trees/cb70b792312d559a4da09064d92009079671815f?recursive=1) 和 [README](https://github.com/pollen-robotics/microduck_rl/blob/cb70b792312d559a4da09064d92009079671815f/README.md)。 | 2026-09-28 |
| 实际公开的 MJCF | `robot_walk.xml`、`robot_groundcontact.xml`、`robot_allcollisions.xml`、rollers／backlash 变体、scene、关节属性和传感器配置等；三类主机器人 XML 均有 14 个 position actuator。见 [机器人目录](https://github.com/pollen-robotics/microduck_rl/tree/cb70b792312d559a4da09064d92009079671815f/src/mjlab_microduck/robot/microduck)。 | 2026-09-28 |
| CAD 导出来源 | `config_mjcf_walk.json`／allcollisions 配置引用 Onshape，`outputFormat=mujoco`、`simplify_stls=true`、`max_stl_size=1.0`。见 [导出配置](https://github.com/pollen-robotics/microduck_rl/blob/cb70b792312d559a4da09064d92009079671815f/src/mjlab_microduck/robot/microduck/config_mjcf_walk.json)。 | 2026-09-28 |

Onshape 引用为 [此工作区 URL](https://cad.onshape.com/documents/804927696f06d877f3f1803e/w/5b75db19292e71970de02dee/e/ef6e972847fec8d82570b35e)。它包含工作区标识 `/w/`，不是本轮已固定的 Onshape 版本。本轮访问未取得可编辑 CAD 或导出文件；**公开程度、可制造完整性、许可均未验证**。

为确认仓库资产不是只有索引或 Git LFS 指针，本轮实际读取：

| 文件 | 实际内容／大小 | SHA-256 |
|---|---|---|
| [robot_walk.xml](https://github.com/pollen-robotics/microduck_rl/blob/cb70b792312d559a4da09064d92009079671815f/src/mjlab_microduck/robot/microduck/robot_walk.xml) | MJCF XML，32,023 字节 | `80fc4424ed71e430ec4919110dfdb5c714dc1c4e1138e1832a16865cf31eb8c8` |
| [assets/xl330.stl](https://github.com/pollen-robotics/microduck_rl/blob/cb70b792312d559a4da09064d92009079671815f/src/mjlab_microduck/robot/microduck/assets/xl330.stl) | 二进制 STL，206,384 字节，非 LFS 指针 | `96238ed0d020ce0009cf1a5aa4b6926176c800840318ee65e4375be2298d2744` |

**用途边界：** 简化后的仿真 STL 和 MJCF 并不自动提供原生零件、制造公差、完整装配约束或可改尺寸的结构源。URDF 未找到也不表示上游完全没有可用仿真模型；它实际采用 MJCF。

### 1.3 运行端关节和策略接口

来源：[model.rs](https://github.com/pollen-robotics/microduck/blob/a9ec4b2079ef8ee7904014089c885bb07d57d63c/duck-control/src/model.rs)、[obs.rs](https://github.com/pollen-robotics/microduck/blob/a9ec4b2079ef8ee7904014089c885bb07d57d63c/duck-control/src/obs.rs)、[bus.rs](https://github.com/pollen-robotics/microduck/blob/a9ec4b2079ef8ee7904014089c885bb07d57d63c/duck-control/src/bus.rs)、[control.rs](https://github.com/pollen-robotics/microduck/blob/a9ec4b2079ef8ee7904014089c885bb07d57d63c/robotd/src/control.rs)、[policy manifest](https://github.com/pollen-robotics/microduck/blob/a9ec4b2079ef8ee7904014089c885bb07d57d63c/docs/policy-manifest.md)。全部检索于 2026-09-28。

| 运行端顺序 | 关节名 | DYNAMIXEL ID |
|---|---|---|
| 0–4 | `left_hip_yaw`, `left_hip_roll`, `left_hip_pitch`, `left_knee`, `left_ankle` | 20, 21, 22, 23, 24 |
| 5–9 | `neck_pitch`, `head_pitch`, `head_yaw`, `head_roll`, `mouth` | 30, 31, 32, 33, 34 |
| 10–14 | `right_hip_yaw`, `right_hip_roll`, `right_hip_pitch`, `right_knee`, `right_ankle` | 10, 11, 12, 13, 14 |

- 总线 15 个关节；嘴的运行端索引为 9。策略忽略嘴，所以策略关节顺序要在上述列表中去掉 `mouth`，不能把总线数组长度当策略动作长度。
- feed-forward 观测形状为 `[1,61]`，动作形状 `[1,14]`。嘴的输入单独夹到 0–1，再映射到 −5° 至 +30°。
- 观测块为 gyro 3、projected gravity 3、相对 home 的关节位置 14、关节速度 14、上一步未缩放 action 14、命令 13。
- 13 维命令包括平移／转向速度 3、颈／头姿态 4、body x/y/z/roll/pitch/yaw 6；当前 body x、y、yaw 输入固定为 0。
- `home + action_scale × raw_action` 生成目标；运行端默认 action scale 0.9、standing 1.0、position gain 200，并存在头／腿不同的低通参数。这些是上游实现参数，不是 Goose 的验证结果。
- 上游生产总线 1 Mbps、DYNAMIXEL Protocol 2；联合 fast sync read 读取自定义 IMU ID 200 及 15 个舵机，舵机读区从地址 124 起 12 字节，含 PWM／current／velocity／position；之后写 Goal Position。当前查看的总线初始化没有证明每次启动均显式设置 Operating Mode 为 5，不能据有电流字段就断言实机一定运行 current-based position 模式。
- 上游 IMU 是自定义 `imu_to_dxl` v2 寄存器接口；SparkFun I²C IMU 不具备这个接口，不能按同一型号读取代码直接替换。
- policy manifest schema 2 记录 obs/action 维数、机器人和硬件修订、舵机、控制频率、模型 API、训练提交／运行／checkpoint 等。model API 1 为 feed-forward，2 为 LSTM。
- 官方策略权重指向 [pollen-robotics/microduck-policies](https://huggingface.co/pollen-robotics/microduck-policies)，不在以上 Git 源码树中。本轮没有下载或运行权重，不能认定其适用于 Goose。

### 1.4 机械限位、仿真电压与保护配置

| 原始事实 | 源 URL | 检索日期 |
|---|---|---|
| RL `robot_walk.xml` 的关节限位换算为角度：左 hip yaw −25°/+30°，右 −30°/+25°；两侧 hip roll ±22°；hip pitch/knee/ankle ±90°；neck pitch −90°/+60°；head pitch ±90°、yaw ±170°、roll ±25°。XML 中轴写为局部 body 坐标 `0 0 1`，不是所有关节都绕世界竖轴。 | [robot_walk.xml](https://github.com/pollen-robotics/microduck_rl/blob/cb70b792312d559a4da09064d92009079671815f/src/mjlab_microduck/robot/microduck/robot_walk.xml) | 2026-09-28 |
| 运行端安全夹限是全关节 `[-π,+π]`；源码明确说明尚非逐关节机械限位。它与上面的 MJCF 限位不同。 | [safety.rs](https://github.com/pollen-robotics/microduck/blob/a9ec4b2079ef8ee7904014089c885bb07d57d63c/duck-control/src/safety.rs) | 2026-09-28 |
| RL 的 BAM actuator 参数声明 `motor_name=xl330`、`model=m6`、`kp_fw=200`；电压随机范围 6.5–8.2 V、最小电压 6 V；具有电压下降和延迟随机化。不能把这些参数视作 XC330 或 5 V 电源的实测模型。 | [microduck_constants.py](https://github.com/pollen-robotics/microduck_rl/blob/cb70b792312d559a4da09064d92009079671815f/src/mjlab_microduck/robot/microduck_constants.py) | 2026-09-28 |
| MJCF 关节属性含 position actuator 的 `kp=0.55`、`kv=0`、`forcerange=±0.96`、`ctrlrange=±10`。这些是仿真配置，不是供应商连续力矩规格。 | [joints_properties.xml](https://github.com/pollen-robotics/microduck_rl/blob/cb70b792312d559a4da09064d92009079671815f/src/mjlab_microduck/robot/microduck/joints_properties.xml) | 2026-09-28 |
| 运行端电池显示满／空常量为 8.2／6.6 V，代码说明使用 2S NP-F550；shutdown 值 52 对比出厂 53，清除 input voltage error 触发位，保留 overload／electrical shock／overheat。源码说明满电 2S 高于默认最大电压阈值。 | [model.rs](https://github.com/pollen-robotics/microduck/blob/a9ec4b2079ef8ee7904014089c885bb07d57d63c/duck-control/src/model.rs) | 2026-09-28 |

**差异记录：** 上游选择在超出 ROBOTIS 标准电压区间的供电下修改保护；本轮只确认代码事实，没有取得 ROBOTIS 对该运行方式的批准、寿命或连续热性能资料。

## 2. ROBOTIS 执行器

### 2.1 精确型号与性能条件

官方来源：[XL330-M288 eManual](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/)、[XC330-M288 eManual](https://emanual.robotis.com/docs/en/dxl/x/xc330-m288/)。检索日期均为 2026-09-28；页面提示新文档站迁移，但本轮读取的是这些精确型号页面。

| 项目 | XL330-M288-T | XC330-M288-T |
|---|---|---|
| 外形尺寸 | 20 × 34 × 26 mm | 20 × 34 × 26 mm |
| 标称质量 | 18 g | 23 g |
| 电机／齿轮 | cored motor／塑料齿轮 | coreless motor／金属齿轮、两轴承 |
| 减速比 | 288.4:1 | 288.35:1 |
| 标准输入／推荐电压 | 3.7–6.0 V／5.0 V | 3.7–6.0 V／5.0 V |
| 3.7 V 堵转力矩／电流 | 0.42 N·m／1.11 A | 0.69 N·m／1.34 A |
| **5 V 堵转力矩／电流** | **0.52 N·m／1.47 A** | **0.93 N·m／1.80 A** |
| 6 V 堵转力矩／电流 | 0.60 N·m／1.74 A | 1.10 N·m／2.15 A |
| 3.7／5／6 V 空载转速 | 76／103／123 rpm | 59／81／97 rpm |
| 位置测量 | 12 bit，4096 counts/rev | 12 bit，4096 counts/rev |

`XC330-M288-T` 的 **M288** 低电压版本与 `XC330-T288-T` 的 **T288** 高电压版本不同；后者 9–12 V 的规格不能套给当前候选。外形相同也不意味着电压、速度或电机模型相同。

官方商店补充信息及差异：

| 来源与字段 | 原始内容／证据等级 | 检索日期 |
|---|---|---|
| [XL330 官方商店](https://robotis.us/products/dynamixel-xl330-m288-t) estimated rated torque | 0.10 N·m；明确按 stall torque 的 20% 估算连续力矩。**供应商估算**，不是本轮取得的实测连续曲线。 | 2026-09-28 |
| [XC330 官方商店](https://robotis.us/products/dynamixel-xc330-m288-t) estimated rated torque | 0.186 N·m；同样注明 20% stall estimate。**供应商估算**。 | 2026-09-28 |
| XC330 商店的 no-load speed | 页面显示 65 rpm，而精确 M288 eManual 在 5 V 下为 81 rpm。**来源差异未解**；本记录保留两者，不把 65 rpm 与 5 V 表拼成一致规格。65 rpm 也出现在 T288 高电压版本相关表中，但是否为商店混录只是假设，未被供应商确认。 | 2026-09-28 |

eManual 对堵转项本身说明其为瞬时最大能力，并提醒实际性能与力矩／转速条件相关。本轮未取得连续力矩对温度、环境散热、负载占空比、电压和时间的完整实测曲线；“官方完全没有连续力矩数值”也不准确，因为官方商店确有上述估算。

### 2.2 电气接口与控制范围

来源仍为上述两份 eManual，检索于 2026-09-28。

- TTL half-duplex；信号为 3.3 V 逻辑、5 V compatible。3 针接口顺序 GND／VDD／DATA，JST EHR-03／B3B-EH 系列。不是 USB 或普通双线 UART 直接全双工接口。
- 模式寄存器：0 current、1 velocity、3 position、4 extended position、5 current-based position、16 PWM。
- 模式 3 的位置区间 0–4095；模式 4／5 允许 ±256 圈的扩展位置计数。**Min／Max Position Limit 只在模式 3 生效，不在 4／5 生效。** 选择带电流限制的位置模式不能据此假定已具备机械关节限位。
- 切换模式会重置相关 gains、profile、goal current／PWM 等字段，需要以具体模式的初始化结果为准。
- XL330 的 Present Current 是输入侧电流量测，不能不经标定就视作瞬时电机相电流或夹持力。
- 官方商店列出配套 X3P 180 mm 线，以及 M2 tapping screw；安装孔是自攻配合体系，不能自动替换为已攻丝 M2 金属孔。

### 2.3 已实际取得的官方 CAD／图纸内容

eManual 的官方 ROBOTIS 下载入口重定向到其指定 Dropbox 文件。本轮核对的是实际响应和内容，不是仅发现下载按钮。所有下列文件检索于 **2026-09-28**。

| 官方入口 → 实际文件 URL | 响应／文件性质 | 字节数 | SHA-256 |
|---|---|---:|---|
| [PDF no=1986](https://www.robotis.com/service/download.php?no=1986) → [XL,XC-330.pdf](https://www.dropbox.com/s/gxgye7wt5sbt4i4/XL,XC-330.pdf?dl=1) | HTTP 200，PDF 1.7；实际文本已读 | 149,731 | `948b707cb26a64501c03fc45b1a9557b69a554dd5d6934f02e8e6f86cf2b46c2` |
| [DWG no=1985](https://www.robotis.com/service/download.php?no=1985) → [XL,XC-330.dwg](https://www.dropbox.com/s/06f9jeq50a1zx78/XL,XC-330.dwg?dl=1) | HTTP 200，文件头 AC1015 | 409,472 | `08423728d1a1f39a65851175df3eac7bad503215991147b7e23864fa60a3c418` |
| [STEP no=1987](https://www.robotis.com/service/download.php?no=1987) → [XL,XC-330.stp](https://www.dropbox.com/s/qlzmp8mlvzrxmzu/XL,XC-330.stp?dl=1) | HTTP 200，**单个 STEP，不是 ZIP**；ISO-10303-21／CONFIG_CONTROL_DESIGN，Creo 导出 | 791,238 | `e2f7b060801a1d6a21f23bca2554f29a402f7d73b8498cb201c9e6adf3139eb6` |
| [惯量 PDF no=2136](https://www.robotis.com/service/download.php?no=2136) → [XL330,XC330 Moment of Inertia.pdf](https://www.dropbox.com/s/88jbmlyv8v1o73t/XL330%2CXC330%20Moment%20of%20Inertia.pdf?dl=1) | HTTP 200，实际文本已读；2023-02 发布，reference only | 137,692 | `dacd173dfde3de78effa6ccb94baeea98edf378d63424aa3b26af81adc0c3df2` |

安装接口证据：

- 参考 PDF 标注 `FOR REFERENCE ONLY`，日期 2020-05-28；具有壳体、舵盘／idler 的尺寸图，含 `4×Ø1.6 HOLE DP3.0(Max)`、`P.C.D 12`、`Using M2 Tapping Screw`、`X330 IDLER` 等标记。本轮文本解析没有完成各视图中坐标与投影的逐项映射，故不把这些标签直接编成自造的全套孔坐标。
- STEP 中实际存在 `CASE_M/CASE_F/CASE_B_DUMMY`、`HORN_DUMMY`、`HORN_IDLE2_DUMMY`、`IDLE_CAP_DUMMY`、`B3B-EH` 和装配 PRODUCT；提供壳体、舵盘、idler、连接器外形的几何依据。`DUMMY` 不应被解释为真实内部电机／齿轮材料组成或其质量分布。
- 官方惯量 PDF 提供 XL330-M288 的 18 g、XC330-M288 的 23 g、质心和惯量矩阵，单位为 mm／g·mm²。但**本轮尚未视觉核对该图纸的坐标系原点和朝向**，不可把矩阵无转换写入某个 MJCF body。后续惯量接入应映射图纸坐标，并保留 reference-only 的属性。
- **许可未解：** 下载入口、eManual 和 STEP header 中本轮未发现明确的 CAD 再分发授权；能下载不等于已确认可复制到公开项目。文件未进入本项目正式 CAD 目录。

## 3. 候选板卡与传感器

### 3.1 Radxa ZERO 3W

| 官方来源 | 已核事实／缺失 | 检索日期 |
|---|---|---|
| [ZERO 3 文档](https://docs.radxa.com/en/zero/zero3)、[ZERO 3W product brief](https://dl.radxa.com/zero3/docs/hw/3w/radxa_zero_3w_product_brief.pdf) | RK3566、四核 Cortex-A55，1.6 GHz；65 × 30 mm；1／2／4／8 GB LPDDR4，eMMC 有多种容量。当前 product brief Rev 1.12，日期 2026-09-20。 | 2026-09-28 |
| 同上供电／端口 | 推荐 5 V／2 A；USB-C USB2 OTG 口兼供电，另一 USB-C 为 USB3 host；GPIO 2／4 可输入 5 V。product brief 对 USB host 给出最大 500 mA 的供电条件，不能自动把相机用电当成整板外的无限余量。 | 2026-09-28 |
| 同上接口／SKU | 4 lane MIPI CSI、22 pin、0.5 mm；2 GB／16 GB SKU 为 `RS107-D2E16H1W15`（带 header）和 `RS107-D2E16H0W15`（无 header）。板修订及天线／排针版本仍需采购时冻结。 | 2026-09-28 |
| [资源下载页](https://docs.radxa.com/en/zero/zero3/download) | 有 V1.11 2D DXF／3D STEP，V1.11 与 V1.12 原理图。不能仅凭较新产品简介就断言 V1.11 机械文件对应所有当前采购版本。 | 2026-09-28 |

实际读取 [官方 3D ZIP](https://dl.radxa.com/zero3/docs/hw/3w/radxa_zero_3w_3d_stp.zip)：HTTP 200，application/zip，4,803,731 字节；归档条目 `radxa_zero_3w_3d.stp`；SHA-256 `0dfc39db5f52665ef92bcab34781132aba399a4061dc2c869f757a00f446d2cf`。本轮核实了归档和文件名，没有完成各零件／孔位几何检查。

**缺失：** 已读官方摘要与产品简介没有板卡质量；需要对应采购 SKU 的实际质量，含排针、天线、散热片或线缆的口径应另外声明。官方文档页脚的 CC BY 4.0 不能不经确认就套给全部硬件 CAD 下载资产。

### 3.2 Arducam B0292／B0292-1／B029202

| 官方／制造商来源 | 已核事实和冲突 | 检索日期 |
|---|---|---|
| [Arducam B0292 产品页](https://www.arducam.com/arducam-usb-autofocus-imx219-b0292.html) | 当前选择器同时列 B0292-1 Standard 与 B029202 Upgraded。页面直读超时／403；以下当前选择器内容由官方页面的搜索索引及其制造商关联商城复核，证据强度低于已读原始 PDF。 | 2026-09-28 |
| [Arducam 官方 UVC selection guide](https://docs.arducam.com/UVC-Camera/USB2-UVC-Camera-Kit/Specs-and-Selection-Guide/) | B0292 是 IMX219 RGB autofocus USB UVC 摄像头；不是 CSI 裸传感器。表中无麦克风、近焦 5 cm。该页直接链接下述 Uctronics 产品页。 | 2026-09-28 |
| [制造商关联 Uctronics 产品页](https://www.uctronics.com/arducam-4k-8mp-imx219-autofocus-usb-camera-module-without-microphone.html) | Standard B0292-1：38 × 38 mm，5 V／1 W，F2.0、2.96 mm，FOV 对角／水平／垂直 72°／60°／47°，近焦 10 cm，USB2。Upgraded B029202：**32 × 32 × 1.6 mm 是板尺寸**，5 V／1.75 W，F1.8、3.95 mm，FOV 75°／61°／50°，近焦 10 cm，具有不同外壳／HDR 描述。 | 2026-09-28 |
| [B0292 原始 datasheet](https://www.uctronics.com/download/Amazon/B0292_8MP_IMX219_Autofocus_USB_Camera_Datasheet.pdf) | 实际读取 8 页；V1.0，2020-12-28，标为 Proprietary to Arducam。5 V，最大 200 mA；板 38 × 38 mm；安装孔距有 34 × 34 和 28 × 28 mm；ZHR 系列 4 pin USB 连接器；IMX219，8 MP，rolling shutter；近焦 **40 mm**。 | 2026-09-28 |

**差异记录：** 原始 datasheet 的 40 mm、官方 wiki 的 50 mm、当前商品的 100 mm 近焦不同；当前页面标题／变体对 microphone 的表述也不一致。B029202 的 32 mm 板不能替代原始 B0292 的 38 mm 板图。采购前应取得精确 SKU、修订、实际外形及镜头／线缆出口图；本轮不选择哪个描述优先适用未冻结的采购件。

官方关联页面给出 [B0292.STEP](https://www.uctronics.com/download/Mechanical_Drawing/B0292.STEP) 下载链接，但本轮请求失败（工具不支持该二进制响应／直接读取 403），**实际 STEP 未取得**，不能列为本轮完成的 CAD。原始数据表没有整机质量，也没有充分给出所有镜头、连接器和线缆的外包络。数据表的 proprietary 声明不构成自由再分发许可。

### 3.3 SparkFun SEN-21336

| 官方来源 | 已核事实 | 检索日期 |
|---|---|---|
| [SEN-21336 产品页](https://www.sparkfun.com/sparkfun-micro-6dof-imu-breakout-lsm6dsv16x-qwiic.html)、[hardware overview](https://docs.sparkfun.com/SparkFun_6DoF_LSM6DSV16X/hardware_overview/) | SEN-21336 是 **Micro** LSM6DSV16X Qwiic breakout，0.3 × 0.75 in＝7.62 × 19.05 mm；不是较大的 SEN-21325。供电范围 1.71–3.6 V，Qwiic 为 3.3 V 系统。 | 2026-09-28 |
| 同上接口 | I²C 默认地址 0x6B，可改为 0x6A；micro 板引出一个中断。芯片有 SPI 能力不等于 micro breakout 暴露一整套 SPI 接口，不能把大板的排针说明无条件复制给 micro 板。 | 2026-09-28 |
| [官方硬件仓库](https://github.com/sparkfun/SparkFun_6DoF_LSM6DSV16X/tree/81f28abb82c4edfa63f5bcc623be1ea7ef1c1ce5)、[资源页](https://docs.sparkfun.com/SparkFun_6DoF_LSM6DSV16X/resources_and_going_further/) | 有 Eagle BRD／SCH 和板轮廓来源；本轮实际解析 micro BRD，板轮廓为 19.05 × 7.62 mm。 | 2026-09-28 |
| [License.md](https://github.com/sparkfun/SparkFun_6DoF_LSM6DSV16X/blob/81f28abb82c4edfa63f5bcc623be1ea7ef1c1ce5/License.md) | **硬件 CC BY-SA 4.0；代码 MIT**。不能把此硬件授权写成上游 Microduck 的 Apache-2.0。 | 2026-09-28 |

固定提交 `81f28abb82c4edfa63f5bcc623be1ea7ef1c1ce5`（2023-06-15）。[micro BRD](https://github.com/sparkfun/SparkFun_6DoF_LSM6DSV16X/blob/81f28abb82c4edfa63f5bcc623be1ea7ef1c1ce5/Hardware/Qwiic%20Micro/SparkFun_Micro_6DoF_LSM6DSV16X.brd) SHA-256 `a8ddf8335877f13af4259fbae6a18392a9cdb599025ef0dd441409606657eaf4`。

**缺失：** 整板质量、精确安装孔几何及连接器整体高度尚未在本轮完成核对；Eagle 文件内有 standoff 元件，本记录不据顶层 plain/hole 为空就断言板上没有孔。姿态输出时间戳、坐标系和驱动与上游自定义 IMU 的接口适配也未完成。

### 3.4 Pololu #3417：VL53L5CX carrier

| 官方来源 | 已核事实 | 检索日期 |
|---|---|---|
| [Pololu #3417 产品页](https://www.pololu.com/product/3417) | 产品就是 **VL53L5CX** carrier；13 × 18 × 3 mm，0.5 g（无排针）；VIN 2.5–5.5 V，典型约 100 mA、峰值约 150 mA；4 × 4／8 × 8，多区域 ToF，I²C；不是 VL53L8CX 的 SPI 接口。 | 2026-09-28 |
| 同上光学／电平 | 有利条件下范围 20 mm–4 m，FOV 对角 65°、水平／垂直各约 45°；含 3.3 V regulator 和 I²C level shifter，**SDA／SCL 上拉到 VIN**。其他控制脚不应按已电平转换的 SDA／SCL 处理。 | 2026-09-28 |
| [官方资源页](https://www.pololu.com/product/3417/resources) | 有载板 STEP、尺寸 PDF、原理图、drill DXF 及 ST datasheet。 | 2026-09-28 |

实际读取 [载板 STEP](https://www.pololu.com/file/0J1874/vl53l5cx-carrier-model.step)：HTTP 200，ISO STEP，4,275,468 字节；SHA-256 `1cb6ed4c1e94aaade7337a5fcfc2e263b14cceeac0295d1ce1ff2bb8b43b1bcc`。其官方配套文件为 [尺寸 PDF](https://www.pololu.com/file/0J1873/vl53l5cx-carrier-dimension-diagram.pdf)、[原理图](https://www.pololu.com/file/0J1877/vl53l5cx-time-of-flight-sensor-schematic.pdf)、[drill DXF](https://www.pololu.com/file/0J1997/irs18a-drill.dxf)。后面三项为已定位的官方资源，不代表本轮逐项完成制造几何检查。

**差异／缺失：** #3417／VL53L5CX 引用本身正确。要核对的是与主板连接时的 VIN 和逻辑电压、控制脚和安装空间；本轮未确认 CAD 再分发许可。测距上限与 FOV 不是本机器人场景中的实测避障性能。

### 3.5 Pololu D24V90F5：#2866

| 官方来源 | 已核事实／条件 | 检索日期 |
|---|---|---|
| [产品页](https://www.pololu.com/product/2866)、[规格页](https://www.pololu.com/product/2866/specs) | 型号 D24V90F5 对应 #2866；40.6 × 20.3 × 7.6 mm；规格质量 4.8 g；固定输出 5 V，精度 ±4%；输入标称 5–38 V。 | 2026-09-28 |
| 同上电流／dropout | 标题／规格表有 9 A，但详细性能说明为典型连续 **4–8 A**，随输入电压、散热和环境变化；dropout 约 0.5–1.5 V 随负载变化。因此 VIN=5 V 不能据“输入下限 5 V”保证满载稳压输出 5 V。 | 2026-09-28 |
| 同上控制／保护 | reverse voltage protection；thermal shutdown 约 160°C；UVLO 典型 4.2 V；PG open-drain，输出低于标称约 90% 时拉低；EN 经 100 kΩ 上拉到 VIN，可拉到低于 0.6 V 禁用。 | 2026-09-28 |
| [资源页](https://www.pololu.com/product/2866/resources) | 官方 STEP／尺寸图／drill 图；4 个 Ø0.086 in（约 2.1844 mm）安装孔供 M2 使用。 | 2026-09-28 |

实际读取 [D24VxF5 STEP](https://www.pololu.com/file/0J1582/step-down-voltage-regulator-d24vxf5.step)：HTTP 200，ISO STEP，4,884,801 字节；SHA-256 `cdb901f06d5b13f49c6af5d5e64b2a2cd8bafedf1ddfd5c23ed21663bb8f295a`。官方图纸入口：[尺寸 PDF](https://www.pololu.com/file/0J1581/step-down-voltage-regulator-d24vxf5-dimensions.pdf)、[drill DXF](https://www.pololu.com/file/0J915/reg15b02-drill.dxf)。

**缺失／用途边界：** 不能以 9 A 标题完成多舵机电源验收。本轮没有该机器人负载波形、实际布线／接插件电流能力或稳压器热测试；没有确认 CAD 再分发许可。4.8 g 不应被默认为已包含项目选用的接线端子、排针、固定件和线缆。

### 3.6 igus JFM-0304-03

| 官方来源 | 已核事实 | 检索日期 |
|---|---|---|
| [精确 SKU 产品页](https://www.igus.com/iglide-ibh/flange-bearings/product-details/iglide-j-m?artnr=JFM-0304-03) | iglidur J 注塑法兰滑动轴承；d1=3、d2=4.5、d3=7.5、b1=3、b2=0.75 mm。被动机械件，无电气供电。 | 2026-09-28 |
| 同上装配说明 | 轴承孔径按压入正确座孔后的状态定义；未压入前可能较大。不能把名义 3 mm 当自由状态下已验证的精确内径，也不能无验证就用名义 4.5 mm 冻结 FDM 打印座孔。 | 2026-09-28 |
| [官方 2016 iglide catalog](https://www.igus.com/contentData/Product_Files/Download/pdf/2016%20iglide%20section.pdf) | 历史表对 JFM-0304-03 给钢制座孔 4.500–4.512 mm、轴径 2.975–3.000 mm、压入后孔径 3.014–3.054 mm；法兰厚度 0.75 mm 的 −0.14 公差。它是历史钢制座孔条件，不能当现行 FDM 配合验证。 | 2026-09-28 |

官方 [CAD portal](https://www.igus-cad.com/) 已定位，但本轮没有取得这个精确 SKU 的 STEP／原生文件或再分发条款。官方精确 SKU 页面未找到可确认的单件质量；本记录没有用经销商包装重填充该缺失项。

## 4. 当前缺失项与下一轮可核事实

以下是尚未闭合的事实项，**不是本轮决定实施的结构方案**：

| 缺失项 | 当前证据状态 | 后续取证对象 |
|---|---|---|
| Microduck 可编辑装配 CAD | 有 Onshape 工作区链接，未实际取得；无固定 CAD 版本或独立许可 | 上游固定 Onshape version、可导出装配、物料／紧固件与许可说明 |
| 执行器连续热能力 | 官方商店有 20% stall 估算；无选定散热／负载下实测曲线 | ROBOTIS 详细试验条件，或对应装配和驱动模式的测试 |
| XC330 no-load speed 来源差异 | eManual 5 V=81 rpm；商店=65 rpm | 精确 M288 SKU／修订的厂家澄清 |
| 舵机孔位／惯量坐标接入 | 真实 STEP／DWG／参考 PDF 已读，未完成视图坐标和装配映射 | 图纸坐标系、idler／horn 的实际装配、M2 自攻配合 |
| Radxa 采购版本／质量 | 当前简介与 V1.11 CAD 修订不同；质量未取得 | SKU、板版本、带／不带排针、天线／散热件质量与图纸 |
| 相机精确机械／光学版本 | B0292-1 与 B029202 有尺寸／功率差异；近焦和音频描述冲突；STEP 未取得 | 精确 SKU 实物、对应数据表／CAD、整机质量及镜头／线缆外包络 |
| Micro IMU 安装／软件接口 | Eagle 和许可取得；孔位、Z 包络、质量和驱动时序未闭合 | micro 板原图、实际安装图、具体固件／驱动时间戳和坐标约定 |
| Pololu 电源／ToF 集成 | 型号配对正确；资源存在；项目电流波形和逻辑电平未验收 | 精确采购件、原理图接线、电源条件、热／电压测量 |
| igus 轴承质量／制造配合 | 精确名义尺寸和历史钢座孔条件有据；CAD／质量缺失 | 精确 SKU 文件、实物质量、所选轴与打印材料的配合验证 |
| 第三方 CAD 许可 | SparkFun 硬件许可明确；其他实际取得 CAD 的再分发权限未确认 | 供应商具体 CAD 使用／再分发许可；授权前不视为可公开资产 |

本轮记录可用于明确后续建模需要什么原始数据；不以来源缺失补造尺寸、质量、材料惯量或执行器能力。
