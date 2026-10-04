# 身体曲壳自交修复检查点

旧六片身体壳面虽然能通过拓扑有效、正体积与封闭网格检查，原生自交检查仍拒绝它们。此前门片的零交集读数与材料查询矛盾，不能当作配合通过。这里重建独立的六片裸壳，保留旧装配、旧参数和003运行包；**尚未替换当前460对象装配，也不是完整检修门或制造放行。**

## 修复范围

身体截面输入、名义2.4mm壁厚与轴位输入未改。旧坐标映射把门片经向宽度绑定到作者网格行，却同时让物理X随纬向变化，会带来后缘折返风险；仅平滑插值的尝试仍未解决原生自交拒绝。新映射把纬向特征绑定到物理X，用单调X映射生成身体曲面。直接在同一外、内原生曲面上裁剪固定壳与门片，不把裁剪后的采样点重新拟合成另一配合曲面。

曲面生成方式改变了下部出口和门沿几何，**不能继承旧装配、孔位、质量或动作资格**。原生自交通过只关闭该项输入缺陷，名义壁厚没有因此获得全域最小厚度证明。

| 资料 | 内容 |
|---|---|
| [结构输入](../configs/torso_service_skin.json) | UV裁剪、名义配合间隙、裸门片几何转轴与扫掠范围 |
| [CAD/STEP/STL清单](../cad/exports/torso_service_skin/manifest.json) | 六片原生、交换、全quad源、质量/完整惯量与哈希 |
| [显示源](../cad/source/torso_service_skin/quad_scene.json) | 六片CAD派生的封闭四边面；不含整机装配 |
| [原生配合与旋转距离界](../evidence/torso_service_skin_fit.json) | 原始拒绝、阳性对照、四组关闭配合和限定扫掠证明 |
| [原失败复现](../evidence/wing_door_geometry_rejection.json) | 4.730269mm³关闭位交集及查询矛盾，追加原生自交拒绝 |
| [源绑定检查图](../images/torso_service_skin_geometry.png) | 右侧三片实际quad源；不是最终外观图 |

六片均通过原生拓扑/小边/自交、STEP回读、封闭绕序与STL体积误差门槛。STL使用经过闭合/绕序/体积回读检查的binary32格式；精确编辑源继续使用BREP/STEP，quad源使用双精度坐标。没有靠修网格或扩大布尔容差获得通过。

## 当前证据

| 检查 | 结果与范围 |
|---|---|
| 旧六片原生自交 | 全部拒绝；与其拓扑有效标记分别保存 |
| 新六片原生及交换 | 六个源与STEP回读均通过独立自交检查；quad全部四边面并闭合；STL回读闭合且体积相对误差≤0.005 |
| 关闭位门片↔后固定壳 | 左、右各0交集；各最小距离0.675870769mm |
| 关闭位门片↔前固定壳 | 左、右各0交集；各最小距离0.879621395mm |
| Common阳性对照 | 两侧门片各与自身求交，恢复其原生体积，而非仅接受零值 |
| 裸壳几何旋转 | 左右各两组0–90°单轴旋转的距离下界通过，最低要求0.01mm；共128次中点距离查询 |
| 质量 | 六片裸壳按PETG1270kg/m³计算合计418.007438g；每片门31.796174g。屋顶安装凸台、真实铰链和锁止件尚未计入 |

转轴候选右侧Y−105/Z367mm，绕X负向旋转；左侧镜像并反向旋转。旋转检查对每个区间在中点测距，再扣除`2R sin(Δθ/4)`的全区间位移上界；R使用原生保守包围范围，距离对刚体位移的1-Lipschitz性质给出下界。区间不能满足下界则继续二分，达到预设最小区间仍失败，或耗尽每对128次查询预算，均拒绝。结果覆盖的只有**裸门片与同侧裸前、后壳**，没有实际铰链、内部零件或多轴整机运动。

13项针对性测试覆盖原生查询矛盾、真实旧壳自交拒绝、修复源、平面裁剪控制、封闭quad、旋转界的阳性/真实障碍阴性对照，以及现有相邻碰撞过滤。测试总数不替代上述限定范围。

## 下一整机退出条件

1. 保留本曲面基础，装回屋顶固定支承及实际颈部圆形开口，检查全域厚度、孔边与接缝支承。
2. 把几何转轴实现为有承力路径、轴向保持和实际五金的手动铰链，补可靠关闭保持；用真实零件复查闭合、开合与工具/线束路径。
3. 新零件与真实BOM合入独立整机装配，重建逐体质量、COM、完整惯量及同源静力，再给同版外观/动力学版本。

现有11凸包、9对相邻例外/46对保留和003运行包没有变化。几何修复不靠游戏碰撞过滤绕过制造干涉；头与躯干等非相邻碰撞继续保留。供电/驱动额定、完整任务与各后端验收仍是独立未完成项。

## 复现

需要build123d/OCP、NumPy、SciPy、trimesh；画图另需Matplotlib。本轮环境Python3.12.14、build123d0.11.1、OCP7.9.3.1。

```bash
env OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/cad/build_goose_torso_service_skin.py
env OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/diagnostics/check_goose_torso_service_skin.py
env OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/models/render_goose_torso_service_skin.py
env OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python -m pytest tests/test_native_cad_query_sanity.py tests/test_native_cad_skin_integrity.py tests/test_goose_collision_filters.py -q
```

原生检查使用已安装OCCT的`BRepAlgoAPI_Check`并开启小边与自交检查；[官方接口说明](https://www.occt3d.com/dev/doc/refman/html/class_b_rep_algo_a_p_i___check.html)与实际环境绑定的报告分别保留。所有通过项以该候选源及其报告哈希为准。
