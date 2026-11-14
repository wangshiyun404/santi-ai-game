# 第 10 步：从 ye_final.blend 渲染样张 —— 表情 7 格（正面近景）、三视图近景（与锚点相机同位）、全身正面
# 用法: /tmp/bpyenv/bin/python 10_sheets.py <ye_final.blend> <cams.json> <outdir> [samples]
import bpy, os, sys, json, mathutils
BLEND, CAMS, OUT = sys.argv[1:4]; SAMPLES = int(sys.argv[4]) if len(sys.argv) > 4 else 32
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")
from bl_ext.user_default.mpfb.services.faceservice import FaceService
from bl_ext.user_default.mpfb.services.targetservice import TargetService
h = bpy.data.objects["YeWenjie"]; sc = bpy.context.scene
eyes = [o for o in bpy.data.objects if "high-poly" in o.name][0]
ez = sum((eyes.matrix_world @ vv.co).z for vv in eyes.data.vertices) / len(eyes.data.vertices)
T = mathutils.Vector((0, 0, ez - 0.03))
sc.render.engine = 'CYCLES'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
w = sc.world or bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.70, 0.70, 0.72, 1); bg.inputs[1].default_value = 0.35
def light(nm, loc, e, size=1.0):
    l = bpy.data.lights.new(nm, 'AREA'); l.energy = e; l.size = size
    o = bpy.data.objects.new(nm, l); sc.collection.objects.link(o); o.location = loc
    d = T - o.location; o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler(); return o
light("key", (0.7, -1.3, ez + 0.5), 48, 2.0); light("fill", (-1.1, -1.1, ez + 0.1), 25, 2.5); light("rim", (0.2, 1.3, ez + 0.7), 30, 1.0)
cams = json.load(open(CAMS))
cam = bpy.data.cameras.new("cam"); co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co); sc.camera = co
cam.sensor_fit = 'HORIZONTAL'; cam.sensor_width = 36
def place(c, pull=1.0):
    M = mathutils.Matrix(c["cam_world"]); cam.lens = c["lens_mm"]
    pos = M.to_translation(); M.translation = T + (pos - T) * pull; co.matrix_world = M
def set_all(expr):
    FaceService.clear_expression(h)
    for o in bpy.data.objects:
        if o.type == 'MESH' and o is not h and o.data.shape_keys:
            for kb in o.data.shape_keys.key_blocks: kb.value = 0.0
    FaceService.set_expression(h, expr)
    for name, wv in expr.items():
        kn = TargetService.expression_name_to_shapekey_name(name)
        for o in bpy.data.objects:
            if o.type == 'MESH' and o is not h and o.data.shape_keys and kn in o.data.shape_keys.key_blocks:
                o.data.shape_keys.key_blocks[kn].value = wv
def render(path, rx, ry, pct=100):
    sc.render.resolution_x = rx; sc.render.resolution_y = ry; sc.render.resolution_percentage = pct
    sc.render.filepath = path; bpy.ops.render.render(write_still=True); print("rendered", path)
# 三视图近景（与锚点相机同位，用于对照）
set_all({})
for view in ("front", "q34", "left"):
    place(cams[view], 1.0); render(f"{OUT}/view_{view}.png", *cams[view]["size"], 100)
# 表情：正面相机后拉 1.35 倍，方形构图
EXPR = {
    "neutral": {},
    "smile": {"mouthSmileLeft": 0.7, "mouthSmileRight": 0.7, "cheekSquintLeft": 0.3, "cheekSquintRight": 0.3, "eyeSquintLeft": 0.2, "eyeSquintRight": 0.2},
    "sad": {"browInnerUp": 0.6, "mouthFrownLeft": 0.5, "mouthFrownRight": 0.5},
    "surprise": {"browInnerUp": 0.8, "browOuterUpLeft": 0.6, "browOuterUpRight": 0.6, "eyeWideLeft": 0.6, "eyeWideRight": 0.6, "jawOpen": 0.3},
    "angry": {"browDownLeft": 0.8, "browDownRight": 0.8, "noseSneerLeft": 0.3, "noseSneerRight": 0.3, "mouthPressLeft": 0.4, "mouthPressRight": 0.4},
    "blink": {"eyeBlinkLeft": 1.0, "eyeBlinkRight": 1.0},
    "speak": {"jawOpen": 0.5, "mouthFunnel": 0.2},
}
place(cams["front"], 0.8)
for name, expr in EXPR.items():
    set_all(expr); render(f"{OUT}/expr_{name}.png", 590, 941, 80)
set_all({})
# 全身正面：相机沿正视方向后拉到能框住全身
M = mathutils.Matrix(cams["front"]["cam_world"]); fwd = (M.to_translation() - T).normalized()
zs = [(h.matrix_world @ vv.co).z for vv in h.data.vertices]; hgt = max(zs) - min(zs); mid = mathutils.Vector((0, 0, (max(zs) + min(zs)) / 2))
cam.lens = 50; dist = hgt * 1.15 * cam.lens / (36 * 1200 / 600) * 1.0  # 横向 sensor 36mm，纵向视场 = 36×(1200/600)
M2 = M.copy(); M2.translation = mid + fwd * dist; co.matrix_world = M2
render(f"{OUT}/body_front.png", 600, 1200, 100)
print("done")
