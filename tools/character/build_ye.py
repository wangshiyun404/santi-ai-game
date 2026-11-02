import bpy, math, sys, os, mathutils
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService
from bl_ext.user_default.mpfb.services.faceservice import FaceService
D=os.path.expanduser("~/.config/blender/5.0/extensions/.user/user_default/mpfb/data")
OUT="/tmp/ye"
RIG=os.environ.get("YE_RIG","mixamo_unity")
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
macro=TargetService.get_default_macro_info_dict()
macro.update(gender=0.08, age=0.52, muscle=0.45, weight=0.44, proportions=0.75, height=0.48, cupsize=0.4, firmness=0.6)
macro["race"]={"asian":1.0,"caucasian":0.0,"african":0.0}
h=HumanService.create_human(macro_detail_dict=macro)
h.name="YeWenjie"
# 细节微调：脸型
for tgt,w in [("cheek/l-cheek-bones-decr|incr",0.15),("cheek/r-cheek-bones-decr|incr",0.15),("chin/chin-width-decr|incr",-0.1),("mouth/mouth-scale-horiz-decr|incr",-0.05)]:
    try: TargetService.load_target(h,tgt,weight=w)
    except Exception as e: print("tgt skip",tgt,e)
rig=HumanService.add_builtin_rig(h,RIG)
HumanService.set_character_skin(f"{D}/skins/young_asian_female/young_asian_female.mhmat",h,skin_type="ENHANCED_SSS")
def asset(path,atype,**kw):
    o=HumanService.add_mhclo_asset(path,h,asset_type=atype,subdiv_levels=0,material_type="MAKESKIN",**kw); print("asset",atype,o.name); return o
eyes=asset(f"{D}/eyes/high-poly/high-poly.mhclo","Eyes")
try:
    from bl_ext.user_default.mpfb.services.materialservice import MaterialService
    from bl_ext.user_default.mpfb.entities.material.makeskinmaterial import MakeSkinMaterial
    MaterialService.delete_all_materials(eyes); m=MakeSkinMaterial(); m.populate_from_mhmat(f"{D}/eyes/materials/brown.mhmat"); mat=MaterialService.create_empty_material("eyes_brown",eyes); m.apply_node_tree(mat); print("eyes brown ok")
except Exception as e: print("eye mat err",e)
asset(f"{D}/eyebrows/eyebrow003/eyebrow003.mhclo","Eyebrows")
asset(f"{D}/eyelashes/eyelashes02/eyelashes02.mhclo","Eyelashes")
asset(f"{D}/teeth/teeth_base/teeth_base.mhclo","Teeth")
asset(f"{D}/tongue/tongue01/tongue01.mhclo","Tongue")
hair=asset(f"{D}/hair/braid01/braid01.mhclo","Hair")
suit=asset(f"{D}/clothes/male_casualsuit05/male_casualsuit05.mhclo","Clothes")
shoes=asset(f"{D}/clothes/shoes03/shoes03.mhclo","Clothes")
# 外套换成橄榄绿贴图
for mat in suit.data.materials:
    for n in mat.node_tree.nodes:
        if n.type=='TEX_IMAGE' and n.image and 'diffuse' in n.image.filepath.lower():
            img=bpy.data.images.load(f"{OUT}/suit_olive.png"); n.image=img; print("recolored",mat.name)
# 表情：专注、略带忧虑
try:
    FaceService.set_expression(h,{"eyebrows-left-down":0.25,"eyebrows-right-down":0.25,"mouth-smile":0.0,"eye-left-closure":0.05,"eye-right-closure":0.05})
    print("expr ok")
except Exception as e: print("expr err",e)
print("height",max(v.co.z for v in h.data.vertices))
bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}/ye_{RIG}.blend")
print("saved")
