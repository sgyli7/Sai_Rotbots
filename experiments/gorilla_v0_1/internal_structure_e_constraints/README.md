# Gorilla E 开局：完整轴参考约束探针

以已提交D原生几何/质量、真实姿态COM重建与地面顶点为输入，附加23个旋转轴位置、顺序和旧C15远端body代理；维持D8液压轴与4等分脚撑假设。不是E装配，也不是完整SI。手指16轴未计独立任务接触；参考case同D48例。

所有追加容量只是减速器目录L10 rated参考，不是静态、峰值、完整电机/传动/轴承或热额定。23轴实际串联carrier、转子/流体动态质量尚未建立；这里的轴位/坐标和旧body分配是明确假设。混合N和N m需求均除以同单位容量后入无量纲联合minimax。不能据这个探针否定AA3、删任务或声称原图不能实现。

48例均超过该参考包络：最小共同峰值1.24373–15.94140。中值中立空载1.41204，共同witness髋roll约±862.8Nm/ref611与foot roll约±251.3Nm/ref178。前伸空载waist pitch约1915.8Nm/ref611，100kg约2680.4Nm；独立3t压力约9220.5Nm，不是搬运载荷。腰/肩子树没有地面接触时该参考矩不受反力分配影响；其余轴某一个高t witness可能有自由度，不能把那个轴的数值叫全部分配的最低必需。

primal方程、非负、归一化不等式及dual/reduced cost/gap均按声明容差检查。该probe补充而不改写冻结D的48个八腿轴有限witness；不能混成“D完整驱动48例通过”。用于E选择多轴载荷壳、增力臂、关节/驱动与总体安装方向，再重新算真实新几何和质量。physical_acceptance=false。

reference_axes.py.txt是实际执行的完整只读脚本；原执行位置为.scratch/gorilla_internal_e_constraints/reference_axes.py。报告保留该路径及SHA，脚本硬编码本工作区和ignored输出目录，复制回原位置可在uv run --no-sync环境复算；不是最终可移位交付入口。D的历史源/评估/渲染没有覆盖。
