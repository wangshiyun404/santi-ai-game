"""把 Tripo 原始角色网格"脖子以下"前后镜像（x→2·xc−x），保留头部不动。
用途：主角原始网格脚/腿朝 −X、脸朝 +X（REA E23）。只镜像脚不够——Tripo 绑骨仍判前向为 −X，
所以把躯干+四肢整体镜像到与脸一致，脖子藏在围巾里，接缝不可见。
用法: /tmp/bpyenv/bin/python scripts/mirror_body_glb.py in.glb out.glb [neck_height_ratio=0.855]
"""
import sys, bpy, numpy as np
src, dst = sys.argv[1], sys.argv[2]; ratio = float(sys.argv[3]) if len(sys.argv) > 3 else 0.855
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
meshes=[o for o in bpy.data.objects if o.type=='MESH']
allv=np.array([o.matrix_world@v.co for o in meshes for v in o.data.vertices]); zmin,zmax=allv[:,2].min(),allv[:,2].max()
H=zmax-zmin; zcut=zmin+ratio*H
band=allv[(allv[:,2]>zcut-0.01*H)&(allv[:,2]<zcut+0.01*H)]; xc=float(band[:,0].mean())
print(f'height {H:.3f} cut z={zcut:.3f} neck center x={xc:.4f} (band verts {len(band)})')
n_flip=0
for o in meshes:
    me=o.data; mw=o.matrix_world; inv=mw.inverted()
    co=np.array([mw@v.co for v in me.vertices])
    flip_poly=[]
    for p in me.polygons:
        c=co[list(p.vertices)].mean(0)
        if c[2]<zcut: flip_poly.append(p.index)
    vflip=set()
    for pi in flip_poly: vflip.update(me.polygons[pi].vertices)
    for vi in vflip:
        w=co[vi].copy(); w[0]=2*xc-w[0]; me.vertices[vi].co=inv@__import__('mathutils').Vector(w)
    # 翻转受影响面的环绕方向（镜像改变手性）
    for pi in flip_poly: me.polygons[pi].flip()
    me.update(); n_flip+=len(flip_poly)
print('flipped polys',n_flip)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=dst, export_format='GLB', export_yup=True, export_apply=False, export_image_format='AUTO', export_normals=True, export_texcoords=True)
print('exported',dst)
