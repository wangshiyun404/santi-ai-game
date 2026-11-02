import bpy, math, sys, mathutils
blend=sys.argv[-2]; prefix=sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=blend)
scene=bpy.context.scene
scene.render.engine='CYCLES'; scene.cycles.samples=96; scene.cycles.use_denoising=True; scene.cycles.device='CPU'
scene.render.film_transparent=False
w=scene.world or bpy.data.worlds.new("W"); scene.world=w; w.use_nodes=True
bg=w.node_tree.nodes["Background"]; bg.inputs[0].default_value=(0.08,0.085,0.09,1); bg.inputs[1].default_value=0.6
cam=bpy.data.cameras.new("c"); co=bpy.data.objects.new("c",cam); scene.collection.objects.link(co); scene.camera=co
def look(loc,target,lens):
    co.location=loc; cam.lens=lens
    d=mathutils.Vector(target)-co.location; co.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
def light(n,loc,e,col=(1,1,1),size=1.2,target=(0,0,1.0)):
    l=bpy.data.lights.new(n,'AREA'); l.energy=e; l.size=size; l.color=col; o=bpy.data.objects.new(n,l); scene.collection.objects.link(o); o.location=loc
    d=mathutils.Vector(target)-o.location; o.rotation_euler=d.to_track_quat('-Z','Y').to_euler(); return o
light("key",(1.8,-2.0,2.3),650,(1,0.93,0.85)); light("fill",(-2.4,-1.6,1.3),140,(0.75,0.85,1.0),size=2.5); light("rim",(0.6,2.2,2.4),500,(0.9,0.95,1.0))
# 地面
bpy.ops.mesh.primitive_plane_add(size=8); pl=bpy.context.object; m=bpy.data.materials.new("floor"); m.use_nodes=True; m.node_tree.nodes["Principled BSDF"].inputs[0].default_value=(0.12,0.12,0.13,1); m.node_tree.nodes["Principled BSDF"].inputs[2].default_value=0.7; pl.data.materials.append(m)
shots={"front":((0.0,-4.2,1.05),(0,0,0.9),60,(900,1350)),"three_quarter":((2.6,-3.3,1.1),(0,0,0.9),60,(900,1350)),"back":((0.4,4.2,1.05),(0,0,0.9),60,(900,1350)),"face":((0.35,-1.05,1.56),(0,0,1.53),105,(1200,1200))}
for name,(loc,tgt,lens,res) in shots.items():
    look(loc,tgt,lens); scene.render.resolution_x,scene.render.resolution_y=res
    scene.render.filepath=f"{prefix}_{name}.png"; bpy.ops.render.render(write_still=True)
