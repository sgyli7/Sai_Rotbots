# Untitled Goose Game：拖拽与拾取录像来源核对

检索日期：**2026-09-28（Asia/Chongqing）**。本轮使用 research 工作流核对官方和原玩家／原攻略作者的资料，选取 8 条原 YouTube 录像，覆盖购物篮、耙、扫帚、纸箱、布类、拖鞋与完整流程。拖拽与拾取按同等重要的交互类别搜集。

这是游戏交互事实报告，不冻结机器人架构、拖拽力阈值、尺寸、步态或采购。游戏任务、动画与速度不能直接作为实物物理参数。

## 证据口径：没有虚报观看

**本调研子 agent 本轮实际观看的视频帧为 0；根 agent 也报告未能播放官方视频。** 本子 agent 的独立播放器调用返回 in-app browser unavailable，浏览器清单为空；YouTube 文字页读取出现 throttled／fetch error。没有操作根 agent 的 tab，没有登录、绕过验证或下载多媒体。

| 标记 | 本轮取得的材料 | 能支持的结论 |
|---|---|---|
| **正文** | 实际读取原作者网页或玩家 Steam 章节帖 | 作者描述的任务／拖动行为及其章节入口；不能证明具体动作第几秒开始 |
| **索引描述** | 搜索服务返回原 YouTube 标题、上传者、日期、作者描述 | 来源、作者声明和主题；不是本轮观看到的画面 |
| **待观看** | 已定位原录像，未播放到画面 | 不能断言持续地面接触、倒退步态、转弯轨迹、嘴的夹持点或物品完全离地 |

YouTube ID 是来源定位标识，不是内容 SHA。本轮未取得视频文件；描述可能修改。下列时间链接仅为**作者章节入口**或**全片入口**，不冒充视觉确认的动作起点。

## 第二轮播放器核查：2026-09-28

本次追加任务要求核实捡起和拖拽的实际画面。于 2026-09-28 05:15 起（Asia/Chongqing；2026-09-27 21:15 UTC）重新尝试，**新增实际观看帧仍为 0，取得的视频截图为 0，新增视觉动作时间点为 0**。仅有浏览器/页面工具的失败结果，没有播放器画面。

| 实际执行的尝试 | 原来源与结果 | 可支持的结论 |
|---|---|---|
| 为 V2 创建独立 in-app browser tab，未操作根 agent 的现有 tab | [Arbor Daze 原录像 Go Shopping](https://www.youtube.com/watch?v=-2sot4d13ho)；`Browser is not available: iab` | 该子 agent 本次无法创建可控播放器，不证明视频已删除或原链接失效 |
| 查询可用浏览器表面 | `apps=[]`、`browsers=[]` | 当前工具未暴露浏览器；不能声称已打开或看过任何游戏画面 |
| 页面工具读取原玩家与官方视频 | [V2 原玩家录像](https://www.youtube.com/watch?v=-2sot4d13ho)、[V1 House House 官方 Trailer](https://www.youtube.com/watch?v=5OrLdnOUEkY) 均返回 `Error fetching` | 未取得页面、视频帧或播放器时间；不是视觉核验 |
| 用 Codex UI 工具请求新的 V2 播放器页，再查询可用表面 | 返回 `status=queued`；随后仍 `apps=[]`、`browsers=[]` | “等待打开”不是已呈现/可播放；不将请求成功当播放成功 |

检索其余可调用工具后，没有发现另一项视频播放、浏览器截图或原片帧查看能力。未下载视频、音频、时间轴缩略图或其他远程媒体绕过显示限制，未登录或绕过验证。环境在创建/呈现浏览器这一层就没有提供可用画面，因此没有反复尝试其余 6 条已定位视频。

现有报告中的购物篮、耙、纸箱等仍是**原作者文字/索引证据**；所有 V8 时间仍是**作者章节入口**。没有本轮视觉依据来断言拾起后的完全离地、持续拖地、倒退、转弯、嘴部夹点、松口重抓或布/鞋的移动方式。要补这类证据，必须先能直接显示原视频；在可播放前不填写动作起止秒点，也不推导机器人控制或物理参数。

## 1. 本轮选取的 8 条原录像

全部检索于 **2026-09-28**。除第 8 条的 Steam 原帖实际读到正文外，视频元数据为原 YouTube 的**索引描述**；全部画面仍待观看。

| 编号 | 原视频 | 原上传者／日期 | 取得的内容与限制 |
|---|---|---|---|
| V1 | [Launch Day Trailer](https://www.youtube.com/watch?v=5OrLdnOUEkY) | House House／2019-09-19 | 官方发行期视频；没有已核物品动作秒点 |
| V2 | [Go Shopping](https://www.youtube.com/watch?v=-2sot4d13ho) | Arbor Daze／2020-01-02 | **原作者描述明确先拖购物篮到店主看不到的位置，再装物品**；未核装满后是否继续拖 |
| V3 | [Rake In The Lake% Tutorial](https://www.youtube.com/watch?v=BQYtHouGcgg) | FloxyCola／2022-01-22 | 原作者描述为耙入湖 speedrun 教学；不把速通时间当物理能力 |
| V4 | [How To Break The Broom](https://www.youtube.com/watch?v=aiabq_kLxHo) | Quick Tips／2019-09-28 | 原作者描述为扫帚任务演示；对拉细节由下述原作者正文提供 |
| V5 | [How To Get Thrown Over The Fence](https://www.youtube.com/watch?v=XsoQSd1tVm0) | Quick Tips／2019-09-29 | 原作者描述为越栅栏任务演示；纸箱拖动由原作者正文提供 |
| V6 | [How to Do the Washing](https://www.youtube.com/watch?v=J89ky0EX9OM) | LMAOWTF／2020-02-10 | 原作者描述为找齐洗衣物品；不能据任务名认定柔性布持续拖地 |
| V7 | [How To Make The Man Go Barefoot](https://www.youtube.com/watch?v=uS4fbdeXGyw) | Quick Tips／2019-09-28 | 原作者描述为赤脚任务；搬移拖鞋与拖鞋沿地拖行尚未区分 |
| V8 | [Full Walkthrough — Includes To do As Well](https://www.youtube.com/watch?v=xflTYTz5Y2Q) | 2019-09-21 的玩家来源帖；YouTube 上传者身份未独立核实 | [peaplays33 的 Steam 原帖](https://steamcommunity.com/app/837470/discussions/0/1626286205701937535/)实际提供此链接和章节；不把 Steam 账号名冒充已核频道名 |

[游戏官方网站](https://untitled.goose.game/)确认 House House 制作、Panic 发行并嵌有 YouTube 播放器。官方描述确认 slapstick／stealth／sandbox 的定位；本轮没有播放器画面证据。

## 2. 物品案例：明确文字与画面缺口分列

一手文字补充为 [CHRSuperstar 的自有攻略页面](https://chrsuperstar.com/untitled_goose_game/en/)，本轮实际读取正文。作者说明有自己制作的 YouTube trophy playlist；未取得该作者视频内的动作时间点。其正文能支持下表的“作者称如何移动”，不能替代连续画面。

| 物品／互动 | 本轮已核文字事实 | 原录像／时间入口 | 未核细节 |
|---|---|---|---|
| **购物篮：先移篮，再装物** | V2 原上传者描述明确将篮拖到离店主足够远的位置后装入小物 | [V2 全片入口 0:00](https://www.youtube.com/watch?v=-2sot4d13ho&t=0s)；V8 集市章节 | 持续接地、咬住提手的位置、倒退、转弯、装载后拖行；0:00 不是已核动作起点 |
| **长柄耙：移到湖边／入水** | CHRSuperstar 正文明确写抓耙并拖到湖里 | [V3 全片入口](https://www.youtube.com/watch?v=BQYtHouGcgg&t=0s)；[V8 Garden 00:54](https://www.youtube.com/watch?v=xflTYTz5Y2Q&t=54s) | 物体接地部分、鹅是否倒退、长柄过门／绕花坛的转向 |
| **扫帚：与店主对拉** | CHRSuperstar 正文称抓扫帚并朝店主反向拉，直到断开 | [V4 全片入口](https://www.youtube.com/watch?v=aiabq_kLxHo&t=0s)；[V8 High Street 06:57](https://www.youtube.com/watch?v=xflTYTz5Y2Q&t=417s) | 对拉不等于整根扫帚持续拖地；身体朝向、位移与嘴接触部位未看 |
| **纸箱：跨区域拖到后院，再藏入箱中** | CHRSuperstar 正文明确把酒吧旁箱子拖到男邻居院子，并通过栅栏缝隙 | [V5 全片入口](https://www.youtube.com/watch?v=XsoQSd1tVm0&t=0s)；[V8 Get thrown over the fence 56:01](https://www.youtube.com/watch?v=xflTYTz5Y2Q&t=3361s) | 56:01 是任务段入口，不是已核首次咬箱／拖行帧；箱子如何过弯未核 |
| **花盆、凳子、铃：改变位置／带回** | CHRSuperstar 正文分别称拖花盆、从后方拉走凳子、拖铃回起点 | V8 [后院 15:21](https://www.youtube.com/watch?v=xflTYTz5Y2Q&t=921s)、[酒吧 25:38](https://www.youtube.com/watch?v=xflTYTz5Y2Q&t=1538s)、[模型村 34:20](https://www.youtube.com/watch?v=xflTYTz5Y2Q&t=2060s) | 无单独动作秒点；可能的抓取、离地、拖地状态转换未核 |
| **布类：袜子、胸衣的洗衣互动** | V8 原帖列 washing 物品；V6 原作者称演示找齐所需物品 | [V6 全片入口](https://www.youtube.com/watch?v=J89ky0EX9OM&t=0s)；V8 后院章节 | **没有证实布持续拖地、布形变／甩动或具体夹点**；任务存在不能充作柔性布拖拽证据 |
| **鞋类：男人的拖鞋** | V8 原帖有 barefoot；V7 原作者称演示此任务 | [V7 全片入口](https://www.youtube.com/watch?v=uS4fbdeXGyw&t=0s)；V8 后院章节 | **没有证实鞋持续拖地**；咬鞋口／鞋面、搬起还是沿地拉动均待看。男孩解鞋带不等于搬走其鞋 |
| **桶：推／掉落对照** | CHRSuperstar 正文称把桶推离边缘；V8 原帖列桶的掉落任务 | V8 酒吧章节 | 尚未证明这是拖桶案例；可移动容器不能都归为拖拽 |

购物篮、耙、紙箱、花盆有原作者明确拖动文字；扫帚是对拉；凳子是拉走；桶是推落；布和拖鞋目前仅能确认任务及搬运主题。**“拖拽”不能从“拾取／搬运物品”自动推得。**

CHRSuperstar washing 段未列胸衣，但 V8 玩家任务清单有胸衣。本记录以“来源存在列项差异”保留，未将其中任何一份攻略当完整的逐帧验证。

## 3. V8 的原作者时间索引

以下全部来自实际读取的 [2019 年 Steam 原帖](https://steamcommunity.com/app/837470/discussions/0/1626286205701937535/)，不是本 agent 测出的事件时间。

| 原帖章节／任务 | 原视频时间入口 | 查找内容与边界 |
|---|---|---|
| 00:54 Garden | [00:54](https://www.youtube.com/watch?v=xflTYTz5Y2Q&t=54s) | 耙、野餐；下一章节 06:57 |
| 06:57 High Street | [06:57](https://www.youtube.com/watch?v=xflTYTz5Y2Q&t=417s) | 扫帚、购物篮；下一章节 15:21 |
| 15:21 Back Gardens | [15:21](https://www.youtube.com/watch?v=xflTYTz5Y2Q&t=921s) | 布、拖鞋、花盆相关任务；下一章节 25:38 |
| 25:38 Pub | [25:38](https://www.youtube.com/watch?v=xflTYTz5Y2Q&t=1538s) | 凳子、桶、摆桌；下一章节 34:20 |
| 34:20 Model Village | [34:20](https://www.youtube.com/watch?v=xflTYTz5Y2Q&t=2060s) | 取铃并带回；credits 入口为 41:31 |
| 55:32 Catch an object as it's thrown over the fence | [55:32](https://www.youtube.com/watch?v=xflTYTz5Y2Q&t=3332s) | 拾取／接住的对照主题，不是拖拽事件 |
| 56:01 Get thrown over the fence | [56:01](https://www.youtube.com/watch?v=xflTYTz5Y2Q&t=3361s) | 纸箱任务入口；下一条任务为 57:18 |

“下一章节”仅缩小查找范围，不保证区间只有一个任务，也不保证第一次抓取／拖动从章节第一秒开始。V2–V7 未取得作者所标动作秒点，只能给全片入口。

## 4. 尚待连续画面核实的事实

| 待核项 | 当前证据状态 | 对应来源 |
|---|---|---|
| 物体部分持续接地、嘴仍保持抓取 | 作者使用 drag；本轮没有视觉接触证据 | 购物篮、耙、纸箱 |
| 倒退：身体朝向与平移方向相反 | 无本轮原录像画面证据，不从评论里的 backwards 一词补造 | 耙、扫帚 |
| 转弯：物体随鹅改变方向，长物／容器在拐角的扫掠 | 无本轮原录像画面证据 | 耙、纸箱、铃路线 |
| 布的一端夹住，其余部分拖地／形变 | 有洗衣主题，无动作证据 | V6、V8 后院 |
| 鞋的夹持部位及搬起／拖地状态转换 | 有拖鞋任务，无动作证据 | V7、V8 后院 |
| 先拖容器、装物、再拖装载后的容器 | **先拖购物篮**有原上传者描述；**装载后拖行未证实** | V2 |
| 松口、重抓、卡住、被 NPC 拿回 | 未核动作发生时间与连续性 | V8 完整流程 |

补看时须记录观察者、原 URL、真实动作起止时间、嘴接触部位、物体接地／离地、鹅的平移／转向及松口重抓。暂停单帧只能支持当帧姿态；倒退、拖行、转弯需要连续多帧或片段。

本轮已经提供可追溯原视频与作者时间索引；持续拖地、倒退、转弯以及布／鞋具体拖法仍明确留空。未把搜索摘要写成“已看过”，未下载录像，未补造物理参数或动作秒点。
