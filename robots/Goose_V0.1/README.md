# Goose V0.1

**当前碰撞交付（2026-10-04）：[11 叶 Sim2Sim 工程入口](design/task_proxy_11_v1.md)已通过 M0 验收。** [唯一入口](configs/task_proxy_11_v1_entry.json)绑定同版模型、契约与原生接收器；硬件源未改，源／目标各完成 2,500 次实际积分，并通过有限 FK、已知危险组合、惯量、时钟与摩擦测试。该入口可交 Sai_Lab 绑定新策略；学会行走、起身、拾取／拖拽、复杂地面、其他引擎及完整制造仍各自验收。旧 30,105 叶和 89 叶失败版本保留为历史，以下较早“默认／最新”均属于各自检查点。

**当前优先级：先跑通虚拟侧。** [本周期训练冻结及直接交接](design/virtual_training_freeze_handoff.md)固定004包和10.430690821kg完整SI，不等待PCB、采购及制造收尾；Lab独立物理／GPU准入通过后开展训练。后续硬件候选与虚拟版的逐体参数差异已明确记录，没有静默改入训练版。

碰撞范围与参考：[现行对照与范围](configs/game_collision_budget_v1.json)、[MicroDuck 双足游戏包计数核对](evidence/microduck_game_collision_baseline_v1.json)、[MD/G1 接触角色与精度对照](design/simulation_collision_reference_review.md)。29 是用户澄清的随手数字，MD 的 11 个是具体参考版本实数；新版以任务接触、实际目标后端及动态测试共同验收。原 512 目标与 30,105 块源参考均不作为游戏交付。硬件源与完整 SI 参数保留；本版足底采用独立的平地整体接触近似，未继承真实多区 TPU 的材料和复杂地面资格。

相邻凸包可在连接处交错；[有效过滤表](configs/task_proxy_11_v1_collision_filter.json)只忽略同机内 9 组连接处配对，其余 46 组自碰保留，包括头与身体、左右脚。地面、物品与其他机器人接触均保留；[逐对实测](evidence/task_proxy_11_v1_collision_filter_acceptance.json)在 MuJoCo 和原生 Rapier 各通过 97 个刻意重叠夹具。真实 CAD 装配干涉单独检查，代理例外不放行制造。

[Godot/Jolt过滤实测](evidence/task_proxy_11_v1_godot_filter_acceptance.json)另外通过152个原生夹具（同样97个配对／外部接触检查，另加55个未过滤阳性对照），并验证实例重新应用、错误排除拒绝和关节默认屏蔽复位。新接收工具逐对应用有效表，不沿用旧接收器的全部关节自动排除。这里只验收独立形状／过滤夹具，Jolt整机动力学仍未放行；[Godot自带物理后端的深重叠失败](evidence/godot_physics_collision_filter_rejection.json)保留，未混入Jolt通过结论。

当前独立整机结构：[手动翼形检修门检查点](design/manual_wing_service_checkpoint.md)。478显示对象、18主动轴、19体SI、10.398672986kg条件质量；真实双铰链、轴向保持和手拧关闭件已进入24件CAD/采购增量，有限配合、同源静力及19项针对性测试通过。四色实际图已更新，门缝/最终审美、完整制造与电气仍待资格。003运行模型保持原身份；新结构未冒充旧训练版本。

当前电气：[精确驱动资料与18轴端点](hardware/power_release_checkpoint.md)绑定478件源、17CAN＋独立5V TTL。[绝对阈值制动候选](hardware/absolute_brake_chopper_checkpoint.md)已补实际可编辑KiCad、原生针脚/网络核对、阈值角点和真实NGSPICE行为/故障对照；名义及单电阻断开峰值约26.08V，关闭制动反例被检出。这仍未覆盖PCB时序/热、完整断开、冷启动或安装资格；供电保护、制造线束和实机启用门槛保留，未改CAD/SI或003包。

后续[制动安装比较](hardware/brake_packaging_checkpoint.md)提供独立48件CAD增量、525件装配源和10.486951740kg条件SI；零位原生配合、21个有限转向／低姿态及同版静力已通过。PCB仍是预留，热／工具／线束和连续扫掠未放行；没有替换上面的478件基线或11凸体003运行模型。

当前供电增量：[独立原生制动板](hardware/brake_pcb_checkpoint.md)提供44个板上元件、8个外置电阻、同版原理图／PCB、35条信号连接和45件包络STEP。KiCad DRC与复制项目检查均为0违规／0未连接，实际破坏焊盘或反馈走线均被拒绝；42项相关测试通过。PCB包络落在前轮预留内，但质量、真实固定、功率／散热、冷启动及急停使能链仍待闭合；未改写上述硬件参数或11凸体交付。

历史初始训练版本：[460件 Sai_Lab 初始训练检查点](design/training_checkpoint_handoff.md)。同源一体头壳、18主动轴、10.430762603kg；MJCF/URDF、完整SI参数、软脚底、四色实际图和运行入口已打包。实际65/18接口与0.2秒自由根站立冒烟通过，零初始自碰撞候选、零求解器警告；解压校验见[打包检查](evidence/training_checkpoint_bundle_check.json)。完整制造、电气、步行/转向/夹拖及第三、第四阶段仍未完成；不是硬件冻结，不把旧动作当本版通过。

[单件头壳结构说明](design/one_piece_head_checkpoint.md)记录10姿态、33核心平移及126同源静力筛查，完整装配仍未通过。

# Goose_V0.1 — 工程与原始资料入口

历史整机结构增量：[固定机壳到内部框架的四处连接](design/torso_shell_mount_checkpoint.md)。独立462个显示对象、18轴、10.4408944kg条件质量，比446件版增加36.198g；30件名义原生CAD/五金、19体SI参数与采购表已保存，18个有限姿态及两组63个静力工况通过。外部轮廓和连续头壳保持；翼门/接缝、整机强度、电气与同版动力学仍待闭合，三、四阶段未完成。

最新局部修正：[头壳后缘与相机闭合检查点](design/camera_head_closure_checkpoint.md)。原生 CAD 已去除头壳后缘台阶，并补上相机面与头壳之间的连续空心鼻罩；独立候选为446个显示对象、18轴、10.4046964kg条件质量，比419件版增加2.29248g。十个有限头部姿态与同源静力筛查通过；完整装配、制造、审美和训练放行仍未通过。新版[头部近景](images/microduck_color_blocking_446_parts/cream_head_detail.png)及[四色实际渲染](design/microduck_color_blocking_446_parts.md)与原生装配同源。

整机增量汇总：[419件装配与静力参数候选](design/integrated_hardware_candidate.md)。前端夹持、相机架、电源和计算板固定件汇入同一份源与19体闭合姿态惯量，条件质量10.4024039kg，比默认版增加44.548g；嘴尖20N／中部50N各63个静力工况通过，嘴尖50N的63个超载失败保留。右膝静力余量约0.09Nm，最终装配质量与动态余量仍需收敛。此候选尚无同版新碰撞/动力学模型，不是新训练或制造放行，默认344件版保持不变。

**现行默认模型入口：[整机机械与物理检查点](design/mechanical_integration_checkpoint.md)。** 当前344件、18主动轴、10.3578562kg条件质量；真实可更换夹持组件和四组上喙固定紧固已合入源几何、完整惯量、MJCF/URDF与碰撞模型。63个静力工况、限定短时站立和实际两垫对预置50g物体的保持/受拉通过。真实垫面使旧低位参考从24mm变为43.5mm；15mm目标的36组有限姿态筛查没有可用组合，尚未地面拾取。**第三、第四阶段、训练硬冻结与最终制造外观仍未完成。** 完整装配/承力、供电保护、实际硬件控制和整机任务仍待闭合。

独立主线试验：[前端夹取与连续动作检查点](design/tip_grip_checkpoint.md)。六件替换候选仅增重1.673g，保留18轴；补入双脚承重前馈并修正路径后，19.9秒完成自由根站立→地面50g样件夹取→抬升保持→放回→回站，保持段最低间隙约73.7mm、最大机身倾角约2.12°。无超过0.2mm的非脚部碰撞候选、速度越限或求解器警告，但颈根6次控制请求被连续力矩上限截断，严格完整门槛仍为false。候选源和参数独立保存，未覆盖默认装配，未训练硬冻结；早期碰地及掉落失败保留。

电气软件增量：[当前18轴硬件通信检查点](hardware/current_hybrid_control_checkpoint.md)。选定USB-CAN-A串口协议、AK V3与17CAN+独立TTL调度、有限被动采集和故障处理已实现；65项软件/PTY检查通过。当前电机／固件档案、供电保护、独立急停和实物通信仍未验证，不能直接通电或宣布整机完成。

整机安装增量：[两块电源板的框架固定](design/power_module_mount_checkpoint.md)。按厂商真实安装孔补齐两件载板和完整紧固叠层，36件原生CAD、STEP/STL及84,192个闭合quad源已保存；与现行框架、机壳和活动髋部的34个有限姿态筛查通过。保留现有电源/散热/线束质量预留后保守新增10.122g，机身与关节包络未改变。增量采购表和装配图已交付；接线、散热、机壳支承及同版整机集成仍待完成，未覆盖默认344件装配。

整机安装增量：[计算板与集线器的框架固定](design/compute_module_mount_checkpoint.md)。按两套真实孔位生成42件原生固定/替换件和完整紧固叠层，净增28.991g；有效源的34个有限姿态筛查通过，Radxa无效厂商主实体对应13组接触未确认。完整安装仍未通过；USB-CAN-A官方78.52×18.36mm尺寸也揭示旧预留不足。保留失败源，不宣称制造或整机完成。

配色重新验收：[446件 MicroDuck 色块分区候选](design/microduck_color_blocking_446_parts.md)，四张同版实际渲染：[Cream](images/microduck_color_blocking_446_parts/cream.png)、[Graphite](images/microduck_color_blocking_446_parts/graphite.png)、[Lavender](images/microduck_color_blocking_446_parts/lavender.png)、[Sky](images/microduck_color_blocking_446_parts/sky.png)。主壳、中性检修门/脸板、深色骨架和嘴脚点缀分别配色；头部闭合与后缘修正已进入这一版源，仍等待用户审美验收。存在前部过渡空隙的[419件图](design/microduck_color_blocking_419_parts.md)、[344件图](design/microduck_color_blocking_344_parts.md)、[314件图](design/microduck_color_blocking_314_parts.md)与[292件图](design/microduck_color_blocking.md)保留为历史，不能混称本版。

整机装配增量：[真实相机承力架与视野检查点](design/camera_installation_checkpoint.md)。完整原厂三层PCB包络筛查及三个自研原生件已保存；相对现有头架和展示光学件净增约3.762g，保留夹嘴轴承固定结构。现有夹取动作中样件被上嘴遮挡，需要先观察定位；一组低头观察姿态通过有限几何/名义静力检查。相机候选尚未并入默认装配，插头、固定五金、线束、标定及同版整机回归仍未闭合，没有追加PPO。

[36件真实夹持/框架安装](evidence/mechanical_grip_installation.json)核对六个旧对应件替换、净增15.51g及80g预留不抵扣；[组件说明](design/grip_cassette_candidate.md)列出名义几何及未放行的材料、强度、工具路径。现有成功不代表可直接打印装机或下单。

## 历史检查点与原始资料

[314件安装前检查点](design/mechanical_checkpoint_pre_grip_installation.md)及[安装前参数预估](evidence/grip_cassette_parameter_delta_pre_install.json)保留当时的未合入状态；完整原运行资产可由基线记录的Git提交恢复。旧参考、质量和任务结果不得沿用当前验证结论。

以下数字和模型保留其当时版本，不能作为最新参数。

本轮新增：[当前装配的同版参数与运动学参考](design/body_bay_reference_handoff.md)。19个刚体、18轴及10.0525kg条件质量已导出同版MJCF/URDF和CSV，保留262件实际装配显示件；仅用于坐标、惯量和装配核对，碰撞模型未完成，不能用于行走/夹拖训练。第三、第四阶段及最终外观仍未通过。

最新检查点：[机箱容纳与高髋原生装配](design/body_bay_native_checkpoint.md)。134件新建/重建原生实件已与新轴位、条件质量10.0525kg及逐体惯量合并；63组静力和13组限定任务姿态的下半身碰撞筛查通过，262件实际Blender源全部quad拓扑通过。**第三、第四阶段、新训练版本及最终外观仍未冻结**；完整载荷链、供电回馈、连续运动和一项原生体内分类分歧尚未关闭。颈腿护罩研究完成，优先白色薄分段开放罩，尚未加入实际装配。

最新工作：[训练前整机髋部布局比较](design/hip_architecture_optimization.md)与[颈腿护罩研究](design/neck_leg_cover_trade_study.md)。用户尚未开始Sai_Lab训练，现按整机可落地与外观共同优化，旧参数不限制新布局。五组髋部候选完成静力和有限包络比较，**没有整体容纳放行候选**；不把大开口试验或未通过面积阈值的Blender皮壳当成最终外观。优先试白色分段、内侧开放的连杆护罩，局部TPU遮线作为比较；尚未制作护罩CAD。

新增[髋侧倾至俯仰连接件及两组开口诊断](design/hip_carrier_candidate.md)保留原生CAD、29组限定碰撞检查和9.643kg条件台账；静力及局部无交集不等于全机可制造。下一轮训练交付仍待整体布置、承力框架、真实模块容纳与新同版质量/惯量闭合。

最新制造候选：[追加两小时检查点](design/stage_three_four_extension.md)。六组带孔叉架、独立后支承、弹性脚底、转向筛查及同版质量台账已保存。保守条件质量9.608kg，63组静力通过，自由脚夹具23/24通过。**第三、第四阶段及最终外观仍未通过**，不能直接采购装机或作为新冻结训练版本。[实际候选图](images/pitch_foot_candidate/three_quarter.png)保留未制造部分状态。

新增最终交付要求：[实体与电子版外观一致](design/manufacturing_appearance_acceptance.md)。最终图片必须直接来自同版制造装配；现有第二阶段图片不是最终制造外观。[原生曲面壳体增量](cad/exports/manufacturing_skins/manifest.json)仅包含八件外壳基础实体，[一致性检查](evidence/manufacturing_appearance_gate.json)通过不等同整机或最终外观放行。

[第三、第四阶段中途检查点](design/stage_three_manufacturing_checkpoint.md)：八件原生壳体与六件带孔电机接口已验证；头部安装口与统一光学位姿修正通过限定包络检查，实际全机连接与供电尚未放行。[安装候选预览](images/manufacturing_skin_candidate/three_quarter.png)及其 [Blender 源](cad/source/manufacturing_preview/quad_assembly.blend)仍包含第二阶段未制造结构，不能当作最终外观。[壳体物理参数增量](evidence/manufacturing_skin_parameter_delta.json)为名义 8.825kg，仅替换壳体与相机位置；未发布新冻结模型。

第二阶段交接：[嘴部传动、低位接近与供电架构](design/stage_two_parameter_handoff.md)。**当前候选为 `goose_stage_two_si_v2`，18 轴、8.854 kg；嘴部和中颈驱动升级，名义及 4 个扰动低位往返通过。** 供电窗口/回馈保护与封闭头壳热能力仍阻止硬件硬冻结。Sai_Lab 新实验请显式选择第二阶段；下方第一阶段保持历史记录。

第一阶段交接：[18 轴结构与物理参数包](design/stage_one_parameter_handoff.md)。**约 8.62 kg、MJCF + URDF + 逐体惯量 + 统一 SI 契约 + PPO 入口已提供，可启动初训；硬件硬冻结尚未通过。** 嘴持续输出、电源配套和低位拾取控制的未决项与修改边界均在交接页列明。旧 16 轴 RC2 资料不能作为本版训练输入。

执行节奏：[整机里程碑与 Sai_Lab 交接门槛](design/hardware_milestones.md)。当前先收敛大结构，再交付训练基线，制造细节随后完善。

硬件主线：[已确认外观到完整硬件交付](design/accepted_hardware_execution.md)，包含交付证明要求和同版质量／颈部负载初筛。

最新硬件增量：[脚底分层候选与嘴部传动筛查](design/foot_support_and_beak_transmission.md)；保留接地轮廓、增加金属板毛坯，条件减重约 280 g，固定接口尚未完成。

当前已确认外观入口：[饱满机身／大眼／流线鹅掌候选](design/fuller_exterior_review.md)。按最新三条反馈扩大机身并检查八组模块预留，恢复大眼表达、调整脚掌；**用户已确认这一阶段外观并授权上传 GitHub**；进入同版硬件落地，物理和制造仍未通过。

[上一版铰接嘴候选](design/hinged_beak_exterior_review.md)保留对照；约 50 N 仍为待验证目标。

[肩胸与收尾曲面候选](design/sculpted_exterior_review.md)因头嘴不协调、身体不够简约而被后续方向取代，不是获批外观。

[流线型候选失败记录](design/streamlined_exterior_review.md)：用户否决头身卵形比例，当前继续重做形体，不能进入物理放行。

本目录保留了交接包中的图片、文档、工作簿和 CSV；包内旧方案仍可完整查阅。**当前工程候选**按用户后来确认的目标推进：室内平地双足鹅、游戏般的好奇和捣蛋感、叼起与拖拽同等重要、简约手动翼形检修门、鹅叫和头颈动作。所有设计须同时满足外观方向与可制造、可运行。概念图不是尺寸或性能依据。

**当前状态：fuller 外观已获用户确认；旧 RC2 外观曾被否决，其物理结果不适用于新版。制造和采购均未放行。** 原交接包的 [B 步行鹅](design/concepts/history/walker_b_selected_reference.png) 及用户再次指定的 [R2 闭嘴尖嘴](design/concepts/r2_pointed_beak_closed_reference.jpg)、[R2 平行张嘴](design/concepts/r2_pointed_beak_parallel_open_reference.jpg) 是历史外观基线；用户随后允许按反馈与审美重新设计，最新铰接嘴候选优先。旧 RC2 虽已有可编辑 CAD 源、STEP/STL、MuJoCo 模型、统一 SI 控制/训练接口和 Godot/Jolt 接收器，但[实际外形](design/exterior_review.md)严重偏离原图；旧几何和对应的静态试验不能作为新版放行证据。初版缩壳试验曾让嘴代替双脚撑地；[短鞋与前移膝轴候选](design/forward_knee_trade_study.md)找到无物体的双脚低位保持。[小机箱与前颈够地候选](design/r2_compact_front_reach_review.md)把视觉机箱收至 `280×190×180 mm`；随后[同版尖嘴修正](design/r2_pointed_bill_mechanism_gate.md)消除了原视觉上下喙壳的实体穿插，并按 R2 四连杆的前移轨迹张嘴。修正后的简化模型通过指定坐姿 50 g 等效力保持；它仍未复刻原图、夹住物体、单脚行走或完成可装配结构。[MicroDuck Max Pro 对照](design/microduck_max_pro_baseline.md)明确了可沿用的双足方法和 Goose 必须新增的腿脚机动、真实夹取与拖拽能力；18 主动轴已有独立第二阶段训练候选，第一阶段亦保留，旧 RC2 规格仍是 16 轴历史模型。UnitySim2Sim、BevySim2Sim 仍应从引擎无关的 SI 契约适配，尚未实现或验证。

| 历史 RC2 与过渡资料入口（18 轴请使用上方交接包） | 内容 |
|---|---|
| [RC2 历史规格](configs/robot_spec.json) | 机体、16 主动轴候选、尺寸、器件、动作边界与单位 |
| [交付完整性核查](evidence/delivery_integrity_rc2.json) | 59 个交接文件、本地链接、363 个 CAD 文件哈希及现行 BOM 数量核对；仅证明资料完整 |
| [CAD 清单](cad/exports/cad_manifest.json) / [整机 STEP](cad/exports/goose_rc2_assembly.step) | 打印件、材料/质量、各 STEP/STL；清单标示制造验收状态 |
| [RC2 候选 BOM](hardware/goose_rc2_bom.xlsx) / [CSV](hardware/goose_rc2_bom.csv) / [接线装配稿](hardware/goose_rc2_wiring_and_assembly.md) | 与 CAD/规格同步的工作清单；中国报价、线束、螺钉和额定核查未放行 |
| [MuJoCo 模型](models/full/robot.xml) / [跨引擎中立数据](models/full/rigid_transfer.json) | 自由根、双腿、头颈、嘴部闭环与质量惯量，运行接口为 SI |
| [工程基线](design/engineering_baseline.md) / [整机放行判定](design/release_readiness.md) / [早期验收快照](evidence/design_review_baseline.json) | 当前门槛、已通过证据及不能下单/交付的缺口；早期记录只保留溯源 |
| [本轮抽样装配](evidence/part_clearance_sampled_rc2.json) / [叼取](evidence/grasp_50g_rc2.json) / [短距牵引](evidence/drag_short_pull_rc2.json) / [Jolt v5 站立](evidence/godot_jolt_standing_v5_rc2.json) | 同一模型哈希下的分项证据，范围见各文件；[旧叼取姿态站立失败](evidence/godot_jolt_ground_grasp_stance_failure_rc2.json)保留 |
| [游戏动作观察](design/gameplay_sources_review.md) / [行为要求](design/behavior_requirements.md) | 叼、拖、停顿、回望、鹅叫；外部视频未实际取得画面时明确标注 |
| [实际外形核查](design/exterior_review.md) | 当前 CAD 渲染与游戏鹅的差距、下一版外饰和工程复查门槛 |
| [后掌候选与物理复核](design/stance_layout_review.md) | 脚型对照、条件质量与重心、MuJoCo 限力试验；外观及动力学均未放行 |
| [MicroDuck Max Pro 对照](design/microduck_max_pro_baseline.md) | 原机质量/脚型/关节/训练方法量测；Goose 6 轴腿与 18 主动轴新候选的验证条件 |
| [R2 加长尖嘴外观对照](images/r2_pointed_max_pro_three_quarter_candidate.png) / [张嘴细节](images/r2_pointed_max_pro_open_detail_candidate.png) | 仅供 B/R2 视觉比较，未通过外观或工程放行 |
| [R2 高颈比例侧视](images/r2_proportion_side_candidate.png) / [斜视](images/r2_proportion_three_quarter_candidate.png) / [平行张嘴](images/r2_proportion_open_beak_candidate.png) | 前一轮视觉候选；仍有头、颈、脚的大轮廓偏差，未通过外观验收 |
| [六轴腿与单脚证据](evidence/physics_stance_trial_r2_proportion_ankle_roll_single_support.json) / [踝部包装筛查](evidence/ankle_roll_package_screen_r2_proportion.json) | 双脚侧移有改善，三组单脚卸载均失败；第六轴未放行 |
| [较紧凑 R2 比例侧视](images/r2_ankle_clearance_side_candidate.png) / [斜视](images/r2_ankle_clearance_three_quarter_candidate.png) / [平行张嘴](images/r2_ankle_clearance_open_beak_candidate.png) | 上一轮外观候选；踝轴保留高度，仍未通过外观和制造验收 |
| [新比例低头与单脚试验](evidence/physics_stance_trial_r2_ankle_clearance_six_axis.json) / [踝电机本体盒](evidence/ankle_roll_package_screen_r2_ankle_clearance.json) | 站立 2 秒，低头与单脚失败；鞋壳、电机承力与线束仍未闭合 |
| [缩壳站立侧视](images/r2_compact_body_side_candidate.png) / [斜视](images/r2_compact_body_three_quarter_candidate.png) / [坐姿低头](images/r2_compact_body_seated_reach_side_candidate.png) | 最新视觉对照；缩壳和双腿折低只改善几何可达性，外观复刻仍未通过 |
| [缩壳视觉 STEP 与清单](cad/exports/goose_r2_compact_body_visual_candidate_manifest.json) / [坐姿几何](evidence/exterior_seated_reach_r2_compact_body_tip40.json) / [坐姿接触试验](evidence/physics_seated_reach_r2_compact_body_tip40.json) | 视觉实体不可直接制造；嘴端受地面反力，未验证坐姿夹物 |
| [短鞋／前移膝轴对照](design/forward_knee_trade_study.md) / [候选斜视](images/r2_forward_knee_three_quarter_candidate.png) / [坐姿侧视](images/r2_forward_knee_seated_reach_x280_side_candidate.png) | 保留缩壳与 R2 尖嘴；双脚承重的无物体坐姿通过 2 秒简化试验，50 g 仅过静力初筛；外观、真实夹取和步行未放行 |
| [紧凑轮廓审查](design/r2_compact_silhouette_review.md) / [闭嘴斜视](images/r2_compact_silhouette_v51_three_quarter_candidate.png) / [张嘴近景](images/r2_compact_silhouette_v51_open_beak_candidate.png) | 机箱 `310×190×180 mm` 视觉草模；一条坐姿几何路径和 50 g 等效力低位保持通过初筛，仍无夹持、步行或制造放行 |
| [小机箱与前颈够地审查](design/r2_compact_front_reach_review.md) / [站姿斜视](images/r2_compact_front_reach_v53_three_quarter_candidate.png) / [坐姿侧视](images/r2_compact_front_reach_v53_seated_side_candidate.png) | 视觉机箱前后缩至 `280 mm`；15 点坐姿工作区几何初筛通过 13 点，嘴尖高 15／25 mm 的 50 g 外力代理保持通过，10 mm 动态碰地失败；外观和制造仍未放行 |
| [尖嘴实体与 R2 机构一致性](design/r2_pointed_bill_mechanism_gate.md) / [闭嘴近景](images/r2_nonintersecting_bill_v55_closed_detail_candidate.png) / [平行张嘴近景](images/r2_nonintersecting_bill_v55_open_detail_candidate.png) | 消除原视觉喙壳约 `9.13 cm³` 穿插，九点理想运动中两片橙色壳零穿插；同版低位外力保持仅为无物体必要初筛。旧 RC2 嘴机构型号、轴距和传动比均不符合指定 R2，不能直接换皮 |
| [小机身／高髋／前颈坐姿拾取权衡](design/seated_pickup_layout_trade.md) / [几何记录](evidence/seated_pickup_layout_trade_v55.json) | 再缩机箱没有增加已筛可达点；髋上移 25 mm 与现翼门外形冲突，更宽双脚增加单脚换重心距离；15 mm 嘴尖目标在张嘴后可能撞地，均未制造或夹取放行 |
| [内藏嘴部电机必要包络](design/r2_pointed_bill_mechanism_gate.md#内藏电机与传动带的必要包络初筛) / [几何记录](evidence/r2_internal_belt_gross_package_v61.json) | XL330 和假定 2:1 带路可在头壳／嘴根粗包络中放下；侧颊、细长立耳仍不符合指定外观，未放行制造和采购 |
| [头壳包覆 v69](design/r2_pointed_bill_mechanism_gate.md) / [闭嘴斜视](images/r2_head_wrap_v69_closed_three_quarter_candidate.png) / [张嘴近景](images/r2_head_wrap_v69_open_detail_candidate.png) / [实体核查](evidence/r2_head_wrap_gross_package_v69.json) | 收回外突大侧颊；九点理想张合的头壳／尖嘴／立耳无实体互穿。仍未复刻指定外观，也不是可装配、可采购或已验证夹拖的结构 |
| [头嘴与低鞋门 v72](design/r2_pointed_bill_mechanism_gate.md) / [闭嘴斜视](images/r2_head_wrap_v72_closed_three_quarter_candidate.png) / [平行张嘴](images/r2_head_wrap_v72_open_detail_candidate.png) / [实体核查](evidence/r2_head_wrap_gross_package_v72.json) | 修正相机面板与固定上喙干涉并保留隐藏电机／带路的假设包络；头罩更圆、翼门和鞋底更薄。仍未通过外观、装配、夹拖或采购验收 |
| [薄下喙 v73](design/r2_pointed_bill_mechanism_gate.md) / [闭嘴斜视](images/r2_slim_bill_v73_closed_three_quarter_candidate.png) / [张嘴近景](images/r2_slim_bill_v73_open_detail_candidate.png) / [坐姿侧视](images/r2_slim_bill_v73_sit90_x300_z25_head60_open_side_candidate.png) | 保留尖嘴、平行张嘴与头内藏驱动方向；一处下蹲视觉姿态通过有限几何净空筛查。仍未复刻外观，也未证实真实抓拖、步行或可打印装配 |
| [上颈默认折姿 v79](design/exterior_review.md) / [侧视](images/r2_neck_rest15_v79_closed_side_candidate.png) / [斜视](images/r2_neck_rest15_v79_closed_three_quarter_candidate.png) | 上颈向后折 15°，头嘴保持水平；同一低位九目标仍过 8/9，但拾取终点多需 15° 头颈关节转角。仅作外观对照，不替换 v73，也未通过外观或工程验收 |
| [贴合曲面的翼形门 v81](design/exterior_review.md) / [侧视](images/r2_conformal_wing_v81_closed_side_candidate.png) / [斜视](images/r2_conformal_wing_v81_closed_three_quarter_candidate.png) | 原机身轮廓上切分贴面门片，保留简约翼门方向；低位九目标仍过 8/9。门片缺薄壳、铰链和锁止，仅为局部外观备选，不能打印装配；整机仍按未通过外观的 v73 工作候选继续 |
| [低头罩与长颈比例 v92](design/r2_whole_proportions_review.md) / [闭嘴斜视](images/r2_whole_proportions_v92_closed_three_quarter_candidate.png) / [张嘴近景](images/r2_whole_proportions_v92_open_detail_candidate.png) / [坐姿侧视](images/r2_whole_proportions_v92_sit90_open_side_candidate.png) | 同版低位九目标几何初筛 9/9、嘴部粗包络通过；条件重心升高约 5.62 mm，所需头颈角度、真实夹拖与整机外观均未验收。只作为比例比较，不能打印装配或采购 |
| [连续头罩与内收四杆 v95](design/r2_whole_proportions_review.md#v95-嘴根与连续头罩的局部试样) / [闭嘴整机](images/r2_swept_head_v95_closed_three_quarter_candidate.png) / [张嘴整机](images/r2_swept_head_v95_open_three_quarter_candidate.png) | 去掉 v92 的矩形头罩缺口；开闭两端所列头罩／连杆实体不互穿，但中途只做有限采样；原头罩网格的退化面已另存清理版，仍非可装配打印件。外观与同版物理未通过 |
| [居中脚掌 v96](design/r2_whole_proportions_review.md#v96-脚掌居中站姿与低位任务一起看) / [站姿侧视](images/r2_centered_foot_v96_closed_side_candidate.png) / [坐姿张嘴](images/r2_centered_foot_v96_sit90_open_side_candidate.png) | 只把两鞋后移 `20 mm`；条件站姿余量改善，低位叼取前方余量变小，髋部负载仍未过粗筛。保留比较，不定版或下单 |
| [v95 整机对齐闸门](evidence/r2_swept_head_v95_system_alignment.json) / [放行总览](design/release_readiness.md) | 最新视觉 R2 与 RC2 模型在嘴机构轴距、电机、传动比和机身包络上不一致；旧模型试验不得用于新版放行 |
| [v73 与运行模型一致性闸门](evidence/r2_slim_bill_v73_model_alignment.json) | 明确检出当前 RC2 的 `18 mm/XC330/1:1/16 轴` 与 v73 视觉 R2 的 `14 mm/XL330/暂定 2:1` 不一致；旧模型与 CAD 不能作为 v73 的 Sai_Lab、采购或制造交付 |
| [结构/执行器核查](design/servo_mount_geometry_review.md) / [电源事实](design/power_bus_facts.md) | 原厂几何、电气限制与来源 |
| [跨引擎验收清单](design/backend_conformance_facts.md) | Godot 局部单位转换；Unity/Bevy 后续应逐项证实的适配条件 |
| [双足控制审查](design/locomotion_review.md) | 旧训练失败根因、现行站姿控制和独立步态判据；行走仍未通过 |
| [打印机与材料](design/printer_selection.md) / [采购包装核查](design/procurement_packaging_facts.md) | 当前建议 X2D 普通打印配置、P2S 为 PETG 经济选项；中国现价与供货待核 |
| [鹅叫素材](models/full/audio/honk.wav) / [音频清单](models/full/audio/audio_manifest.json) | 自制声音，用于动作表达；扬声器音量须实物验收 |

## 保留的交接包与设计历程

- [conversation_handoff.md](design/conversation_handoff.md) 和[交接时的机器人 README](source/robot_readme_handoff.md)记录原交接时的目标和决策顺序；其 18 轴/XL330 与“尚无 CAD”等表述是**当时状态**，不能覆盖此后的 16 轴/XC330 工程候选。
- [嘴部 R2 原说明](design/beak_r2.md)、[机构图复核](design/kinematic_review.md)、[整体旧结构](design/walker_structure.md) 与 [原采购工作簿](hardware/walker_r2_bom.xlsx) 都保留原始设计线索；旧工作簿不是当前订货单。
- [原嘴部采购 CSV](hardware/beak_r2_purchase.csv)、[原打印件 CSV](hardware/beak_r2_print_parts.csv)、[图片资料库](design/concepts/index.html) 和 [完整导入索引](source/asset_index.md) 可查旧版与用户补图。包内图片、文档、表格保留；仅原包 README 修复两处本地相对链接。
- 当前外形参考 [用户的翼形检修门批注图](design/concepts/wing_access_reference.png)；门手动开合、抽象曲面，不画写实羽毛、不增加翅膀电机。

构建入口位于仓库的 `scripts/cad/build_goose_cad.py`、`scripts/models/build_goose.py`、`scripts/models/export_goose_transfer.py`、`scripts/training/train_goose_rsl.py`。模型和加工验收结果必须记录所用规格与文件哈希，不能把早期失败试验的输出覆盖成成功。
