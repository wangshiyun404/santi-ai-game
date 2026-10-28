# 《三体：三体游戏》AI 制作工程

逆向 Sac《小王子》管线（PRD → 视觉锚点 → Tripo 资产 → Blender 搭建 → Unity 打包）的《三体》低多边形 3D 剧情探索游戏。
非官方同人改编，教学/研究用途，原著 © 刘慈欣。

```
santi/
├── docs/PRD.md                 产品需求与关卡设计（第 1 天产出）
├── docs/tripo_prompts.md       A 类资产的 Tripo 提示词与参数
├── docs/tripo_manifest.json    Tripo 批量生成清单（16 项）
├── scripts/tripo_batch.py      Tripo 批量生成脚本（上传→建任务→轮询→下载 GLB）
├── scripts/tripo_rig.py        Tripo v3 绑骨 + 预设动画重定向
├── scripts/apply_tripo_layout.py  布局接入 Tripo 资产
├── audio/vo/                   旁白 TTS 源文件（txt + mp3）
├── concept/                    视觉锚点图（4 张，GPT Image 生成）
├── blender/build_assets.py     B 类几何体资产 + 场景布局 + 预览渲染脚本（bpy 5.0）
├── blender/render_layout.py    用 Unity GLB + layout 复现 Unity 场景的"虚拟 Game 视图"（round04）
├── scripts/coords.py           Blender ↔ Unity 坐标/欧拉角换算（glTFast 反转 X 轴）
├── assets/glb/                 12 个低多边形 GLB 资产（Y-up，1 unit = 1 m）
├── layouts/scene_*.json        三个场景的布局、光照、线索、事件数据
├── preview/                    Blender Cycles 预览（供盲审对照）
├── review/round01–04*.md       盲审记录（第 3 轮 Tripo 质检，第 4 轮 Unity 布局复现）
├── assets/tripo/               Tripo 原始 GLB、任务 id、绑骨/动画输出
└── unity/SanTiGame/            Unity 6.3 LTS 工程（URP + glTFast）
    ├── Assets/Scripts/Runtime  控制器、相机、线索、字幕、士兵实例化、纪元事件
    ├── Assets/Scripts/Editor   SceneBuilder：读 JSON 自动搭场景
    ├── Assets/Models/*.glb     资产（由 glTFast 导入为 Prefab）
    └── Assets/StreamingAssets/layouts/*.json
```

## 当前进度（第 3 天）

| 环节 | 状态 |
|---|---|
| PRD、关卡表、色板 | ✅ docs/PRD.md |
| 视觉锚点图（红岸、乱纪元、人列计算机、角色 T-Pose） | ✅ concept/ |
| 多视角参考图（三场景俯视图 + 红岸主控台特写） | ✅ concept/*b_*, 03c |
| B 类几何体资产（地形、金字塔、脱水卷、干湖床、士兵、高台、远山、天线塔、营房、窗光、围栏、旗杆、云海、落叶松、悬崖、太阳） | ✅ 18 个 GLB |
| 三个场景布局 JSON + 预览渲染 + 两轮盲审（review/round01–02） | ✅ 人列计算机 117 块方阵、36,512 名士兵，含中央核心块 |
| Unity 工程：第三人称控制、跟随相机、线索/字幕系统、3 万士兵 GPU 实例化、乱纪元日落、三日凌空、场景切换、SceneBuilder | ✅ 代码就绪，待在编辑器中首次运行 |
| A 类资产（Tripo）：16 项清单 docs/tripo_manifest.json + 批量脚本 scripts/tripo_batch.py | ✅ 16 件全部生成并通过第 3 轮盲审（4 件重做一次），已按真实尺寸归一化导入 Unity（review/round03_tripo.md） |
| 绑骨与动作（改用 Tripo v3 自动绑骨 + 预设动画，scripts/tripo_rig.py） | ✅ 玩家 idle/walk/run，4 名 NPC + 黑旗士兵 idle；Assets/Models/Anim/*.glb，CharacterAnimator 驱动 |
| 旁白音频（9 条，TTS，原著原句） | ✅ Assets/Resources/VO/*.wav |
| WebGL / macOS 打包 | ⏳ |

## 在 Mac 上跑起来（一次性准备）

1. **清磁盘**：当前剩余约 5.9 GB。Unity Hub + 编辑器 + WebGL 模块 + 工程 Library 约需 20 GB。
2. **装 Unity Hub**（unity.com/download），登录后安装 **Unity 6.3 LTS（6000.3.x）**，勾选模块：WebGL Build Support、Mac Build Support (IL2CPP)。
3. Hub → Add → 选择 `santi/unity/SanTiGame` 文件夹 → 打开。首次打开会自动拉取 URP 与 glTFast 包（需联网，国内可能较慢；若 glTFast 拉取失败，改用 Package Manager → Add from git URL：`https://github.com/atteneder/glTFast.git`）。
4. 若控制台报 `InvalidOperationException ... UnityEngine.Input`：Edit → Project Settings → Player → Other Settings → Active Input Handling 改为 **Both**。
5. URP：Edit → Project Settings → Graphics 若 Default Render Pipeline 为空，在 Assets 里右键 Create → Rendering → URP Asset (with Universal Renderer) 并拖入。
6. 菜单 **SanTi → Build All Scenes**。会生成 `Assets/Scenes/scene_00_red_coast.unity` 等三个场景并加入 Build Settings。
7. 打开 `scene_00_red_coast` 按 Play：WASD 走动、鼠标环顾、靠近发光物件按 E。

## Tripo 批量生成（API Key 已配置）

```bash
# 需在 Python 3.11 环境（/tmp/bpyenv）下运行；凭据由代理注入，不需要在命令里写 key
pplx credentials run <tripo-handle> -- /tmp/bpyenv/bin/python scripts/tripo_batch.py --balance
pplx credentials run <tripo-handle> -- /tmp/bpyenv/bin/python scripts/tripo_batch.py docs/tripo_manifest.json
pplx credentials run <tripo-handle> -- /tmp/bpyenv/bin/python scripts/tripo_batch.py docs/tripo_manifest.json --only dish_tower,char_player
```
生成结果落在 `assets/tripo/<name>.glb`，任务 id 记录在 `assets/tripo/tasks.json`。

## Tripo 资产进入 Unity 的流程（已跑通）

```bash
/tmp/bpyenv/bin/python blender/review_tripo.py          # 三视角渲染 → review/tripo/，人工/盲审
/tmp/bpyenv/bin/python blender/normalize_tripo.py       # 缩放到真实尺寸、原点归脚底、朝向 +Z → 覆盖 unity/.../Assets/Models/<name>.glb
python3 scripts/apply_tripo_layout.py                   # 布局接入：修正原点、NPC 换成角色模型、新增主控台/吉普/沙盘/青铜剑/竹简/碎石
pplx credentials run <tripo-v3-handle> -- /tmp/bpyenv/bin/python scripts/tripo_rig.py   # 绑骨 + 预设动画 → assets/tripo/anim/
cp assets/tripo/anim/<name>_anim.glb unity/SanTiGame/Assets/Models/Anim/<name>.glb
```

- `Assets/Models/<name>.glb`：静态资产，1 unit = 1 m，原点在底部中心，正面朝 +Z，SceneBuilder 直接按 layout 摆放。
- `Assets/Models/Anim/<name>.glb`：带骨骼与动画的角色，保持 Tripo 原始归一化（1 m 高、朝 −X），由 `SceneBuilder.InstantiateCharacter` 统一缩放到身高表并转向，再挂 `CharacterAnimator`（玩家按速度切 idle/walk/run，NPC 循环 idle）。
- 重新生成某件资产后只需同名覆盖，Unity 自动重新导入，场景引用不变。

## 迭代流程（Sac 的两个工程动作）

- **视觉锚点**：改任何场景前先改 `concept/` 里的参考图，而不是直接改 3D。
- **做查分离**：每次改完 `build_assets.py` 重跑 → 看 `preview/` → 在 `review/roundNN.md` 中记录差异与修改指令 → 再改。Unity 内同理：Game 视图截图对照参考图。

```bash
# 重新生成资产、布局与预览（需 bpy：uv venv -p 3.11 && uv pip install bpy）
cd santi/blender && python build_assets.py          # 全部
cd santi/blender && python build_assets.py 1        # 只重跑乱纪元
cp ../layouts/*.json ../unity/SanTiGame/Assets/StreamingAssets/layouts/
cp ../assets/glb/*.glb ../unity/SanTiGame/Assets/Models/
```

## 性能预算

- 桌面：士兵 density = 1.0（约 3 万实例），目标 60 fps。
- WebGL：SoldierFormation.density = 0.33，maxDrawDistance = 400，目标 30 fps。
- 所有静态物件勾选 Batching Static；材质纯色，不用贴图。
