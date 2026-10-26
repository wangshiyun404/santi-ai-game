# A 类资产 · Tripo 生成清单与提示词

> 规则（照搬 Sac）：道具用 **Tripo H3.1**（高精度、保留硬表面细节）；角色用 **Smart Mesh P2.0**（可控面数、四边面拓扑，便于 Auto-Rig Pro 绑骨）。
> 所有模型：低多边形风格、纯色材质、无贴图文字。生成后在 Blender 中统一到 1 unit = 1 m、Y-up 导出 GLB，用相同文件名覆盖 `unity/SanTiGame/Assets/Models/`。
> 每个资产先用对应锚点图（concept/）做图生 3D；若 Tripo 对多视角支持好，把参考图裁出局部作为输入。

## 道具（H3.1）

| 文件名 | 场景 | 提示词 | 目标面数 | 尺寸（m） |
|---|---|---|---|---|
| `dish_tower.glb` | 红岸 | Low-poly stylized giant parabolic radar dish antenna on a cylindrical concrete tower with a railing deck, 1970s military radio telescope, faceted flat-shaded surfaces, muted grey and steel colors | 8k | 高 40，碟直径 28 |
| `control_console.glb` | 红岸 | Low-poly 1970s military control console desk with rows of toggle switches, round analog gauges, one large red transmit button under a cover, olive green metal panels, flat shading | 4k | 2.4 × 0.9 × 1.3 |
| `jeep.glb` | 红岸 | Low-poly 1970s Chinese military jeep BJ212, olive green, canvas top, faceted, flat shading | 3k | 3.8 × 1.7 × 1.9 |
| `pyramid.glb` | 乱纪元 | Low-poly ancient stone pyramid with a single dark doorway at the base and worn faceted stone blocks, sand-grey | 2k | 底 40，高 28 |
| `dehydrated_roll.glb` | 乱纪元 | Low-poly dehydrated human body rolled up like a dried parchment scroll, wrinkled faceted leather texture, pale tan color, lying flat | 2k | 1.7 × 0.5 × 0.45 |
| `bamboo_slips.glb` | 乱纪元 | Low-poly ancient Chinese bamboo slip scroll partially unrolled, bound with dark cord, faceted | 1.5k | 0.6 × 0.3 × 0.05 |
| `sand_table.glb` | 人列计算机 | Low-poly ancient military sand table on a wooden stand showing a miniature grid formation of soldiers carved in relief, flat shading | 3k | 2.0 × 1.2 × 1.0 |
| `bronze_sword.glb` | 人列计算机 | Low-poly Qin dynasty bronze sword with a long straight blade and a simple hilt, faceted, dark bronze | 800 | 长 0.9 |
| `platform.glb` | 人列计算机 | Low-poly massive rammed-earth viewing platform with wide stone stairs on one side and a flat top with a low parapet, grey-brown | 3k | 24 × 16 × 10 |

## 角色（Smart Mesh P2.0，T-Pose 四视图输入 concept/04_character_tpose.png）

| 文件名 | 角色 | 提示词 | 面数 | 绑骨 |
|---|---|---|---|---|
| `char_player.glb` | 玩家（斗篷人） | Low-poly stylized adult human in T-pose wearing a long tattered desert cloak with hood down, wrapped boots, faceted flat-shaded, simple faceless head planes, quad topology | ≤ 8k | Auto-Rig Pro → Mixamo idle / walk / look around / reach |
| `char_ye_wenjie.glb` | 叶文洁 | Low-poly stylized young woman in T-pose, 1970s thick padded military-green cotton coat, fur hat, faceted, faceless | ≤ 8k | idle / walk / press_button（IK 微调手接触按键） |
| `char_follower.glb` | 追随者 / 周文王 | Low-poly stylized elderly man in T-pose wearing ancient Chinese robe and tall hat, long beard as a faceted block, faceless | ≤ 6k | idle / kneel |
| `char_von_neumann.glb` | 冯·诺依曼 | Low-poly stylized man in T-pose in a dark 1940s suit, round glasses as simple geometry, faceless | ≤ 6k | idle / point |
| `char_qin.glb` | 秦始皇 | Low-poly stylized emperor in T-pose, black and gold ceremonial robe, flat-top crown with hanging beads as simple rods, faceless | ≤ 6k | idle |
| `soldier_black.glb` / `soldier_white.glb` | 士兵基准 | Low-poly ancient Qin soldier standing at attention holding a flagpole upright with a square black (white) flag, armor as simple faceted plates, extremely low poly | ≤ 600 | 不绑骨（GPU 实例化） |

## IK 微调提示词（Blender Agent，仿 Sac）

> 请参考提供的 Mixamo "Button Pushing" 动作，保留其中适用的部分，并使用 Auto-Rig Pro 的手臂 IK 控制器调整右手姿势，使指尖准确接触主控台上的红色发射键表面，按下过程中手腕保持自然、手肘不穿过桌面，按下后停顿 0.5 秒再收回。避免穿模、手指悬空或与按键脱离。

## 质检（盲审 Agent）

> 你是审片人。对比 Tripo 导出的 `<asset>.glb` 在 Blender 三视图中的截图与 concept 参考图中的对应物件，列出：①轮廓与比例差异；②多余的细节或噪声几何；③法线/面数是否超标；④是否为四边面（角色）。按严重程度排序给出修改指令，不要自己动手修。
