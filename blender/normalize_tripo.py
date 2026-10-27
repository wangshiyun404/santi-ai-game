"""
把 Tripo 导出的 GLB（默认归一化到 1 m）缩放到目标尺寸，原点归到底部中心，导出到 Unity Assets/Models。
用法: python normalize_tripo.py
"""
import bpy, os, sys
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "..", "assets", "tripo")
DST = os.path.join(ROOT, "..", "unity", "SanTiGame", "Assets", "Models")

# name: (axis, target_m)  axis: "z" = 高度, "max" = 最长边
TARGETS = {
    "dish_tower": ("z", 40.0), "control_console": ("z", 1.3), "jeep": ("max", 3.8), "pyramid": ("z", 28.0),
    "dehydrated_roll": ("max", 1.7), "bamboo_slips": ("max", 0.6), "sand_table": ("max", 2.0), "bronze_sword": ("max", 0.9),
    "rock_small": ("max", 1.2), "char_player": ("z", 1.72), "char_ye_wenjie": ("z", 1.62), "char_follower": ("z", 1.65),
    "char_von_neumann": ("z", 1.75), "char_qin": ("z", 1.78), "soldier_black": ("z", 1.75), "soldier_white": ("z", 1.75),
}

# Tripo 输出的角色/车辆/主控台正面朝 +X；Blender -Y 导出后对应 glTF/Unity +Z（正前方），统一绕 Z 转 -90°
FACE_PX = {"char_player", "char_ye_wenjie", "char_follower", "char_von_neumann", "char_qin", "soldier_black", "soldier_white", "jeep", "control_console"}

def bbox(objs):
    mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
    for o in objs:
        if o.type != "MESH": continue
        for v in o.bound_box:
            p = o.matrix_world @ Vector(v); mn = Vector(map(min, mn, p)); mx = Vector(map(max, mx, p))
    return mn, mx

for name, (axis, target) in TARGETS.items():
    src = os.path.join(SRC, name + ".glb")
    if not os.path.exists(src): print("skip", name); continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)
    objs = list(bpy.data.objects)
    meshes = [o for o in objs if o.type == "MESH"]
    # 把所有网格并到一个根空物体下，统一缩放平移
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    import math
    if name == "dehydrated_roll":   # Tripo 生成为竖立的皮卷，放倒
        for o in meshes: o.rotation_mode = "XYZ"; o.rotation_euler = (0, math.radians(90), 0)
        bpy.ops.object.transform_apply(rotation=True)
    if name in FACE_PX:
        for o in meshes: o.rotation_mode = "XYZ"; o.rotation_euler = (0, 0, math.radians(-90))
        bpy.ops.object.transform_apply(rotation=True)
    mn, mx = bbox(meshes); size = mx - mn
    cur = size.z if axis == "z" else max(size)
    s = target / cur
    for o in meshes:
        o.scale = (s, s, s)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mn, mx = bbox(meshes)
    offset = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    for o in meshes:
        o.location -= offset
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.transform_apply(location=True)
    # 删除空物体，保留网格
    for o in objs:
        if o.type == "EMPTY": bpy.data.objects.remove(o)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=os.path.join(DST, name + ".glb"), export_format="GLB", use_selection=True, export_yup=True)
    mn, mx = bbox([o for o in bpy.data.objects if o.type == "MESH"])
    print(f"{name}: size=({mx.x-mn.x:.2f},{mx.y-mn.y:.2f},{mx.z-mn.z:.2f}) bottom_z={mn.z:.2f}", flush=True)
print("DONE")
