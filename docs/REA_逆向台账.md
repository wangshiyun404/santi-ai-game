# 《三体：三体游戏》REA 逆向台账

> 方法来源：[Reverse Engineer Anything（morluto/rea）](https://github.com/morluto/rea)。
> 被逆向的"目标"不是别人的程序，而是我们自己的成品（take4 真机录像 + 仓库资产）。
> 规矩：每条结论拆成 **观察（O）/ 推断（I）/ 未知（U）**，挂证据编号；先列问题清单，再按最小证据面取证；修完必须拿新录像与证据对照验证；收尾时回看清单，标注已答 / 部分 / 未解。

## 0. 目标与成功判据

- 目标：找出"画面与游戏设计不过关"的根因，而不是逐个修表面症状。
- 成功判据（可验证）：
  1. 角色移动时面朝移动方向（新录像任意一帧，脸/胸朝向 = 速度方向，误差 < 30°）。
  2. 角色在默认镜头下可辨认五官（眼、嘴），对话时有表情变化（≥ 3 种）。
  3. 速度 > 阈值时播放 run 剪辑，脚步与位移速度匹配（无明显滑步）。
  4. 无悬空道具；地面/天空有层次，不再是纯色平面。
  5. NPC 面向玩家或剧情方向，不再背对/斜对。

## 1. 证据索引

| 编号 | 文件 | 来源 | 内容 |
|---|---|---|---|
| E01 | `docs/rea_evidence/E01_walk_frames.jpg` | take4 录像 t=20.5/22/36.5/85/90/155/158/165 s | 三个场景的角色行走裁切 |
| E02 | `docs/rea_evidence/E02_walk_zoom.jpg` | take4 t=20.5/22/85/155 s，3× 放大 | 角色朝向 vs 位移方向 |
| E03 | `docs/rea_evidence/E03_char_textures.jpg` | `Assets/Textures/Tripo/char_*_base.png` | Tripo 角色贴图（UV 图集） |
| E04 | `docs/rea_evidence/E04_player_render_axis.jpg` | Blender/Cycles 渲染 `assets/tripo/char_player.glb` | 静态模型侧视 + 头部正/背面 |
| E05 | `docs/rea_evidence/E05_rig_axes.jpg` | Blender 渲染 `assets/tripo/anim/char_player_anim.glb`，相机分别在 −Y/−X/+X/+Y | 绑骨模型四向视图 |
| E06 | `docs/rea_evidence/E06_rig_head.jpg` | 同上，头部特写，相机在 −X / +X | 脸的朝向与五官 |
| E07 | `docs/rea_evidence/E07_scene_frames.jpg` | take4 t=10/28/50/75/118/180 s 全画面 | 三个场景整体观感 |
| E08 | `unity/SanTiGame/Assets/Scripts/Editor/SceneBuilder.cs` L239–244 | 源码 | 角色实例化：`localRotation = Euler(0, 90, 0)`，注释称"原始朝向 −X（glTFast 翻转 X 轴后）" |
| E09 | `Runtime/ThirdPersonController.cs` L36–40 | 源码 | `walkSpeed = 2.6`，朝向用 `Euler(0, angle, 0)`，位移用同一角度 × `Vector3.forward` |
| E10 | `Runtime/CharacterAnimator.cs` L13–14 | 源码 | `walkThreshold = 0.3`，`runThreshold = 3.5` |
| E11 | `Runtime/FollowCamera.cs` L7–9 | 源码 | 距离 6 m、高 2.5 m、俯角 15°（PRD §6 "让角色显小"） |
| E12 | Blender 骨骼读取（`/tmp/face_anchor.py`） | 绑骨 GLB | Mixamo 命名骨架 65 根，`mixamorig:Head` 原点 z=0.883（1 m 归一化） |
| E13 | `Assets/StreamingAssets/layouts/scene_01_chaotic.json` | 布局数据 | 60 块 `rock_small` 全部 y=0，不随地形起伏 |
| E14 | `layouts/scene_02_computer.json` | 布局数据 | 三位 NPC 统一 yaw=20°，与玩家来向无关 |
| E10/E12 | `docs/rea_evidence/E10_face_check_a.jpg`、`E12_face_check_b.jpg` | Blender 渲染，绿线=候选眼线、红线=候选嘴线 | 6 个角色脸部核验 |
| E11 | `docs/rea_evidence/E11_heads4_a.jpg`、`E11_heads4_b.jpg` | Blender 渲染，相机 +X/−X/+Y/−Y | 6 个角色头部四向 → 全部面朝 +X |
| E13 | `docs/rea_evidence/E13_yewenjie_full.jpg` | Blender 渲染 | 叶文洁全身：脸与手为紫色（贴图错） |
| E14' | `docs/rea_evidence/E14_face_patches_v3a.jpg`、`E14_face_patches_v3b.jpg` | Blender 渲染 | 几何五官薄片贴合效果（玩家 / 牛顿 / 秦始皇 / 叶文洁） |
| E15 | `docs/rea_evidence/E15_yewenjie_fixed.jpg` | Blender 渲染（Unity 实际贴图） | 叶文洁脸部贴图修复后 |
| E17 | `docs/rea_evidence/E17_facecam_minus90_backhead.jpg`、`E17b_chasecam_minus90_eyes_to_camera.jpg` | Unity 真机 PlayCapture（−90° 版本） | 脸部特写拍到后脑；追尾镜头看到正脸 → −90° 错 |
| E18 | `docs/rea_evidence/E18_facecam_plus90_faces.jpg`、`E18b_play_plus90_back.jpg` | Unity 真机 PlayCapture（+90° 版本） | 正脸五官清晰、追尾看到后背 → Q1 通过；几何五官挂接位置正确（Q2 判据 2 通过） |
| E19 | `docs/rea_evidence/E19_soldier_axes.jpg` | Blender 四向渲染 | 人列计算机士兵（静态网格）原始朝向 glTF +Z，与绑骨角色（+X）不同；`SoldierFormation` yaw≈0 正确，阵列面向高台 |
| E21 | `docs/rea_evidence/E21_ground_textures_play.jpg` | Unity 真机 PlayCapture | 三场景地面贴图生效（Q5 第二批通过）；`REA_round7_board.jpg` 为本轮前后对照看板 |
| E16 | Blender 射线实验（`/tmp/dbg*.py`，见 §2 Q2 O7） | 实验 | 绑骨 GLB 导入后停在 idle 第 1 帧，头部已偏离绑定位 → 必须用 REST 姿态取脸面 |

## 2. 问题清单与结论

### Q1 角色为什么"跑步方向是错的"？

- **O1**（E02）：四帧中角色均在远离镜头移动（阴影与位置变化），但看到的是胸口、脸和披风正面 —— 身体面朝镜头、背着走。
- **O2**（E06）：绑骨模型在 Blender 中，相机放 +X 才看到脸，放 −X 看到后脑 → 模型原始朝向为 **+X**（glTF 坐标）。
- **O3**（E08）：代码按"原始朝向 −X，glTFast 翻转 X 轴"的假设旋转 +90°。
- **I1**：glTFast 转手性是翻 Z 不翻 X；+X 朝向经 +90° 偏航后指向 −Z，正好与控制器 `forward` 反向 → 180° 背着跑。两个独立证据（录像 E02、模型 E06）指向同一结论。
- **I2**：NPC 走同一函数，所以 NPC 的面向也整体错 180°（E07 第 6 帧三位 NPC 看似各朝一方，与 E14 的统一 yaw 矛盾，可由此解释）。
- **U1**：glTFast 版本差异是否影响翻转轴 —— 不猜，用新录像验证（判据 1）。
- **修复假设（已被推翻）**：`Euler(0, −90, 0)`。
- **O10（E17，真机脸部特写，决定性）**：按 −90° 重建后，从玩家根节点 `forward` 正前方 1.3 m 拍脸，拍到的是**后脑**；追尾镜头（根节点正后方）反而看到带眼睛的正脸 → −90° 让角色背对前进方向。
- **I5（修正）**：O1 是误读——E02 是 480p 录像再裁切放大，"胸口与脸"实际是披风兜帽的**背面**；低清证据不能作朝向定论。I1 对 glTFast 转手性的推断也错了：glTFast 翻的是 X 轴（+X 朝向 → −X），+90° 偏航把 −X 转到 +Z，**原代码本来是对的**。
- **O11（E18）**：恢复 +90° 后，脸部特写拍到正脸（眼、眉、嘴清晰，一帧捕捉到眨眼），追尾镜头看到后背 → Q1 判据 1 通过。
- **教训（写入方法）**：朝向这类二值问题，必须用"已知相机位 + 可辨识特征（五官）"的专用证据回答，不能靠全景抽帧目测；本轮为此新增 `PlayCaptureRunner.FaceShot` 作为固定核验手段。
- **用户所说"跑步方向错"的其余可能**（未结）：U1' 过场/自动演示中转向时镜头偏航滞后（1.5 s 时间常数）使角色短暂侧身奔跑；U1'' 人列计算机阵列与 NPC 的朝向（Q6）。待新录像复核。

### Q2 为什么"没有五官、没有表情"？

- **O4**（E06）：几何上有鼻梁楔形与耳朵，但贴图在脸部没有任何眼睛、嘴的绘制 —— 是贴图缺失，不是几何缺失。
- **O5**（E03）：Tripo 贴图是碎片化 UV 图集，1024²；脸部区域仅占极小比例。
- **O6**（E11、E07）：默认镜头 6 m / 俯角 15°，角色占画面高度约 1/6，脸部不足 20 px —— 即便有五官也看不见。
- **I3**：根因有两层：(a) 生成期参考图是全身远景，Tripo 没有脸部信息可画；(b) 镜头设计刻意"让角色显小"，放大了缺陷。
- **I4**：Tripo 输出没有表情 blendshape（E12 只有骨骼），表情必须由我们自己做。
- **U2**：重新生成（带正脸参考）能否画出可用五官 —— 需实验，成本约 40 积分/角色 + 绑骨重定向；余额约 575，6 角色全重做会耗尽预算。
- **修复（设计选择，非观察）**：
  1. 否决"画进贴图"：脸部在 1024² 图集里只占约 60×60 像素，眼睛不到 6 像素，再经 Crunch 压缩会糊成一团（O5）。
  2. 采用**几何五官薄片**（`scripts/face_patches.py`）：REST 姿态下沿 +X 向脸面打射线，椭圆采样 → 贴合脸面、沿法线外推 3–4 mm 的薄片：眼白、瞳孔、闭眼线、眉、嘴线、张嘴，共 10 件，导出 `Assets/Models/Face/<name>_face.glb`。分辨率无关、任何距离都清晰（E14'）。
  3. 运行时 `FaceExpression`：薄片挂到 `mixamorig:Head`，`child.local = bindposes[head]`（薄片与蒙皮同处绑定空间）；随机眨眼（2.5–5.5 s）、说话（张/闭嘴 6–12 Hz）、惊讶（眼白 ×1.25 + 张嘴）。触发：线索对话 → NPC 说话 + 越肩近景；乱纪元/三日凌空事件 → 玩家惊讶。
  4. 叶文洁紫脸：`scripts/face_skin_fix.py` 用脸部多边形的 UV 三角形做掩膜，只把掩膜内的紫色像素改成肤色（E15）；裤子等同色相区域不动。
  5. 镜头拉近到 4.2 m / 俯角 10° / 高 1.9 m；对话时切越肩近景（`FollowCamera.focusDistance`）。
  6. 跟随者与冯·诺依曼已有贴图五官，不加薄片（避免双眼睛）；他们暂无表情（U6）。
- **U2 更新**：不再需要重新生成 6 个角色；可选实验仅剩"叶文洁整体重做"（参考图需正脸），非本轮必需。
- 验证：E14'/E15（Blender）已通过；Unity 侧用 `PlayCaptureRunner.FaceShot`（玩家正前方 1.3 m）截图核验挂接位置与朝向，再看新录像对话段。

### Q3 为什么从来没见过跑步动画？

- **O7**（E09、E10）：`walkSpeed = 2.6` < `runThreshold = 3.5`，玩家手动操作永远触发不了 run；只有演示模式 4.5 m/s 会跑。
- **O8**（E02）：行走帧中步幅与位移比例不协调（脚部拖影）。
- **I5**：动画播放速率固定，没有按实际速度缩放 → 滑步。
- **修复假设**：步行 3.0 m/s、按住 Shift 冲刺 5.5 m/s；`runThreshold = 4.0`；按 `speed / 参考速度` 缩放剪辑速率。验证：录像中脚落地点是否相对地面静止。

### Q4 悬空的石头从哪来？

- **O9**（E13）：60 块石头 y 全为 0，而乱纪元地面是起伏网格。
- **O10**（E07 第 3 帧）：天际线处多块石头悬空。
- **I6**：布局脚本按平地放置，Unity 里没有做落地。
- **修复假设**：SceneBuilder 对小道具、NPC、石碑做向下射线贴地（`Physics.Raycast` 自 +50 m）。验证：编辑态截图对照。

### Q5 画面为什么"像灰盒"？

- **O11**（E07）：三个场景地面均为单色，无贴图；天空为纯色；高台/营房是纯色方块；乱纪元地面棋盘格明显。
- **I7**：A 类资产（Tripo）质量尚可，B 类（Blender 平涂）和环境（天空、地面、远景）没有做细节层级，是"灰盒"感的主因。
- **修复假设**（分批）：
  - 第一批：程序化天空（`Skybox/Procedural`，按场景设日色）、按场景调雾；地面叠加程序化噪声贴图（红岸：冻土 + 枯草；乱纪元：龟裂泥地；三体世界：石板）。
  - 第二批：替换 B 类方块（营房、高台）为 Tripo 资产或加细节（窗、门、栏杆）。
- 验证：盲审截图对照锚点图（`《三体》视觉锚点图`）。

### Q6 NPC 的站位与面向

- **O12**（E14）：三位 NPC 统一 yaw=20°，而玩家从 −Z 方向上坡接近。
- **修复假设**：`NpcLookAt` —— 玩家进入 8 m 时头/身体平滑转向玩家；平时回到预设朝向。验证：新录像三体世界段。

### Q7（未取证，列入清单）

- 音频：脚步声、环境声缺失（U3）。
- 交互反馈：进入线索半径无提示音/高亮（U4）。
- UI：字幕无说话人名字（U5）。
- **取证（E20，代码审读）**：`Clue.Trigger` 只放旁白音频（Resources/VO 已有 9 条）与 4 s 固定字幕；靠近时已有自发光脉冲与"按 E 查看"提示，但无声音；`SubtitleUI` 不区分说话人。
- **修复（第一批）**：`Clue.speaker` 由 `SceneBuilder` 按 NPC 显示名注入（叶文洁 / 跟随者 / 冯·诺依曼 / 牛顿 / 秦始皇），字幕显示为"说话人：台词"；字幕时长 = 1.5 s + 0.28 s/字（4–9 s），对话近景与说话口型同步该时长；`Sfx` 运行时合成两段短音（确认音 660→990 Hz，靠近提示 880 Hz），不增加 WebGL 体积。
- 未结：脚步声、环境声（风 / 阵列翻旗声）—— 需音频资源或程序化合成，列入 v0.3。

## 3. 重建蓝图（观察到的行为 vs 设计选择）

| 模块 | 观察到的现状 | 设计选择（v0.2） | 依据 |
|---|---|---|---|
| 角色朝向 | 原判"背着跑"系误读，+90° 正确 | 保留 +90°；新增脸部特写核验 | Q1 |
| 脸 | 4/6 角色无五官，叶文洁紫脸 | 几何五官薄片 + 可见性切换表情；UV 掩膜修肤色 | Q2 |
| 镜头 | 6 m / 15° | 4.2 m / 10°，对话近景 | Q2 |
| 移动 | 2.6 m/s 单速 | 3.0 走 / 5.5 冲刺，动画速率匹配 | Q3 |
| 道具落地 | y=0 | 射线贴地 | Q4 |
| 天空/地面 | 纯色 | 程序化天空 + 噪声贴图 | Q5 |
| NPC | 固定朝向 | 注视玩家 | Q6 |

## 4. 路线图

- v0.2（本轮）：Q1、Q3、Q4、Q6 + Q5 第一批 + Q2 的镜头与贴图五官/表情 → 重录对照。
- v0.3：Q5 第二批（B 类资产替换）、Q7 音频与交互反馈、字幕说话人。
- v1.0：剧情补全（红岸发射、脱水/浸泡、人列计算机运行），移动端/校园网性能验证。

## 5. 清单回看（随修复更新）

| 问题 | 状态 | 已落地的改动 |
|---|---|---|
| Q1 | 已核验（E17/E18）：原 +90° 正确，−90° 误改已回退 | `PlayCaptureRunner.FaceShot` 脸部特写核验 |
| Q2 | 已答；Blender 与真机（E18）核验通过，表情触发待录像复核 | `face_patches.py`、`face_skin_fix.py`、`FaceExpression.cs`、`FollowCamera` 近景、`Clue` 触发 |
| Q3 | 已答，待真机核验 | `ThirdPersonController` 2.0/4.5 m/s + Shift；`CharacterAnimator` 阈值 3.3、速率缩放 |
| Q4 | 已答，待真机核验 | `SceneBuilder` 射线贴地 |
| Q5 | 第一、二批已真机核验（E21）；第三批（方块建筑替换、远景）未开始 | `Skybox/Procedural`；`scripts/ground_textures.py` + `SceneBuilder.ApplyGroundTexture`（cliff 用世界 XZ 平面 UV） |
| Q6 | 已答，待真机核验 | `NpcLookAt.cs` |
| Q7 | 第一批已实现，待录像核验 | `Clue.speaker`（字幕"说话人："）、字幕时长随字数、`Sfx` 运行时合成确认音/靠近提示音 |

核验入口：Mac 上 `bash scripts/mac_verify.sh` → `~/santi_review.zip`（每场景 3 个时刻的全景 + 正面脸部特写）。
