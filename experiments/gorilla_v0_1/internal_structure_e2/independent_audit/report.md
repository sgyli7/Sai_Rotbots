# E2 5a9a 原候选独立审查 receipt

**候选不完整：右髋 yaw 六件实际模块漏镜像，缺失质量范围 28.42 / 29.75 / 32.35 kg。** 缺件为 gear、motor、brake、encoder、controller、wire_coolant_connector；旧右包已经移除，但静力仍借用该轴 CSG65 容量。原因是镜像条件只匹配 left_ body 或 e2_left_ name，而 e2_ds_left_hip_yaw 源件 parent 为 pelvis。需建立真实右侧六件，再实际集成、COM、LP 与渲染重算；不能算术补重后宣称完成。

本 receipt 绑定 integrated scene `5a9aeca66ade1defcf34d0e0bd2e14a7928bfca1741753b096f86b977f5b66d4`；未修改任何冻结源。1579 parts / 1105 rows 的**已列库存**质量为 1715.894628644 / 1891.081576192 / 2173.479532015 kg。独立三角面四面体积分与142实际钢材 manifold union 复算闭合：最大质量残差 1.42e−14 kg，COM误差 1.30e−12 m，代理惯量误差 1.88e−12 kg m²。代理 tensor 不构成转子/齿轮移动分体的真实 SI 资格。

四旧 unbored 袖均移除，四新冷却 case 都存在；只有三个完整新电包的18个源子件存在，右侧六件缺失。五 hydraulic 转换已去旧gear/motor，20电子/制动/编码/连接模块保留且只计一次，名义15.25kg；8handle aliases 不单独计重。111原甲对象和4主pad顶点/三角面完全同源；77原显示代理未逐件计重，仍需制造物料至真实模块的alias闭合。

四 case 与 continuous gear bridge 有真实正交体积搭接，分别2.394734、3.198378、2.394890、2.394889 cm³，7850 kg/m³下合计0.081505700kg。case各名义质量由实际开孔钢净体积×7850，范围0.9/1/1.2倍。连接构造名义搭接2mm，同材同parent；仅明确焊接整体假设可对该材料做union。若为独立装配件，保持库存与干涉，不删质量冒充解决冲突。

油库存30L只计一次，质量24.6/25.5/26.4kg；各段冷却水和一次EMRAX内部液体未知预留共12.457176/13.106456/13.980556kg。OEM泵阀滤内部油仍未知，应在单库存内分配。未按油水相交去重。pack/BMS维持已列模块范围，不能由包装代理确认实际电压、绝缘、回馈或内部cell质量分布。

来源存在metadata-only冻结先后例外，精确旧/现hash及referrer保留在JSON，不改冻结链；四motor case数值/几何与system嵌入接口相同。独立LP核对48已有成功证书，未发现竖直平衡、广义轴矩或液压正负容量符号错误。初读圆环横剪系数问题已由root修正，当前源码确认含修正因子；历史初读hash未保存，不把问题标成现版未修。液压eye力和轴承反力尚未落具体截面，child exterior-wrench只作gross section sensitivity，不是实际shaft stress或上下界。

复算入口：`.venv/bin/python .scratch/gorilla_internal_e2_audit/recompute_mass_neutral.py`。只读中立材料/列重审查，不替代整机动态、热、连接强度、运动软管或全姿态碰撞资格。

收尾来源补充：两条metadata-only记录分别为motor_cooling_interfaces 5b0d→7a09当前冻结引用先后不一致，以及structure_scene 373a88→baf16的历史metadata refresh。后者不是第二条当前input mismatch；现native指纹独立匹配记录的刷新前后共同指纹2d1ad3a7…，旧全字节未保留。4custom cell+case pack范围合计76/92/112kg，另4external HV BMS/fuse/service范围1.8/3.2/5.6kg；源自身明确cell+case不含外置服务row，故不作为重复删重。
