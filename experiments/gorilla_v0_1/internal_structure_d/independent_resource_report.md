# Gorilla canonical D 资源身份审计

绑定master：2933318e60dfe786f5cae61d88682519589f1eb5f8a23c999e6f7c6566cdd280。只读一次稳定快照，未开Blender、未重渲、未修改受控文件。

资源检查通过=False；unknown=[]。

源 1482 件，其中新增 1091、保留 391；原111甲壳逐值保留=True，保留391row完整逐值一致=True。
原生WT/绕向/正体积/有限坐标失败=[]。
render retained before/after相等=True；所有manifest输入SHA一致=True；所有输出SHA一致=True。
图参数=[800, 800] / 64samples / 6图。
trimesh实际载入GLB：geometry=1482，mesh node=1482，名字一致=True；GLB失败=['right_blue_elbow_yoke', 'right_vent_fastener_3', 'right_vent_fastener_2', 'right_vent_fastener_1', 'right_vent_fastener_0', 'right_radiator_louver_10', 'right_radiator_louver_09', 'right_radiator_louver_08', 'right_radiator_louver_07', 'right_radiator_louver_06', 'right_radiator_louver_05', 'right_radiator_louver_04', 'right_radiator_louver_03', 'right_radiator_louver_02', 'right_radiator_louver_01', 'right_radiator_louver_00', 'left_blue_elbow_yoke', 'left_vent_fastener_3', 'left_vent_fastener_2', 'left_vent_fastener_1', 'left_vent_fastener_0', 'left_radiator_louver_10', 'left_radiator_louver_09', 'left_radiator_louver_08', 'left_radiator_louver_07', 'left_radiator_louver_06', 'left_radiator_louver_05', 'left_radiator_louver_04', 'left_radiator_louver_03', 'left_radiator_louver_02', 'left_radiator_louver_01', 'left_radiator_louver_00', 'rear_door_screw_3', 'rear_door_screw_2', 'rear_door_screw_1', 'rear_door_screw_0', 'rear_door_upper_tab', 'rear_service_latch', 'pelvis_front_black_latch', 'central_indicator_lit_strip', 'central_indicator_gold_frame', 'central_indicator_recess', 'crown_fastener_3', 'crown_fastener_2', 'crown_fastener_1', 'crown_fastener_0']。

GLB法线/材质缝会复制同位置顶点，raw attribute topology不等于材料断裂。本检查只将完全相同位置的顶点合并，不挪动坐标；随后检查三角WT、绕向、正体积，并将标准Y-up转换回源SI Z-up。坐标匹配阈值2µm，每个实际三角须是原polygon的合法顶点子集且总三角数一致。

**资源通过不等于物理通过。D仍是拒绝候选，接口干涉、真实部件、载荷、材料、驱动与连接能力没有因此关闭，AA3改形必需性没有据此证明。**

新增1091件对raw control严格匹配=True；原391保留显示GLB对冻结C15实际GLB逐mesh匹配=True。
严格所有1482 GLB→raw control判据仍通过=False，46个原件已有显示倒角与raw control不一致，完整保留为严格失败，不静默放宽。
另列 source-bound display身份判据通过=True（新增必须匹配raw control，原件必须匹配冻结C15显示网格，全部GLB必须闭合且源row/材料before-after/所有SHA不变）。
