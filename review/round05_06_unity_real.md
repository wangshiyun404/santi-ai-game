# 盲审记录 · 第 5–6 轮（Unity 真机 + WebGL 构建）

第 4 天。Unity 6000.3.27f1 在 Mac 上以 batchmode 跑通整条流水线：`BuildScenes → CaptureReview（编辑态 5 机位）→ PlayCapture（运行态 t=1/4/9 s，4 s 后自动前行）→ BuildWebGL / BuildMac`。一轮"改代码 → 推送 → Mac 拉取 → 重建 + 截图"约 70 s。截图由 Mac 侧生成（review/unity/，不入库），看板见 review/round06_unity_board.jpg。

## 第 5 轮（首批真机截图暴露的问题 → 已修）

| # | 现象 | 根因 | 修法 |
|---|---|---|---|
| 1 | 所有角色 T-Pose 不动 | glTFast 把动画 GLB 按 Mecanim 导入（meta `animationMethod: 2`），而 CharacterAnimator 用 Legacy Animation | Pipeline.SetupProject 改写 `Assets/Models/Anim/*.glb.meta` → `animationMethod: 1` 并强制重导 |
| 2 | Tripo 资产像镀铬 | glTF `metallicFactor=1` + 金属粗糙贴图，再加平直环境光 | Mats.cs 把 Tripo 材质复制为 URP/Lit：金属 0、光滑 0.25（Assets/Materials/Tripo/） |
| 3 | 乱纪元一片白、阴影面全黑 | 线性空间下 sun×0.6 + 环境色 #D9D6CF 直接当强度 | 太阳 `clamp(强度×0.5, 0.3, 1.0)`；环境光改三色（Trilight），峰值随太阳强度反向调整 `clamp(1 − sun×0.7, 0.25, 0.5)`；全局 ACES + 轻 Bloom/暗角 |
| 4 | 乱纪元地面成巨型棋盘 | ground_chaotic 22% 面片用深色 crack 材质，Unity 里对比过强 | Mats.ColorOverride：`ground_chaotic/crack` → 线性 0.47（≈dust 的 85%）；注意 `_BaseColor` 走 sRGB 约定需 `.gamma`，第一次写线性值无效 |
| 5 | 人列计算机出生点在高台巨影里 | 太阳 yaw −120° 让影子正好盖住 (120,0,0) | 太阳改 (70,0,60)，影子背离出生点（build_assets.py + 两份 layout JSON 同步） |
| 6 | 工程无 URP Asset、缺 ImageConversion 模块、ThreeSunsEvent 少分号、NamedBuildTarget 命名空间 | 代码从未在编辑器里编译过 | 全部在 SetupProject / 源码里修掉 |

## 第 6 轮（WebGL 体积与可运行性）

- 首个 WebGL 构建 **145 MB**，贴图占 96%：每个 Tripo GLB 内嵌 3 张 2048² 贴图，Unity 以未压缩 RGBA32 打包（单个资产 37–40 MB）。
- 修法：`scripts/strip_glb_textures.py` 把基础色抽成外置 PNG（角色/主体 1024、道具 512，Crunch 压缩 + mipmap），GLB 去掉 images/textures 并重建缓冲（Models 目录 68 MB → 13 MB）；金属粗糙/法线贴图弃用（低模风格无感）。Mats.Convert 优先取 `Assets/Textures/Tripo/<asset>_base.png`。
- 结果：**WebGL 20 MB**（data 12.8 MB + wasm 8.2 MB，Gzip + 解压回退），增量构建 1.1 min；macOS 通用版 135 MB（Desktop/三体三体游戏_macOS.zip 55 MB），3.1 min。
- 云端浏览器实测：加载到 100%，WASD 行走、相机跟随、营房碰撞均正常。
- 发现一个加载器问题：在**沙箱 iframe（无 allow-same-origin）**里 Unity 加载器读 `window.caches` 直接抛 SecurityError，进度卡 0%。已在 dist/webgl/Build/WebGL.loader.js 打补丁（try/catch 后回退到普通 fetch），index.html 另把 companyName/productName 置空关闭 UnityCache。每次重新构建后需重打这个补丁（见 README）。

## 三场景观察（第 6 轮截图）

| 场景 | 通过 | 待改 |
|---|---|---|
| 红岸 | 黄昏色调、天线塔/吉普贴图、行走动画、相机跟随、碰撞 | 营房仍是深色方块（B 类），可换 Tripo 砖房 |
| 乱纪元 | 曝光正常，地面为细碎斑驳的尘土，脱水卷/竹简贴图可见，金字塔在远处 | 角色背光面偏暗，可加 0.2 补光；地面抖动仍让部分碎石微悬空 |
| 人列计算机 | 方阵黑白旗清晰、出生点有阳光、高台影子背离 | 高台仍是灰块；平原无细节（可加远处军帐/旗帜）；ThirdPersonController 的跑步阈值永远达不到（walkSpeed 2.6） |

## 结论
Unity 真机链路已闭环，三场景可玩且 WebGL 体积进入"课堂可下载"区间（20 MB）。下一步是托管路径（见 README「交付」）与 B 类资产替换。
