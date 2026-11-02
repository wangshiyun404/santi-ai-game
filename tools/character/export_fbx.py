import bpy
bpy.ops.wm.open_mainfile(filepath="/tmp/ye/ye_mixamo_unity.blend")
for o in list(bpy.data.objects):
    if o.type in ('CAMERA','LIGHT') or o.name.startswith("Plane"): bpy.data.objects.remove(o)
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:
    if o.type in ('MESH','ARMATURE'): o.select_set(True)
bpy.ops.export_scene.fbx(filepath="/tmp/ye/ye_wenjie_mh.fbx",use_selection=True,apply_scale_options='FBX_SCALE_ALL',bake_space_transform=True,object_types={'ARMATURE','MESH'},use_mesh_modifiers=True,add_leaf_bones=False,bake_anim=False,path_mode='COPY',embed_textures=True,mesh_smooth_type='FACE')
import os; print("fbx",os.path.getsize("/tmp/ye/ye_wenjie_mh.fbx")/1e6,"MB")
print("bones",len([a for a in bpy.data.objects if a.type=='ARMATURE'][0].data.bones))
print("tris",sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in bpy.data.objects if o.type=='MESH'))
