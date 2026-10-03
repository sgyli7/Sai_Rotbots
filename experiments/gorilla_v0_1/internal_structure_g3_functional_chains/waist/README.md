# Gorilla G3 roll 输入候选（冻结）

范围为一套 CSG50/QTR160 的有限输入机构；原 AA3 可见外形调整0mm。两宏观方案只试A原7mm间距、B完整电机/holder/后bearing/制动/编码器沿自身轴向后移13mm，最终B。`scene.json` 是18mm WG条件深度；`wg6_scene.json` 是同拓扑6mm深度敏感项，不是第三布局。G2与历史失败源均未改。

原图重新辨读纠正：CSG50总长90mm，旧98mm错误；J8是向内台阶。局部B固定面q0、WG pilot/input端q−5mm、overall左外端q+85mm。小PCD输出A取q+84mm（图L1mm，明确为条件安装基准，尚非文字核实datum）；支承压力中心条件q+66mm。全模块B世界位置[−.123,0,2.05]、轴+X。对应G2旧输出面偏移−14mm，需要重建载体/法兰，不能只改标签。

81件真实闭面有限材料、81唯一ID。签名资源契约通过；中立自身材料0正体积、111原甲0对。新有限材料5.802753kg，gear8.9+motor1.613仅计一次，本模块16.315753kg；6mm深度变体16.287529kg。外部controller/wiring保留G2 context，未计入这些局部数字。质量/COM/完整材料惯量逐件在mass_and_load_screen；OEM实际输入gear惯量与rotor惯量分别计入理想反射敏感项，不把gross实柱惯量当OEM。

传力路径为转子ID111→0.1mm径向胶层→全长holder套筒/端spider→带键主轴→Ø19H7 WG输入；固定stator→0.1mm胶层→冷却壳/连续bearing制动载体→14有限B安装螺栓。两有限输入bearing20×47×14有圈/沟/滚珠/保持架，额定、预紧、轴向保持公差未闭合。双面制动有盘/衬片/压力板/六真实弹簧/导向销/释放coil与yoke；理论μ.2..4仅15.07..30.13Nm，不能宣称实际holding/release额定。编码器target有键路径与readhead间隙。水腔/两4mm空心接头存在，整机路由未接通，液体是原stock分配，不新增储液。

20个OEM gross交叠逐对在source_bound_reference_queries分开：严格落于已核Ø111/Hr24.6孔尺寸及Ø19H7/6JS9 key窗口者列确切体积；电机轴向datum和端空间仍未知。14螺栓仅匹配PCD174/M8与条件6mm接合，螺纹实材/盲孔深未知；不是删gross后通过。QTR rotor OD未知，不以臆造外径做装配。

唯一新增原厂资料为[Henkel LOCTITE638 May2024 TDS](https://datasheets.tdx.henkel.com/LOCTITE-638-en_GL.pdf)，已读实际page2。工程暂用1MPa不是厂商下限；转子表材、清洁/固化、hot creep/fatigue/离心与维护条件开放。40Nm接口挑战下转子胶平均0.084MPa、条件SF11.90；此40高于source ultimate34，不是运行额定。WG 18mm条件下SF3轴向保持对应输出约796.30Nm，最短6mm只有265.43Nm，因此不能在全6..18范围声称611Nm保持或2678Nm冲击。参见retaining_compound_condition真实两深度源绑定。

13个released旋转采样各有六个spring/pressure-seat约3.387mm³交叠：探针平移压力板−0.3mm而未将工作弹簧同步变形，属于变形运动模型不完整，不作为真实硬碰撞结论，也不放行释放运动。连续扫掠/接触动力/释放力未通过。保留G2其余38件后有16对冲突，最大新case×旧gear_load_shell88.584cm³；旧载荷壳和14螺栓不能作为名字重复删掉，下一阶段必须重建真实父体安装路径。所有对与exact替换名单保留。

三张native诊断图已实际看过；四视同1588.235294px/m，剖面从真实材料三角截取。不是新审美权威或CAD合格宣称。轴向剖面A文字末端略裁切，完整datum见parameters。`handoff_receipt.json` 与 `snapshot_manifest.json` 绑定源/检查/图/全部历史文件。安装、整腰、连续热、稳定SI、实物和审美放行均false。下一步是弹簧联动变形、真实OEM端空间/轴向datum、最短键/轴向固持负载范围和父体安装共同设计；本轮不扩65或第三宏观。
