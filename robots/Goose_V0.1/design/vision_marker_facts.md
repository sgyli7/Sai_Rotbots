# 首版指定物标签视觉：一手事实核查

检索日期：2026-09-28（UTC 2026-09-27）。仅核查接口、相机规格和可复现依赖，不决定机器人控制。OpenCV官网`4.x`本轮重定向到4.13.0；下文源码固定4.13.0对应commit **`fe38fc608f6acb8b68953438a62305d8318f4fcd`**，不是无版本的master。PyPI当前默认版本另为5.0.0.93，不能把固定4.13称作PyPI最新版。[官方tag对象](https://api.github.com/repos/opencv/opencv/git/tags/2e1f8da65e4f9fa1a98423e6ac223187438a4db8)、[PyPI当前元数据](https://pypi.org/pypi/opencv-python/json)

## 检测与角点顺序

**fact**：Python接口可直接使用主模块包中的`cv2.aruco`；本轮实际验证，无需仅为新`ArucoDetector`额外安装contrib。`DICT_4X4_50`有50个4×4编码，ID为0–49；默认黑边宽1个bit，生成图不是只含内部4×4区域。[官方字典源码](https://github.com/opencv/opencv/blob/fe38fc608f6acb8b68953438a62305d8318f4fcd/modules/objdetect/include/opencv2/objdetect/aruco_dictionary.hpp)、[生成/检测文档](https://docs.opencv.org/4.13.0/d5/dae/tutorial_aruco_detection.html)

```python
import cv2
ar = cv2.aruco
d = ar.getPredefinedDictionary(ar.DICT_4X4_50)
detector = ar.ArucoDetector(d, ar.DetectorParameters())
corners, ids, rejected = detector.detectMarkers(image)
```

**fact**：检测返回四角的标签原始方向顺序：标签TL→TR→BR→BL，在图像中顺时针。标签旋转后，corner0不一定在屏幕左上；源码根据解码得到的旋转量执行`correctCornerPosition`。**不得再按屏幕x/y或x+y把检测角点重排**，否则标签自身轴的对应关系会变。[检测源码](https://github.com/opencv/opencv/blob/fe38fc608f6acb8b68953438a62305d8318f4fcd/modules/objdetect/src/aruco/aruco_detector.cpp#L537)

`SOLVEPNP_IPPE_SQUARE`只接受以下有序四个共面objectPoints。L是已知的标签正方形边长，需与检测到的外黑边方形对应；外部白色留边不加入L。imagePoints使用上述检测顺序，浮点数组可整理成4×2，objectPoints为4×3。

| index | 标签角 | 精确objectPoint |
| --- | --- | --- |
| 0 | TL | `(-L/2,+L/2,0)` |
| 1 | TR | `(+L/2,+L/2,0)` |
| 2 | BR | `(+L/2,-L/2,0)` |
| 3 | BL | `(-L/2,-L/2,0)` |

**fact**：相机坐标轴为x右、y下、z向前；`rvec,tvec`表示**object→camera**，即`p_camera=R(rvec)@p_object+tvec`。tvec单位随L：L用米，tvec用米。`tvec[2]`是光轴深度，`norm(tvec)`是中心到相机原点距离，两者不同；camera frame也不自动等于机身/喙坐标。IPPE平方可有两个解，`solvePnPGeneric`能取多解；当前源码按重投影误差排列，而`solvePnP`只返回第一解。多个解存在不等于已解决遮挡、噪声下姿态歧义。[官方PnP文档](https://docs.opencv.org/4.13.0/d5/d1f/calib3d_solvePnP.html)、[solvePnP源码](https://github.com/opencv/opencv/blob/fe38fc608f6acb8b68953438a62305d8318f4fcd/modules/calib3d/src/solvepnp.cpp)

## 标定字段及边界

**fact**：K为3×3矩阵`[[fx,0,cx],[0,fy,cy],[0,0,1]]`，参数以像素计。常用5系数顺序是`(k1,k2,p1,p2,k3)`；标准calib3d接口还支持4/8/12/14系数，延伸顺序为k4/k5/k6、s1/s2/s3/s4、tau_x/tau_y。不能仅按数组长度把其他畸变模型的D混用。[标定教程](https://docs.opencv.org/4.13.0/dc/dbb/tutorial_py_calibration.html)、[calib3d接口](https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html)

官方标定样例实际保存`camera_matrix`、`distortion_coefficients`、`image_width/image_height`、`square_size`、`flags`、`calibration_time`、`avg_reprojection_error`，可附`per_view_reprojection_errors`。这些是样例字段名，不是OpenCV规定的唯一工程文件格式。相机型号/序列号、焦点状态、采集格式、标定模型及单位也需可追溯（工程记录建议）。[固定版本标定样例](https://github.com/opencv/opencv/blob/fe38fc608f6acb8b68953438a62305d8318f4fcd/samples/cpp/calibration.cpp#L247)

**fact / derived**：ArucoDetector不自动校正镜头畸变。原始图像角点可配原始K,D给PnP；若先去畸变，则必须配去畸变后的K和零D，不能重复应用原D。图像缩放需同步缩放fx/fy/cx/cy；裁剪会移动主点；不能以FOV反算出的粗略K替代实机标定。OpenCV明确改变焦点属于光学变化，原标定不应无条件复用。[检测API源码说明](https://github.com/opencv/opencv/blob/fe38fc608f6acb8b68953438a62305d8318f4fcd/modules/objdetect/include/opencv2/objdetect/aruco_detector.hpp)、[标定与光学变化说明](https://docs.opencv.org/4.13.0/d5/dae/tutorial_aruco_detection.html)、[去畸变接口](https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html)

**本任务约束**：仿真视觉输入必须来自真正相机RGB渲染帧，实机来自实摄帧，均再执行标签检测。objecttruth可以作为独立评估参考，不能直接给视觉测量返回标签中心、角点或距离。标签ID只编码识别身份；距离来自检测像素、已知L与标定。OpenCV API不会自动防止程序读取objecttruth，需在工程接口上保持此边界。本轮未运行MuJoCo/Godot相机链，也没有实摄标定数据。

## Waveshare SKU24710：实际规格与准确性缺口

| 项目 | 官方fact |
| --- | --- |
| 产品 | OV5693 5MP USB Camera (A)，SKU24710，USB2.0，自动对焦；商品标题同时出现fixed-focus/auto focusing，参数表明确Auto focusing。 |
| 视野 | **135°对角 / 95°水平 / 70°垂直**；70°不能当水平FOV。EFL2.5 mm，F2.1。 |
| 近焦 | 官方wiki FAQ写自动对焦范围**约5 cm–5 m**，是对焦范围，不是测距范围或精度承诺。 |
| 数据/供电 | MJPG、YUY2；MJPG 2592×1944、1920×1080、1280×720均15FPS；5 V±5%，500 mA。 |

来源：[SKU24710商品页](https://www.waveshare.com/product/modules/ov5693-5mp-usb-camera-a.htm)、[官方wiki FAQ](https://www.waveshare.com/wiki/OV5693_5MP_USB_Camera_%28A%29)。本轮商品页正文可读取；wiki直接打开403/Cloudflare，**5cm–5m取自检索工具返回的官方wiki正文，不声称成功直接抓取wiki或实机测试**。

**inference，非厂家保证**：FOV说明覆盖角度，近焦说明能否对焦；均不能推出标签测距准确。缺失实机K/D、焦点变化量、实际标签尺寸误差、工作距离/角度下误检率与距离误差、曝光/运动模糊影响，也没有厂家测距精度指标。能检测到标签或重投影误差较小，也不是实物距离误差已验收。

## 可复现依赖与本轮小探针

**建议固定，非修改主配置**：CPython3.12，`opencv-python-headless==4.13.0.92`、`numpy==2.2.6`。这是本轮aarch64 / Python3.12.14实际跑通的组合；不用OpenCV GUI时可采用headless。四种OpenCV wheel共用`cv2`命名空间，同一环境只装一种。[官方PyPI安装说明](https://pypi.org/project/opencv-python-headless/4.13.0.92/)

**PyPI fact**：4.13.0.92元数据对于Python≥3.9要求`numpy>=2`，**没有upper bound**；Python<3.9要求`numpy<2.0`。NumPy2.2.6本身要求Python≥3.10。选择固定2.2.6是本轮复现建议，不是上游唯一允许版本。下面两个OpenCV ARM64 wheel真实公开：

| wheel / Linux glibc门槛 | SHA-256 |
| --- | --- |
| `opencv_python_headless-4.13.0.92-cp37-abi3-manylinux2014_aarch64.manylinux_2_17_aarch64.whl` / 2.17 | `5c8cfc8e87ed452b5cecb9419473ee5560a989859fe1d10d1ce11ae87b09a2cb` |
| `opencv_python_headless-4.13.0.92-cp37-abi3-manylinux_2_28_aarch64.whl` / 2.28 | `eb60e36b237b1ebd40a912da5384b348df8ed534f6f644d8e0b4f103e272ba7d` |

[OpenCV版本原始JSON](https://pypi.org/pypi/opencv-python-headless/4.13.0.92/json)、[NumPy版本原始JSON](https://pypi.org/pypi/numpy/2.2.6/json)。CPython3.12的NumPy ARM64 manylinux2.17 wheel SHA为`f2618db89be1b4e05f7a1a847a9c1c0abd63e63a1607d892dd54668dd92faf87`。这些只确认Linux ARM64轮子，未验证Radxa板上的性能、USB采集及系统兼容。

**probe fact**：依赖仅装入忽略的`.scratch/vision_marker_probe/site_packages`；主环境和配置未改。脚本先生成240px标签PNG/透视PNG，再`imread→ArucoDetector→PnP`，不把渲染器角点送入检测或PnP。透视图使用假定K、零D、L=0.06 m，仅检验API链，不是相机测距验收：

- ID7正向、逆时针90°、透视图均检出；空白图返回无ID。
- 逆时针90°后corner0约`(199.56,359.44)`，在屏幕左下；验证须保留标签自身角点顺序。
- 透视PNG中PnP成功，tvec约`(0.01525,0.00997,0.60345)` m；Generic返回2解，重投影误差约0.279/1.180 px。
- 本轮生成的旋转/透视图已实际观看；没有实摄结果、仿真闭环或距离精度结论。

取证脚本、JSON与图像仅在上述私有目录。脚本SHA-256：`92786ed14090948b6a81aa61c38a42dc6c06c6a8f4617f84a9da1d8a055c6b7f`；透视输入PNG SHA-256：`b45d1c6b2169bcb7c541b2d7b76c20811906941ea1b907743194d0e8cda07eb1`。
