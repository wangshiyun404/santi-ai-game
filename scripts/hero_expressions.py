"""第 10 轮（REA Q9 角色形象）：给写实主角的绑骨动画 GLB 加表情形变键（glTF morph targets），供 Unity 里 FaceExpression 以 BlendShape 驱动。
Tripo 绑骨输出没有表情；本脚本在 Blender 里按"贴图取色 + 几何位置"自动定位眼睛/嘴，生成 4 个形变键：
  blink     上眼睑下拉盖住眼球（眨眼 / 闭眼）
  jaw_open  下巴与下唇下移（说话 / 惊讶）
  smile     嘴角上提外扩（轻微微笑）
  brows_up  眉弓上抬（惊讶）
定位方法：头部前半、面中线附近，按顶点 UV 采样基础色——最暗的一簇 = 瞳孔（左右各一），最红的一簇 = 嘴唇。
用法: /tmp/bpyenv/bin/python scripts/hero_expressions.py in_anim.glb out_anim.glb [--debug 前缀]
输出：带形变键与原 3 段动画的 GLB；--debug 时另渲染 4 个表情的脸部特写到 前缀_{neutral,blink,jaw,smile_brows}.png
"""
import sys, os, bpy, numpy as np, mathutils
src, dst = sys.argv[1], sys.argv[2]
dbg = sys.argv[sys.argv.index('--debug') + 1] if '--debug' in sys.argv else None
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
body = max([o for o in bpy.data.objects if o.type == 'MESH'], key=lambda o: len(o.data.vertices))
me = body.data; mw = body.matrix_world
co = np.array([(mw @ v.co)[:] for v in me.vertices]); N = len(co)
mn, mx = co.min(0), co.max(0); H = mx[2] - mn[2]; z = (co[:, 2] - mn[2]) / H
# 轴：左右轴 = 肩高跨度大的轴；前 = 脚尖相对小腿偏移方向
sh = co[(z > 0.78) & (z < 0.83)]; side = 0 if np.ptp(sh[:, 0]) > np.ptp(sh[:, 1]) else 1; fa = 1 - side
sole = co[z < 0.012]; shin = co[(z > 0.12) & (z < 0.20)]; fsign = 1 if sole[:, fa].mean() > shin[:, fa].mean() else -1
head = co[z > 0.86]; c_side = head[:, side].mean(); c_f = head[:, fa].mean()
front = (co[:, fa] - c_f) * fsign            # >0 为脸前方
ds = co[:, side] - c_side                    # 左右偏移
print(f"H={H:.3f} side_axis={'xy'[side]} front={'+' if fsign>0 else '-'}{'xy'[fa]}")
# ---- 贴图取色 ----
mat = me.materials[0]; img = next(n.image for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE' and n.outputs['Color'].links and n.outputs['Color'].links[0].to_socket.name == 'Base Color')
W, Hh = img.size; px = np.empty(W * Hh * 4, dtype=np.float32); img.pixels.foreach_get(px); px = px.reshape(Hh, W, 4)
uv = np.zeros((N, 2)); seen = np.zeros(N, bool)
uvl = me.uv_layers.active.data
for p in me.polygons:
    for li, vi in zip(p.loop_indices, p.vertices):
        if not seen[vi]: uv[vi] = uvl[li].uv[:]; seen[vi] = True
ix = np.clip((uv[:, 0] % 1.0 * (W - 1)).astype(int), 0, W - 1); iy = np.clip((uv[:, 1] % 1.0 * (Hh - 1)).astype(int), 0, Hh - 1)
rgb = px[iy, ix, :3]; lum = rgb.mean(1)
# ---- 眼睛：头前半、眼高带、中线 ±0.045H，最暗 → 瞳孔 ----
cand = np.where((z > 0.895) & (z < 0.945) & (front > 0.03 * H) & (np.abs(ds) < 0.032 * H) & (np.abs(ds) > 0.010 * H))[0]
dark = cand[np.argsort(lum[cand])[:max(12, len(cand) // 12)]]
eyes = {}
for nm, sel in (('L', dark[ds[dark] > 0]), ('R', dark[ds[dark] < 0])):
    if len(sel) < 3: raise SystemExit(f"eye {nm} not found")
    eyes[nm] = co[sel].mean(0)
    print(f"eye {nm}: n={len(sel)} center z={((eyes[nm][2]-mn[2])/H):.3f} side={(eyes[nm][side]-c_side)/H:+.3f} lum={lum[sel].mean():.2f}")
eye_z = np.mean([eyes['L'][2], eyes['R'][2]])
# ---- 嘴：眼下方 0.03–0.08H、中线 ±0.03H、前方，最红（r−g 最大）→ 唇 ----
mc = np.where((co[:, 2] < eye_z - 0.03 * H) & (co[:, 2] > eye_z - 0.08 * H) & (front > 0.02 * H) & (np.abs(ds) < 0.03 * H))[0]
red = rgb[mc, 0] - rgb[mc, 1]; lips = mc[np.argsort(-red)[:max(10, len(mc) // 10)]]
mouth = co[lips].mean(0); mouth_z = mouth[2]
print(f"mouth: n={len(lips)} z={(mouth_z-mn[2])/H:.3f} (eye−mouth {(eye_z-mouth_z)/H:.3f}H) redness={red.max():.2f}")
# ---- 形变键 ----
if me.shape_keys is None: body.shape_key_add(name='Basis', from_mix=False)
def add_key(name, disp):
    k = body.shape_key_add(name=name, from_mix=False)
    inv = mw.inverted()
    for i in np.nonzero(np.abs(disp).sum(1) > 1e-9)[0]:
        k.data[int(i)].co = inv @ mathutils.Vector(co[i] + disp[i])
    print(f"key {name}: {int((np.abs(disp).sum(1) > 1e-9).sum())} verts moved")
up = np.zeros(3); up[2] = 1; fw = np.zeros(3); fw[fa] = fsign; sd = np.zeros(3); sd[side] = 1
def smooth(t): t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)
# blink：眼心半径 r 内、z ≥ 眼心−0.003H 的顶点下拉到眼心下方 0.006H 处（眼睑滑过眼球），下眼睑轻微上抬
disp = np.zeros((N, 3))
for nm, ec in eyes.items():
    d = np.linalg.norm((co - ec) * np.array([1 if a != fa else 0.5 for a in range(3)]), axis=1) / H   # 前后方向权重减半（眼窝深度）
    w = 1 - smooth((d - 0.008) / 0.010)                              # r<0.008H 全权重，到 0.018H 归零（不带动眉毛）
    sel = (w > 0) & (front > 0.015 * H) & (co[:, 2] < ec[2] + 0.011 * H)   # 不带动眉毛
    upper = sel & (co[:, 2] >= ec[2] - 0.003 * H)
    tgt = ec[2] - 0.0035 * H                                          # 低模脸顶点稀疏，下拉过多会把眉毛贴图一起拽下来
    disp[upper, 2] += (tgt - co[upper, 2]) * w[upper]
    lower = sel & (co[:, 2] < ec[2] - 0.003 * H)
    disp[lower, 2] += (ec[2] - 0.0035 * H - co[lower, 2]) * 0.5 * w[lower]
    disp[sel] += (fw * (-0.002 * H))[None, :] * w[sel, None]        # 略微后退，避免穿过眼球
add_key('blink', disp)
# jaw_open：嘴线以下、下巴以上（mouth_z−0.045H）、脸前方、中线 ±0.045H 的顶点下移 0.014H（权重从嘴线渐变）
disp = np.zeros((N, 3))
w = smooth((mouth_z + 0.004 * H - co[:, 2]) / (0.012 * H)) * (1 - smooth((mouth_z - 0.05 * H - co[:, 2]) / (0.015 * H)))
w *= (1 - smooth((np.abs(ds) - 0.03 * H) / (0.02 * H))) * (front > -0.01 * H)
disp[:, 2] -= 0.014 * H * w
disp += (fw * (-0.003 * H))[None, :] * w[:, None]                    # 张嘴时下巴稍后收
add_key('jaw_open', disp)
# smile：嘴角（嘴线高度 ±0.012H，|side| 0.012–0.03H）上提 0.005H、外扩 0.004H
disp = np.zeros((N, 3))
w = (1 - smooth((np.abs(co[:, 2] - mouth_z) - 0.006 * H) / (0.01 * H))) * (1 - smooth((np.abs(np.abs(ds) - 0.02 * H) - 0.006 * H) / (0.01 * H))) * (front > 0.0)
disp[:, 2] += 0.005 * H * w; disp += (sd[None, :] * np.sign(ds)[:, None]) * (0.004 * H * w[:, None])
add_key('smile', disp)
# brows_up：眉弓带（眼心上 0.012–0.03H、|side|<0.045H、脸前方）上抬 0.006H
disp = np.zeros((N, 3))
w = (1 - smooth((np.abs(co[:, 2] - (eye_z + 0.021 * H)) - 0.006 * H) / (0.01 * H))) * (1 - smooth((np.abs(ds) - 0.035 * H) / (0.012 * H))) * (front > 0.02 * H)
disp[:, 2] += 0.006 * H * w
add_key('brows_up', disp)
for k in me.shape_keys.key_blocks: k.value = 0.0
# ---- 调试渲染 ----
if dbg:
    for a in bpy.data.objects:
        if a.type == 'ARMATURE': a.data.pose_position = 'REST'   # 用绑定姿态渲染，与分析坐标一致
    scene = bpy.context.scene; scene.render.engine = 'CYCLES'; scene.cycles.samples = 32; scene.render.resolution_x = scene.render.resolution_y = 600
    world = bpy.data.worlds.new("W"); scene.world = world; world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[1].default_value = 4.0
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("C")); scene.collection.objects.link(cam); scene.camera = cam
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 0.2 * H
    hc = mathutils.Vector((0, 0, 0)); hc[side] = c_side; hc[fa] = c_f; hc[2] = eye_z - 0.02 * H
    f = mathutils.Vector(tuple(fw)) * -1; r = f.cross(mathutils.Vector((0, 0, 1))).normalized(); u = r.cross(f)
    # 正面偏 25° 的 3/4 视角更能看出形变
    q = mathutils.Quaternion((0, 0, 1), np.radians(25)); f = (q @ f).normalized(); r = f.cross(mathutils.Vector((0, 0, 1))).normalized(); u = r.cross(f)
    cam.matrix_world = mathutils.Matrix.Translation(hc - f * 3) @ mathutils.Matrix((r, u, -f)).transposed().to_4x4()
    os.makedirs(os.path.dirname(dbg) or '.', exist_ok=True)
    for tag, vals in (('neutral', {}), ('blink', {'blink': 1}), ('jaw', {'jaw_open': 1}), ('smile_brows', {'smile': 1, 'brows_up': 1})):
        for k in me.shape_keys.key_blocks: k.value = vals.get(k.name, 0.0)
        scene.render.filepath = f"{dbg}_{tag}.png"; bpy.ops.render.render(write_still=True)
    for k in me.shape_keys.key_blocks: k.value = 0.0
    scene.collection.objects.unlink(cam)
    for a in bpy.data.objects:
        if a.type == 'ARMATURE': a.data.pose_position = 'POSE'
# ---- 顺手修 Tripo 重定向的已知毛病：run 剪辑的髋骨在水平方向整体偏移约 0.53 m（旧主角也一样，E26c 抽帧时人物出画）。
# 把每个剪辑髋骨 location 的水平分量（骨骼局部 X/Z = 世界 X/Y）均值对齐到 idle，原地动画不再"跑到控制器前面半米"。
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
def hips_loc_fcurves(act):
    out = {}
    for layer in act.layers:
        for strip in layer.strips:
            for slot in act.slots:
                cb = strip.channelbag(slot)
                if cb is None: continue
                for fc in cb.fcurves:
                    if fc.data_path.endswith('Hips"].location'): out[fc.array_index] = fc
    return out
ref = {i: float(np.mean([k.co[1] for k in fc.keyframe_points])) for i, fc in hips_loc_fcurves(bpy.data.actions['idle']).items()} if 'idle' in bpy.data.actions else {0: 0.0, 2: 0.0}
for act in bpy.data.actions:
    if act.name == 'idle': continue
    for i, fc in hips_loc_fcurves(act).items():
        if i not in (0, 2): continue                   # 1 = 竖直（上下起伏要保留）
        m = float(np.mean([k.co[1] for k in fc.keyframe_points])); d = m - ref.get(i, 0.0)
        if abs(d) > 0.02:
            for k in fc.keyframe_points: k.co[1] -= d; k.handle_left[1] -= d; k.handle_right[1] -= d
            print(f"recenter {act.name} hips loc[{i}] by {-d:+.3f}")
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=dst, export_format='GLB', export_yup=True, export_apply=False, export_image_format='AUTO',
                          export_normals=True, export_texcoords=True, export_morph=True, export_morph_normal=False, export_try_sparse_sk=False, export_animations=True)   # 不用稀疏 accessor：glTFast 读稀疏形变键会出乱几何（真机 E27 楔形面罩）
print('exported', dst)
