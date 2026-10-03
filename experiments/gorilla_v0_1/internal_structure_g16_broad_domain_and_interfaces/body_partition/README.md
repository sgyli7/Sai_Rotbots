# G16 宽厚身体功能分区封存

两套真实宏观候选均未采用；本轮停止几何。A/B 原 producer、native、CAD 和诊断均独立保存，不修改 G15 或受控模型。

| 同版结果 | A | B |
|---|---:|---:|
| 实际 native 件数 | 2522 | 2529 |
| 主要完整功能 profile 相交 | 13 | 2 |
| changed×all 正体积（混合有限/参考/流体） | 1297 | 958 |
| 其中有限材料×有限材料 | 74 | 45 |
| 新 cage 净质量，假设钢7850kg/m³ | 62.9354kg | 62.9354kg |

B 保留完整480芯、四套电池辅助、18套21件方向阀、原18保持组、两完整液压输入组及G13A肩完整组。S1为4×ES0707完整254×212×80mm芯+1×ES0714完整457×212×80mm芯，各176mm完整硬件厚度及6个172×51mm风机、非零plenum/guard/seal/连接器；不是缩4320继承能力。泵/脱气/控制/filter/relief/隔离/支座已画，但最新低回路双EWP150串联140×190×270mm建议**未画入**，B仍单EWP80低回路，因此不称S1完整装配或流量通过。

B两处ES0707完整profile×肩各31.8175cm³；45处finite–finite主要为下电池/水罐与腰传动，详细ID/体积见b/final_receipt.json。958不是958个已知金属硬碰撞；完整OEM参考、有限自有材料、逻辑液体的范围在changed_all_collision_receipt.json分开。主要块测试未覆盖单独aux/tanks/HV/compute，不能把2pair称完整功能非交叠。

计算域338.588L来自实际C15曲面采样与显式工程封口，共238条射线、120条缺面插值。封口不是真甲皮或认证可用腔；四视、真实切面和域差均保留。B按现功能profile排除后的条件剩余246.424L，仅是设计域探针；旧carrier单独作为条件挑战，没有永久锁成非设计材料，service仅拆壳后候选，不全部扣作永久空域。它仍不能证明内部空间可用或AA3全局不可行。

主cage是200×80mm/5mm壁闭口宽梁与有限节点。OCC primary合法1solid，SI STEP回读体积相对差8.0e−15；native64段圆弧近似与OCC体积差−0.02609%，最大弦差0.0964mm明确保存，非逐顶点相同CAD。native资源门通过、主cage1材料root，仅证明几何资源。原G15无效CAD只读查到solid级无效、faces/edges/wires本地状态NoError；未定位单一建模根因，不把容差猜测写成已证因果。新源改用解析Cut/Fuse，未修旧源。

两独立肩锚各15.127006kg，**未并入**新62.935418kg frame，合计93.189429kg。肩X=.115共面仅接触，未建立能传Fz/My的螺栓/焊接/剪切接面；不能由单实体宣称肩→腰承力完成。旧pitch/roll仍有下游功能，保留且干涉未关。新module质量行是子集：包含max70g芯预算、有限材料ρ和自定区间；retained完整部件质量/rotor分配、全机COM/I和真实安装质量未闭，不输出合格整机SI。

A水工作填充0.6L；B低/高罐工作1.2/0.8L，总2.0L与S1建议一致；B油工作7L。global油30L/水12.481996L仅库存一次，不能全部归箱中心或把未路由液体称安装完成。有限tank尺寸/壳和当前分配见final_receipt，膨胀/回流/吸空/NPSH/全腔/工作fill与routes库存仍红。肩 bounded_water_region 即使库存alias也排他，不能因不另计质量许可框架侵入。

111旧可见面字节保持只证明来源恒等。实渲可见B背屏/阀/边梁等新增装配外露；未采用外形变动，也没有证明轮廓fit。原画缺面、维护、完整参考空间和外露需要下一共同架构决定。无新增第三布局、没有FEM/SIMP/资格结论。

复现：使用`/home/ethan/Projects/Sai_Rotbots/.venv/bin/python`运行a或b目录对应build_partition.py，再同目录audit_partition.py；finish_diagnostics.py重建条件设计余域与同版4视，finalize.py生成收据。复现会覆盖本目录产物，冻结审计优先读取原bytes及manifest。每版producer独立，B输入schema失败前producer/log另存b_failed_input_schema。输出位置都是scratch，未Git。

冻结身份：A `a8a09ca09554057b9a18d83d6bd63528d96db0426af496d5a835caf7e2f41b3e`；B `99beca60399d0d5b59fb18abfc20c392bbe01dbf86cb258967eeef59301eefe2`。所有输入/输出具体hash由freeze_manifest.json给出。最新thermal文档仅作为未实施建议绑定，不冒充B建模输入。
