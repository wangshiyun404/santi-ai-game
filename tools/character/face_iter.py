# 面部造型迭代：一次生成多个变体的脸部特写（仅头部渲染，快）
import bpy, os, sys, json, mathutils
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService
from bl_ext.user_default.mpfb.services.faceservice import FaceService
from bl_ext.user_default.mpfb.services.materialservice import MaterialService
from bl_ext.user_default.mpfb.entities.material.makeskinmaterial import MakeSkinMaterial
D=os.path.expanduser("~/.config/blender/5.0/extensions/.user/user_default/mpfb/data")
cfg=json.load(open(sys.argv[-1])); OUT=cfg["out"]; os.makedirs(OUT,exist_ok=True)
SAMPLES=cfg.get("samples",64); RES=cfg.get("res",800)

def T(h,name,w):
    p=TargetService.target_full_path(name)
    if not p: print("NO TARGET",name); return
    TargetService.load_target(h,p,weight=w)

def build(v):
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
    for b in (bpy.data.meshes,bpy.data.materials,bpy.data.images):
        for x in list(b):
            if x.users==0: b.remove(x)
    macro=TargetService.get_default_macro_info_dict()
    macro.update(v.get("macro",{})); macro["race"]={"asian":1.0,"caucasian":0.0,"african":0.0}
    h=HumanService.create_human(macro_detail_dict=macro); h.name="Ye"
    for n,w in v.get("targets",{}).items(): T(h,n,w)
    skin=v.get("skin",f"{D}/skins/young_asian_female/young_asian_female.mhmat")
    HumanService.set_character_skin(skin,h,skin_type="ENHANCED_SSS")
    def A(path,atype):
        return HumanService.add_mhclo_asset(path,h,asset_type=atype,subdiv_levels=0,material_type="MAKESKIN")
    eyes=A(f"{D}/eyes/high-poly/high-poly.mhclo","Eyes")
    MaterialService.delete_all_materials(eyes); m=MakeSkinMaterial(); m.populate_from_mhmat(v.get("eyemat",f"{D}/eyes/materials/brown.mhmat")); mat=MaterialService.create_empty_material("eyes",eyes); m.apply_node_tree(mat)
    A(f"{D}/eyebrows/{v.get('brow','eyebrow001')}/{v.get('brow','eyebrow001')}.mhclo","Eyebrows")
    A(f"{D}/eyelashes/{v.get('lash','eyelashes02')}/{v.get('lash','eyelashes02')}.mhclo","Eyelashes")
    A(f"{D}/teeth/teeth_base/teeth_base.mhclo","Teeth"); A(f"{D}/tongue/tongue01/tongue01.mhclo","Tongue")
    hair=v.get("hair","long01"); hp=v.get("hair_path",f"{D}/hair/{hair}/{hair}.mhclo")
    ho=A(hp,"Hair")
    # 头发材质：降高光、双面、细分平滑
    for mt in ho.data.materials:
        for n in mt.node_tree.nodes:
            if n.type=='BSDF_PRINCIPLED':
                n.inputs["Roughness"].default_value=v.get("hair_rough",0.6)
                if "Specular IOR Level" in n.inputs: n.inputs["Specular IOR Level"].default_value=v.get("hair_spec",0.3)
    if v.get("hair_tex"):
        for mt in ho.data.materials:
            for n in mt.node_tree.nodes:
                if n.type=='TEX_IMAGE' and n.image and ('diff' in n.image.filepath.lower() or 'hair.png' in n.image.filepath.lower()):
                    n.image=bpy.data.images.load(v["hair_tex"]); print("hair tex replaced")
    if v.get("hair_subdiv",1):
        md=ho.modifiers.new("subd",'SUBSURF'); md.levels=md.render_levels=1
    if v.get("suit",True):
        so=A(f"{D}/clothes/male_casualsuit05/male_casualsuit05.mhclo","Clothes")
        for mt in so.data.materials:
            for n in mt.node_tree.nodes:
                if n.type=='TEX_IMAGE' and n.image and 'diffuse' in n.image.filepath.lower(): n.image=bpy.data.images.load("/tmp/ye/suit_olive.png")
    if v.get("expr"): FaceService.set_expression(h,v["expr"])
    # 皮肤微调：略暖、略红唇（通过材质节点）
    return h

def render(h,name):
    scene=bpy.context.scene
    scene.render.engine='CYCLES'; scene.cycles.samples=SAMPLES; scene.cycles.use_denoising=True
    w=bpy.data.worlds.get("W") or bpy.data.worlds.new("W"); scene.world=w; w.use_nodes=True
    bg=w.node_tree.nodes["Background"]; bg.inputs[0].default_value=(0.10,0.10,0.11,1); bg.inputs[1].default_value=0.8
    eyes=[o for o in bpy.data.objects if "high-poly" in o.name][0]
    ez=sum((eyes.matrix_world@vv.co).z for vv in eyes.data.vertices)/len(eyes.data.vertices)
    Tg=mathutils.Vector((0,0,ez-0.03))
    def light(n,loc,e,col=(1,1,1),size=1.0):
        l=bpy.data.lights.new(n,'AREA'); l.energy=e; l.size=size; l.color=col; o=bpy.data.objects.new(n,l); scene.collection.objects.link(o); o.location=loc
        d=Tg-o.location; o.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
    # 人像三灯：柔和主光偏正面上方（蝴蝶光），大面积补光，发丝轮廓光
    light("key",(0.5,-1.3,ez+0.6),110,(1,0.95,0.9),size=1.4); light("fill",(-1.3,-1.1,ez),45,(0.85,0.9,1.0),size=2.0); light("rim",(-0.4,1.3,ez+0.7),80,(1,0.97,0.9),size=0.8)
    cam=bpy.data.cameras.new("c"); co=bpy.data.objects.new("c",cam); scene.collection.objects.link(co); scene.camera=co
    for tag,loc,lens in [("f",(0.18,-1.05,ez+0.03),110),("q",(0.65,-0.85,ez+0.06),95)]:
        co.location=loc; cam.lens=lens; d=Tg-co.location; co.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
        scene.render.resolution_x=scene.render.resolution_y=RES; scene.render.filepath=f"{OUT}/{name}_{tag}.png"; bpy.ops.render.render(write_still=True)

for v in cfg["variants"]:
    print("=== variant",v["name"]); h=build(v); render(h,v["name"])
    if v.get("save"): bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}/{v['name']}.blend")
print("DONE")
