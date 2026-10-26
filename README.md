# 《三体：三体游戏》AI 制作工程

逆向 Sac《小王子》管线（PRD → 视觉锚点 → Tripo 资产 → Blender 搭建 → Unity 打包）的《三体》低多边形 3D 剧情探索游戏。
非官方同人改编，教学/研究用途，原著 © 刘慈欣。

```
santi/
├── docs/PRD.md                 产品需求与关卡设计（第 1 天产出）
├── docs/tripo_prompts.md       A 类资产的 Tripo 提示词与参数
├── concept/                    视觉锚点图（4 张，GPT Image 生成）
├── blender/build_assets.py     B 类几何体资产 + 场景布局 + 预览渲染脚本（bpy 5.0）
├── assets/glb/                 12 个低多边形 GLB 资产（Y-up，1 unit = 1 m）
├── layouts/scene_*.json        三个场景的布局、光照、线索、事件数据
├── preview/                    Blender Cycles 预览（供盲审对照）
├── review/round01.md           盲审记录
└── unity/SanTiGame/            Unity 6.3 LTS 工程（URP + glTFast）
    ├── Assets/Scripts/Runtime  控制器、相机、线索、字幕、士兵实例化、纪元事件
    ├── Assets/Scripts/Editor   SceneBuilder：读 JSON 自动搭场景
    ├── Assets/Models/*.glb     资产（由 glTFast 导入为 Prefab）
    └── Assets/StreamingAssets/layouts/*.json
```

## 当前进度（第 1 天结束）

| 环节 | 状态 |
|---|---|
| PRD、关卡表、色板 | ✅ docs/PRD.md |
| 视觉锚点图（红岸、乱纪元、人列计算机、角色 T-Pose） | ✅ concept/ |
| B 类几何体资产（地形、金字塔、脱水卷、士兵、高台、天线塔、营房、落叶松、悬崖、太阳） | ✅ 12 个 GLB |
| 三个场景布局 JSON + 预览渲染 + 第 1 轮盲审 | ✅ |
| Unity 工程：第三人称控制、跟随相机、线索/字幕系统、3 万士兵 GPU 实例化、乱纪元日落、三日凌空、场景切换、SceneBuilder | ✅ 代码就绪，待在编辑器中首次运行 |
| A 类资产（Tripo）：抛物面天线、主控台、脱水人、竹简、沙盘、角色 | ⏳ 需在 Tripo 中生成（提示词见 docs/tripo_prompts.md） |
| 绑骨与动作（Auto-Rig Pro / Mixamo） | ⏳ |
| 旁白音频 | ⏳ 放入 Assets/Resources/VO/ |
| WebGL / macOS 打包 | ⏳ |

## 在 Mac 上跑起来（一次性准备）

1. **清磁盘**：当前剩余约 5.9 GB。Unity Hub + 编辑器 + WebGL 模块 + 工程 Library 约需 20 GB。
2. **装 Unity Hub**（unity.com/download），登录后安装 **Unity 6.3 LTS（6000.3.x）**，勾选模块：WebGL Build Support、Mac Build Support (IL2CPP)。
3. Hub → Add → 选择 `santi/unity/SanTiGame` 文件夹 → 打开。首次打开会自动拉取 URP 与 glTFast 包（需联网，国内可能较慢；若 glTFast 拉取失败，改用 Package Manager → Add from git URL：`https://github.com/atteneder/glTFast.git`）。
4. 若控制台报 `InvalidOperationException ... UnityEngine.Input`：Edit → Project Settings → Player → Other Settings → Active Input Handling 改为 **Both**。
5. URP：Edit → Project Settings → Graphics 若 Default Render Pipeline 为空，在 Assets 里右键 Create → Rendering → URP Asset (with Universal Renderer) 并拖入。
6. 菜单 **SanTi → Build All Scenes**。会生成 `Assets/Scenes/scene_00_red_coast.unity` 等三个场景并加入 Build Settings。
7. 打开 `scene_00_red_coast` 按 Play：WASD 走动、鼠标环顾、靠近发光物件按 E。

## 替换为 Tripo 资产的流程

1. 在 Tripo 中按 `docs/tripo_prompts.md` 生成模型（道具 H3.1，角色 Smart Mesh P2.0），导出 GLB。
2. 用 **相同文件名** 覆盖 `unity/SanTiGame/Assets/Models/<asset>.glb`（如 `dish_tower.glb`），Unity 会自动重新导入，场景中引用无需改动。
3. 若尺寸不对，在 Blender 中缩放到 1 unit = 1 m 再导出，或在 layout JSON 里改 `scale`。

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
