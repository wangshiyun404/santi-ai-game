"""REA 台账 Q2：给 Tripo 角色加几何五官（贴在脸面上的薄片），导出 assets/face/<name>_face.glb。
用法：blender-python scripts/face_patches.py <name> [eyeZ_offset] [mouthZ_offset]
思路：沿模型 +X（脸的朝向）向 -X 打射线取脸面采样点，按法线外推 1.5 mm 组成薄片网格；
眼白/瞳孔/闭眼线/嘴线/张嘴 各为独立物体，运行时由 FaceExpression 切换可见性做表情。"""
import bpy, sys, json, math
from mathutils import Vector
import numpy as np

name = sys.argv[-1]
# 每个角色的标定（E12 核验渲染得出）：眼线/嘴线 = Head 骨骼原点 + k × 头骨长度；眼距为半距
CONFIG = {
    'char_player':    dict(eyeK=0.26, mouthK=0.08, eyeSep=0.020, size=1.0),
    'char_newton':    dict(eyeK=0.30, mouthK=0.06, eyeSep=0.022, size=1.1),
    'char_qin':       dict(eyeK=0.30, mouthK=0.10, eyeSep=0.020, size=1.0),
    'char_ye_wenjie': dict(eyeK=0.22, mouthK=0.07, eyeSep=0.019, size=0.95),
}
cfg = CONFIG[name]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=f'assets/tripo/anim/{name}_anim.glb')
bpy.context.view_layer.update()
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
arm.data.pose_position = 'REST'   # 导入后停在 idle 第 1 帧，头会偏；必须回到绑定姿态（Unity 侧按 bindpose 挂接）
bpy.context.view_layer.update()
mesh = max([o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith('Icosphere')], key=lambda o: len(o.data.vertices))
inv = mesh.matrix_world.inverted()
head = arm.data.bones['mixamorig:Head']
hz = (arm.matrix_world @ head.head_local).z; tz = (arm.matrix_world @ head.tail_local).z
P = np.array([tuple(mesh.matrix_world @ v.co) for v in mesh.data.vertices])
Hv = P[(P[:, 2] > hz - 0.01) & (P[:, 2] < hz + 0.6 * (tz - hz)) & (np.abs(P[:, 1]) < 0.12)]
xmax = float(Hv[:, 0].max()); Fv = Hv[Hv[:, 0] > xmax - 0.04]
hy = float(np.median(Fv[:, 1]))     # 脸正面中心 y（不是骨骼 y：有的模型脸偏一侧）

from mathutils.bvhtree import BVHTree
_dg = bpy.context.evaluated_depsgraph_get(); _bvh = BVHTree.FromObject(mesh, _dg)
def cast(y, z, x0=1.0):
    loc, nrm, idx, dist = _bvh.ray_cast(Vector((x0, y, z)), Vector((-1, 0, 0)))
    if loc is None: return None
    return loc, nrm.normalized()

eyeZ = hz + cfg['eyeK'] * (tz - hz); mouthZ = hz + cfg['mouthK'] * (tz - hz); eyeSep = cfg['eyeSep']; S = cfg['size']
noseZ = (eyeZ + mouthZ) / 2
# 脸中线：在鼻梁高度横向扫描，取最靠前（x 最大）的 y（REST 姿态下）
scan = [(y, cast(y, noseZ)) for y in np.arange(-0.08, 0.0801, 0.004)]
scan = [(y, r[0].x) for y, r in scan if r]
hy, noseX = max(scan, key=lambda t: t[1]) if scan else (hy, xmax)
hy = float(hy)

def patch(objname, cy, cz, a, b, color, offset=0.0015, nu=None, nv=None, taper=False):
    """椭圆薄片：中心 + 2 圈 × 24 角采样，贴合脸面后沿法线外推 offset。半轴 a（横 y）、b（竖 z）。"""
    verts = []; rings = []
    r0 = cast(cy, cz)
    if not r0: print(f'WARN {objname}: center miss'); 
    center = (r0[0] + r0[1] * offset) if r0 else Vector((noseX, cy, cz))
    verts.append(center)
    NA = 24
    for k, rr in enumerate((0.5, 1.0)):
        ring = []
        for i in range(NA):
            t = 2 * math.pi * i / NA
            r = cast(cy + a * rr * math.cos(t), cz + b * rr * math.sin(t))
            if r: p = r[0] + r[1] * offset
            else: p = Vector((center.x, cy + a * rr * math.cos(t), cz + b * rr * math.sin(t)))
            ring.append(len(verts)); verts.append(p)
        rings.append(ring)
    faces = []
    for i in range(NA):
        j = (i + 1) % NA
        faces.append([0, rings[0][i], rings[0][j]])
        faces.append([rings[0][i], rings[1][i], rings[1][j], rings[0][j]])
    me = bpy.data.meshes.new(objname); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    ob = bpy.data.objects.new(objname, me); bpy.context.scene.collection.objects.link(ob)
    mat = bpy.data.materials.new(objname + '_mat'); mat.use_nodes = True
    bsdf = mat.node_tree.nodes['Principled BSDF']; bsdf.inputs['Base Color'].default_value = (*color, 1); bsdf.inputs['Metallic'].default_value = 0; bsdf.inputs['Roughness'].default_value = 0.6
    me.materials.append(mat)
    return ob

W = (0.93, 0.92, 0.88); K = (0.06, 0.05, 0.05); M = (0.30, 0.10, 0.09)
objs = []
for side, sy in (('L', +eyeSep), ('R', -eyeSep)):
    objs.append(patch(f'eye_white_{side}', hy + sy, eyeZ, 0.0108 * S, 0.0066 * S, W, offset=0.0028))
    objs.append(patch(f'pupil_{side}', hy + sy, eyeZ - 0.0005, 0.0042 * S, 0.0042 * S, K, offset=0.0040))
    objs.append(patch(f'eye_closed_{side}', hy + sy, eyeZ - 0.001, 0.0108 * S, 0.0016 * S, K, offset=0.0032))
    objs.append(patch(f'brow_{side}', hy + sy, eyeZ + 0.0105 * S, 0.0105 * S, 0.0015 * S, K, offset=0.0028))
objs.append(patch('mouth_line', hy, mouthZ, 0.0095 * S, 0.0015 * S, M, offset=0.0028))
objs.append(patch('mouth_open', hy, mouthZ - 0.002, 0.0065 * S, 0.0048 * S, K, offset=0.0034))
for o in bpy.data.objects: o.select_set(o in objs)
bpy.ops.export_scene.gltf(filepath=f'assets/face/{name}_face.glb', use_selection=True, export_yup=True, export_apply=True, export_animations=False, export_skins=False, export_materials='EXPORT')
# 导出脸部区域多边形的 UV 三角形（供 scripts/face_skin_fix.py 修贴图：叶文洁脸部贴图为紫色）
uvl = mesh.data.uv_layers.active.data
tris = []
H = tz - hz
for poly in mesh.data.polygons:
    pts = [mesh.matrix_world @ mesh.data.vertices[i].co for i in poly.vertices]
    if all(hz - 0.06 < p.z < hz + 0.62 * H and p.x > noseX - 0.07 and abs(p.y - hy) < 0.075 for p in pts):
        tris.append([[uvl[li].uv.x, uvl[li].uv.y] for li in poly.loop_indices])
json.dump(tris, open(f'assets/face/{name}_face_uv.json', 'w'))
info = {'name': name, 'face_polys': len(tris), 'headZ': round(hz, 3), 'headTopZ': round(tz, 3), 'noseZ': round(float(noseZ), 3), 'noseX': round(float(noseX), 3), 'eyeZ': round(float(eyeZ), 3), 'mouthZ': round(float(mouthZ), 3),
        'faces': {o.name: len(o.data.polygons) for o in objs}}
print('JSON' + json.dumps(info))

# 校验渲染用 Unity 实际使用的外置贴图（可能经 face_skin_fix.py 修过）
import os
texp = os.path.abspath(f'unity/SanTiGame/Assets/Textures/Tripo/{name}_base.png')
if os.path.exists(texp):
    img = bpy.data.images.load(texp)
    for mat in mesh.data.materials:
        bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf is None or not bsdf.inputs['Base Color'].is_linked: continue
        n = bsdf.inputs['Base Color'].links[0].from_node
        while n.type != 'TEX_IMAGE' and n.inputs and any(i.is_linked for i in n.inputs):
            n = next(i for i in n.inputs if i.is_linked).links[0].from_node
        if n.type == 'TEX_IMAGE': n.image = img
# 校验渲染：头部正面 + 3/4 侧
scene = bpy.context.scene; scene.render.engine = 'CYCLES'; scene.cycles.samples = 12; scene.cycles.device = 'CPU'
scene.render.resolution_x = 480; scene.render.resolution_y = 480
world = bpy.data.worlds.new('W'); scene.world = world; world.use_nodes = True; world.node_tree.nodes['Background'].inputs[1].default_value = 1.6
sun = bpy.data.lights.new('s', 'SUN'); so = bpy.data.objects.new('sun', sun); scene.collection.objects.link(so); sun.energy = 3; so.rotation_euler = (0.9, 0.2, 0.6)
# 隐藏闭眼与张嘴，渲染"中性"
for o in objs:
    if o.name.startswith('eye_closed') or o.name == 'mouth_open': o.hide_render = True
def shot(pos, out):
    cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('cam', cam); scene.collection.objects.link(co); scene.camera = co
    co.location = pos; d = Vector((noseX, hy, (eyeZ + mouthZ) / 2)) - Vector(pos); co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler(); cam.lens = 110
    scene.render.filepath = out; bpy.ops.render.render(write_still=True); bpy.data.objects.remove(co)
shot((noseX + 0.5, hy, eyeZ + 0.01), f'/tmp/face_{name}_front.png')
shot((noseX + 0.38, hy - 0.32, eyeZ + 0.04), f'/tmp/face_{name}_34.png')
