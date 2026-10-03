# Gorilla V0.2 全身感知候选

建议胸中央金边区承担 **RGB＋LWIR 热像**，主动近红外／立体深度放到保有双目基线的前向宽视区域，腕部承担近距抓放，后向视野与外置 LiDAR 补环境盲区。所有能力不应塞进一枚中央镜头。本报告是器件事实与接口分配研究，未完成新本体 SI 定标、安装 CAD、覆盖率或自主任务验收。

已实际查看最新四视照片（SHA `2e07e1a10c4655690b58c150e5d207bfc2a593c69b4287f300249b99df7f37cd`）：胸中央 Camera 金边、暖白膝及橙色踝点作为新参考；最初 Camera 图及首事实表保留历史。当前可读下半身 `native_lower_scene.json` SHA `432a7db2…` 是 **归一化外观单位，不是米**，并非最新图片已交接 CAD；不继承旧 2.65m 高度、脚承载或关节 ABI。

## 完整紧凑器件的公开事实

以下质量是各厂商说明的模块范围，电缆、支架、窗口、接口盒及宿主计算通常另计。最大帧率不能直接当所选组合输出模式，内部 COM／惯量未知。

| 候选与用途 | 尺寸／质量 | 电功、视域与量程 | 接口与重要限制 |
|---|---|---|---|
| Hadron 640R+，中央 RGB／热像 | 网页35×49×45mm；工程估计36×50×43mm；约56g | 25°C典型<1.8W，FFC峰<3W；LWIR640×512／60Hz／32°H；RGB67°H | RGB4lane MIPI，IR USB或2lane MIPI；EXT_VSYNC pin43／1.8V；热像最近工作距离未知；背板导热、后部密封另做。[型号页](https://oem.flir.com/en-150/products/hadron-640/?model=70640AS32-6PARXP&segment=oem&vertical=lwir)、[工程Rev170](https://flir.netx.net/file/asset/52567/original/attachment/) |
| OAK-D Pro W／OV9782，前后宽视主动深度 | 97×29.5×23.1mm／91g；双目75mm | 基础2.5–3W，全功能约7.5W；Pro供电另留15W峰值；RGB／单目127°H×79.5°V；深度理想0.4–6m，扩展MinZ约0.20m，800p约0.37m | USB-C 3.2Gen1／5Gbps；940nm点阵与泛光，夜视是mono，RGB有IR截止；Class1原机条件；USB版硬触发连接未核。[W产品](https://checkout.luxonis.com/products/oak-d-pro-w)、[供电部署](https://docs.luxonis.com/hardware/platform/deploy/usb-deployment-guide) |
| MID-360，环境激光雷达 | 65×65×60mm／265g | 9–27V；平均6.5W，−20..0°C自热峰14W；905nm；360°H、−7..52°V；10Hz，20万点/s | 100BASE-TX、PTPv2／GPS；100klx下10%反射40m／80%70m；<0.1m盲区，0.1–0.2m仅参考；Class1原机条件。[规格](https://www.livoxtech.com/mid-360/specs) |
| D405，双腕近距 | 42×42×23mm／60g | 深度／IR流1.55W；理想7–50cm，MinZ7cm是在480p；87°H×58°V；最高90fps | USB2／3.1；无IMU、**被动立体且无IR投射器**；RGB来自左目；环境0..35°C。完整同步模式、黑暗效果需实测。[产品](https://www.realsenseai.com/products/d405-series/)、[400系列表](https://www.realsenseai.com/download/21345/?tmstv=1778232235) |
| VN-100 Rugged，主躯 IMU | 36×33×9mm／15g | 220mW；4.5–5.5V；原始IMU最高800Hz，姿态400Hz；±16g、±2000°/s | TTL／RS232，最高921600baud，SyncIn／Out；钢结构及大电流下磁航向需重新标定。[规格](https://www.vectornav.com/products/detail/vn-100) |
| Mini45，腕6轴力参考 | Ø45×15.7mm／91.7g，含标准接口板 | SI580-20标定：Fx/y580N、Fz1160N、各力矩20Nm | AFE、电功、采样与总线依具体DAQ／Net／EtherCAT／CAN版本另核，20Nm未必够 Gorilla；组合载荷不能用单轴超载值代替。[ATI](https://www.ati-ia.com/products/ft/ft_models.aspx?id=Mini45) |

**资料冲突隔离：**Hadron 页面将64MP EO与60Hz并列，但工程资料指定的 OV64B 官方全阵列9248×6944最高15fps／RAW10，4K60是另一个模式。因此不采用64MP60带宽或RGB帧率承诺；摄像头BOM及宿主模式待核。其尺寸、IMU版本、辐射测温条件也须按实物版本关闭。[OmniVision brief](https://www.ovt.com/wp-content/uploads/2022/01/OV64B-PB-v1.2-WEB.pdf)；OAK普通Pro与W的量程／接口不能混用，普通产品文档75cm基线与W75mm及97mm壳宽冲突，该75cm不采用。[普通Pro文档](https://docs.luxonis.com/hardware/products/OAK-D%20Pro)

## 光学分区与全身分配

LWIR Boson+对应8–14µm；940nm主动深度／夜视与905nmLiDAR属于不同光路，近红外深度不能代替热像。普通玻璃遮挡热像，需独立合适LWIR窗；FLIR给出锗窗方案，锗通带与AR涂层、角度、温度和窗口自发热仍需核。可采用同一金边外框中的不同材料小窗，不能用一整块普通玻璃或一枚镜头承诺所有谱段。[Boson波段](https://oem.flir.com/en-ca/products/boson-plus/?model=23640A008)、[FLIR保护窗](https://oem.flir.com/support/support-center/knowledge-base/for-protection-is-a-special-window-needed-in-front-of-my-flir-camera-that-wont-interfere-with-the-thermal-imaging/)、[普通玻璃限制](https://www.flir.com/discover/home-outdoor/can-thermal-imaging-see-through-walls/)

以下是**自己的安装预留假设**，不是已核厂商安装净空或模型实装：中央Hadron先留60×75×70mm，OAK每处120×50×55mm，D405每腕65×60×55mm，LiDAR85×85×90mm，主IMU55×50×25mm。这些量包含初步支架／导热／连接器余量，实际线缆弯曲半径、窗口口径和固定座均待定；对应机器可读 `perception_allocation.json` 的世界位置全部为null。

前后各一枚127°H摄像头，理想无机体遮挡仍有总106°侧向空缺；实际厚臂、持物、蹲姿及折足可能更差。是否增侧向摄像头要由真实逐姿态射线覆盖图决定。MID-360必须有实际环向视域；把它藏在中央小孔后就失去360°。其−7°下视也不能替代近脚检测。外置位置可能涉及审美，当前未采用。

脚部先按**净6D踝力＋分段前掌／后跟接触＋折叠／锁状态**分工。单块压力垫只有法向信息，不等于6D。ATI高载参考Omega250IP60已到Ø295×94.9mm／31.8kg，SI16000-2000范围Fz32kN／力矩2kNm；3t等效外压29.43kN若偏心0.25m则7.36kNm，仍超该力矩测量范围。因此不能据中心Fz选定脚传感器；分布应变／接触传感与可标定载荷映射仍是工程待核。[ATI高载参考](https://www.ati-ia.com/products/ft/ft_models.aspx?id=Omega250+IP60)

编码器需分电机侧／关节输出侧；电驱反馈要有相／母线电流、电压、制动状态与绕组／壳温；液压要有两腔压力、油温、杆位置与阀反馈。新本体轴数、量程、SKU、电功和接口尚未落实，不能把这些未知写成零质量或零电功，也不能仅“标黄”放行。

## 功热、带宽与50Hz入口

一Hadron、前后两OAK、一MID、两D405、一VN及两Mini45的**目录模块子集**约0.8214kg；计算模块运行预留17.62–26.62W，独立峰值预算相加50.32W。后者不是同工况联合峰值额定；AFE、脚感知、宿主推理、DC转换、网络／USB盒、窗口加热／密封／支架均未计入，整机质量功热未闭合。保守先把所供电功当待排热上界，峰值持续时间另测。

原始视频大于“小摄像头”的直觉预算：OAK例1280×800 RGB8／30Hz＋640×400 Depth16／60Hz为1.032Gbps；再传两mono30Hz增加0.492Gbps。Hadron LWIR16／60Hz约0.315Gbps，OV64B全阵列RAW10／15Hz本身约9.63Gbps。均为自身公式推算，不保证模块同时支持这些格式；共享USB控制器、压缩／裁剪、MIPI宿主和DDR复制必须按实际模式核。

MID点载荷约22.4Mbps，另有包头与网络开销；官方包内首点时间为ns，包内time_interval以0.1µs计首末点总时间差，N点在该区间内均分。这是分辨率，不是实际时钟误差；协议坐标mm要换m，IMU加速度g要换m/s²，并按每点采样时刻做去畸变。[官方MID协议](https://livox-wiki-en.readthedocs.io/en/latest/tutorials/new_product/mid360/livox_eth_protocol_mid360.html)

已有Gorilla交接文件的50Hz／20ms／每tick一次原生积分作为本轮**对接目标**；本次未运行Bevy。感知按各自频率异步采集，10Hz点云不能重复贴成50Hz新观测。统一样本带模型／外参／episode身份、采样与到达时间、曝光区间、时钟误差、序号、有效性及age；根据采样时刻查询躯干／腕运动历史。Hadron EXT_VSYNC、VN同步脚及MID PTP可分别探索；OAK USB硬触发口未核，不能借PoE型号接口。曝光→传输→推理→执行p50/p95/p99、拥塞、漂移、重置与超时必须实测，当前均null。超时恢复与安全停止分开；物理反馈tick不等待推理服务。完整可加载契约见 `feedback_contract.json`。

先关闭的红线是新本体米制外形与安装扫掠、所有动作下视野／近距盲区、主动光学窗口与眼安全、真实采样模式／时间误差、脚6D量程与载荷映射、供电／持续温升和宿主端到端延迟。下一阶段先做同源传感器覆盖与接口探针，再做有真实接触的搬运／开门闭环；当前没有算法成功率或实物能力放行。

## 重跑与证据

在仓库根运行 `python .scratch/gorilla_internal_g26_perception_modules/build_contract.py` 可重新生成派生候选（会产生新UTC／hash），不是重抓网页或恢复OEM规格。`first_facts.json` 原字节保留；`final_facts.json`记录来源冲突与最新图片绑定。`limited_check_receipt.json`只检查身份／算术，`source_manifest.json`绑定输入和最终文件。没有生成新CAD、采用审美、稳定SI或采购决定。
