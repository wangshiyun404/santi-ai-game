"""在 build_assets.py 生成的布局基础上，接入 Tripo 资产：修正原点、替换占位角色、添加新道具。运行后同步到 Unity。"""
import json, os, random, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import coords
random.seed(7)
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
L = os.path.join(ROOT, "layouts"); U = os.path.join(ROOT, "unity", "SanTiGame", "Assets", "StreamingAssets", "layouts")

def load(n): return json.load(open(os.path.join(L, n + ".json"), encoding="utf-8"))
def save(n, d):
    json.dump(d, open(os.path.join(L, n + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    shutil.copy(os.path.join(L, n + ".json"), os.path.join(U, n + ".json"))
def obj(asset, name, bpos, rz=0.0, scale=1.0, **kw):
    """以 Blender 坐标 (x, y, z) 与绕 Z 朝向角 rz（度，0 = 模型正面朝 -Y）定义，统一换算到 Unity。"""
    return {"asset": asset, "name": name, "position": coords.blender_pos_to_unity(bpos),
            "rotation": [0.0, coords.yaw_to_unity(rz), 0.0], "scale": [scale, scale, scale], "static": kw.pop("static", True), **kw}
def ryaw(): return random.uniform(0, 360)
def face_north(d):
    """玩家出生点面朝 Blender +Y（场景主体方向）"""
    for o in d["objects"]:
        if o.get("role") == "player_spawn": o["rotation"] = [0.0, coords.yaw_to_unity(180), 0.0]

# ---- 红岸 ----
d = load("scene_00_red_coast")
for o in d["objects"]:
    if o["asset"] == "dish_tower": o["position"][1] = 0; o["rotation"] = [0, 0, 0]
    if o["name"] == "Barracks_0": o.pop("clue", None)
d["objects"] += [
    obj("control_console", "ControlConsole", (-30, -11.5, 0), 0, clue="clue_control_room"),   # 营房 0 门前，面朝南（玩家来向）
    obj("jeep", "Jeep", (12, -34, 0), 25),
    obj("char_ye_wenjie", "YeWenjie", (-28.5, -13.5, 0), 180, static=False, role="npc"),      # 背对玩家，面向主控台
]
face_north(d); save("scene_00_red_coast", d)

# ---- 乱纪元 ----
d = load("scene_01_chaotic")
for o in d["objects"]:
    if o["asset"] == "pyramid": o["position"][1] = 0
    if o["asset"] == "dehydrated_roll": o["position"][1] = 0; o["rotation"] = [0, ryaw(), 0]
rolls_extra = [obj("dehydrated_roll", f"DehydratedRoll_x{i:02d}", (random.uniform(-80, 80), random.uniform(5, 160), 0), ryaw()) for i in range(26)]
rocks = [obj("rock_small", f"Rock_{i:02d}", (random.uniform(-120, 120), random.uniform(0, 220), 0), ryaw(), random.uniform(0.4, 1.6)) for i in range(60)]
d["objects"] += rolls_extra + rocks + [
    obj("bamboo_slips", "BambooSlips", (38, 160, 0), 30, clue="clue_slips"),            # 金字塔门前
    obj("char_follower", "Follower", (44, 162, 0), 20, static=False, role="npc"),       # 面朝南迎向玩家
]
d["clues"].append({"id": "clue_slips", "subtitle": "周文王的卦象，预测不了乱纪元。", "narration": ""})
face_north(d); save("scene_01_chaotic", d)

# ---- 人列计算机 ----
d = load("scene_02_computer")
for o in d["objects"]:
    if o["name"] == "VonNeumann": o["asset"] = "char_von_neumann"
    if o["name"] == "QinShiHuang": o["asset"] = "char_qin"
    if o["name"] == "Newton": o["asset"] = "char_follower"   # 暂代，待生成牛顿
    if o.get("role") == "npc": o["rotation"] = [0, coords.yaw_to_unity(-20), 0]   # 面朝南（玩家从 -Y 侧上台）
d["objects"] += [
    obj("sand_table", "SandTable", (-150, 24, 10), 0),
    obj("bronze_sword", "BronzeSword", (-146, 21, 10), 60, clue="clue_sword"),
]
d["clues"].append({"id": "clue_sword", "subtitle": "朕的三千万大军，就是这台计算机。", "narration": ""})
face_north(d); save("scene_02_computer", d)
print("layouts patched")
