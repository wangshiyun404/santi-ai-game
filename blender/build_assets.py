"""
《三体》低多边形资产与场景生成脚本（B 类几何体资产 + 场景布局 + 预览渲染）
用法: python build_assets.py  (需 bpy)
输出:
  assets/glb/*.glb          — 单个资产（Y-up, 1 unit = 1 m）
  layouts/scene_XX.json     — 场景布局（Unity SceneBuilder 读取）
  preview/scene_XX.png      — Cycles 预览图（供盲审 Agent 对照参考图）
"""
import bpy, bmesh, json, math, os, random, sys
from mathutils import Vector, Euler

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_GLB = os.path.join(ROOT, "..", "assets", "glb")
OUT_LAYOUT = os.path.join(ROOT, "..", "layouts")
OUT_PREVIEW = os.path.join(ROOT, "..", "preview")
for d in (OUT_GLB, OUT_LAYOUT, OUT_PREVIEW):
    os.makedirs(d, exist_ok=True)

random.seed(3)

# ---------- 色板（来自 PRD §6） ----------
PAL = {
    "red_coast": {"green": "#4B5A3A", "rust": "#8B3A2F", "blue": "#1B2A4A", "warm": "#F2B866", "concrete": "#8A8A82", "snow": "#DDE3EA"},
    "chaotic": {"dust": "#8C8275", "crack": "#4A433C", "sun": "#FFFFFF", "frost": "#B8C9D9", "roll": "#A89A80", "stone": "#6E665C"},
    "computer": {"sky": "#5F7A99", "stone": "#6E6E6E", "black": "#111111", "white": "#F5F5F5", "ground": "#7E7466", "cloth": "#3A3F4A"},
}

def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4)) + (1.0,)

_mats = {}
def mat(name, hexcol, emission=0.0):
    key = (name, hexcol, emission)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = hex2rgb(hexcol)
    bsdf.inputs["Roughness"].default_value = 0.9
    if emission > 0:
        bsdf.inputs["Emission Color"].default_value = hex2rgb(hexcol)
        bsdf.inputs["Emission Strength"].default_value = emission
    _mats[key] = m
    return m

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()

def flat(obj):
    for p in obj.data.polygons:
        p.use_smooth = False

def set_mat(obj, m):
    obj.data.materials.clear()
    obj.data.materials.append(m)

def export_glb(obj_or_list, name):
    objs = obj_or_list if isinstance(obj_or_list, list) else [obj_or_list]
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    path = os.path.join(OUT_GLB, f"{name}.glb")
    bpy.ops.export_scene.gltf(filepath=path, use_selection=True, export_format="GLB",
                              export_apply=True, export_yup=True)
    return path

# ---------- 几何体生成器 ----------
def make_ground(name, size=400, cuts=60, jitter=0.35, mat_=None):
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=cuts, y_subdivisions=cuts, size=size)
    o = bpy.context.object; o.name = name
    for v in o.data.vertices:
        d = (v.co.xy.length / (size / 2))
        v.co.z += random.uniform(-jitter, jitter) * (0.3 + d)  # 远处起伏更大
    flat(o)
    if mat_: set_mat(o, mat_)
    return o

def make_pyramid(name, base=40, height=28, mat_=None):
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=base / math.sqrt(2), depth=height, location=(0, 0, height / 2))
    o = bpy.context.object; o.name = name
    o.rotation_euler = (0, 0, math.radians(45))
    flat(o)
    if mat_: set_mat(o, mat_)
    return o

def make_dehydrated_roll(name, length=1.7, radius=0.22, mat_=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=7, radius=radius, depth=length, location=(0, 0, radius))
    o = bpy.context.object; o.name = name
    o.rotation_euler = (0, math.radians(90), 0)
    bm = bmesh.new(); bm.from_mesh(o.data)
    for v in bm.verts:
        v.co.x *= random.uniform(0.85, 1.1)
        v.co.y *= random.uniform(0.8, 1.2)
    bm.to_mesh(o.data); bm.free()
    flat(o)
    if mat_: set_mat(o, mat_)
    return o

def make_capsule_figure(name, height=1.7, mat_=None):
    """占位角色（将来替换为 Tripo Smart Mesh 角色）"""
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.25, depth=height * 0.75, location=(0, 0, height * 0.375))
    body = bpy.context.object
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.14, location=(0, 0, height * 0.86))
    head = bpy.context.object
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True); head.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    o = bpy.context.object; o.name = name
    flat(o)
    if mat_: set_mat(o, mat_)
    return o

def make_soldier_with_flag(name, flag_hex, cloth_hex):
    """士兵基准（≤ 600 面）：身体 + 举起的旗杆 + 旗面"""
    bpy.ops.mesh.primitive_cylinder_add(vertices=5, radius=0.22, depth=1.3, location=(0, 0, 0.65))
    body = bpy.context.object; set_mat(body, mat("cloth", cloth_hex))
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.13, location=(0, 0, 1.45))
    head = bpy.context.object; set_mat(head, mat("skin", "#C9A98B"))
    bpy.ops.mesh.primitive_cylinder_add(vertices=4, radius=0.02, depth=2.2, location=(0.3, 0, 1.6))
    pole = bpy.context.object; set_mat(pole, mat("wood", "#5A4632"))
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0.3, 0, 2.4))
    flag = bpy.context.object
    flag.scale = (0.02, 0.5, 0.35); flag.rotation_euler = (math.radians(90), 0, 0)
    set_mat(flag, mat("flag", flag_hex))
    bpy.ops.object.select_all(action="DESELECT")
    for o in (body, head, pole, flag):
        o.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    o = bpy.context.object; o.name = name
    flat(o)
    return o

def make_platform(name, w=24, d=16, h=10, mat_=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, h / 2))
    o = bpy.context.object; o.name = name; o.scale = (w, d, h)
    # 台阶
    bpy.ops.mesh.primitive_cube_add(size=1, location=(w / 2 + 3, 0, h / 4))
    s = bpy.context.object; s.scale = (6, d * 0.4, h / 2)
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); s.select_set(True)
    bpy.context.view_layer.objects.active = o; bpy.ops.object.join()
    flat(o)
    if mat_: set_mat(o, mat_)
    return o

def make_dish_tower(name, pal):
    """红岸巨型抛物面天线 + 混凝土塔"""
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=6, depth=18, location=(0, 0, 9))
    tower = bpy.context.object; set_mat(tower, mat("concrete", pal["concrete"]))
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=7, depth=1.2, location=(0, 0, 18.6))
    deck = bpy.context.object; set_mat(deck, mat("concrete", pal["concrete"]))
    # 抛物面：用低细分球截取
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=22, location=(0, 0, 0))
    dish = bpy.context.object
    bm = bmesh.new(); bm.from_mesh(dish.data)
    geom = [v for v in bm.verts if v.co.z > -16.0]
    bmesh.ops.delete(bm, geom=geom, context="VERTS")
    bm.to_mesh(dish.data); bm.free()
    dish.location = (0, 0, 19.2 + 22)
    dish.rotation_euler = (math.radians(-35), 0, 0)
    set_mat(dish, mat("dish", "#B8BCC2"))
    bpy.ops.mesh.primitive_cylinder_add(vertices=5, radius=0.25, depth=12, location=(0, 0, 25))
    feed = bpy.context.object; feed.rotation_euler = (math.radians(-35), 0, 0); set_mat(feed, mat("steel", "#6B6F75"))
    bpy.ops.object.select_all(action="DESELECT")
    for o in (tower, deck, dish, feed): o.select_set(True)
    bpy.context.view_layer.objects.active = tower; bpy.ops.object.join()
    o = bpy.context.object; o.name = name; flat(o)
    return o

def make_barracks(name, w=14, d=7, h=3.2, pal=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, h / 2))
    wall = bpy.context.object; wall.scale = (w, d, h); set_mat(wall, mat("green", pal["green"]))
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=max(w, d) * 0.58, depth=2.2, location=(0, 0, h + 1.1))
    roof = bpy.context.object; roof.rotation_euler = (0, 0, math.radians(45)); roof.scale = (1, d / w, 1)
    set_mat(roof, mat("rust", pal["rust"]))
    bpy.ops.object.select_all(action="DESELECT"); wall.select_set(True); roof.select_set(True)
    bpy.context.view_layer.objects.active = wall; bpy.ops.object.join()
    o = bpy.context.object; o.name = name; flat(o)
    return o

def make_larch(name, h=9, pal=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=5, radius=0.18, depth=h * 0.35, location=(0, 0, h * 0.175))
    trunk = bpy.context.object; set_mat(trunk, mat("wood", "#3E3027"))
    parts = [trunk]
    for i in range(3):
        bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=1.6 - i * 0.4, depth=h * 0.3, location=(0, 0, h * (0.35 + 0.2 * i) + h * 0.1))
        c = bpy.context.object; set_mat(c, mat("pine", "#2E4A3B")); parts.append(c)
    bpy.ops.object.select_all(action="DESELECT")
    for p in parts: p.select_set(True)
    bpy.context.view_layer.objects.active = trunk; bpy.ops.object.join()
    o = bpy.context.object; o.name = name; flat(o)
    return o

def make_sun(name, radius=30, hexcol="#FFFFFF", strength=6):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=radius)
    o = bpy.context.object; o.name = name
    set_mat(o, mat("sun", hexcol, emission=strength))
    return o

# ---------- 布局与渲染 ----------
def add_sun_light(angle_deg=(60, 0, 30), energy=4, color=(1, 1, 1)):
    bpy.ops.object.light_add(type="SUN")
    l = bpy.context.object
    l.rotation_euler = tuple(math.radians(a) for a in angle_deg)
    l.data.energy = energy; l.data.color = color; l.data.angle = math.radians(2)
    return l

def set_world(hexcol, strength=1.0):
    w = bpy.data.worlds.new("World") if not bpy.context.scene.world else bpy.context.scene.world
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = hex2rgb(hexcol); bg.inputs[1].default_value = strength

def add_camera(loc, look_at, lens=28):
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.object
    direction = Vector(look_at) - Vector(loc)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    bpy.context.scene.camera = cam
    return cam

def render(path, res=(960, 540), samples=24):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.filepath = path
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "AgX"
    bpy.ops.render.render(write_still=True)

def to_unity(obj):
    """Blender Z-up 右手系 → Unity Y-up 左手系（与 glTF 导出一致）"""
    p = obj.matrix_world.to_translation()
    r = obj.matrix_world.to_euler()
    s = obj.matrix_world.to_scale()
    return {
        "position": [round(p.x, 3), round(p.z, 3), round(p.y, 3)],
        "rotation": [round(-math.degrees(r.x), 2), round(-math.degrees(r.z), 2), round(-math.degrees(r.y), 2)],
        "scale": [round(s.x, 3), round(s.z, 3), round(s.y, 3)],
    }

def write_layout(scene_id, title, entries, extras):
    data = {"scene": scene_id, "title": title, "unit": "meters", "up": "Y", "objects": entries, **extras}
    path = os.path.join(OUT_LAYOUT, f"{scene_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path

# =====================================================================
# 场景 1：乱纪元·脱水
# =====================================================================
def build_scene_chaotic():
    clear_scene(); P = PAL["chaotic"]
    entries = []
    ground = make_ground("Ground_Chaotic", size=600, cuts=48, jitter=0.5, mat_=mat("dust", P["dust"]))
    export_glb(ground, "ground_chaotic"); entries.append({"asset": "ground_chaotic", "name": ground.name, **to_unity(ground), "static": True})

    pyr = make_pyramid("Pyramid", mat_=mat("stone", P["stone"]))
    pyr.location = (40, 180, 14)
    export_glb(pyr, "pyramid"); entries.append({"asset": "pyramid", "name": pyr.name, **to_unity(pyr), "static": True, "clue": "clue_pyramid_follower"})

    roll_proto = make_dehydrated_roll("DehydratedRoll", mat_=mat("roll", P["roll"]))
    export_glb(roll_proto, "dehydrated_roll")
    bpy.data.objects.remove(roll_proto)
    for i in range(14):
        r = make_dehydrated_roll(f"DehydratedRoll_{i:02d}", mat_=mat("roll", P["roll"]))
        r.location = (random.uniform(-40, 40), random.uniform(5, 90), 0.22)
        r.rotation_euler = (0, math.radians(90), random.uniform(0, math.pi))
        entries.append({"asset": "dehydrated_roll", "name": r.name, **to_unity(r), "static": True, **({"clue": "clue_dehydration"} if i == 0 else {})})

    fig = make_capsule_figure("PlayerSpawn", mat_=mat("cloak", "#3A332C"))
    fig.location = (0, 12, 0)
    entries.append({"asset": "player_placeholder", "name": "PlayerSpawn", **to_unity(fig), "static": False, "role": "player_spawn"})

    sun = make_sun("Sun_Chaotic", radius=40, hexcol=P["sun"], strength=8); sun.location = (60, 500, 260)
    entries.append({"asset": "sun_sphere", "name": sun.name, **to_unity(sun), "static": False, "role": "sun"})
    export_glb(sun, "sun_sphere")

    add_sun_light((35, 0, 160), energy=3.5, color=(1, 0.98, 0.95))
    set_world("#D9D6CF", 0.45)
    add_camera((-3, -4, 2.4), (10, 60, 6), lens=24)
    render(os.path.join(OUT_PREVIEW, "scene_01_chaotic.png"))
    write_layout("scene_01_chaotic", "乱纪元·脱水", entries, {
        "palette": P,
        "lighting": {"sunAngle": [35, 0, 160], "intensity": 6, "ambient": "#D9D6CF", "fog": {"color": "#D9D6CF", "start": 120, "end": 520}},
        "clues": [
            {"id": "clue_dehydration", "subtitle": "脱水——", "narration": "vo_01_dehydration.wav"},
            {"id": "clue_pyramid_follower", "subtitle": "跟我来，大王在金字塔里等你。", "narration": "vo_01_follower.wav"},
            {"id": "clue_lakebed", "subtitle": "乱纪元开始了。", "narration": "vo_01_chaotic_begins.wav"},
        ],
        "events": [{"id": "sun_fall", "trigger": "player_reaches", "at": [0, 3, 60], "duration": 20, "to": {"ambient": "#1B2A4A", "ground": "#B8C9D9"}}],
    })

# =====================================================================
# 场景 2：人列计算机
# =====================================================================
def build_scene_computer():
    clear_scene(); P = PAL["computer"]
    entries = []
    ground = make_ground("Ground_Plain", size=900, cuts=40, jitter=0.25, mat_=mat("ground", P["ground"]))
    export_glb(ground, "ground_plain"); entries.append({"asset": "ground_plain", "name": ground.name, **to_unity(ground), "static": True})

    sb = make_soldier_with_flag("Soldier_Black", P["black"], P["cloth"]); export_glb(sb, "soldier_black")
    sw = make_soldier_with_flag("Soldier_White", P["white"], P["cloth"]); export_glb(sw, "soldier_white")
    bpy.data.objects.remove(sb); bpy.data.objects.remove(sw)

    # 预览用：方阵用实例化（Blender 中用集合实例近似），Unity 中由 SoldierFormation 组件生成
    blocks = []
    bx, by, gap = 20, 14, 8   # 每块 20×14 士兵，间距 1.2 m；块间留 8 m 总线通道
    for gx in range(-5, 6):
        for gy in range(0, 12):
            if random.random() < 0.08:
                continue  # 留空作为"寄存器"空位
            pattern = random.choice(["checker", "rows", "black", "white"])
            blocks.append({"origin": [gx * (bx * 1.2 + gap), gy * (by * 1.2 + gap) + 40], "cols": bx, "rows": by, "spacing": 1.2, "pattern": pattern})
    # Blender 预览：只放前 3 排，低成本
    proto_b = make_soldier_with_flag("pb", P["black"], P["cloth"]); proto_w = make_soldier_with_flag("pw", P["white"], P["cloth"])
    for blk in blocks:
        if blk["origin"][1] > 150: continue
        ox, oy = blk["origin"]
        for c in range(0, blk["cols"], 2):
            for r in range(0, blk["rows"], 2):
                src = proto_b if (c + r) % 4 == 0 else proto_w
                inst = src.copy(); inst.data = src.data
                inst.location = (ox + c * 1.2, oy + r * 1.2, 0)
                bpy.context.collection.objects.link(inst)
    bpy.data.objects.remove(proto_b); bpy.data.objects.remove(proto_w)

    plat = make_platform("Platform", mat_=mat("stone", P["stone"])); plat.location = (-150, 20, 0)
    export_glb(plat, "platform"); entries.append({"asset": "platform", "name": plat.name, **to_unity(plat), "static": True, "clue": "clue_von_neumann"})
    for i, nm in enumerate(["VonNeumann", "Newton", "QinShiHuang"]):
        f = make_capsule_figure(nm, mat_=mat("cloak", "#2B2F38")); f.location = (-150 + i * 2.5 - 2.5, 20, 10)
        entries.append({"asset": "npc_placeholder", "name": nm, **to_unity(f), "static": False, "role": "npc"})
    fig = make_capsule_figure("PlayerSpawn", mat_=mat("cloak", "#3A332C")); fig.location = (-120, 0, 0)
    entries.append({"asset": "player_placeholder", "name": "PlayerSpawn", **to_unity(fig), "static": False, "role": "player_spawn"})

    add_sun_light((70, 0, -120), energy=3, color=(0.85, 0.9, 1.0))
    set_world("#5F7A99", 0.7)
    add_camera((-170, -30, 22), (0, 120, 0), lens=28)
    render(os.path.join(OUT_PREVIEW, "scene_02_computer.png"))
    write_layout("scene_02_computer", "人列计算机", entries, {
        "palette": P,
        "lighting": {"sunAngle": [70, 0, -120], "intensity": 3, "ambient": "#5F7A99", "fog": {"color": "#6F86A3", "start": 200, "end": 900}},
        "formation": {"blackAsset": "soldier_black", "whiteAsset": "soldier_white", "blocks": blocks, "flipWaveSpeed": 6.0},
        "clues": [
            {"id": "clue_gate_soldier", "subtitle": "你是一个门电路。", "narration": "vo_02_gate.wav"},
            {"id": "clue_bus", "subtitle": "这是系统总线。", "narration": "vo_02_bus.wav"},
            {"id": "clue_von_neumann", "subtitle": "这是一台计算机！", "narration": "vo_02_computer.wav"},
        ],
        "events": [{"id": "three_suns", "trigger": "all_clues_done", "duration": 60}],
    })

# =====================================================================
# 场景 0：红岸基地
# =====================================================================
def build_scene_red_coast():
    clear_scene(); P = PAL["red_coast"]
    entries = []
    # 山顶平台 + 悬崖
    bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=70, depth=60, location=(0, 0, -30))
    cliff = bpy.context.object; cliff.name = "Cliff"
    bm = bmesh.new(); bm.from_mesh(cliff.data)
    for v in bm.verts:
        if v.co.z > -1: v.co.xy *= random.uniform(0.9, 1.05)
        else: v.co.xy *= random.uniform(0.75, 1.15)
    bm.to_mesh(cliff.data); bm.free(); flat(cliff); set_mat(cliff, mat("rock", "#4F5560"))
    export_glb(cliff, "cliff"); entries.append({"asset": "cliff", "name": cliff.name, **to_unity(cliff), "static": True})

    dish = make_dish_tower("DishTower", P); dish.location = (0, 25, 0)
    export_glb(dish, "dish_tower"); entries.append({"asset": "dish_tower", "name": dish.name, **to_unity(dish), "static": True, "clue": "clue_antenna"})

    bar_proto = make_barracks("Barracks", pal=P); export_glb(bar_proto, "barracks"); bpy.data.objects.remove(bar_proto)
    for i, (x, y, rz) in enumerate([(-30, -5, 0), (28, -10, 8), (-18, -32, -12), (24, 18, 90)]):
        b = make_barracks(f"Barracks_{i}", pal=P); b.location = (x, y, 0); b.rotation_euler = (0, 0, math.radians(rz))
        entries.append({"asset": "barracks", "name": b.name, **to_unity(b), "static": True, **({"clue": "clue_control_room"} if i == 0 else {})})

    tree_proto = make_larch("Larch", pal=P); export_glb(tree_proto, "larch"); bpy.data.objects.remove(tree_proto)
    for i in range(18):
        t = make_larch(f"Larch_{i:02d}", h=random.uniform(7, 11), pal=P)
        ang = random.uniform(0, 2 * math.pi); rad = random.uniform(45, 62)
        t.location = (math.cos(ang) * rad, math.sin(ang) * rad, 0)
        entries.append({"asset": "larch", "name": t.name, **to_unity(t), "static": True})

    fig = make_capsule_figure("PlayerSpawn", mat_=mat("coat", "#2F3A2B")); fig.location = (-8, -40, 0)
    entries.append({"asset": "player_placeholder", "name": "PlayerSpawn", **to_unity(fig), "static": False, "role": "player_spawn"})

    add_sun_light((8, 0, 250), energy=1.2, color=(1.0, 0.6, 0.35))
    set_world("#1B2A4A", 0.5)
    add_camera((-45, -70, 14), (0, 20, 22), lens=30)
    render(os.path.join(OUT_PREVIEW, "scene_00_red_coast.png"))
    write_layout("scene_00_red_coast", "红岸基地", entries, {
        "palette": P,
        "lighting": {"sunAngle": [8, 0, 250], "intensity": 1.2, "sunColor": "#FF9A59", "ambient": "#1B2A4A", "fog": {"color": "#2A3B5C", "start": 60, "end": 400}},
        "clues": [
            {"id": "clue_antenna", "subtitle": "红岸基地，1971 年。", "narration": "vo_00_redcoast.wav"},
            {"id": "clue_control_room", "subtitle": "发射。", "narration": "vo_00_transmit.wav"},
            {"id": "clue_reply", "subtitle": "不要回答！不要回答！！不要回答！！！", "narration": "vo_00_do_not_answer.wav"},
        ],
        "events": [{"id": "transmit_whiteout", "trigger": "clue_control_room", "duration": 3, "loadScene": "scene_01_chaotic"}],
    })

if __name__ == "__main__":
    which = sys.argv[1:] or ["0", "1", "2"]
    if "1" in which: build_scene_chaotic()
    if "2" in which: build_scene_computer()
    if "0" in which: build_scene_red_coast()
    print("DONE", os.listdir(OUT_GLB))
