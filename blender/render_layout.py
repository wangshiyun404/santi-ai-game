"""
用 Unity 工程里的 GLB + layout JSON 在 Blender 中复现 Unity 场景（Unity 坐标经 scripts/coords.py 反算回 Blender），
从玩家出生点视角渲染，作为 Unity 首次运行前的"虚拟 Game 视图"盲审素材。
用法: python render_layout.py [scene_id ...]   输出 preview/unity_<scene>.png
"""
import bpy, json, math, os, sys
from mathutils import Vector, Euler
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "..", "scripts")); import coords
MODELS = os.path.join(ROOT, "..", "unity", "SanTiGame", "Assets", "Models")
LAYOUTS = os.path.join(ROOT, "..", "layouts")
OUT = os.path.join(ROOT, "..", "preview")

def hex2rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)) + (1.0,)

_cache = {}
def proto(asset):
    """导入一次，返回该资产的网格对象列表（隐藏的原型）。"""
    if asset in _cache: return _cache[asset]
    path = os.path.join(MODELS, asset + ".glb")
    if not os.path.exists(path): _cache[asset] = None; return None
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    for o in meshes:   # 展平父子层级：把世界矩阵烘焙到对象上，脱离空父物体
        mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    for o in new:
        if o.type != "MESH": bpy.data.objects.remove(o)
    col = bpy.data.collections.new("proto_" + asset); bpy.context.scene.collection.children.link(col)
    for o in meshes:
        for c in o.users_collection: c.objects.unlink(o)
        col.objects.link(o)
    col.hide_render = True; col.hide_viewport = True
    _cache[asset] = meshes
    return meshes

def place(asset, upos, urot, uscale, name):
    ps = proto(asset)
    if not ps: return None
    bpos = Vector(coords.unity_pos_to_blender(upos))
    brot = Euler(coords.unity_euler_to_blender(*urot), "XYZ")
    bscale = Vector((uscale[0], uscale[2], uscale[1]))
    out = []
    for p in ps:
        inst = p.copy(); inst.data = p.data; inst.name = f"{name}:{p.name}"
        inst.matrix_world = Matrix_TRS(bpos, brot, bscale) @ p.matrix_world
        bpy.context.scene.collection.objects.link(inst); out.append(inst)
    return out

from mathutils import Matrix
def Matrix_TRS(pos, rot, scale):
    return Matrix.Translation(pos) @ rot.to_matrix().to_4x4() @ Matrix.Diagonal((*scale, 1.0))

def build(scene_id, step=2, max_soldiers=12000):
    bpy.ops.wm.read_factory_settings(use_empty=True); _cache.clear()
    data = json.load(open(os.path.join(LAYOUTS, scene_id + ".json"), encoding="utf-8"))
    spawn = None
    for o in data["objects"]:
        if o.get("role") == "player_spawn": spawn = o; continue
        asset = o["asset"]
        if o.get("role") == "npc" and not os.path.exists(os.path.join(MODELS, asset + ".glb")): asset = "char_follower"
        place(asset, o["position"], o["rotation"], o["scale"], o["name"])
    # 玩家：静态 T-Pose 模型
    if spawn: place("char_player", spawn["position"], spawn["rotation"], [1, 1, 1], "Player")
    # 方阵（抽样）
    f = data.get("formation"); n = 0
    if f:
        for b in f["blocks"]:
            for c in range(0, b["cols"], step):
                for r in range(0, b["rows"], step):
                    if n >= max_soldiers: break
                    black = ((c + r) % 2 == 0) if b["pattern"] == "checker" else (r % 2 == 0) if b["pattern"] == "rows" else b["pattern"] == "black"
                    place(f["blackAsset"] if black else f["whiteAsset"], [b["origin"][0] + c * b["spacing"], 0, b["origin"][1] + r * b["spacing"]], [0, 0, 0], [1, 1, 1], f"S{n}"); n += 1
    # 光照
    L = data["lighting"]; a = L["sunAngle"]
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN")); bpy.context.scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(a[0]), math.radians(a[1]), math.radians(a[2])); sun.data.energy = L.get("intensity", 3) * 1.2
    if L.get("sunColor"): sun.data.color = hex2rgb(L["sunColor"])[:3]
    w = bpy.data.worlds.new("W"); bpy.context.scene.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = hex2rgb(L["ambient"]); w.node_tree.nodes["Background"].inputs[1].default_value = 0.8
    # 相机：出生点身后 6 m、高 2.5 m，沿朝向看
    sp = Vector(coords.unity_pos_to_blender(spawn["position"])) if spawn else Vector((0, 0, 0))
    rz = coords.unity_euler_to_blender(*spawn["rotation"])[2] if spawn else 0
    fwd = Vector((math.sin(rz), -math.cos(rz), 0))     # 模型 rz=0 时正面朝 -Y
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); bpy.context.scene.collection.objects.link(cam)
    cam.location = sp - fwd * 6 + Vector((0, 0, 2.5)); look = sp + fwd * 30 + Vector((0, 0, 3))
    cam.rotation_euler = (look - cam.location).to_track_quat("-Z", "Y").to_euler(); cam.data.lens = 24
    bpy.context.scene.camera = cam
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 24; sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720; sc.view_settings.view_transform = "AgX"
    sc.render.filepath = os.path.join(OUT, f"unity_{scene_id}.png"); bpy.ops.render.render(write_still=True)
    print(f"rendered unity_{scene_id}.png  objects={len(sc.objects)} soldiers={n}", flush=True)

if __name__ == "__main__":
    ids = [a for a in sys.argv[1:] if a.startswith("scene_")] or ["scene_00_red_coast", "scene_01_chaotic", "scene_02_computer"]
    for s in ids: build(s)
