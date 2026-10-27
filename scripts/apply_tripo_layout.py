"""在 build_assets.py 生成的布局基础上，接入 Tripo 资产：修正原点、替换占位角色、添加新道具。运行后同步到 Unity。"""
import json, os, random, shutil
random.seed(7)
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
L = os.path.join(ROOT, "layouts"); U = os.path.join(ROOT, "unity", "SanTiGame", "Assets", "StreamingAssets", "layouts")

def load(n): return json.load(open(os.path.join(L, n + ".json"), encoding="utf-8"))
def save(n, d):
    json.dump(d, open(os.path.join(L, n + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    shutil.copy(os.path.join(L, n + ".json"), os.path.join(U, n + ".json"))
def obj(asset, name, pos, rot=(0, 0, 0), scale=(1, 1, 1), **kw):
    return {"asset": asset, "name": name, "position": list(pos), "rotation": list(rot), "scale": list(scale), "static": kw.pop("static", True), **kw}

# ---- 红岸 ----
d = load("scene_00_red_coast")
for o in d["objects"]:
    if o["asset"] == "dish_tower": o["position"][1] = 0; o["rotation"] = [0, 0, 0]
    if o["name"] == "Barracks_0": o.pop("clue", None)
d["objects"] += [
    obj("control_console", "ControlConsole", (-30, 0, -11.5), (0, 180, 0), clue="clue_control_room"),
    obj("jeep", "Jeep", (12, 0, -34), (0, 25, 0)),
    obj("char_ye_wenjie", "YeWenjie", (-28.5, 0, -13.5), (0, 180, 0), static=False, role="npc"),
]
save("scene_00_red_coast", d)

# ---- 乱纪元 ----
d = load("scene_01_chaotic")
for o in d["objects"]:
    if o["asset"] == "pyramid": o["position"][1] = 0
    if o["asset"] == "dehydrated_roll": o["position"][1] = 0; o["rotation"] = [0, random.uniform(0, 360), 0]
rolls_extra = [obj("dehydrated_roll", f"DehydratedRoll_x{i:02d}", (random.uniform(-80, 80), 0, random.uniform(5, 160)), (0, random.uniform(0, 360), 0)) for i in range(26)]
rocks = [obj("rock_small", f"Rock_{i:02d}", (random.uniform(-120, 120), 0, random.uniform(0, 220)), (0, random.uniform(0, 360), 0), (random.uniform(0.4, 1.6),) * 3) for i in range(60)]
d["objects"] += rolls_extra + rocks + [
    obj("bamboo_slips", "BambooSlips", (38, 0, 160), (0, 30, 0), clue="clue_slips"),
    obj("char_follower", "Follower", (44, 0, 162), (0, 200, 0), static=False, role="npc"),
]
d["clues"].append({"id": "clue_slips", "subtitle": "周文王的卦象，预测不了乱纪元。", "narration": ""})
save("scene_01_chaotic", d)

# ---- 人列计算机 ----
d = load("scene_02_computer")
for o in d["objects"]:
    if o["name"] == "VonNeumann": o["asset"] = "char_von_neumann"
    if o["name"] == "QinShiHuang": o["asset"] = "char_qin"
    if o["name"] == "Newton": o["asset"] = "char_follower"   # 暂代，待生成牛顿
    if o.get("role") == "npc": o["rotation"] = [0, 20, 0]
d["objects"] += [
    obj("sand_table", "SandTable", (-150, 10, 24), (0, 0, 0)),
    obj("bronze_sword", "BronzeSword", (-146, 10, 21), (0, 60, 0), clue="clue_sword"),
]
d["clues"].append({"id": "clue_sword", "subtitle": "朕的三千万大军，就是这台计算机。", "narration": ""})
save("scene_02_computer", d)
print("layouts patched")
