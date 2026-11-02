import bpy, sys, mathutils
bpy.ops.wm.open_mainfile(filepath="/tmp/ye/ye_mixamo_unity.blend")
scene=bpy.context.scene
h=bpy.data.objects["YeWenjie"]
# 眼睛高度
eyes=[o for o in bpy.data.objects if "high-poly" in o.name][0]
ez=sum((eyes.matrix_world@v.co).z for v in eyes.data.vertices)/len(eyes.data.vertices); print("eye z",ez)
# 头发减反光
for o in bpy.data.objects:
    if "braid" in o.name:
        for m in o.data.materials:
            for n in m.node_tree.nodes:
                if n.type=='BSDF_PRINCIPLED':
                    n.inputs["Roughness"].default_value=0.75; n.inputs["Specular IOR Level"].default_value=0.25 if "Specular IOR Level" in n.inputs else None
                    print("hair mat fixed")
scene.render.engine='CYCLES'; scene.cycles.samples=128; scene.cycles.use_denoising=True
w=scene.world or bpy.data.worlds.new("W"); scene.world=w; w.use_nodes=True
bg=w.node_tree.nodes["Background"]; bg.inputs[0].default_value=(0.08,0.085,0.09,1); bg.inputs[1].default_value=0.6
cam=bpy.data.cameras.new("c"); co=bpy.data.objects.new("c",cam); scene.collection.objects.link(co); scene.camera=co
def light(n,loc,e,col=(1,1,1),size=1.0,target=None):
    l=bpy.data.lights.new(n,'AREA'); l.energy=e; l.size=size; l.color=col; o=bpy.data.objects.new(n,l); scene.collection.objects.link(o); o.location=loc
    d=mathutils.Vector(target)-o.location; o.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
T=(0,0,ez-0.02)
light("key",(0.9,-1.2,ez+0.5),120,(1,0.93,0.85),target=T); light("fill",(-1.2,-1.0,ez),35,(0.75,0.85,1.0),size=1.5,target=T); light("rim",(0.3,1.2,ez+0.6),90,(0.9,0.95,1.0),target=T)
for name,loc,lens in [("face",(0.25,-0.95,ez+0.02),105),("face34",(0.6,-0.75,ez+0.05),85)]:
    co.location=loc; cam.lens=lens; d=mathutils.Vector(T)-co.location; co.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
    scene.render.resolution_x=scene.render.resolution_y=1100; scene.render.filepath=f"/tmp/ye/ye2_{name}.png"; bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath="/tmp/ye/ye_mixamo_unity.blend")
