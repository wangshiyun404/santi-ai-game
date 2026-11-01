"""
侧视步态抽帧看板：对 GLB 中的 walk / run 各抽 6 帧，从人物右侧（+Y）拍全身，脸朝画面左。
用法: /tmp/bpyenv/bin/python scripts/gait_strip.py in.glb out.jpg [标题]
用于体态复核（驼背/前扑/朝向）。渲染用 Cycles CPU 16 采样，相机矩阵显式构造（避免 to_track_quat 退化导致的滚转）。
"""
import sys, bpy, math
from mathutils import Vector, Matrix
src, out = sys.argv[1], sys.argv[2]
title = sys.argv[3] if len(sys.argv) > 3 else ''
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
scene = bpy.context.scene
scene.render.engine = 'CYCLES'; scene.cycles.samples = 16; scene.cycles.device = 'CPU'   # 沙盒无 GPU/EGL，Workbench 不可用
scene.render.resolution_x, scene.render.resolution_y = 360, 640; scene.render.film_transparent = False
world = bpy.data.worlds.new('W'); scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.5, 0.5, 0.5, 1); bg.inputs[1].default_value = 1.0
sun_d = bpy.data.lights.new('S', 'SUN'); sun_d.energy = 3; sun = bpy.data.objects.new('S', sun_d); scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(120))
cam_d = bpy.data.cameras.new('C'); cam_d.lens = 50; cam = bpy.data.objects.new('C', cam_d); scene.collection.objects.link(cam); scene.camera = cam
tgt = Vector((0, 0, 0.8)); pos = Vector((0, 2.6, 0.9))
f = (tgt - pos).normalized(); r = f.cross(Vector((0, 0, 1))).normalized(); u = r.cross(f)
cam.matrix_world = Matrix(((r.x, u.x, -f.x, pos.x), (r.y, u.y, -f.y, pos.y), (r.z, u.z, -f.z, pos.z), (0, 0, 0, 1)))
frames = []
for name in ('walk', 'run'):
    act = bpy.data.actions.get(name)
    if act is None: continue
    arm.animation_data.action = act
    f0, f1 = map(int, act.frame_range)
    for i in range(6):
        fr = f0 + int((f1 - f0) * i / 6)
        scene.frame_set(fr); scene.render.filepath = f'/tmp/_gait_{name}_{i}.png'; bpy.ops.render.render(write_still=True)
        frames.append((name, scene.render.filepath))
import subprocess, json
subprocess.run(['python3', '-c', '''
import sys, json
from PIL import Image, ImageDraw, ImageFont
frames, out, title = json.loads(sys.argv[1]), sys.argv[2], sys.argv[3]
ims = [Image.open(p) for p in frames]; w, h = ims[0].size; cols = 6; rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (w * cols, h * rows + 40), (30, 30, 30))
for k, im in enumerate(ims): sheet.paste(im, ((k % cols) * w, 40 + (k // cols) * h))
try: font = ImageFont.truetype('/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc', 24)
except Exception: font = ImageFont.load_default()
ImageDraw.Draw(sheet).text((12, 8), f'{title}  上排 walk / 下排 run，右侧视，脸朝画面左', fill=(240, 240, 240), font=font)
sheet.save(out, quality=85); print("saved", out)
''', json.dumps([p for _, p in frames]), out, title], check=True)   # bpy 自带 Python 无 PIL，拼图交给系统 python3
