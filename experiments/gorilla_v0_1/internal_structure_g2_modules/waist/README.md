# Gorilla G2：旋转腰链有界候选

只新增本 scratch；G1、原 AA3/C15 111甲、canonical 和 Git 均不作为修改目标。两种宏观布局 A/B 已实际生成；A 的 pitch 沿 +Y 输出、B 沿 -Y 输出。两套初版 36 件均通过资源检查、neutral 自身2对/原甲15对；A 所查姿态原甲较少，选择 A 在同一拓扑落实安装。没有第三宏观布局。

**当前源 `scene.json` SHA `3c462863c2a58286c79b008aa7822bcee461605b217f3d1bdd1001d91fb26edb`；44 unique native 资源契约通过，但整套安装/物理/SI/审美均未通过。**

## 实际源与机械结果

- yaw CSG65：core `[0,0,1.42]`、轴 +Z，A 输出 Z1.486；pitch CSG65：core `[0,0,1.78]`、轴 +Y，A 输出 Y.066；roll CSG50：core `[-.078,0,2.05]`、轴 +X，A 输出 X-.025。全长保留123.5/123.5/98mm。
- 三套各十项完整功能库存：gear/motor/壳/冷却壳/联轴器/输出适配/制动/编码器/controller/connector。完整参照与有限自建材料分列；库存齐全不能证明实际转子、制动、反馈力链接通。
- 窄100×140×6mm 6082-T6假设主梁/脊柱及真实钢接口替代大钢盒；Al原坯按钢座和完整 gear/motor/控制盒安装空间实际加工。四个钢/Al组合反力 core各1连续材料体；八肩螺栓单独有间隙，预紧/线程/联接力未知。
- 新模块干质量 **158.412 / 162.402 / 170.202 kg**，排除全身甲、臂腿、系统及旧上身。不能与 G1 相减称整机减重。

原 controller/connector 穿 pelvis壁、gear占入B固定面/Al框已实建空腔消除。B固定法兰置于B面外侧；motor输入大盘置于完整motor端面外。生产时遇一处共线退化三角，保留 `selected_install_resource_rejected_scene.json`；用100.8mm Al原坯加工到101mm钢接触面重新生产，未删face/翻面/放宽validator。最终源资源通过。

## 未闭合的主要机械问题

**中立真材0，但七对组件/接口仍 unresolved：**三 gear↔WG hub、三 motor↔小轴/孔域、一个 roll brake↔输入2.171cm³。R35 hub flange也越过B面3mm，不能仅凭中心孔解释整片法兰。WG插深与露出法兰、rotor holder、制动孔/制动力传递、encoder rotating target均是实际机械缺口，不能作为采购证书缺失处理。

QTR rotor ID已核111mm，现 flange R52比孔R55.5小3.5mm，尚未接到转子。QTL rotor ID/OD/L=140/148/41mm；R74端盘已移出gross66mm motor，但真实转子端基准、套筒/支架与转矩路径仍未知。输入壳、轴承、输出螺栓/预紧、所有螺接梁节点仍要落实。不能以body owner替真实联接证明。

pitch -10°有0.612cm³、-15°有5.123cm³两Al carrier交；-5/+5/+10/+15及所查组合姿态真材0，仅为采样。当前只能讨论 **[-5,+15]** 候选范围并继续连续扫掠，原±25°没有实现。

neutral原甲15对＝12有限材料＋3硬盒，多在骨盆壁、肩钢座/主梁及隐藏回边。逐对、位置、源皮厚/回边不确定性见 receipt。先比较内部梁端/接口/控制bay重排；主梁现延伸至±570mm，超过原肩轴±460mm110mm，内部端长可作为下一P0讨论。是否仅改内皮尚未证明；本轮0mm改甲，没有证据要求扩大整肩外观。

## 物理粗核与边界

`section_load_inertia_screen.json`直接从最终native截取肩梁/脊柱及roll carrier的钢/Al净截面。肩梁A=2736mm²、I=7.48755e-6m⁴；旧207.27kg臂＋50kg手、1.5倍、.46m悬臂仅敏感性下σ16.275MPa、δ.234mm。没有接触/螺栓/扭转/局部疲劳通过。

CSG65 Tr/Tav=1236/1976Nm；CSG50=611/866Nm，来源July2026安装目录p12/13。Tr条件为gear入力2000rpm；超Tr不等于绝对驱动失败，低于参考也不保证整套持续运行。旧上身880–1053kg加本候选子体仅保留上下文载荷挑战，不是新版整机质量。原[-25,+25]高档pitch重力挑战峰约1.60kNm，仍未验证动态/热。

输入J使用已核gear入力及bare rotor、实际自建coupling积分后反射；完整OEM固定/输入/输出3D惯量没有用实体圆柱伪造。QTL Tc65/Ts46、Pc690W是100°C coil/20°C mount条件，QTR48V Tc点260rpm；供电、回馈、冷却、完整转子支承/保持没有闭合。

## 身份与图

A/B初源及各同A制造阶段都保留确切scene/producer字节，映射在manifest。`bare_chain_native_four_view.png`与`with_original_armor_native_four_view.png`已实际打开；44件及原111甲同scale native诊断投影，没有其余全身硬件，不是新审美权威。

首次复制renderer误留G1输出路径，意外覆盖G1三产物；root恢复原精确字节。当前renderer使用自身目录并断言，未改G1源或其manifest。主验收见 `installation_and_route_receipt.json`；所有放行仍false。
