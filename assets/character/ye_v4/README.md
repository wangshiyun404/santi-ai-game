# 叶文洁 v4：锚点脸投射 + 表情系统（E36）

- `ye_wenjie_face_v1.fbx` — MakeHuman/MPFB2 标准拓扑，mixamo_unity 64 骨（Unity Humanoid 可自动映射），75 个形态键（ARKit 52 面部单元 `!ex-*` + 微软 22 口型），贴图内嵌。51k 三角面。
- `ye_face_projected_diffuse.png` — 由 `assets/anchors/ye_v3/ye_head_turnaround.png` 三视图投射合成的身体 diffuse（2048）。
- `suit_olive_v2.png` — male_casualsuit05 改色（橄榄绿外套 + 米白衬衫，去条纹领带）。
- `long01_black.png` — long01 发片黑发贴图（临时，待换双辫）。
- `anchor_cams.json` — 三视图锚点相机（PnP 解），用于同机位对照渲染。

生成流程见 `tools/character/faceproj/`（`run_all.sh` → `09_finalize.py` → `10_sheets.py`），说明见《REA × 3A 设计研究》8.8。
素材许可：MakeHuman 资产 CC0（https://static.makehumancommunity.org/about/license.html）；本项目为非官方同人改编，原著 © 刘慈欣。
