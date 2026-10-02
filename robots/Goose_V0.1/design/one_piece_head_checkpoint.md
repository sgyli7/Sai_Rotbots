# 主头壳改为单件打印的结构检查点

原来左右主壳和前鼻罩三件改为 **一个真实空心原生实体**。侧面分件缝已消除，主壳到相机前部使用同一连续 NURBS 曲面；黑色相机面板、橙色夹嘴与内部承力框架仍是各自的功能件。相机光学面和已有紧固孔位置保持。后口和底部提供安装入口，不再为了拼装白壳保留侧面接缝。

这是独立460显示对象、18轴、19体闭合姿态参数候选。按PETG名义密度1270kg/m³计算，主壳 **52.862552g**、整机条件质量 **10.430762603kg**，比462件版减少10.131755g。实体、打印网格与实际渲染同源；完整制造、实物及三四阶段目标仍未放行。

## 同版资料

| 资料 | 内容 |
|---|---|
| [整机装配源](../cad/source/one_piece_head_service_fixture/assembly_scene.json) | 459个保留对象原样；三片旧头壳替换成一个主壳 |
| [CAD与交换文件清单](../cad/exports/one_piece_head_service/manifest.json) | 可编辑BREP、STEP、闭合STL和全quad显示源及哈希 |
| [结构输入](../configs/one_piece_head_service.json) | 名义壁厚、光学面、后/底入口与原厂PCB局部净空 |
| [完整参数](../evidence/one_piece_head_service_parameters.json)／[19体SI表](../hardware/one_piece_head_service_body_parameters.csv) | kg、m、kg·m²，保持原18轴顺序与中立坐标 |
| [候选增量BOM](../hardware/one_piece_head_service_bom.csv)／[XLSX](../hardware/one_piece_head_service_bom.xlsx) | 一个自研打印件替换三片旧壳；其他五金和预留不抵扣 |
| [有限原生几何与同源静力](../evidence/one_piece_head_service_fit.json) | 头部有限姿态、保留核心拆装样本、原厂完整源与静力；不是整机放行 |
| [同源四色及头部近景](microduck_color_blocking_one_piece_head_service.md) | 与本装配一一对应的实际图，等待用户审美验收 |
| [失败保留](../evidence/one_piece_head_failure_history.json)／[STEP交换恢复](../evidence/one_piece_head_step_exchange_recovery.json) | 旧折痕、净空和拆装失败，以及没有降低阈值的交换复查 |

装配源SHA256：`1a05dc55c66f96bee59f8cdb50d2f15942fdcf201e91c8d2e72140ba30be25de`。344默认物理模型、462壳支承源和全部旧交付保留；没有用旧动作或旧动力学替本版放行。

## 结构及检查范围

主壳名义正常壁厚2.2mm，前部名义径向壁厚1.4mm，前安装面1.2mm；这些名义值不是已认证的全壳最小厚度。前上部连续曲面平滑增加最多1.8mm，给原厂PCB留空间。三处局部内侧避让依据完整原厂源的指定shell包络，各扩大0.7mm；到外部连续曲面的最小距离为1.717373mm，其余两处约2.7475mm。原厂未闭合组的475个shell、12448个face完整保留作保守检查，不以删掉PCB元件获得通过，也不把未闭合厂商源称为完整制造实体。

后口X100.75mm；底部开口名义110×70mm，上缘Z588mm、X100至210mm，连通后口。首版100×70mm底口的边缘挡住框架/电机，直接向下取出框架也失败；原始位置和接触量保留。扩大底口只改变底部真实入口，主体上部轮廓、光学面与接口位置保持。

单件源有效且只含一个实体，显示源全为四边面并闭合，STL回读闭合且绕序一致；源quad是CAD派生采样，不是细分曲面艺术控制笼。STEP使用原生声明容差的GREATEST模式，回读仍要求体积相对差不大于1e−5；此前AVERAGE导出超限及精度比较均保留。实际打印层高、方向、支撑拆除、后缘去毛刺、局部强度和公差需继续确认。

装入整机时仍需按序安装内部承力框架、电机、轴承、相机及夹嘴。有限直线核心检查只保留真实框架、电机、头轴适配和两只夹嘴轴承；相机、夹嘴连杆、面板、紧固工具和线束属于后续独立路径。不能把有限样本解释为连续扫掠、完整装配顺序或全部可维修性通过。

同源静力使用完整更新质量、重心和惯量，保留嘴尖20N／中部50N两组各63工况及原条件力矩上限。该上限仍是设计筛选依据，不代表封闭安装的实物热额定；动态行走、转向和夹拖任务仍需新同版模型验证。Unity/Bevy/Godot共用的18轴SI契约未变，没有追加PPO。

## 复现与后续

```bash
env PYTHONPATH=src .venv/bin/python scripts/cad/build_goose_one_piece_head_service.py
env PYTHONPATH=src .venv/bin/python scripts/diagnostics/check_goose_one_piece_head_service.py
env PYTHONPATH=src .venv/bin/python scripts/diagnostics/build_goose_one_piece_head_service_bom.py
```

构建还需要依据[相机来源记录](../evidence/camera_catalog_layout.json)下载原厂STEP，保存到记录的本地artifacts路径并匹配原始哈希。完整供应商源不随自研打印件重分发。

本检查点完成主白壳的单件建模与当前有限结构复查。整机主线继续处理实际组件/工具/线束安装、翼门与接缝支承、供电保护、当前同版动力学和完整工程回归。不会因头壳或四色渲染完成而宣布第三、第四阶段完成。
