# 髋部连接与转向候选检查点

本候选继续第三阶段机械工作；**第三、第四阶段均未完成，不能交付最终外观或冻结硬件**。不扩训 PPO，不修改已发布第二阶段模型和契约。原有全部资料保留。

最新用户指令：Sai_Lab 尚未开始训练，应充分优化整体结构，不为旧训练参数凑合。后续整机布局比较见[训练前髋部布局比较](hip_architecture_optimization.md)；本页连接件与开口均是诊断候选，未选为最终结构。

## 回到整机：本次解决什么

每条腿仍为髋偏航、髋侧倾、髋俯仰、膝俯仰、踝俯仰、踝侧倾六轴。髋偏航范围为 ±0.6 rad，约 ±34.4°；它是关节范围，不是整机转向半径或速度。实际目标包括小步原地转向和弧线转向，最终需要连续左右90°/180°、换脚与带物转向回放；本轮没有把终点逆解称为行走验收。

真实 AK45-36 STEP 量出：原髋侧倾转接盘至髋俯仰电机仅 **0.25 mm**。新增5.5 mm承力板会占用间隙。因此制作独立候选，把两侧髋俯仰及其全部下游轴、叉架、脚和接地轮廓整体前移 **8 mm**，轴顺序和轴向保留。新转接盘至电机8.25 mm，承力板至电机 **2.75 mm**。电机原始 STEP 是表面装配，使用精确表面距离；不能拿它的零实体交集作为无碰撞证明。

## 局部承力增量

- 两侧合计8件原生连接件，6061-T6候选体积质量 **122.316 g**：输出转接盘、5.5mm侧板、交叉攻丝角块、4mm电机定子前支承环。
- 新增 **38颗M3螺钉**，保守螺钉/头部/垫片实体上界 **59.294 g**；长度与有效啮合检查通过。原髋俯仰背侧独立支承螺钉只保留一份。
- 替换两份12g安装预留，并消费两份10g转接件预留；其他未完成框架、线束等预留继续保留，没有将未知件设成零质量。
- 无壳体修订时条件整机 **9.745 kg**，63组静力工况通过接触可行性和原连续设计力矩范围。此质量不是称重值或最终硬件质量。

## 下侧开口试验与失败

原壳体会挡住真实连接件。另做六件原生壳体替换候选，采用向下开放的椭圆髋部开口，X半径95mm、Z半径80mm，中心X=-15mm/Z=210mm，左右从|Y|=50mm向外。开口以外保留原NURBS曲面；头壳不变。没有批准该可见外观改动。

这版削去94.851g皮壳，整机条件质量 **9.651 kg**，63组静力检查通过。但29组单轴/组合极限姿态中 **4组失败**：同侧髋偏航与侧倾组合时，支承环和前壳仍交叠约19.143mm³。不能因为单轴姿态通过就放行。失败详见[装配检查](../evidence/hip_clearance_carrier_screen.json)，后续只做一次加宽开口比较。

第二次比较将 X 半径改为105mm，其余开口参数保留。六件皮壳减少102.868g，条件质量 **9.643kg**，63组静力与29组限定原生交集检查通过。[限定装配证据](../evidence/hip_clearance_wide_carrier_screen.json)、[同版质量](../evidence/hip_clearance_wide_component_parameters.json)。**该范围只检查新连接件与现有原生件/电机包络，未验全机。**[实际侧视](../images/hip_carrier_wide_candidate/side.png)显示开口对简约机箱破坏明显，不能作为最终外观；不继续把开口做大。

同版转向终点逆解中，左右±15°共4组通过；±30°中的两组仍在膝限位处产生约1.78mm位置误差。8组静力接触与力矩检查通过；**连续转弯步态、实际换脚和硬件转向均未验收**。

## 网格与验证

14件新连接/开口皮壳共 **1,793,382个四边面**，独立拓扑、体积、世界重心和哈希检查通过。工程编辑源为原生BREP/STEP；NPZ四边面是原生表面离散化，板件采用共享边平面分割，不冒充艺术细分控制笼。STL按格式提供三角面。

加宽版14件原生离散化 NPZ 的 **1,782,198个四边面**通过[双精度源检查](../evidence/hip_carrier_wide_quad_gate.json)。但247件实际 Blender 装配的2,626,842个四边面中，四件壳体共5,147个面低于现有 `1e-14m²` 面积阈值，尽管无非流形边、体积为正，**Blender编辑源仍失败**。不能把“全是四边面”称为可用性通过，也没有删除小面或放宽标准来伪造通过。[保存源审计](../evidence/hip_carrier_wide_blender_quad_gate.json)。此试验本身已因外观问题不选用；后续选定的壳体必须重新产生并通过有效四边面源。

初次相对精度二进制STL失败，已保存在本地scratch。最终皮壳采用OCCT **0.12mm绝对离散参数**及保留双精度坐标的ASCII STL，回读闭合、绕序和质量检查通过；没有补洞、删除面、翻转法线或修饰几何。0.12mm是请求离散参数，不是已测连续Hausdorff界。

原生交集运算改为直接OCCT，保留STEP子装配位姿，拒绝表面-only输入。9组独立解析盒体交集/公共刚体变换回归和表面拒绝测试通过。原156件叉架重新检查13组姿态仍通过。全套测试 **96通过，20.86秒**。

髋部布局比较给静力求解器增加显式左右接地中心参数，旧版本仍默认±89mm。修改后全套测试 **96通过，20.71秒**；新布局静力另由解析力矩与MuJoCo重力/Jacobian相互核对，不拿原布局结果替代。

## 可复现入口

```bash
PYTHONPATH=src .venv/bin/python scripts/cad/build_goose_hip_roll_carriers.py
PYTHONPATH=src .venv/bin/python scripts/cad/build_goose_hip_clearance_skins.py
PYTHONPATH=src .venv/bin/python scripts/diagnostics/check_goose_hip_roll_carriers.py --skin-manifest robots/Goose_V0.1/cad/exports/hip_clearance_skins/manifest.json
PYTHONPATH=src .venv/bin/python scripts/diagnostics/check_goose_hip_carrier_parameters.py --skin-manifest robots/Goose_V0.1/cad/exports/hip_clearance_skins/manifest.json
PYTHONPATH=src .venv/bin/python scripts/models/build_goose_hip_carrier_preview.py
```

## 回到总目标

仍缺髋偏航至侧倾、踝部交叉轴、完整机架、头/嘴轴系和夹力路径、电气释放、线束扫掠、制造装配与最终外观一致验收。静力和这两组连接件不能代表全机可制造，也不能代表第四阶段通过。供应商电压确认与GitHub PR文字发布审批继续等待；本检查点不绕过审批发布描述。
