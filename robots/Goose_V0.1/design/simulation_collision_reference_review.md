# 任务碰撞参考核对

本记录区分实际运行形状、作者输入和未验证项；不把“29”或参考产品的数量当成通用合格标准。

MicroDuck 的冻结 game015 包核对结果见[原始计数证据](../evidence/microduck_game_collision_baseline_v1.json)：整机 11 个碰撞叶、15 个物理刚体、14 个执行器，源端凸图支持顶点共 23,041。行走接触配置只保留 5 个叶，不能替代整机任务包。嘴部三块几何固定在同一刚体，不能当作 Goose 独立强夹持器的功能证明。配置选择和接触几何来自[固定版本的上游模型](https://github.com/pollen-robotics/microduck_rl/blob/5946fd9cdbc58956424420153e51975af3b30d77/src/mjlab_microduck/robot/microduck/robot_allcollisions.xml)。

本地冻结的 G1 Arena/Homie 转换数据含 53 个刚体记录、52 个碰撞记录。原始 `g1_physics.json` 的 SHA256 为 `571cb2558c137dccafa2d18adda5021f0885e0f10abf6d61edd62f1c6e8f13bd`；参考查询来自 G1 任务的实际转换源码，记录不是新的目标运行读回。其 38 个 convexHull 输入、8 个脚角球、4 个胶囊和 2 个解析盒按连杆与接触角色分配；固定传感器等仍保留质量惯量，未逐件生成碰撞。脚角球表达所选支撑位置，不能用其半径声称全脚表面达到同等精度。

G1 目标构造源码按记录创建一对一 single-child compound，预期 52 个叶；本轮没有重新读取 G1 的目标烹制支持几何，所以不声称目标数值精度等同源 PhysX。冻结任务配置[明确关闭 articulation 自碰](https://github.com/isaac-sim/IsaacLab-Arena/blob/7d75c95934c51a0318c957a8831e862ca43c53b5/isaaclab_arena/embodiments/g1/g1.py)，不能把这一过滤直接搬给需要颈、嘴、腿互相避让的 Goose。参考的手部材料和训练变体也没有升级为 Goose 的通过证据。

Goose 按躯干、两段颈、头／上喙、下喙和左右大腿／小腿／鞋分配 11 个角色。内部安装细件继续由 CAD 负责，完整质量和惯量独立保留。夹持面、实际脚底支撑和外部接触分别检查；形状少、零位无碰撞或加载成功都不等于任务通过。

当前[同版代理、接触映射和实测](task_proxy_11_v1.md)已读取目标实际 11 个叶及 4,788 个支持点，并完成限定 M0 整机积分。行走、起身、复杂地面和真实物体夹拖须用同版策略继续验收。
