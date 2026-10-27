"""
Tripo 资产质检：导入每个 GLB，打印尺寸/面数/朝向，渲染三视图小图拼成 contact sheet。
用法: python review_tripo.py [name ...]
"""
import bpy, os, sys, math, json
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "..", "assets", "tripo")
OUT = os.path.join(ROOT, "..", "review", "tripo")
os.makedirs(OUT, exist_ok=True)

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    w = bpy.data.worlds.new("W"); bpy.context.scene.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.6, 0.62, 0.66, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.8
    bpy.ops.object.light_add(type="SUN"); l = bpy.context.object; l.rotation_euler = (math.radians(50), 0, math.radians(35)); l.data.energy = 3

def stats(objs):
    mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3); faces = 0; quads = 0
    for o in objs:
        if o.type != "MESH": continue
        for v in o.bound_box:
            p = o.matrix_world @ Vector(v); mn = Vector(map(min, mn, p)); mx = Vector(map(max, mx, p))
        faces += len(o.data.polygons); quads += sum(1 for p in o.data.polygons if len(p.vertices) == 4)
    return mn, mx, faces, quads

def shoot(name, center, radius, angle_deg, path, lens=50):
    a = math.radians(angle_deg)
    loc = center + Vector((math.sin(a) * radius, -math.cos(a) * radius, radius * 0.45))
    bpy.ops.object.camera_add(location=loc); cam = bpy.context.object
    cam.rotation_euler = (center - loc).to_track_quat("-Z", "Y").to_euler(); cam.data.lens = lens
    bpy.context.scene.camera = cam
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = 16; sc.cycles.use_denoising = True
    sc.render.resolution_x = 360; sc.render.resolution_y = 360; sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)

report = {}
names = sys.argv[1:] or sorted(f[:-4] for f in os.listdir(SRC) if f.endswith(".glb"))
for name in names:
    reset()
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(SRC, name + ".glb"))
    objs = [o for o in bpy.data.objects if o not in before]
    mn, mx, faces, quads = stats(objs)
    size = mx - mn; center = (mn + mx) / 2
    report[name] = {"size_m": [round(size.x, 2), round(size.y, 2), round(size.z, 2)], "faces": faces, "quad_ratio": round(quads / max(faces, 1), 2), "height_axis": "Z" if size.z >= max(size.x, size.y) * 0.8 else "flat"}
    print(name, report[name], flush=True)
    radius = max(size) * 1.9
    for i, ang in enumerate((0, 90, 180)):
        shoot(name, center, radius, ang, os.path.join(OUT, f"{name}_{i}.png"))

json.dump(report, open(os.path.join(OUT, "report.json"), "w"), indent=1)
print("DONE")
