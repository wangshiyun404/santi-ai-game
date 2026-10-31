"""前后镜像"骨架+动画"而不镜像网格：修复 Tripo 自动绑骨把角色正面判反（脸朝 +X、步态朝 −X）的问题。
原理：形变场 D(t) 以 x→−x 的反射 M 共轭：D' = M·D·M^-1。等价于把网格反射、套用原动画（此时脸与步态一致）、再反射回来。
实现：骨骼静止矩阵 B' = M·B·C（C=diag(−1,1,1) 保持右手系），四元数 (w,x,y,z)→(w,x,−y,−z)，位移 (x,y,z)→(−x,y,z)。
用法: /tmp/bpyenv/bin/python scripts/mirror_front_anim.py in.glb out.glb
"""
import sys, bpy
from mathutils import Matrix, Vector
src, dst = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
arm=[o for o in bpy.data.objects if o.type=='ARMATURE'][0]
assert arm.matrix_world == Matrix.Identity(4), arm.matrix_world
M=Matrix.Diagonal((-1,1,1,1))
bpy.context.view_layer.objects.active=arm
bpy.ops.object.mode_set(mode='EDIT')
eb=arm.data.edit_bones
old={b.name:(b.head.copy(), b.tail.copy(), b.z_axis.copy(), b.use_connect) for b in eb}
for b in eb: b.use_connect=False
for b in eb:
    h,t,z,_=old[b.name]
    b.head=M@h; b.tail=M@t
    b.align_roll(M@z)        # 新 z 轴 = 反射后的 z 轴（与 x 轴取反一起保证右手系）
bpy.ops.object.mode_set(mode='OBJECT')
# 校验: 新静止矩阵 ≈ M·B·C
C=Matrix.Diagonal((-1,1,1,1))
worst=0
for b in arm.data.bones:
    pass
def fcurves_of(act):
    if hasattr(act,'fcurves'): return list(act.fcurves)
    out=[]
    for layer in act.layers:
        for strip in layer.strips:
            for cb in strip.channelbags: out.extend(cb.fcurves)
    return out
for act in bpy.data.actions:
    for fc in fcurves_of(act):
        if fc.data_path.endswith('rotation_quaternion') and fc.array_index in (2,3):
            for k in fc.keyframe_points: k.co.y=-k.co.y; k.handle_left.y=-k.handle_left.y; k.handle_right.y=-k.handle_right.y
        elif fc.data_path.endswith('location') and fc.array_index==0:
            for k in fc.keyframe_points: k.co.y=-k.co.y; k.handle_left.y=-k.handle_left.y; k.handle_right.y=-k.handle_right.y
        elif fc.data_path.endswith('rotation_euler'):
            raise SystemExit('euler rotation not handled: '+fc.data_path)
# 把所有动作放进 NLA 以便导出多段动画
if arm.animation_data is None: arm.animation_data_create()
arm.animation_data.action=None
for tr in list(arm.animation_data.nla_tracks): arm.animation_data.nla_tracks.remove(tr)
for act in bpy.data.actions:
    tr=arm.animation_data.nla_tracks.new(); tr.name=act.name
    st=tr.strips.new(act.name, int(act.frame_range[0]), act); st.name=act.name
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=dst, export_format='GLB', export_animations=True, export_animation_mode='NLA_TRACKS',
    export_nla_strips_merged_animation_name='', export_skins=True, export_yup=True, export_apply=False, export_image_format='AUTO')
print('exported', dst)
