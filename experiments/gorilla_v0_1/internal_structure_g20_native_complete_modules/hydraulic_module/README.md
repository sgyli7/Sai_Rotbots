# Gorilla G20 — 350 bar 控制／保持完整功能探针（拒绝）

只探索一个近端控制组＋一个直接安装在执行器上的双保持组。A/B 为两次有界原生尝试，不是已安装技术模块，不改变 Gorilla 原甲、轴位、18 数量、整机合同或 G19 冻结记录。原生四视已实际查看。根线程选择下一整机路线。

| 实际来源 | A | B |
|---|---:|---:|
| 场景 | `scene_a.json.gz` | `b/scene_b.json.gz` |
| 件数（含真实空腔／服务参照） | 45 | 65 |
| 当前条件干库存，kg | 13.085–14.350 | 13.979–15.244 |
| 独立有限材料正体积交 | 2 | 5 |
| OEM gross／CAD 参照交 | 7 | 2 |
| 本应为单材料件却有多个正根 | 5 | 9 |
| 可采用／完整净重／整机 SI | **否** | **否** |

这些干库存包含条件密度的实际自制件、源给出的 OEM 总质量和明确功能预留；缺实际 O-ring、线圈配套插头／线束、过滤器可拆端盖、辅助液路、实际执行器安装面等，不能称完整可安装净重。材料交也不能靠同 owner 豁免。没有获得 G19 预想减重。

## 官方参照与实际模型

- [HSP12-47C](https://www.hydraforce.com/globalassets/2.-products/product-pdf-files/hsp12-47c_25sep2024_16-39.pdf)：正常 350 bar、端口 1 作为入口最高 276 bar；裸阀 .44 kg 不含线圈／螺母。无手动按钮版本官方上／下包络 117.7／98.4 mm。**本 probe 上部 gross 实际只有 115.7 mm，缺 2 mm；原 metadata 的 117.7 不能当真几何。**
- [HVC12-4 原腔图](https://www.hydraforce.com/contentassets/9d139588879c412aad92f2469953ff3f/hvc12-4.gif)：按官方孔径／孔深作可编辑平滑名义腔和四真实油道；未加工螺旋牙、Detail A 74–76° 密封面及完整公差。70×70×120 mm 钢假设块，实际净质量 4.192696 kg；装阀前空腔／油道 52.2403 mL，不等于实际油库存。
- [完整 E coil STEP](https://www.hydraforce.com/globalassets/2.-products/product-stp-files/coil_10_e_stp.zip)：原 ZIP→ER ZIP→2007 STEP 保留；源 CAD 一实体有效，原导出有 **4 条 degree≠2 边**，未修法线或采用 Manifold 转换重写。两实际参照各 49.530 mm 高，与 2026 图 49.3 mm 有 .230 mm 版本差异；不缩放消除。质量各 .37 kg 取 [2026 E coil 文件](https://www.hydraforce.com/globalassets/2.-products/product-pdf-override-files/coil_10-xxex-x_2026-07-22.pdf)，不由 gross 密度算 OEM 质量或惯量。
- [A-VBSO-DE-78-FC2](https://www.hydraforce.com/globalassets/2.-products/product-pdf-override-files/re18307-56.pdf)：完整 213 mm 调整端范围、138×45×24.5 mm 块、1.2 kg、350 bar／40 L/min；C 口直接 gasket 装执行器，保双向保持。**原 producer C1/C2、V1/V2 左右标签反了**；`paths_and_source_identity_receipt.json` 单独记录官方 C2/V2 在左、C1/V1 在右的正确坐标。更正未修改原 native／interfaces 字节。

全部来源路径、哈希及许可在 `source_registry.json`。厂商资料为技术参考，未发现宽泛重分发授权；2016 保持块原文件明确厂商财产权／复制限制。只保本地研究缓存，不把它当自有可发布 OEM CAD。OEM 内材料、COM、fullI 和装阀后的油空腔未知。

## 失败的具体机械原因

A 护罩×底板／P4 接头穿料，保持块四螺栓头与杆断开。B 加入真实安装脚、两条 bench 空心工作线，但四盲安装脚压进各自壳体材料，B 线×差压壳 1.21325 cm³；护罩和 8 个安装／护罩螺栓仍有多个正根。原资源检查的 `NoError`、边次数、单材料根分别报告，不混为装配通过。

B 两真实 bench 油腔合 52.0672 mL；物理端点按官方更正为 P4→V1(right)、P2→V2(left)。这不是机器人软管，也没有辅助供油／LS／传感／滤／泄压液路、真实缸头、端口密封／保持回路完整性。现 source 不能称完整 hydraulic circuit。

拆护罩后 +Z 抽阀 15 个 10 mm 样本未发现与固定材料正体积交；原 coil 边界和装配失败仍阻止资格，不能叫实际可抽出通过。服务 stock 不是材料／质量，也不是自动自由空间。过滤器当前闭壳没有可拆端盖，是明确维修功能缺口。

## 条件公式及门禁

`limited_technical_screen.json` 保存 pQ、直管 Darcy 和 Lamé 的可重算范围。单支路 15／25 L/min、160／210／350 bar 是设计问题，机械液压功率分别用 `p_bar Q_Lmin/600`，不是整机可同时运行量。实际 ID9／OD14 mm bench 钢管在理想 350 bar 内压下内壁 VM≈103.3 MPa；没有材料许用／焊接／弯头／孔／疲劳资格。Re≈3340 的例子在过渡区，Blasius 数值仅敏感性，不能作可靠压降边界。

保持设置需要≥1.3×实际最高载荷压力；零回压时 350 bar 设置给出载荷压力≤269.23 bar 的限定，300 bar 载荷不满足；回压增加设置、最低 200 bar 弹簧设置和低载稳定性不能省略。HSP 中位 350 bar 上限泄漏 .164 L/min，对应约 95.7 W，仅源中位条件；它不能替代双保持。正常一个线圈取 20.31 W 初始上界，两同时故障 40.62 W，不凭 PWM 声称节能／连续热合格。

差压补偿、滤、隔离、泄压、传感、安全驱动完整功能均有实际有限壳／功能库存，**没有由此得到 350 bar 功能额定**。OEM inlet／回馈／失压关闭／同时工作／稳定性／持续热、材料壁／线程／公差／油污染仍红；供应未落实单独为黄，不能用黄替代物理未知。

## 文件与下一动作

`final_probe_report.json` 为简洁机器总览；A/B 的 `individual_net_material_and_fluid_receipt.json` 给逐自制件质量、COM、fullI 和 signed 根数，只适用于这些个体，不是整机质量。`cad/` 和 `b/cad/` 含自制主块／适配板的有符号原生平面 BREP/STEP，回读体积相对误差约 6e−13／2.5e−12；这是 faceted 可编辑几何交换，不是精确厂商腔体加工许可。

下一一个工作包先落实完整源接口／可拆制造方法：正确全包络与 C/V 标识、可实际保持的完整 350 bar 补偿／保护域、连续螺栓／真实接合面、独立材料无交、全部液路及执行器直接接口，再把近端控制与局部保持两个完整组放回整机。共享滤／补偿是否可分摊由整组系统设计决定，不能自动删掉。此局部失败**不证明 AA3 必须变形**。本轮停止于两源，没有第三几何布局、外形生成、FE／GPU／Git。
