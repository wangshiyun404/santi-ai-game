# 第 2 步：平光渲染头部正视/侧视（用于在渲染图上检测人脸关键点），并保存相机参数
# 用法: /tmp/bpyenv/bin/python 02_calib_render.py <base.blend> <outdir>
import bpy, sys, json, os, mathutils, math
BLEND, OUT = sys.argv[-2], sys.argv[-1]; os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene
h = bpy.data.objects["YeWenjie"]
eyes = [o for o in bpy.data.objects if "high-poly" in o.name][0]
ez = sum((eyes.matrix_world @ v.co).z for v in eyes.data.vertices) / len(eyes.data.vertices)
print("eye z", ez)
sc.render.engine = 'CYCLES'; sc.cycles.samples = 48; sc.cycles.use_denoising = True
sc.render.resolution_x = sc.render.resolution_y = 1000; sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'
w = sc.world or bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.9, 0.9, 0.9, 1); bg.inputs[1].default_value = 1.0
cam = bpy.data.cameras.new("calib"); cam.lens = 85; cam.sensor_width = 36; cam.sensor_fit = 'HORIZONTAL'
co = bpy.data.objects.new("calib", cam); sc.collection.objects.link(co); sc.camera = co
T = mathutils.Vector((0, 0, ez - 0.03))
views = {"front": (0, -1.0, ez - 0.03), "left": (1.0, 0, ez - 0.03), "q34": (0.6, -0.8, ez - 0.03)}
if os.environ.get("VIEWS"): views = {k: v for k, v in views.items() if k in os.environ["VIEWS"].split(",")}
meta = {"eye_z": ez, "lens": cam.lens, "sensor_width": cam.sensor_width, "res": 1000, "views": {}}
for name, loc in views.items():
    co.location = loc; d = T - co.location; co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()
    sc.render.filepath = f"{OUT}/calib_{name}.png"; bpy.ops.render.render(write_still=True)
    meta["views"][name] = {"matrix_world": [list(r) for r in co.matrix_world]}
json.dump(meta, open(f"{OUT}/calib_meta.json", "w"), indent=1)
print("done")
