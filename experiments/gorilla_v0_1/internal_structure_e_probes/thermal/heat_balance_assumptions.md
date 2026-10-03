独立条件热预算，2026-10-02 19:12 UTC。原D未改；所有W区间为目录/自设条件组合，非实际同时任务、完整joint额定或可达上界。

官方值：QTL21065-N Pc690W/Rth.116K/W/Tc65/Ts46/Ic7.45/Is5.27；QTR16034-Z printed p20 Pc450W/Rth.17/Tc15.3/Ic16.4，未公布Ts。条件coils100C、mount20C。5+18裸电机Pc目录合11.55kW，不能与gear rated同时拼成joint输出。Pc官方标签为continuous power loss，热3I²R数值吻合铜损参考；是否包含完整速度铁损/机械损未列，gear/cable/drive总损未知。

D匹配5×CSG65(1236Nm)、10×CSG50(611)、8×CSG32(178)，全部100:1。旋转效率η仅own sensitivity，Ti=Tout/(100η)，铜损条件Pc*(Ti/Tc)^2仅在线性Kt≤Ic/源热R与换相假设下使用；不能当stall效率或真实hold。每个轴的Ti/I/Tc/Ts与出处在JSON。

|ηgear|23轴按gear额定参考的条件铜损W|
|---:|---:|
|0.55|2945.857|
|0.7|1818.616|
|0.85|1233.386|

自设其他热敏感性：23drivers345–920W，2inverters200–600，compute/network/screen100–500，fan/pumpaux100–400，未闭合iron/cable/gear/bearing300–2000。不是器件额定。EMRAX各≥6L/min、入口≤50C，仍需空气流通，不能完全封闭；96%只是源peak效率，预算85–96%完全是own sensitivity。

|油路条件（均假设无回收且油能量全耗散）|输出/gear目录扭矩比例|条件总热W low–high|
|---|---:|---:|
|matched_speed_no_recovery|0.25|14142.3–25882.0|
|matched_speed_no_recovery|0.5|14373.5–26434.3|
|matched_speed_no_recovery|1|15298.6–28643.7|
|both3000rpm_full21MPa_no_recovery_only_if_this_mode|0.25|29198.5–42800.6|
|both3000rpm_full21MPa_no_recovery_only_if_this_mode|0.5|29429.7–43352.9|
|both3000rpm_full21MPa_no_recovery_only_if_this_mode|1|30354.8–45562.3|

两泵3000rpm敏感Q59.4–64.02L/min，相比端点最大27.96765余31.43–36.05。全21MPa空烧不是默认；matched-speed约1310–1413rpm可作公式条件，最小端点需要约180–194rpm，低于源700rpm最低泵速，不能宣称全范围直接变速成立。闲置全流卸荷假设0.2–1MPa stream198–1067W；hold漏流假设.1–2L/min@21MPa=35–700W，均不含未知机械/电损或hold资格。负Fv去向为热/储能/回馈尚未选择，表中9.79kW不是电输入。油热须明确油-水或油-空气交换接口才可分配到radiator。

P=ρcpQΔT。water ownρ1000/cp4180，glycol own1040/3500。native66.5L/min仅运输输入：ΔT10K水46.33kW、glycol40.34kW，非额定或各branch保流。EMRAX12L/min最低并联条件仍独立满足；23branch冷板R/Δp/均衡未核。完整液体ΔT5/10/15K表在JSON。

空气ownρ1.2/cp1005，V=P/(ρcpΔT)，A_net=V/v，A_gross=A_net/φ。30kW、空气ΔT20K需1.244m³/s≈4478m³/h；v4m/s需净.311m²，φ.5–.7需gross.444–.622m²。这只有焓守恒，不是零阻力、fan delivered flow或coreUA额定。原两core gross.0351m²不是实际C15格栅净面积。所有热档与ΔT10/20/30K、v2/4/6表在JSON。

红线：ambient>20C无制冷不能保证载荷mount20C；EMRAX入口50C不满足Tecnotion20C安装面。QTR Ts未知、源bus曲线/真实功率/冷板接触R与并联阻力未闭合。所有热档不得作持续热放行或最终架构结论。

来源：

- [官方PDF p20](https://www.tecnotion.com/wp-content/uploads/2022/05/Torque_Brochure_EN_2-5.pdf)，SHA256 `649c4d4d8a779346f7590b7b91eaf6e3856004a90397804e2d4cce3a03a13dd4`。

- [官方PDF p1](https://www.tecnotion.com/wp-content/uploads/2025/11/QTL210_Specsheet_EN_2.4.pdf)，SHA256 `076168597ba2aac09287e4b0f5e2d749c2e52303b6b8b342d7fddc6a7f10c289`。

- [官方PDF p2](https://emrax.com/wp-content/uploads/2025/03/EMRAX_188_datasheet_v1.6.pdf)，SHA256 `cfa72eec662495d12eec6cafb61413b71c428cf0083019c52620a009e39631fa`。
