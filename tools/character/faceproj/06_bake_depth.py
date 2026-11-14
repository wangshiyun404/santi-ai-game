# 第 6 步：烘焙身体网格的世界坐标/法线到 UV 贴图（npy），并从各锚点相机渲染深度图（npy）
# 用法: /tmp/bpyenv/bin/python 06_bake_depth.py <base.blend> <cams.json> <outdir> [texsize]
import bpy, sys, json, os, mathutils, numpy as np
BLEND, CAMS, OUT = sys.argv[1:4]; TS = int(sys.argv[4]) if len(sys.argv) > 4 else 2048
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene; cams = json.load(open(CAMS))
h = bpy.data.objects["YeWenjie"]
sc.render.engine = 'CYCLES'; sc.cycles.samples = 1; sc.cycles.use_denoising = False
for o in bpy.data.objects:
    if o.type == 'MESH' and o.name != "YeWenjie" and "high-poly" not in o.name:
        o.hide_render = True; o.hide_viewport = True
# ---- 烘焙 position / normal ----
SKIP_BAKE = os.path.exists(f"{OUT}/normal.npy")
bpy.ops.object.select_all(action='DESELECT'); h.select_set(True); bpy.context.view_layer.objects.active = h
for kind in ([] if SKIP_BAKE else ["POSITION", "NORMAL"]):
    img = bpy.data.images.new(f"bake_{kind}", TS, TS, float_buffer=True, alpha=True)
    nodes = []
    for mat in h.data.materials:   # 身体有 7 个材质槽（body/lips/ears/...），每个都要挂上目标贴图节点
        nt = mat.node_tree; node = nt.nodes.new("ShaderNodeTexImage"); node.image = img; nt.nodes.active = node; nodes.append((nt, node))
    sc.render.bake.margin = 6; sc.render.bake.use_selected_to_active = False
    if kind == "NORMAL": sc.render.bake.normal_space = 'OBJECT'
    bpy.ops.object.bake(type=kind, margin=6)
    arr = np.array(img.pixels[:], dtype=np.float32).reshape(TS, TS, 4)
    np.save(f"{OUT}/{kind.lower()}.npy", arr); print("baked", kind, arr.shape, arr[..., :3].min(), arr[..., :3].max())
    for nt, node in nodes: nt.nodes.remove(node)
# ---- 深度图 ----
vl = bpy.context.view_layer; vl.use_pass_z = True
tree = bpy.data.node_groups.new("comp", "CompositorNodeTree"); sc.compositing_node_group = tree
rl = tree.nodes.new("CompositorNodeRLayers"); fo = tree.nodes.new("CompositorNodeOutputFile")
fo.directory = OUT; fo.format.file_format = 'OPEN_EXR_MULTILAYER'; fo.format.color_depth = '32'
item = fo.file_output_items.new('FLOAT', 'Depth'); tree.links.new(rl.outputs["Depth"], fo.inputs["Depth"])
cam = bpy.data.cameras.new("proj"); co = bpy.data.objects.new("proj", cam); sc.collection.objects.link(co); sc.camera = co
cam.sensor_fit = 'HORIZONTAL'; cam.sensor_width = 36; cam.clip_start = 0.05; cam.clip_end = 20
for view, c in cams.items():
    W, H = c["size"]; sc.render.resolution_x = W; sc.render.resolution_y = H; sc.render.resolution_percentage = 100
    cam.lens = c["lens_mm"]; co.matrix_world = mathutils.Matrix(c["cam_world"])
    fo.file_name = f"depth_{view}_"
    bpy.ops.render.render(write_still=False)
    print(view, "depth exr written (读取用 OpenEXR，在 07 步)")
print("done")
