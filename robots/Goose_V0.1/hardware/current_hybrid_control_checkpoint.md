# 当前18轴硬件通信检查点

当前344件装配的18个主动轴已接到独立的软件通信链：17个AK经两条USB-CAN-A串口接口，`head_roll`单独使用5V XC330 TTL。新增代码处理真实选型的串口封包、AK V3字段、SI转换和整机协调停机；旧16轴DYNAMIXEL模型保留兼容。**这完成了可检查的软件增量，没有放行实物通电或第三、第四阶段完整工程目标。**

## 已交付及边界

| 内容 | 交付 | 验证范围 |
|---|---|---|
| USB-CAN-A传输 | [串口驱动](../../../src/sai_agent/goose/can_transport.py) | 固定20字节、校验、分段/连续接收、有限缓存、部分写入、明确配置；真实pyserial库经本地PTY验证，非实际适配器 |
| AK V3协议 | [协议实现](../../../src/sai_agent/goose/cubemars_v3.py) | 扩展ID、带边界的MIT封包、电流命令、禁用与状态帧；不套用通用演示参数到AK40/45 |
| 当前18轴控制 | [混合总线调度](../../../src/sai_agent/goose/hybrid_hardware.py) | 按当前契约分配9/8条CAN轴与1条TTL轴；先检查全部档案和命令，再写入；独立软件看门狗和故障锁存 |
| 单独TTL轴 | [既有DYNAMIXEL驱动](../../../src/sai_agent/goose/hardware.py)加只读预检入口 | 构造当前`head_roll`专用规格，保留当前限位；不把旧`beak_drive`或12V轴带进来 |
| 被动检查 | [有限采集命令](../../../scripts/diagnostics/inspect_goose_can.py) | 两条串口、缺轴/故障/校验记录；只采集，不发送电机命令。可明确请求适配器silent配置 |
| 待标定资料 | [18轴空白标定模板](../configs/hybrid_hardware_commissioning_template.json) | 未知值是null，放行标记为false；不是能直接运行的电机配置 |

[验证记录](../evidence/current_hybrid_transport_checkpoint.json)对应本轮源文件。65项检查通过，包含原厂独立封包向量、分段/错误恢复、带符号反馈、转换量纲、真实PTY双接口采集、整机上电前检查、末轴越限不导致先发首轴、B总线断开时仍尝试A总线和TTL停止，应用不继续调用时软件看门狗停止，以及350W正向机械功率越限时发送前拒绝。

当前力矩控制使用经单台实测确认后的电流模式与`Nm/A`。每台设备需绑定型号、固件、实体身份、轴向/零位、输出位置语义、极对数/减速比、电流与温度限值，以及驱动器自身超时行为。嘴轴的档案还要覆盖实际传动链。没有采用名义堵转数据填入这些标定值。

## 原厂协议复核

[Waveshare封包说明](https://files.waveshare.com/wiki/USB-CAN-A/Demo/USB%20(Serial%20port)%20to%20CAN%20protocol%20defines.pdf)的工作示例与[原厂Python示例](https://files.waveshare.com/wiki/USB-CAN-A/Demo/python/USB-CAN-A-py.zip)确认CAN ID为小端。配置采用固定20字节、扩展帧、1Mbps CAN和2Mbps串口；配置帧写完只代表主机已发请求，配置ACK与持久化尚未证实。

[AK V3.2.0手册](https://www.cubemars.com/data/cms/202602/ak-series-prodcut-manual-v3-2-0-for-ak-3-0-robotic-actuator.pdf)与[原厂演示](https://www.cubemars.com/data/cms/202603/arduino-demo-for-ak-3-0-series-motor.zip)用于字段定义。MIT顺序为Kp、Kd、位置、速度、前馈；手册量化公式的上端溢出问题按演示中的有界公式处理。状态保留电气转速ERPM和驱动板温度，不冒充输出转速或绕组温度；状态帧没有供电电压字段。

[来源与差异记录](current_hybrid_transport_sources.json)保存原厂文件哈希。供应商下载物留在本地artifacts，不把第三方PDF或示例代码装入交付仓库。正确字段格式不证明当前AK48驱动的电压、电流、超时或MIT参数档案已确认。

## 被动采集入口

安装`hardware`可选依赖后，接入明确的两条串口，例如：

```bash
PYTHONPATH=src python scripts/diagnostics/inspect_goose_can.py \
  --can-a /dev/serial/by-id/ACTUAL_CAN_A \
  --can-b /dev/serial/by-id/ACTUAL_CAN_B \
  --seconds 5 --configure-silent \
  --output artifacts/Goose_V0.1/can_bench/passive_capture.json
```

命令中的设备名需要替换为真实接口；不能靠`ttyUSB0/1`顺序认定总线身份。没有电机或未产生反馈时，命令返回缺轴结果，不能据此标成实物通过。silent节点不会替其他节点提供CAN确认位；单电机台架须另有正常CAN节点形成有效总线。

采集记录的时间是主机收到串口数据的时间，不是电机采样时间。程序结束或异常均关闭串口；有限采集不会写电机Flash、零位或使能寄存器。默认不配置适配器，`--configure-silent`才发送其silent配置。

## 未完成的系统门槛

- [供电与回馈](power_release_checkpoint.md)：当前A2连续电压、回馈、母线保护、浪涌、DC/DC与热布线仍未放行。
- 驱动器实际电流模式、反馈语义、超时及禁用行为需台架确认；无当前电机／固件实测证据，模板保持空白。
- 硬件急停独立于USB与进程；软件线程在操作系统、进程或通信阻塞时不能保证停机。禁用发送成功不等于实物已无力矩，程序不宣称已确认。
- USB/ARM64持续延迟和丢包、TTL延迟、IMU同步与真实满负载200Hz控制未验证；看门狗只在有限软件故障注入中通过。
- 实际控制还要与当前步行、转向和指定物拾取／拖拽闭合。当前接口没有把未测电压补成数值，也没有改动MuJoCo、Godot、Unity或Bevy的中立关节与物理参数。

下一步回到整机供电保护选型及安装、整机装配路径；不扩展PPO或继续在通信字节上打磨非关键功能。
