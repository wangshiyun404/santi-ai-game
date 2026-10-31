"""步态/朝向量化核验（REA E23 复盘后固化）：对 Tripo Anim GLB 逐剪辑计算
  toes_dx    = 脚尖骨(ToeBase) − 脚踝骨(Foot) 的 x 均值           → 应与脸同向
  planted_dx = 着地脚(脚踝 z 接近该剪辑最低值)相邻帧 x 位移均值     → 原地动画里地面向后流，应与脸反向
  lean_dx    = 头骨 − 髋骨 x 均值                                 → 跑步应向脸的方向前倾
用法: /tmp/bpyenv/bin/python scripts/gait_check.py <anim.glb> [+X|-X]   （默认脸朝 glTF/Blender +X）
退出码 0=PASS 1=FAIL。E23 教训：只看"脸朝哪"不够，必须逐剪辑量化步态。
"""
import sys, bpy, numpy as np
path=sys.argv[1]; face=-1 if (len(sys.argv)>2 and sys.argv[2].startswith('-')) else 1
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
arm=[o for o in bpy.data.objects if o.type=='ARMATURE'][0]
def B(n):
    for cand in (f'mixamorig:{n}', n):
        if cand in arm.pose.bones: return arm.pose.bones[cand]
    raise KeyError(n)
def wpos(pb): return np.array(arm.matrix_world @ pb.head)
ok=True
for act in bpy.data.actions:
    arm.animation_data.action=act
    f0,f1=map(int,act.frame_range); rows=[]
    for f in range(f0,f1+1):
        bpy.context.scene.frame_set(f); bpy.context.view_layer.update()
        rows.append({s:(wpos(B(f'{s}Foot')),wpos(B(f'{s}ToeBase'))) for s in ('Left','Right')} | {'hips':wpos(B('Hips')),'head':wpos(B('Head'))})
    toes=np.mean([r[s][1][0]-r[s][0][0] for r in rows for s in ('Left','Right')])
    planted=[]
    for s in ('Left','Right'):
        z=np.array([r[s][0][2] for r in rows]); x=np.array([r[s][0][0] for r in rows]); low=z<z.min()+0.03
        planted+= [x[i]-x[i-1] for i in range(1,len(rows)) if low[i] and low[i-1]]
    lean=np.mean([r['head'][0]-r['hips'][0] for r in rows])
    v=dict(frames=len(rows),toes_dx=round(float(toes),3),planted_dx=round(float(np.mean(planted)),4) if planted else 0.0,n_planted=len(planted),lean_dx=round(float(lean),3))
    bad=[]
    moving='idle' not in act.name.lower()
    if v['toes_dx']*face<=0: bad.append('脚尖与脸反向')
    if moving and v['n_planted'] and v['planted_dx']*face>=0: bad.append('着地脚滑移=倒退')
    if 'run' in act.name.lower() and v['lean_dx']*face<0: bad.append('跑步后仰')
    if bad: ok=False
    print(act.name, v, 'OK' if not bad else ' / '.join(bad))
print('RESULT', 'PASS' if ok else 'FAIL', f'(face {"+" if face>0 else "-"}X)')
sys.exit(0 if ok else 1)
