# G17 connected cage / complete functional co-layout

A/B 两宏观候选均封存，不采用；没有第三布局或有限元。本轮实际改善是自有宽梁、节点和原肩锚形成合法连续 CAD，双EWP150完整stock真实画入；不因此宣布承力、安装、热、外观或整机SI通过。

| 同版事实 | A | B |
|---|---:|---:|
| 实际native件数 | 2530 | 2530 |
| 新/移动×all混合正体积 | 1352 | 336 |
| finite–finite | 473 | 24 |
| 液腔×finite | 17 | 0 |
| 测试主要组profile交 | 8 | 1 |
| 净自有frame+两锚，ρ7850假设 | 95.705637kg | 95.705637kg |

筛查只覆盖本版新/移动件与全部present件，不覆盖unchanged-retained之间、运动/气液全回路。主要组仅4pack/18directional/S1×5/双液压输入/两肩及低串联泵，单独aux/罐/HV/compute由changed×all另审；不同版本数字不能直接作优化率。

B 恢复四个完整120芯axisY包，抬高两层至Z2.140/2.396；两水罐移前侧，油罐完整壳和7Lfill移后中央；完整HX四port、compute、HV/LV、泵/filters/controllers用统一刚体datum搬位。480芯maxØ21.55×70.15、pitch22.5及全部辅助功能保留，min能量7.44kWh只是cell参照，不是整包额定或30min验收。70g是max而非已知nom，rawrows的33.6kg不能成为真实low/nom；部件/rotor分体质量、全机COM/fullI及真实安装均unknown。

B24 finite分类：8port穿Al壳缺真实孔，8port×coldplate同Al安装未净料union，8mountbolt穿壳缺孔，全部保失败；不是macro frame×pack撞但sameowner不豁免。唯一主要组pair为pack3×低串联泵mount/guard等完整profile7.6235cm³，保失败不删辅助。
另外净自有frame含旧锚housing，仍各与CSG65完整profile交84.009315cm³：旧ring(q.020,L.010,Ri.118)侵入q0..024/R.130 flange。OEM没有被union或裁掉，这项gross/真实接口未知是核心安装红线，不能当正常内部空间或同固定body免除。

主CAD来自解析OCC Cut/Fuse，合法1solid；native用相同参数64段圆弧，二者V/最大弦差/实际SI回读在frame_CAD_native_mapping.json。原两锚native重建对原source对称差左1.57e−20、右4.57e−20m³，旧料均被新net实际包含；各独立锚ID退休为一个g17_connected_cage_and_fixed_anchor_net，只计一次，所有OEM case/双支承/bolts/bearings仍独立。真实6mm节点贯入自有前墙并连通，不靠共面或owner；材料制造、焊接/疲劳/载荷闭合未知。

17旧contract只作source datum。新native重新按实际world plane和源区域查询面，不复制G15face编号。PC270 parent席面、B receiver/A output查询面积保留；两旧coreX=.115面已内部化，waistX=.2475实际面变为.00470482m²，不能继承旧traction。四bearing另按当前native真实半径/轴向区间重新裁取弦面，历史面积差0；source座保持不等于接触/预紧/压力中心/FE边界通过。完整新serial肩是另分支，当前候选没有叠加它或删除旧4carrier的下游功能；root综合版本需exact替换。

油罐实际容量10.716264L/work7；水低2.352504/work1.2，高1.741464/work.8。全局库存只逻辑一次，不全归罐中心：rawsource oil range12.759/16.356/21.654L是旧G16工作域，不能套当前7L；同旧external-route proxy应17.151/19.248/22.046L，但新routes未建仍不当实际库存/质量闭合。中条件所需tank10.717139与当前差.875mL只是假设敏感，非额定精度；高条件12.8042明确不足。水range同样不是新实际路线。低pump stage0比低水液面高约154mm，NPSH/吸空/入口压/接管均未关。

S1保4×ES0707完整254×212×80、1×ES0714完整457×212×80，各176mm硬件厚/6完整172×51fans及plenum/guard/ports。低两个完整150 stage共140×190×270，加真实有限OD38/ID32短连接与非零mount/guard/reducers；hot80独立。EGW71°C来源曲线、20°C安装面、35°C环境、branch压降与LC转子空气需求仍红；并未因能画入继承容量。EMRAX空气guard/duct .248×.150×.248/每motor的后续预算尚未画，缺项不为零；两低芯可借原前格栅，其他低/hot仍需真实独立侧后进排口和密封风路，原甲缺面不当通风孔。

111旧可见面保留只证明来源。actual-native白躯曲面配对射线采样下界：低双150前露188.09mm，上电池前露46.64mm，后上散热段后露62.96mm；有缺面样本，既非AABB认证腔，也不能宣称AA3全局不可行。当前同源四视/拆壳/全身/切面都显示失败；至少需要局部侧/前泵包装与后风道包装方案或下一完整架构重排，未自动采用可见改形。未修改外腿脚。

源A `ce5ad4d0736ed1d60c8b7b926358402d0a6e25abdbf3076753e201fab8291242`；源B `52eb6bb53bb84cfacf24fbe4f2f4f4e35b4a97d4cef90729fc3ff9f0382c2756`。每版producer独立保存，当前源不再改。用`/home/ethan/Projects/Sai_Rotbots/.venv/bin/python`执行对应a/b build_connected_layout.py，再audit_connected_layout.py；diagnose_layout.py、map_unchanged_bearing_seats.py和render_whole_context.py生成实际诊断。冻结审计读原bytes/manifest；重放会写本scratch目录，旧G16/G15未改，未Git/GPU/默认SI。
