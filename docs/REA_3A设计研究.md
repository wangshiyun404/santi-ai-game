# 《三体：三体游戏》REA × 3A 设计研究（v0.3 行动稿）

> 目的：回应"去领悟 REA 的精髓，去市面上看别人的游戏，尤其是 3A 大作：他们的审美、视图、动画、故事线设计，还有用户的交互"。
> 方法：按 REA 的工作方式——先拆解对象（观察 → 证据 → 推断 → 未知），再重建（可核验的具体改动）。所有结论都附核验手段；"看起来差不多"不算过。
> 非官方同人改编，教学/研究用途，原著 © 刘慈欣。

---

## 0. REA 的精髓是什么（我们如何落实）

REA（Reverse Engineer Anything，morluto/rea，MIT）的核心不是"工具多"，而是一套工作纪律：分析在本地跑；结论必须**附证据和局限**；明确区分"静态推断"和"运行时观察"；把观察到的行为**兼容地重建**到自己的技术栈里（[morluto/rea README](https://github.com/morluto/rea/)、[REA 文档：静态推断 vs 运行时观察](https://github.com/IronSuit/rea---reverse-engineer-anything/blob/main/README.md)）。REA 的 Evidence 记录甚至会写下"完整性矛盾"（integrity contradictions），即工具看到的字节和预期不一致时不掩盖、照实记录（[REA mcp-contracts](https://github.com/armanatwork/rea-reverse-engineering-anything-/blob/main/docs/mcp-contracts.md)）。

本项目对应的四条铁律（写进 `REA_逆向台账.md` 并执行）：

| REA 原则 | 本项目落实 | 本轮教训 |
|---|---|---|
| 结论必须有证据 | 每条结论挂 E 编号的渲染图/日志/量化输出 | "脸朝前"（E18）被我当成"步态正确"的证据——**证据回答的问题和结论不是同一个问题** |
| 区分静态推断与运行时观察 | Blender 量化（静态）+ Unity `PlayCapture` 真机截图（运行时）双轨 | 只看低清录像、只看编辑器都判错过；现在每个角色改动都要两轨 PASS |
| 记录局限与矛盾 | 台账 U 条目；失败实验保留（`scripts/experiments/`） | 骨架镜像实验数学上成立、视觉失败，保留作反证 |
| 兼容重建而非照搬 | 3A 的"手段"按本项目的低多边形预算和 WebGL 性能翻译 | 下文每条都给"我们怎么做"，不照抄 |

---

## 1. 视图（Camera）

### 3A 在做什么

Journey 的镜头设计师 John Nesky 在 GDC 的《50 Game Camera Mistakes》里把动态第三人称镜头称为最难设计的一类，并给出可操作的规则：镜头应**围绕角色公转**而不是原地转头；必须**尊重玩家意图**（玩家推镜头就必须转过去）；用"胡须"射线预判遮挡并提前避让；俯仰角改变时**距离与视场要联动**，否则物体会怪异地胀缩；跑动时按移动方向自动修正偏航，让玩家看得见要去的地方；避免急转和晃动引发眩晕（[Video Highlight 摘要](https://videohighlight.com/v/C7307qRmlMI)、[VICE 对该演讲的引述](https://www.vice.com/en/article/lights-camera-distraction-the-problem-with-virtual-camera-systems/)）。他的总括是"镜头在失败时最显眼"（[Game Developer](https://www.gamedeveloper.com/design/video-50-common-game-camera-mistakes----and-how-to-fix-them)）。

### 我们现状（观察）

- `FollowCamera`：固定 4.2 m / 俯角 10° / 高 1.9 m，对话时拉到越肩近景；没有遮挡避让、没有移动方向自动偏航、没有俯仰—距离联动。
- 三个场景都是开阔地，遮挡问题轻；但乱纪元的岩石、红岸的营房已经出现过镜头穿墙（第 6 轮盲审）。

### v0.3 行动（可核验）

| # | 改动 | 核验 |
|---|---|---|
| C1 | 镜头避让：从角色头部向镜头位置做球形扫掠（半径 0.3 m），命中即把镜头拉近到命中点；拉近/拉远用不同阻尼（拉近快、拉远慢） | `PlayCapture` 在岩石旁加一个固定机位截图，不得出现穿墙 |
| C2 | 跑动自动偏航：玩家持续前进 >1.5 s 时，镜头偏航以 ≤40°/s 缓慢对齐移动方向；玩家一碰鼠标立即停止自动修正（尊重意图） | 自动演示录像里转弯后 2 s 内角色应回到画面中心线 |
| C3 | 俯仰联动：俯角 10° → 25° 时距离 4.2 → 5.0 m、FOV 55 → 60，一条曲线驱动三者 | 三个俯角各截一帧，角色在画面中高度应一致（±5%） |
| C4 | 事件镜头：三日凌空时镜头缓慢抬头看天（不是硬切），红岸发射时镜头缓慢后拉看天线 | 录像里镜头角速度 <30°/s |

---

## 2. 动画（Animation）

### 3A 在做什么

- **脚不滑**是第一标准：脚滑来自位移速度与动画步幅速度不匹配，解法是按动画实测步幅设定移动速度（或按速度缩放播放率）、用按真实速度标定的 Blend Tree、再用脚部 IK 把着地脚钉在地上（[MoCap Online](https://mocaponline.com/blogs/mocap-news/animation-debugging-troubleshooting)、[Bugnet](https://bugnet.io/blog/how-to-fix-animation-foot-sliding)）。
- Unity 官方要求混合的剪辑**相位对齐**：左脚着地在归一化时间 0.0，右脚在 0.5，否则混合时出现"月球漫步"（[Unity Blend Tree 手册](https://docs.unity3d.com/6000.6/Documentation/Manual/class-BlendTree.html)、[gamestack 动画指南的反模式表](https://github.com/rondorkerin/gamestack/blob/main/plugins/gamestack/skills/animation-systems/GUIDE.md)）。
- 原地转身要有重心转移和踏步，否则就是"坦克转向"；工业做法是按偏航差触发转身剪辑、用脚部锁定防止冰面滑步（[salivity：Turn-in-Place](https://salivity.github.io/game-development/article/designing-responsive-turn-in-place-animations)）。
- 一个可量化门槛：着地脚速度 <0.1 m/s 即视为不滑（[scenario-labs Godot 动画技能的基线表](https://github.com/scenario-labs/skills/blob/main/skills/game-engines/godot/scenario-godot-animation/SKILL.md)）。

### 我们现状（观察）

- 主角此前"倒着跑"的根因已查明并修复（台账 E23）：Tripo 生成的网格本身脚尖朝后，自动绑骨跟着脚判前向；脖子以下整体镜像后重新绑骨/重定向，`scripts/gait_check.py` 三剪辑 PASS。
- `CharacterAnimator` 是 idle/walk/run 三态直切（有 crossfade），无 Blend Tree、无脚 IK、无转身、无起步/停步。
- 移动速度（walk 2.2 / run 4.5 m/s）是拍脑袋值，没有按动画实测步幅标定。
- 所有角色共用 Tripo 的通用 walk/run，没有个性（叶文洁和士兵走路一样）。

### v0.3 行动（可核验）

| # | 改动 | 核验 |
|---|---|---|
| A1 | **步幅标定**：用 `gait_check.py` 扩展输出每剪辑"着地脚相对根的位移 × 帧率" = 动画隐含地速；把 `ThirdPersonController` 的 walk/run 速度改成这两个数 | 真机侧视连续 8 帧（新 `GaitShot` 序列），着地脚脚尖世界坐标漂移 <0.1 m/s |
| A2 | 1D Blend Tree（Speed）替代三态直切；walk/run 相位对齐（用 `gait_check.py` 找左脚着地帧，必要时在 bpy 里循环平移关键帧） | 混合中段（Speed=3.3）侧视截图无双脚同时离地/同时着地 |
| A3 | 简易脚 IK：Animator `OnAnimatorIK` 每脚向下射线，着地相位（由 A1 导出的相位曲线）权重 1，摆动相位 0 | 斜坡上截图脚底与地面间隙 <2 cm |
| A4 | 转身：偏航差 >60° 且无前进输入时播 Tripo 预设里的 turn 剪辑（若无则用 walk 前 6 帧 + 根旋转） | 原地按 A/D 时截图序列有踏步 |
| A5 | 起步/停步各 0.15 s 的身体前倾/后仰（程序化：根据加速度给脊柱 ±6°） | 录像里起跑第一步不是瞬间全速 |

---

## 3. 审美：光照、调色、尺度（Look）

### 3A 在做什么

Naughty Dog 在 GDC 2017 讲 Uncharted 4 环境制作时的流程是概念 → 分块 → 道具 → 光照 → 打磨，叙事空间先用灰模验证"读得懂"，再做材质与光（[GDC：Cinematic Environment Production for Uncharted 4](https://www.youtube.com/watch?v=bEIX-EQNZuQ)）。换言之，**光和色是最后一道、但预算最大的一道**，而且每个空间都有一个"要被读懂的句子"。

### 我们现状（观察）

- 三个场景已有不同天色（红岸深蓝黄昏、乱纪元白昼巨日、人列计算机金秋），但没有后处理：无 Bloom、无颜色分级、无体积光、无雾深度分层。
- 远景是单色块建筑，近景低多边形 Tripo 资产，二者风格断层（第 7 轮看板已指出）。
- 角色与建筑尺度：PRD 要求人物不超过画面 1/10，营造渺小；但镜头拉近到 4.2 m 后这条支柱已被削弱，需要用"远景巨物"补回来。

### v0.3 行动（可核验）

| # | 改动 | 核验 |
|---|---|---|
| L1 | URP Volume：每场景一套 Color Adjustments + Bloom + Vignette；乱纪元偏白热高对比、人列计算机偏暖黄低饱和、红岸偏青蓝高对比 | 三张同构图截图，直方图主峰分离；WebGL 帧率 ≥50 fps（Mac Safari） |
| L2 | 距离雾 + 高度雾：远景建筑融进雾里，掩盖"色块"；雾色取自天色 | 远景色块与天空的边缘对比度下降（截图量化） |
| L3 | 三日凌空：三个太阳用 Bloom 阈值分级，地面投影三重影子（三个方向光 Shadow） | 事件帧截图可见三重影 |
| L4 | 远景巨物：乱纪元金字塔、人列计算机的方阵边界、红岸天线各放大 1.5–2 倍并降低细节，恢复"人很小"的支柱 | 默认机位截图角色高度 ≤ 画面 1/8 |
| L5 | 用 Tripo 替换 4 栋最靠近玩家路径的色块建筑（约 40 积分/栋，余额约 465） | 第 8 轮看板对比 |

---

## 4. 故事线与节奏（Narrative pacing）

### 3A 在做什么

叙事驱动的 3A 普遍采用"张弛循环"：探索（低张力、让玩家自己看）→ 触发（线索/对话）→ 事件（高张力、短、镜头接管）→ 回落（给一句台词或一个空镜让玩家消化）。Uncharted 4 的环境制作就是围绕"每个空间讲一句话"组织的（[GDC 2017](https://www.youtube.com/watch?v=bEIX-EQNZuQ)）。Journey 则靠极少的 UI 和持续的视觉目标（远山）牵引。

### 我们现状（观察）

- 结构是"收集 N 条线索 → 事件 → 换场景"，三个场景同构，第二次就能预测。
- 事件（脱水、三日凌空、不要回答）都有，但事件之前没有**预兆**（乱纪元前的温度变化、三日凌空前的影子变化），事件之后没有**回落**（直接切场景）。
- 旁白全部用原著原句是优点，但线索顺序与原著章节节奏没有对应。

### v0.3 行动（可核验）

| # | 改动 | 核验 |
|---|---|---|
| N1 | 每个场景加一个**预兆**：乱纪元第 2 条线索后太阳开始缓慢变大、地面色温升高 60 s；人列计算机第 2 条线索后远处方阵开始同步翻牌；红岸尾声进门前风声渐起 | 录像时间轴上可标出预兆起点 |
| N2 | 每个事件后 8 s **回落**：镜头静止空镜 + 一句原著短句字幕，再淡出 | 时间轴：事件结束→切场之间 ≥8 s |
| N3 | 线索顺序锁定一条"原著阅读线"：同一场景的线索按原著出现顺序解锁（第 1 条触发后第 2 条才发光），玩家仍可自由走 | 线索 JSON 加 `order` 字段，`ClueManager` 校验 |
| N4 | 结局分支的后果可见：红岸尾声"回答/不回答"后，天线灯光与天色给出两种不同的 10 s 画面，而不是只换字幕 | 两种结局各一张截图 |

---

## 5. 用户交互与引导（UX / Onboarding）

### 3A 在做什么

Nesky 的规则同样适用于交互：**尊重意图**、不要替玩家做他没要求的事、失败要有可见的恢复路径（[gamedesign.gg 对该演讲的要点](https://gamedesign.gg/watch/camera-mistakes/)）。3A 的教学普遍"做中学"：第一个任务就是目标动作本身，提示只在玩家停滞时出现。

### 我们现状（观察）

- 用户的原话是"这个游戏我不会玩"，我们补了用户指南和视频，但**游戏内**引导仍然是开场一段字幕。
- 线索物靠"发光"提示，远距离看不见；没有"下一步在哪"的空间引导。
- E 键交互没有范围反馈（走近了也不知道能不能按）。
- 乱纪元倒计时是数字，紧张感主要靠音效。

### v0.3 行动（可核验）

| # | 改动 | 核验 |
|---|---|---|
| U1 | 首 10 s 做中学：第一条线索就在出生点 6 m 正前方，字幕只说一句"靠近发光物，按 E"；之后不再出现操作提示，除非玩家 20 s 没有触发任何线索 | 新手录像：首次触发 ≤15 s |
| U2 | 交互可用性反馈：进入 2.5 m 范围时线索物增亮 + 屏幕底部出现"E"图标；离开即消失 | 截图对比有/无图标 |
| U3 | 空间引导：当前未触发的最近线索在屏幕边缘有一个淡淡的方向标（Journey 式，不是小地图），触发后消失 | 截图 |
| U4 | 倒计时改成**画面语言**：乱纪元倒计时同时让画面边缘发白（Vignette 反向）、心跳音加速 | 录像 |
| U5 | 暂停/重开/音量在 Esc 菜单里（现在没有） | 截图 |
| U6 | 移动端/触屏：WebGL 加虚拟摇杆与 E 按钮（校园网手机访问需求） | 手机 Safari 截图 |

---

## 6. 本轮已经落地的"REA 纪律"工具

| 工具 | 作用 | 何时必跑 |
|---|---|---|
| `scripts/gait_check.py <anim.glb> [+X]` | 每剪辑脚尖方向、着地脚滑移、前倾，三项与脸向一致才 PASS | 任何角色绑骨/重定向之后 |
| `scripts/tts_tone_check.py --expect 文本 --word 字 --tone 3` | faster-whisper 转写 + Praat F0 声调轮廓 | 任何新配音之后 |
| `PlayCaptureRunner.FaceShot / GaitShot` | Unity 真机正面脸部特写 + 行走侧视 | 每次 `mac_verify.sh` |
| `scripts/mirror_body_glb.py` | 网格局部镜像修复（本轮修"脚反装"） | Tripo 生成资产前后不一致时 |
| `docs/REA_逆向台账.md` | O/E/I/U 四类条目 + 失败实验 | 每轮 |

---

## 7. v0.3 优先级与预算

按"用户一眼能看出来"排序：

1. **A1–A3**（脚不滑、混合、脚 IK）——动画是用户两次批评的焦点，先把地面接触做对。
2. **U1–U3**（做中学、交互反馈、方向标）——用户说"不会玩"，游戏内要自解释。
3. **L1–L2、L4**（调色、雾、巨物）——性价比最高的观感提升，不花 Tripo 积分。
4. **C1–C3**（镜头避让、自动偏航、俯仰联动）。
5. **N1–N2**（预兆与回落）——改脚本不改资产。
6. **L5、N4、U6**——需要 Tripo 积分或新资产，最后做。

每一条完成后在台账里新增 E 条目；没有证据的不算完成。
