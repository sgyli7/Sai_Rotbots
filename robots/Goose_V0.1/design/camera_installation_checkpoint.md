# 相机安装与任务视野检查点

本增量修正旧18mm宽单板相机占位，提供真实原厂包络筛查、保留当前夹嘴轴承固定结构的自研相机承力架、开孔面罩及大眼色环。**三个自研件是独立候选，未并入344件默认装配或前端夹取模型；第三、第四阶段及最终制造外观仍未完成。** 不以本页替代整机退出条件。

[同版增量核查](../evidence/camera_checkpoint.json)验证整个来源链、四边面闭合、默认模型不被改写和本地链接；它还记录四件旧展示光学件的质量台账重心比实际源高1.5mm的既有差异。下一次集成以新原生几何重建这些重心和惯量，不沿用旧光学件参数；这轮没有把该差异静默改入默认训练模型。

## 实际来源与安装结构

[Arducam当前产品页](https://www.arducam.com/arducam-16mp-imx519-fast-auto-focus-usb-3-0-camera-module-without-enclosure.html)的采购候选为B0471-1，34×34mm板，5V±5%、最大1.48W、65°水平/51°垂直视场，USB3.2 Gen1 UVC。页面标称最近对焦10cm、自动对焦0.2–4秒；1920×1080可50fps，USB2仅720p/10fps。2026-10-01页面价格129.99美元，未计运输税费及中国报价。页面同时写“Without Enclosure”和带后盖/三脚架适配件的包装，实际批次必须核对。

[2023年数据表](https://www.arducam.com/downloads/datasheet/B0471_16MP_IMX519_USB3.0_Camera_Datasheet.pdf)与[原厂STEP](https://download.arducam.com/3D-Drawing/B0471.STEP)提供三层PCB及完整26.5mm级深度。STEP不是完整有效闭合实体：四个子装配中`UC-A48_Rev_C`没有闭合实体。检查保留它的完整扩张包络，没有删除后板来获得“装得下”。原厂文件位于本地`artifacts/Goose_V0.1/camera_vendor_docs/`，不随自研制造源再分发；[筛查记录](../evidence/camera_catalog_layout.json)保存来源和SHA。

16组有限位置/俯角方案中9组通过当前两片头壳、带夹嘴轴承固定的头架和嘴部电机的扩张包络检查。选择镜头前端原生坐标`[190,0,604.5]mm`、相对于头部向下20°，接口边朝上；原生CAD与装配坐标仍相差3.7mm刚性基准抬升。前端的Type-C**配对插头和线缆弯曲半径没有包含在供应商模组CAD中**，必须另行闭合。

[自研CAD清单](../cad/exports/camera_carrier/manifest.json)包含：

- `head_frame_camera_carrier`：在当前`head_frame_with_jaw_retention`原生实体上联合新增短悬臂和相机前板托架。完整保留轴承压盖螺孔、固定座和检修凹槽，不回退到旧头架。铝件条件质量约50.522g。
- `camera_open_face`：PETG圆角前面罩，真实13mm镜头通孔和四个候选M2孔，约6.619g；不再用实心展示脸板或假玻璃封住光路。
- `camera_open_eye_bezel`：33.4mm外径薄色环，保持大眼比例，约0.200g；涂装/胶接工艺未放行。

三件BREP/STEP/STL有效性、单实体、交换体积和水密检查通过，源共有64,536个四边面；完整惯量、重心、文件哈希在清单中。相对于当前头架及四件旧展示光学件，**净增约3.762g**；旧25g相机预留和80g头部结构预留没有抵扣或消费。相机的真实质量未获原厂数据，不能把这个局部增量当作全机最终质量。

三件对当前头壳/嘴电机的九组原生配对均无实体交集。[原厂原生安装复核](../evidence/camera_supplier_native_mount_fit.json)分别检查三个有效供应商子装配及非实体后板的保守包络，保留全部四组。前板28×28mm孔网在原厂STEP中的孔径约2.3027mm，名义M2径向间隙约0.1513mm；这不是B0471-1实际批次的公差承诺。先前扩张前板盒与托架支撑唇的正交集没有直接豁免，以实际有效原生PCB形状重新测量。

## 视野与完整动作的关系

[实际轨迹视野记录](../evidence/camera_recorded_task_view.json)读取已保存19.9秒自由根夹取试验的199个真实头部/物体位姿，没有改姿态，也没有追加PPO。用名义视场投影样件中心及八角点，并对八个原生头部实体做精确线段遮挡查询。

**现有动作中的地面样件中心在199帧中都没有同时满足视场、最近对焦和无遮挡。** 靠近后进入视场，但上嘴仍挡住样件；夹紧时镜头到中心约92mm，低于当前页10cm标称最近对焦。原夹取控制器没有相机输入，不能因为夹取成功就宣称指定物视觉自主完成。

三组有限站姿低头观察方案中，`head_pitch=1.05rad`能够看见指定样件中心和八角点。现有完整接触模型在该姿态未出现超过0.2mm的自碰撞候选，名义双脚承重静力也在现行连续力矩范围内。**这些仍使用未加入新相机件的物理模型**，不是新装配的全行程或动态放行。

动作架构需要“观察并定位→固定/校准焦距→按已定位目标接近→基于编码器及接触/电流完成末段夹取”。相机不能持续看到闭嘴夹持区，不能假设自动对焦在运动中即时完成。实际标定、裁切视场、物体识别、定位误差和接触反馈尚未实现；本轮不展开为新的视觉/RL项目。

## 下一段整机工作

相机局部探索在此收束，返回整机装配、电源与驱动的关键路径。相机后续只保留明确安装门槛：实际SKU/批次与近焦确认；M2螺钉/垫片/隔柱及PCB夹紧；USB3插头、服务余量和运动线束；头壳过渡与相机孔位固定；真实质量/惯量、热和整机回归。原有焊点及装饰细节继续延期。

默认344件、18轴及训练接口没有被改写。本候选合入时重新生成同版逐体参数、CAD显示/碰撞及完整装配证据，四套配色继续由同版实际装配渲染；不把现在的旧四图称为新相机候选的最终样貌。

## 复现

本地原厂文件准备好且SHA一致后，按顺序执行；原厂文件版本不同则重新筛查，不能绕过哈希。

```bash
PYTHONPATH=src python scripts/diagnostics/check_goose_camera_layout.py
PYTHONPATH=src python scripts/cad/build_goose_camera_carrier.py
PYTHONPATH=src python scripts/diagnostics/check_goose_camera_mount_geometry.py
PYTHONPATH=src python scripts/diagnostics/check_goose_camera_task_view.py
PYTHONPATH=src python scripts/diagnostics/check_goose_camera_checkpoint.py
```

轨迹投影需要本地已保存的原始夹取运行产物，其SHA在记录中固定；若需重生成，先依[夹取检查点](tip_grip_checkpoint.md)完整复现该试验。初稿误用旧头架的文件单独保留在本地`artifacts/Goose_V0.1/camera_predecessor_attempt/`，没有将其结果沿用为当前装配通过证据。
