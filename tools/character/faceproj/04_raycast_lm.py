# 第 4 步：把渲染图上检测到的关键点沿相机射线投到网格表面，得到 478 个 3D 点（世界坐标）
# 用法: /tmp/bpyenv/bin/python 04_raycast_lm.py <base.blend> <calib_meta.json> <landmarks.json> <out lm3d.json>
import bpy, sys, json, mathutils
BLEND, META, LM, OUT = sys.argv[-4:]
bpy.ops.wm.open_mainfile(filepath=BLEND)
meta = json.load(open(META)); lms = json.load(open(LM))
for o in list(bpy.data.objects):
    if o.type == 'MESH' and o.name != "YeWenjie" and "high-poly" not in o.name:
        bpy.data.objects.remove(o)   # 牙齿/舌头/眉毛/睫毛会挡住射线，直接删掉（不保存）
dg = bpy.context.evaluated_depsgraph_get()
res = {}
for view in ["front", "q34"]:
    key = f"calib_{view}"
    if key not in lms: continue
    M = mathutils.Matrix(meta["views"][view]["matrix_world"])
    f = meta["lens"]; sw = meta["sensor_width"]; W = H = meta["res"]
    pts3 = []; hits = 0
    for x, y, _ in lms[key]["pts"]:
        d_cam = mathutils.Vector(((x / W - 0.5) * sw / f, -(y / H - 0.5) * sw / f, -1.0))
        o = M.translation; d = (M.to_3x3() @ d_cam).normalized()
        ok, loc, nrm, idx, obj, _ = bpy.context.scene.ray_cast(dg, o, d)
        if ok: pts3.append([loc.x, loc.y, loc.z]); hits += 1; hitobj = obj.name
        else: pts3.append(None)
    res[view] = pts3; print(view, "hits", hits, "/", len(pts3))
json.dump(res, open(OUT, "w")); print("saved", OUT)
