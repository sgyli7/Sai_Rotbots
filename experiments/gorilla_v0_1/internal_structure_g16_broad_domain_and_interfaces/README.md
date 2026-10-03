# Gorilla G16：宽厚设计域、完整模块与真实连接入口

G16 保存两套实际布局、合法主笼架 CAD/native、源尺寸分体散热候选与真实肩接口。**首检查点未达标；两套布局、安装、物理和审美均未放行。** 壮硕身体用于宽厚三维承力与完整机电空间共同设计，当前没有真实骨架拓扑减重或吨级能力结论。

| 实际资料 | 入口与范围 |
|---|---|
| 完整布局 A / B | [A 源](body_partition/a/scene.json.gz)、[B 源](body_partition/b/scene.json.gz)；2522 / 2529件，SHA a8a09ca0 / 99beca60 |
| 同版实际图 | [B 完整全身四视](body_partition/b/native_whole_four_view.png)、[B 安装四视](body_partition/b/native_installation_four_view.png)、[实际截面](body_partition/b/actual_sections.png)；工程诊断图，不是批准的新原画 |
| 合法笼架与映射 | [编辑参数/producer](body_partition/a/build_partition.py.txt)、[主 CAD](body_partition/a/load_cage_primary.brep.gz)、[SI STEP](body_partition/a/load_cage_si.step.gz)、[CAD/native映射](body_partition/a/frame_CAD_native_mapping.json)；同参数曲线64面近似差单列 |
| 实际布局拒绝 | [A 审计](body_partition/a/audit_summary.json)、[B 审计](body_partition/b/audit_summary.json)、[作者范围说明](body_partition/README.md) |
| 完整热模块与工作范围 | [主参数](thermal_scope/compact_module_scope.json)、[一手出处/公式/范围](thermal_scope/README.md)；4 ES0707、1 ES0714、6风机、泵/保护/degas/控制/维修；B 尚未安装升级的低温双 EWP150 |
| 真实接口与串联责任 | [17接口](interface_domain/interface_contract.json.gz)、[原生接口四视](interface_domain/native_interface_four_view.png)、[全链替换条件](interface_domain/serial_replacement_contract.json)、[抽装服务](interface_domain/motion_tool_void_contract.json.gz) |
| 独立复核 | [根复核说明](root_review/README.md)、[CAD/native/SI与完整张量](root_review/independent_native_cad.json)、[实际材料/接面](root_review/independent_material_interfaces.json)、[热算](root_review/independent_thermal_scope.json)、[源载荷积分](root_review/independent_interface_resultants.json) |
| 冻结与恢复 | [精确文件映射](snapshot_manifest.json)、[空目录恢复工具](restore_snapshot.py.txt)；只恢复精选字节，不冒称全生成/仿真重放 |

宽截面主笼架 CAD 有效且为1实体；原生 signed 材料同样有效。假定均匀钢7850kg/m³，主笼架 native62.935418kg，**另有两独立肩锚各native15.127006kg，总计93.189429kg**。旧锚声明CAD metadata15.131277kg/侧与现polygon积分不是同一曲线表达，不能混加口述93.198；旧G15锚并入frame的0-additive别名不适用于新源。这一小组件统计不是整机质量、已连成的刚体或承载认证。

B仍有2处完整 ES0707 thermal包络与肩参考组各31.8175cm³交；changed×all诊断中45处finite材料交包括电池/水罐与腰。参考stock相交与实际finite材料相交分别记录；不可把958个混合分类诊断全称真实硬件穿插，也不可因为同owner忽略实体排他。另有未合格装配、布路、模块支承及姿态空间。计算封口域338.588L与条件剩余246.424L不是可用内腔，开面插值/计算cap仍明确未知。

肩锚与新笼架仅X=.115共面接触、没有已建的抗竖向剪力连接；normal-only反力秩3不具备Fz承载。17实际接口、PCD/座面和六维等效载荷只提供重建输入。旧pitch/roll四载体26.596829kg承担完整下游串联链，替换尚未成立，减重credit0。G15B载荷不自动移植到新G16A/B。工具/拆装采样保持已拆件停车，仍有实际材料干涉。第一版接口producer/native/render精确字节未留存，该缺口明确记录，采用最新绑定源和图，不补造历史。

S1历史ES曲线为71.1°C EGW条件；冷回路的H、压降、NPSH和安装未关闭。双EWP150串联只是完整物理候选，不能只相加压头就标黄。六风机与三泵设计功耗一次替换，A30min名义能量需7.475–7.757kWh，480芯源最低7.44kWh有缺口；这是工况/SOC假设计算，不是续航结果。新水12.084–17.550L、油12.759–21.654L是旧线路长敏感性，实际新管网和分体COM仍待重算。50°C安装面QTL/QTR有条件降额入口，真实TIM/热点/工作电流还未验证。S2自制UA目标仍红，不能把采购缺口当物理已闭合。

根复核130项源/几何/单位/张量、12项材料接面、124项热算与12项载荷/秩共278项有限检查通过。初次root把patch原点力矩误比到world-zero，错误比较producer/result保存在before_origin_scope；按源显式patch质心复核后9个载荷积分一致，没有发现作者载荷公式错误。数学等效traction不等于真实bolt/轴承接触。

G17已经并行推进：真实连续宽厚笼架/锚连接，完整pitch→roll→yaw过渡及同版冷却工作点。首个实际源09:55UTC、硬停10:20、root10:20–10:40集成。外观仍以AA3为权威；用户负责的「Gorilla 设计」腿脚新稿未到，不并行外脚改稿。后续稳定SI、双足双手及自主复杂Bevy原生接触任务持续；本轮无GPU/PPO、默认模型修改或主干合并。

精选快照排除依赖环境、日志、缓存和本地下载出版物。完整publication来源/SHA及提取的参数数组保留；需原出版物的生成运行不在本次字节恢复保证内。A/B各次body producer均保存，首次接口字节缺口不能由恢复工具补足。
