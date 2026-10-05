# Goose V0.1

一只幽默又实用的双足机器人鹅：长颈、嘴内夹持、手动翼形检修门。设计参考 Untitled Goose Game 与 MicroDuck；叼取和拖拽同等重要。

## 碰撞体优化交付

**当前版本：`goose_task_proxy_11_v1`，共11个凸碰撞体。**

| 你要找的内容 | 直接打开 | 文件内容 |
|---|---|---|
| **1. 碰撞体示意图** | [打开三视图 PNG](images/task_proxy_11_v1_colliders.png) | 下方同图：斜视、侧视、正视，以及11个碰撞体的颜色图例 |
| **2. 碰撞体文件** | [打开碰撞文件目录](models/task_proxy_11_v1/) · [装配模型 robot.xml](models/task_proxy_11_v1/robot.xml) | 11个OBJ凸包；XML定义位置与关节装配，native_plant.json保留原硬件参数 |

![当前优化版：11个凸碰撞体三视图](images/task_proxy_11_v1_colliders.png)

取用时保留整个文件目录。OBJ以米为单位、使用所属刚体的局部坐标；组装位置以`robot.xml`为准。**这是仿真碰撞代理，真实硬件CAD与打印件另行保存。**

[逐个OBJ文件清单、运行契约与验证说明](design/task_proxy_11_v1.md)。

## 其他当前资料

| 内容 | 入口 |
|---|---|
| 外观、手动检修门与硬件结构候选 | [实际四色图、CAD及采购增量](design/manual_wing_service_checkpoint.md) |
| 电气与制动PCB候选 | [可编辑原理图、PCB与验证范围](hardware/brake_pcb_checkpoint.md) |
| 指定物训练输入 | [圆柱抓杆／把手，100／200／300g](design/task_samples_v1_handoff.md) |
| 虚拟训练版本与后续硬件差异 | [004冻结说明](design/virtual_training_freeze_handoff.md) |

硬件资料属于独立候选，未替换上述碰撞版本。平地工程入口、完整动作任务、各游戏引擎和实体制造分别验收；具体范围见各入口。

<details>
<summary>历史记录与原始导入资料</summary>

[历史记录与阶段候选](design/history_index.md)。旧模型、旧图、聊天交接和阶段试验集中从此页查阅，不作为当前碰撞交付入口。

</details>
