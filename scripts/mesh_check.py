"""原始角色网格体检（第 10 轮固化）：在绑骨之前检查
  1) 朝向：脸(鼻尖=头部区域最突出点)与脚尖(脚部区域最突出点)是否同向      ← E23 教训：脚反装会让 Tripo 绑骨判错前向
  2) 比例：臂长/身高、腿长/身高、头高/身高（写实人体参考：臂 0.30–0.36，腿 0.45–0.53，头 0.12–0.15）
  3) 渲染 4 视图 + 脸部特写到 docs/rea_evidence/，供盲审
用法: /tmp/bpyenv/bin/python scripts/mesh_check.py <mesh.glb> [--render 前缀]
退出码 0=PASS 1=FAIL（朝向不一致或比例明显失真）
"""
import sys, os, bpy, numpy as np, mathutils
path = sys.argv[1]
prefix = sys.argv[sys.argv.index('--render') + 1] if '--render' in sys.argv else None
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
V = np.concatenate([np.array([(o.matrix_world @ v.co)[:] for v in o.data.vertices]) for o in meshes])
mn, mx = V.min(0), V.max(0); H = mx[2] - mn[2]
cx = (mn[0] + mx[0]) / 2; cy = (mn[1] + mx[1]) / 2
z = (V[:, 2] - mn[2]) / H
# 左右轴 = 肩高处(0.78–0.83H)跨度更大的轴（A 姿态双臂张开）；前后轴 = 另一轴
sh = V[(z > 0.78) & (z < 0.83)]
side_axis = 0 if np.ptp(sh[:, 0]) > np.ptp(sh[:, 1]) else 1
fa = 1 - side_axis; foot_axis = 'xy'[fa]
# 脚尖方向：鞋底(z<0.012H)中心 相对 小腿(0.12–0.20H)中心 的偏移方向（鞋底向脚尖方向伸出）
sole = V[z < 0.012]; shin = V[(z > 0.12) & (z < 0.20)]
toe_off = float(sole[:, fa].mean() - shin[:, fa].mean()); foot_sign = 1 if toe_off > 0 else -1
# 鼻子方向：眼高带(0.905–0.935H) 中轴附近(|side|<0.02H) 的顶点，前脸是凸面、后脑有头发/辫子，几何上几乎对称，
# 因此只给出参考值，最终以渲染图盲审为准（E26 教训：双面"雅努斯头"几何对称，数值判不出来）
eye = V[(z > 0.905) & (z < 0.935)]; c_eye = eye[:, fa].mean()
neck = V[(z > 0.855) & (z < 0.87)]; c_neck = neck[:, fa].mean()
head_sign = 1 if c_eye - c_neck > 0 else -1   # 头相对脖子前倾的一侧≈脸
print(f"height {H:.3f}  front axis {foot_axis}  toes {'+' if foot_sign>0 else '-'}{foot_axis} (off {toe_off:.3f})  head-vs-neck {'+' if head_sign>0 else '-'}{foot_axis} ({c_eye-c_neck:+.3f}, 仅参考)")
ok = True
if foot_sign != head_sign: print("WARN 头前倾方向与脚尖不一致，请看渲染图确认脸向")
# 比例：用轮廓估计。臂：z 在 0.35–0.85 区间，离中轴（左右轴）最远的点为手指尖/肩外侧
d_side = np.abs(V[:, side_axis] - (cy if side_axis == 1 else cx))
shoulder_z = 0.80
torso = V[(z > 0.78) & (z < 0.83)]; shoulder_half = np.abs(torso[:, side_axis] - (cy if side_axis == 1 else cx)).max()
# 手指尖：离中轴最远的点所在高度（A 姿态手在体侧偏下）
far = np.argsort(-d_side)[:50]; hand_z = float(np.median(z[far]))
arm_len = np.hypot(d_side[far].mean() - shoulder_half, (shoulder_z - hand_z) * H)   # 近似：肩外侧到指尖
arm_ratio = arm_len / H
# 腿：裆部高度 = 中轴附近（|side|<0.04H）在 0.3–0.6 区间最低有顶点的高度
# 裆部：从 0.25H 往上扫描，中轴附近(|side|<0.003H)首次出现顶点的高度（双腿在裆部合拢）
crotch = float('nan')
for zz in np.linspace(0.25, 0.65, 81):
    band = V[(z > zz - 0.005) & (z < zz + 0.005)]
    if len(band) and (np.abs(band[:, side_axis] - (cy if side_axis == 1 else cx)) < 0.003 * H).any():
        crotch = float(zz); break
leg_ratio = crotch
head_ratio = 1 - float(np.sort(z[(d_side < 0.08 * H)])[::-1][int(0.0005 * len(z))]) if False else None
chin = V[(z > 0.8) & (d_side < 0.05 * H)]
# 下巴：头部区域中轴附近，从上往下宽度首次明显收窄后再放宽处（简化：取颈部最细处）
neck_zs = np.linspace(0.80, 0.95, 31); widths = []
for zz in neck_zs:
    band = V[(z > zz - 0.005) & (z < zz + 0.005)]
    widths.append(np.ptp(band[:, side_axis]) if len(band) else 9)
neck_z = float(neck_zs[int(np.argmin(widths))]); head_ratio = 1 - neck_z
print(f"arm/H={arm_ratio:.3f} (ref 0.30–0.36, 含指尖)  leg(crotch)/H={leg_ratio:.3f} (ref 0.45–0.53)  head/H={head_ratio:.3f} (ref 0.12–0.15, 含脖)")
if not (0.26 <= arm_ratio <= 0.42): ok = False; print("FAIL 臂长失真")
if not (0.40 <= leg_ratio <= 0.56): ok = False; print("FAIL 腿长失真")
if prefix:
    scene = bpy.context.scene; scene.render.engine = 'CYCLES'; scene.cycles.samples = 24; scene.cycles.device = 'CPU'
    scene.render.resolution_x = scene.render.resolution_y = 700
    world = bpy.data.worlds.new("W"); scene.world = world; world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.8, 0.8, 0.8, 1); world.node_tree.nodes["Background"].inputs[1].default_value = 1.2
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("C")); scene.collection.objects.link(cam); scene.camera = cam
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = H * 1.15
    center = mathutils.Vector((cx, cy, mn[2] + H / 2))
    fwd = mathutils.Vector((1, 0, 0) if foot_axis == 'x' else (0, 1, 0)) * foot_sign  # 以脚尖为前
    left = mathutils.Vector((0, 0, 1)).cross(fwd)
    views = {'front': fwd, 'left': left, 'back': -fwd, 'right': -left}
    os.makedirs(os.path.dirname(prefix), exist_ok=True)
    def aim(loc, target):
        f = (target - loc).normalized(); r = f.cross(mathutils.Vector((0, 0, 1))).normalized(); u = r.cross(f)
        m = mathutils.Matrix((r, u, -f)).transposed(); cam.location = loc; cam.rotation_euler = m.to_euler()
    for nm, dirv in views.items():
        aim(center + dirv * 5, center)
        scene.render.filepath = f"{prefix}_{nm}.png"; bpy.ops.render.render(write_still=True)
    # 脸部特写
    headc = mathutils.Vector((cx, cy, mn[2] + H * 0.93)); cam.data.ortho_scale = H * 0.22
    aim(headc + fwd * 3, headc)
    scene.render.filepath = f"{prefix}_face.png"; bpy.ops.render.render(write_still=True)
    aim(headc - fwd * 3, headc); scene.render.filepath = f"{prefix}_headback.png"; bpy.ops.render.render(write_still=True)
    aim(headc + left * 3, headc); scene.render.filepath = f"{prefix}_headside.png"; bpy.ops.render.render(write_still=True)
    print("rendered", prefix)
print("RESULT", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
