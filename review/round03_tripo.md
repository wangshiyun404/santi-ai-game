# 盲审记录 · 第 3 轮（Tripo A 类资产）

对照参考图：concept/04_character_tpose、03c_red_coast_console、各场景锚点 ｜ 被审对象：review/tripo/<name>_{0,1,2}.png（三视角渲染，由 blender/review_tripo.py 生成）

## 生成结果与质检
| 资产 | 模型版本 | 输入 | 第 1 次 | 问题 | 第 2 次 |
|---|---|---|---|---|---|
| dish_tower | H3.1 (v3.1-20260211) | 文本 | ✗ | 生成了整座红岸基地微缩景观，不是单体天线 | ✅ 单体浅碟 + 馈源支架 + 圆座 |
| control_console | H3.1 | 文本 | ✗ | 生成了一个人 | ✅ 军绿色主控台，红色按钮 |
| jeep / pyramid / dehydrated_roll / bamboo_slips / sand_table / bronze_sword / rock_small | H3.1 | 文本 | ✅ | — | — |
| char_player | P1 Smart Mesh | 4 视图 T-Pose 裁切（multiview_to_model） | ✗ | 单视图 → 4 个人并排 | ✅ 与设定图一致的斗篷 + 绑腿 + 短发，T-Pose |
| char_von_neumann | P1 | 文本 | ✗ | 半身像、无腿 | ✅ 全身西装、眼镜 |
| char_ye_wenjie / char_follower / char_qin / char_newton（补做） | P1 | 文本 | ✅ | — | — |
| soldier_black / soldier_white | P1 | 文本 | ✅（首发 429 并发限制，重试成功） | — | — |

规律：
- Tripo 输出统一归一化到最长边 1 m、全三角面、原点在包围盒中心；需要在 Blender 中按 docs/tripo_prompts.md 的目标尺寸缩放、原点归到脚底（blender/normalize_tripo.py）。
- 角色、车辆、主控台的正面统一朝 +X（Blender 坐标）；导出前绕 Z 转 −90° 使其朝 −Y，经 glTF（+Z 朝前）→ Unity glTFast（反转 X 轴）后正好面向 +Z。
- "一个物体" 类提示词必须显式排除场景："single object, isolated, no base, no ground"，否则 H3.1 倾向于生成微缩景观。
- 文本直出的人物容易半身或多人；关键角色用多视图输入（四视图 T-Pose）稳定得多。

## 绑骨与动作（Tripo v3 /animations）
| 角色 | rig-check | rig (v3.0-20260909, biped, mixamo 骨骼命名) | retarget（原地播放） |
|---|---|---|---|
| char_player | ✅ | ✅ 65 根骨骼 | idle / walk / run ✅ |
| char_ye_wenjie、char_follower、char_von_neumann、char_qin、soldier_black | ✅ | ✅ | idle ✅ |
| soldier_white | ✗ 不可绑骨（旗杆与身体连成一体） | — | 方阵中士兵本就是静态实例，不影响 |

输出 GLB 内含 Armature + 多段动画（glTFast 导入为 Legacy Animation，剪辑名 idle/walk/run），附带一个 Icosphere 辅助网格，SceneBuilder 实例化时删除。

## 积分
rock 测试 20 + 道具 180 + 角色 210 + 士兵 80 + 重做 130 + 绑骨 6×25 + 动画 8×10 = 850；补做牛顿 40 + 25 + 10 = 75；合计 925，余额 575 / 1500。

## 结论
A 类资产全部就位（16 件 + 6 件带动画角色）。待办：士兵旗帜独立成子物体以便绑骨、Unity 编辑器首次运行后的 Game 视图盲审。
