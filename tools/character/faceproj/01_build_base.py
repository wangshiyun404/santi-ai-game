# 第 1 步：按 O 变体建叶文洁基础体（不带头发/衣服），供面部贴图投射与标定
# 用法: /tmp/bpyenv/bin/python 01_build_base.py <variants.json> <variant_name> <out.blend>
import bpy, os, sys, json
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService
from bl_ext.user_default.mpfb.services.materialservice import MaterialService
from bl_ext.user_default.mpfb.entities.material.makeskinmaterial import MakeSkinMaterial
from bl_ext.user_default.mpfb.services.faceservice import FaceService
D = os.path.expanduser("~/.config/blender/5.0/extensions/.user/user_default/mpfb/data")
cfg = json.load(open(sys.argv[-3])); v = [x for x in cfg["variants"] if x["name"] == sys.argv[-2]][0]
OUT = sys.argv[-1]
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
macro = TargetService.get_default_macro_info_dict(); macro.update(v["macro"])
macro["race"] = {"asian": 1.0, "caucasian": 0.0, "african": 0.0}
h = HumanService.create_human(macro_detail_dict=macro); h.name = "YeWenjie"
for n, w in v["targets"].items():
    p = TargetService.target_full_path(n)
    if not p: print("NO TARGET", n); continue
    TargetService.load_target(h, p, weight=w)
HumanService.set_character_skin(v["skin"], h, skin_type="ENHANCED_SSS")
def A(path, atype): return HumanService.add_mhclo_asset(path, h, asset_type=atype, subdiv_levels=0, material_type="MAKESKIN")
eyes = A(f"{D}/eyes/high-poly/high-poly.mhclo", "Eyes")
MaterialService.delete_all_materials(eyes); m = MakeSkinMaterial(); m.populate_from_mhmat(f"{D}/eyes/materials/{v.get('eyemat','brown')}.mhmat")
mat = MaterialService.create_empty_material("eyes", eyes); m.apply_node_tree(mat)
A(f"{D}/eyebrows/{v['brow']}/{v['brow']}.mhclo", "Eyebrows")
A(f"{D}/eyelashes/{v.get('lash','eyelashes02')}/{v.get('lash','eyelashes02')}.mhclo", "Eyelashes")
A(f"{D}/teeth/teeth_base/teeth_base.mhclo", "Teeth"); A(f"{D}/tongue/tongue01/tongue01.mhclo", "Tongue")
if v.get("rest_expr"): FaceService.set_expression(h, v["rest_expr"]); print("rest expression", v["rest_expr"])
zs = [vv.co.z for vv in h.data.vertices]; print("height", max(zs))
bpy.ops.wm.save_as_mainfile(filepath=OUT); print("saved", OUT)
