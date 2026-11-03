# 叶文洁 v2：面部造型 K（faces_v5.json）+ 全身服装 + mixamo_unity 骨架
import bpy, os, sys, json, mathutils
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService
from bl_ext.user_default.mpfb.services.faceservice import FaceService
from bl_ext.user_default.mpfb.services.materialservice import MaterialService
from bl_ext.user_default.mpfb.entities.material.makeskinmaterial import MakeSkinMaterial
D=os.path.expanduser("~/.config/blender/5.0/extensions/.user/user_default/mpfb/data")
cfg=json.load(open(sys.argv[-2])); v=[x for x in cfg["variants"] if x["name"]==sys.argv[-1]][0]
OUT="/tmp/ye"
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
macro=TargetService.get_default_macro_info_dict(); macro.update(v["macro"]); macro["race"]={"asian":1.0,"caucasian":0.0,"african":0.0}
h=HumanService.create_human(macro_detail_dict=macro); h.name="YeWenjie"
for n,w in v["targets"].items():
    p=TargetService.target_full_path(n); TargetService.load_target(h,p,weight=w)
rig=HumanService.add_builtin_rig(h,"mixamo_unity")
HumanService.set_character_skin(v["skin"],h,skin_type="ENHANCED_SSS")
def A(path,atype): return HumanService.add_mhclo_asset(path,h,asset_type=atype,subdiv_levels=0,material_type="MAKESKIN")
eyes=A(f"{D}/eyes/high-poly/high-poly.mhclo","Eyes")
MaterialService.delete_all_materials(eyes); m=MakeSkinMaterial(); m.populate_from_mhmat(f"{D}/eyes/materials/brown.mhmat"); mat=MaterialService.create_empty_material("eyes",eyes); m.apply_node_tree(mat)
A(f"{D}/eyebrows/{v['brow']}/{v['brow']}.mhclo","Eyebrows"); A(f"{D}/eyelashes/eyelashes02/eyelashes02.mhclo","Eyelashes")
A(f"{D}/teeth/teeth_base/teeth_base.mhclo","Teeth"); A(f"{D}/tongue/tongue01/tongue01.mhclo","Tongue")
ho=A(f"{D}/hair/{v['hair']}/{v['hair']}.mhclo","Hair")
for mt in ho.data.materials:
    for n in mt.node_tree.nodes:
        if n.type=='BSDF_PRINCIPLED':
            n.inputs["Roughness"].default_value=v.get("hair_rough",0.8)
            if "Specular IOR Level" in n.inputs: n.inputs["Specular IOR Level"].default_value=v.get("hair_spec",0.12)
        if v.get("hair_tex") and n.type=='TEX_IMAGE' and n.image and ('diff' in n.image.filepath.lower() or 'hair.png' in n.image.filepath.lower()): n.image=bpy.data.images.load(v["hair_tex"])
md=ho.modifiers.new("subd",'SUBSURF'); md.levels=md.render_levels=1
suit=A(f"{D}/clothes/male_casualsuit05/male_casualsuit05.mhclo","Clothes")
for mt in suit.data.materials:
    for n in mt.node_tree.nodes:
        if n.type=='TEX_IMAGE' and n.image and 'diffuse' in n.image.filepath.lower(): n.image=bpy.data.images.load(f"{OUT}/suit_olive.png")
A(f"{D}/clothes/shoes03/shoes03.mhclo","Clothes")
FaceService.set_expression(h,{"mouth-smile":0.08,"eyebrows-left-down":0.1,"eyebrows-right-down":0.1})
print("height",max(vv.co.z for vv in h.data.vertices))
bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}/ye_v2.blend"); print("saved")
