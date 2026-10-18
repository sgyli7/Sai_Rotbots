# V0.2 硬件续办入口

本轮按用户最新要求，优先交付独立训练物理数据包。冻结基准为 `models/physics_v0_2_20261018_02/` 内的质量、完整惯量、轴系、外部接触及执行器合同；工程设计和实测不能热覆盖该包。后续必须改变这些参数时，另发物理版本，保留旧版。

1. **整机工程来源。** 当前实际工程整机是 whole05，1824 个原生登记件，1971 个显示项，源身份 `06465d8112d0b5c818692089c74f5dc8b5cc02cef42f49b1a7fbf2644af3b860`。本地装配入口为 `artifacts/goose_v0_2/physics_freeze_20261018_01/integration_release/whole_core_review_05/integration.json`；同目录的 `integrated_native.brep` 是本地工程检查点，不是训练加载依赖。可携带完整1824件原生工程检查点已保存在 `cad/source/engineering_checkpoint_20261018/whole05_native.brep.gz`，配套 `assembly_index.json` 与 `checkpoint_manifest.json` 记录同一来源；无需运行时加载。这不是制造放行。本版本不上传全部失败日志树。原工程 17.365577243 kg，加 E 明确固定分配的 17.411273005 kg 是未发布的baseline01；用户随后要求先做有界减重，最终质量以独立02合同和实际获准材料补丁为准，不能热改01冒充旧版。详细逐项来源保存在包内质量账。
2. **头部。** 训练物理沿用 whole05 的 head10 质量与外形，保持真实 CRBT205A、独立承载 frame/fork 和原 18 轴。head17 双径向盖的有限装入、防脱和工具位置检查有进展，但完整伺服装入顺序被真实碰撞拒绝，**未采用**。下一整套替代是把必要的盖板紧固 lug/螺钉轴放到真实 OEM 外侧可直插、可操作的区域，先验证“伺服先装→盖径向入→螺钉/工具→输出 horn→外罩”及逆序，再细化。不得切 OEM 或恢复未知塑壳承担主拉弯的旧路线。交接 `integration_release/radial_head_phase_handoff_05_10_01.json`，身份 `5f79d90402403c98dcb593d5038983fa9a83e73d6477b2f2bcb663ef683a8c68`。
3. **脚与外观。** 冻结正确旧六件机械回退及原脚底接触。A 的新八件原始健康几何尚未通过工作腔、金属和活动配合门，不能作为新脚采用。续办入口 `form_mechanics/foot_physics_priority_checkpoint_01/foot_physics_priority_checkpoint.json`，身份 `859e0daf4f7fe9d3f498934ca2c95b16e38432a001ef94a8eb467a47d956aa72`，含正确旧六件的实际文件哈希。与 TangPa 的整体外形一致性仍未放行。
4. **电气固定分配。** E 的唯一预算合同为 `thermal_manufacturing/simulation_mass_contract_0519_01/E_simulation_mass_contract.json`，身份 `7200b5f4dbbf4739854bd57b5a7dc083ea1cd024b33c04daa27a2c0bc4dec1a5`。对 whole05 净增 45.695761845 g，全属躯干：未消费的轻件预算 16.200308549 g、NC 内凹单元 14 g、access/cup 相对原 cap04 净增 15.495453296 g。Port/T1 已计入的 8.799691451 g 不再加入；IMU14 g、CAN_A30 g、风扇33.5 g及全324 mm原厂线、原USB/FFC质量保留一次。NC cup/receiver 固定、IMU/CAN+X10联合载体、300 mm FFC储线/应力释放、六尾线与 feeds、T1冷风安装仍未完成。未来构件须消费现有固定分配，不能再追加未说明的质量。
5. **结构。** 当前九条承力链交接 `structural_topology/actual_nine_chain_stage_handoff_04_10_01/actual_nine_chain_structural_handoff.json`，身份 `037b91f8aea94011a4231949bbbab78cd33b2437178d8577c21f33f71b3ef87c`。正常大腿主件联合筛查的进展不等于全部峰值、连接、实际 loaded gap 或整头 frame 筛查已完成。保留 C45/铝件实际失败与边界，不继承修改前的强度绿灯。CRBT 新增名义滚阻 0.03 Nm 与原 0.006 Nm 合计 0.036 Nm，只计一次；默认连续 0.14 Nm、峰值设计 0.18 Nm不再重复扣除。
6. **减重与制造。** 原 BESO/拓扑减重存在真实拒绝，不称已优化成功。材料供货保证、机加工路径、公差/有效牙长、完整采购 BOM、扭矩/预紧、线束与拆检、整机散热、疲劳、实际称重/重心/惯量、温升和实体装配验收继续待办。训练的设计分配不替代实测。
7. **尾部显示。** 旧外凸红按钮、座与孔已从真实原生模型退休，连续母形有独立几何证据；普通尾盖三角化/整机显示仍有缺面，属于明确的显示交付缺陷。后续从真实 native/STEP 正常重导，不能用截图补洞、遮挡或换色伪造完整外壳，也不能误把显示缺面当真实新开口。
8. **训练边界。** 本项目交付物理和接触数据、固定执行器能力及参考 200 Hz/50 Hz适配器。Sai Lab 的任务、奖励、网络、策略和训练仓库由其自行接入；本轮不直接替换它正在使用的模型。任务学会、实体制造完工与本数据包可加载是不同结论。

上述 artifact 路径均相对于工程仓库根，表示本地可续办来源。迁移主机时，优先保留 source tuple 与工程检查点；训练包本身的资产均为相对路径，运行不依赖这些本地工程文件。

9. **本次有界材料恢复。** 最终物理02质量 16.970203928834 kg；对未发布baseline01净减441.069076 g。唯一六件补丁 `structural_topology/hip_7075_material_adoption_01/hip_carrier_light_material_patch.json`，身份 `7902e3d086ad8aa82364bbced1fd9d718080bb6bc7272e7c9347a482eba0d1e0`，全文与旧新完整MCI保存在运行包内。双髋载体同几何7075-T651的有限峰筛查130.248/130.984 MPa，正常压盖与同SKU M3x6外移0.6 mm同步。外来gimbal相对变形、热配合、全ROM与实体装配仍待核。桥件原424 MPa高于本次铝材允许值、AP原钢峰408 MPa亦拒绝直接换铝，均保留原钢；没有新增Ti或虚称BESO成功。
