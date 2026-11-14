# 第 8 步：套用投射贴图 + 双辫头发，用 PnP 解出的三个锚点相机原位渲染，便于与锚点图逐像素对照
# 用法: /tmp/bpyenv/bin/python 08_render_compare.py <base.blend> <cams.json> <diffuse.png> <outdir> [samples] [no_browgeo]
import bpy, sys, json, os, mathutils, numpy as np
BLEND, CAMS, TEX, OUT = sys.argv[1:5]; SAMPLES = int(sys.argv[5]) if len(sys.argv) > 5 else 96
NOBROW = (len(sys.argv) > 6 and sys.argv[6] == "no_browgeo")
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")
from bl_ext.user_default.mpfb.services.humanservice import HumanService
D = os.path.expanduser("~/.config/blender/5.0/extensions/.user/user_default/mpfb/data")
sc = bpy.context.scene; cams = json.load(open(CAMS)); h = bpy.data.objects["YeWenjie"]
# 皮肤贴图替换
newimg = bpy.data.images.load(TEX); n_rep = 0
for m in h.data.materials:
    for n in m.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image and 'diffuse' in n.image.name.lower(): n.image = newimg; n_rep += 1
        if n.type == 'GROUP' and n.node_tree:
            for nn in n.node_tree.nodes:
                if nn.type == 'TEX_IMAGE' and nn.image and 'diffuse' in nn.image.name.lower(): nn.image = newimg; n_rep += 1
print("replaced diffuse nodes", n_rep)
if NOBROW:
    for o in bpy.data.objects:
        if "eyebrow" in o.name.lower(): o.hide_render = True
# 头发
HAIR = os.environ.get("HAIR", "long01"); HAIR_TEX = os.environ.get("HAIR_TEX", "/tmp/ye/long01_black.png")
hair = HAIR
ho = HumanService.add_mhclo_asset(f"{D}/hair/{hair}/{hair}.mhclo", h, asset_type="Hair", subdiv_levels=0, material_type="MAKESKIN")
for mt in ho.data.materials:
    for n in mt.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            n.inputs["Roughness"].default_value = 0.8
            if "Specular IOR Level" in n.inputs: n.inputs["Specular IOR Level"].default_value = 0.15
        if n.type == 'TEX_IMAGE' and n.image and 'diffuse' in n.image.filepath.lower() and HAIR_TEX: n.image = bpy.data.images.load(HAIR_TEX)
md = ho.modifiers.new("subd", 'SUBSURF'); md.levels = md.render_levels = 1
for m in h.data.materials:
    for n in m.node_tree.nodes:
        if n.type == 'GROUP' and 'Clearcoat' in n.inputs: n.inputs['Clearcoat'].default_value = 0.03; n.inputs['Roughness'].default_value = 0.5
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'   # 对照用：不用 AgX，避免去饱和
# 渲染设置：柔和平光（接近棚拍三视图）
sc.render.engine = 'CYCLES'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
w = sc.world or bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.70, 0.70, 0.72, 1); bg.inputs[1].default_value = 0.35
eyes = [o for o in bpy.data.objects if "high-poly" in o.name][0]
ez = sum((eyes.matrix_world @ v.co).z for v in eyes.data.vertices) / len(eyes.data.vertices)
T = mathutils.Vector((0, 0, ez - 0.03))
def light(nm, loc, e, col=(1, 1, 1), size=1.0):
    l = bpy.data.lights.new(nm, 'AREA'); l.energy = e; l.size = size; l.color = col
    o = bpy.data.objects.new(nm, l); sc.collection.objects.link(o); o.location = loc
    d = T - o.location; o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler(); return o
light("key", (0.7, -1.3, ez + 0.5), 48, (1, 1, 1), size=2.0); light("fill", (-1.1, -1.1, ez + 0.1), 25, (1, 1, 1), size=2.5)
light("rim", (0.2, 1.3, ez + 0.7), 30, (1, 1, 1), size=1.0)
cam = bpy.data.cameras.new("pc"); co = bpy.data.objects.new("pc", cam); sc.collection.objects.link(co); sc.camera = co
cam.sensor_fit = 'HORIZONTAL'; cam.sensor_width = 36
VIEWS = os.environ.get("VIEWS", ",".join(cams.keys())).split(",")
for view, c in cams.items():
    if view not in VIEWS: continue
    W, H = c["size"]; sc.render.resolution_x = W; sc.render.resolution_y = H; sc.render.resolution_percentage = 100
    cam.lens = c["lens_mm"]; co.matrix_world = mathutils.Matrix(c["cam_world"])
    sc.render.filepath = f"{OUT}/render_{view}.png"; bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}/ye_projected.blend"); print("done")
