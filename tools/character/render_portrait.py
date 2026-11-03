import bpy, sys, mathutils
blend, prefix = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=blend)
for o in list(bpy.data.objects):
    if o.type in ('CAMERA','LIGHT') or o.name.startswith("Plane"): bpy.data.objects.remove(o)
scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=64; scene.cycles.use_denoising=True
w=bpy.data.worlds.get("W") or bpy.data.worlds.new("W"); scene.world=w; w.use_nodes=True
bg=w.node_tree.nodes["Background"]; bg.inputs[0].default_value=(0.10,0.10,0.11,1); bg.inputs[1].default_value=0.8
eyes=[o for o in bpy.data.objects if "high-poly" in o.name][0]
ez=sum((eyes.matrix_world@vv.co).z for vv in eyes.data.vertices)/len(eyes.data.vertices)
Tg=mathutils.Vector((0,0,ez-0.03))
def light(n,loc,e,col=(1,1,1),size=1.0):
    l=bpy.data.lights.new(n,'AREA'); l.energy=e; l.size=size; l.color=col; o=bpy.data.objects.new(n,l); scene.collection.objects.link(o); o.location=loc
    d=Tg-o.location; o.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
light("key",(0.5,-1.3,ez+0.6),110,(1,0.95,0.9),size=1.4); light("fill",(-1.3,-1.1,ez),45,(0.85,0.9,1.0),size=2.0); light("rim",(-0.4,1.3,ez+0.7),80,(1,0.97,0.9),size=0.8)
cam=bpy.data.cameras.new("c"); co=bpy.data.objects.new("c",cam); scene.collection.objects.link(co); scene.camera=co
for tag,loc,lens in [("f",(0.18,-1.05,ez+0.03),110),("q",(0.65,-0.85,ez+0.06),95)]:
    co.location=loc; cam.lens=lens; d=Tg-co.location; co.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
    scene.render.resolution_x=scene.render.resolution_y=800; scene.render.filepath=f"{prefix}_{tag}.png"; bpy.ops.render.render(write_still=True)
