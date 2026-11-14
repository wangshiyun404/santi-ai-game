# 第 9 步：定稿 —— 按变体重建叶文洁（mixamo_unity 骨架 → 资产 → 投射贴图），加载 ARKit 52 表情 + 22 口型
# 形态键，渲染表情样张，简化材质后导出带形态键的 FBX（Unity Humanoid 可直接用）。
# 用法: /tmp/bpyenv/bin/python 09_finalize.py <variants.json> <variant> <cams.json> <projected_diffuse.png> <outdir> [samples]
import bpy, os, sys, json, mathutils
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService
from bl_ext.user_default.mpfb.services.faceservice import FaceService
from bl_ext.user_default.mpfb.services.materialservice import MaterialService
from bl_ext.user_default.mpfb.services.exportservice import ExportService
from bl_ext.user_default.mpfb.entities.material.makeskinmaterial import MakeSkinMaterial
D = os.path.expanduser("~/.config/blender/5.0/extensions/.user/user_default/mpfb/data")
VJ, VN, CAMS, TEX, OUT = sys.argv[1:6]; SAMPLES = int(sys.argv[6]) if len(sys.argv) > 6 else 32
os.makedirs(OUT, exist_ok=True)
cfg = json.load(open(VJ)); v = [x for x in cfg["variants"] if x["name"] == VN][0]
SUIT_TEX = "/tmp/ye/suit_olive_v2.png"  # 去条纹领带，改米白衬衫

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
macro = TargetService.get_default_macro_info_dict(); macro.update(v["macro"]); macro["race"] = {"asian": 1.0, "caucasian": 0.0, "african": 0.0}
h = HumanService.create_human(macro_detail_dict=macro); h.name = "YeWenjie"
for n, w in v["targets"].items():
    p = TargetService.target_full_path(n)
    if not p: print("NO TARGET", n); continue
    TargetService.load_target(h, p, weight=w)
TargetService.bake_targets(h)                       # 造型目标烘进基础形，表情键在其上叠加
rig = HumanService.add_builtin_rig(h, "mixamo_unity")   # 先加骨架，之后的资产自动绑定
HumanService.set_character_skin(v["skin"], h, skin_type="ENHANCED_SSS")
def A(path, atype): return HumanService.add_mhclo_asset(path, h, asset_type=atype, subdiv_levels=0, material_type="MAKESKIN")
eyes = A(f"{D}/eyes/high-poly/high-poly.mhclo", "Eyes")
MaterialService.delete_all_materials(eyes); m = MakeSkinMaterial(); m.populate_from_mhmat(f"{D}/eyes/materials/{v.get('eyemat','brown')}.mhmat")
mat = MaterialService.create_empty_material("eyes", eyes); m.apply_node_tree(mat)
brows = A(f"{D}/eyebrows/{v['brow']}/{v['brow']}.mhclo", "Eyebrows")
A(f"{D}/eyelashes/{v.get('lash','eyelashes02')}/{v.get('lash','eyelashes02')}.mhclo", "Eyelashes")
A(f"{D}/teeth/teeth_base/teeth_base.mhclo", "Teeth"); A(f"{D}/tongue/tongue01/tongue01.mhclo", "Tongue")
ho = A(f"{D}/hair/{v['hair']}/{v['hair']}.mhclo", "Hair")
for mt in ho.data.materials:
    for n in mt.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            n.inputs["Roughness"].default_value = v.get("hair_rough", 0.8)
            if "Specular IOR Level" in n.inputs: n.inputs["Specular IOR Level"].default_value = v.get("hair_spec", 0.12)
        if v.get("hair_tex") and n.type == 'TEX_IMAGE' and n.image and ('diff' in n.image.filepath.lower() or 'hair.png' in n.image.filepath.lower()):
            n.image = bpy.data.images.load(v["hair_tex"])
suit = A(f"{D}/clothes/male_casualsuit05/male_casualsuit05.mhclo", "Clothes")
for mt in suit.data.materials:
    for n in mt.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image and 'diffuse' in n.image.filepath.lower(): n.image = bpy.data.images.load(SUIT_TEX)
A(f"{D}/clothes/shoes03/shoes03.mhclo", "Clothes")

# 投射贴图替换皮肤 diffuse（全部 7 个材质槽，含节点组内部）
newimg = bpy.data.images.load(TEX); n_rep = 0
for mt in h.data.materials:
    for n in mt.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image and 'diffuse' in n.image.name.lower(): n.image = newimg; n_rep += 1
        if n.type == 'GROUP' and n.node_tree:
            for nn in n.node_tree.nodes:
                if nn.type == 'TEX_IMAGE' and nn.image and 'diffuse' in nn.image.name.lower(): nn.image = newimg; n_rep += 1
    for n in mt.node_tree.nodes:
        if n.type == 'GROUP' and 'Clearcoat' in n.inputs: n.inputs['Clearcoat'].default_value = 0.03; n.inputs['Roughness'].default_value = 0.5
print("replaced diffuse nodes", n_rep)

# 表情系统：ARKit 52 面部单元 + 微软 22 口型 → 形态键；并插值到眉毛/睫毛/牙齿等子网格
FaceService.load_targets(h, load_microsoft_visemes=True, load_arkit_faceunits=True)
FaceService.interpolate_targets(h)
print("shape keys on body:", len(h.data.shape_keys.key_blocks))
# 去掉辅助几何、烘焙遮罩（保留形态键）
# 注：ExportService.bake_modifiers_remove_helpers 在带 75 个形态键时会打乱顶点对应（表情出现碎片），改为 bmesh 直接删辅助顶点，
# Blender 删顶点时会同步所有形态键层。衣服的遮罩（隐藏被覆盖的身体）保留为修改器，由 Unity 侧不处理（衣服本身遮挡）。
import bmesh
def remove_helpers(obj):
    vg = obj.vertex_groups["body"].index
    bm = bmesh.new(); bm.from_mesh(obj.data); dl = bm.verts.layers.deform.active
    todel = [vv for vv in bm.verts if vg not in vv[dl]]
    bmesh.ops.delete(bm, geom=todel, context='VERTS'); bm.to_mesh(obj.data); bm.free(); obj.data.update()
    for md in list(obj.modifiers):
        if md.type == 'MASK' and md.vertex_group == "body": obj.modifiers.remove(md)
remove_helpers(h)
print("verts after helper removal", len(h.data.vertices), "keys", len(h.data.shape_keys.key_blocks) if h.data.shape_keys else 0)
bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}/ye_final.blend")

# ---------- 表情样张 ----------
EXPR = {
    "neutral": {},
    "smile": {"mouthSmileLeft": 0.7, "mouthSmileRight": 0.7, "cheekSquintLeft": 0.3, "cheekSquintRight": 0.3, "eyeSquintLeft": 0.2, "eyeSquintRight": 0.2},
    "sad": {"browInnerUp": 0.6, "mouthFrownLeft": 0.5, "mouthFrownRight": 0.5, "browDownLeft": 0.0},
    "surprise": {"browInnerUp": 0.8, "browOuterUpLeft": 0.6, "browOuterUpRight": 0.6, "eyeWideLeft": 0.6, "eyeWideRight": 0.6, "jawOpen": 0.3},
    "angry": {"browDownLeft": 0.8, "browDownRight": 0.8, "noseSneerLeft": 0.3, "noseSneerRight": 0.3, "mouthPressLeft": 0.4, "mouthPressRight": 0.4},
    "blink": {"eyeBlinkLeft": 1.0, "eyeBlinkRight": 1.0},
    "speak": {"jawOpen": 0.5, "mouthFunnel": 0.2},
}
def set_all(expr):
    FaceService.clear_expression(h)
    for o in bpy.data.objects:                       # 子网格同名形态键同步
        if o.type == 'MESH' and o is not h and o.data.shape_keys:
            for kb in o.data.shape_keys.key_blocks: kb.value = 0.0
    FaceService.set_expression(h, expr)
    for name, w in expr.items():
        kn = TargetService.expression_name_to_shapekey_name(name)
        for o in bpy.data.objects:
            if o.type == 'MESH' and o is not h and o.data.shape_keys and kn in o.data.shape_keys.key_blocks:
                o.data.shape_keys.key_blocks[kn].value = w

sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
w = sc.world or bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.70, 0.70, 0.72, 1); bg.inputs[1].default_value = 0.35
ez = sum((eyes.matrix_world @ vv.co).z for vv in eyes.data.vertices) / len(eyes.data.vertices)
def light(nm, loc, e, col=(1, 1, 1), size=1.0):
    l = bpy.data.lights.new(nm, 'AREA'); l.energy = e; l.size = size; l.color = col
    o = bpy.data.objects.new(nm, l); sc.collection.objects.link(o); o.location = loc
    d = mathutils.Vector((0, 0, ez - 0.03)) - o.location; o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler(); return o
light("key", (0.7, -1.3, ez + 0.5), 48, (1, 1, 1), size=2.0); light("fill", (-1.1, -1.1, ez + 0.1), 25, (1, 1, 1), size=2.5)
light("rim", (0.2, 1.3, ez + 0.7), 30, (1, 1, 1), size=1.0)
cams = json.load(open(CAMS)); c = cams["front"]
cam = bpy.data.cameras.new("cam"); co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co); sc.camera = co
cam.lens = c["lens_mm"]; co.matrix_world = mathutils.Matrix(c["cam_world"])
sc.render.resolution_x = 590; sc.render.resolution_y = 941; sc.render.resolution_percentage = 70
for name, expr in EXPR.items():
    set_all(expr)
    sc.render.filepath = f"{OUT}/expr_{name}.png"; bpy.ops.render.render(write_still=True); print("rendered", name)
set_all({})

# ---------- 简化材质（Principled + 贴图）以便 FBX/Unity 读到贴图 ----------
def simplify(mt):
    img = None
    for n in mt.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image and ('diffuse' in n.image.name.lower() or 'diff' in n.image.filepath.lower() or 'hair' in n.image.filepath.lower()): img = n.image; break
        if n.type == 'GROUP' and n.node_tree:
            for nn in n.node_tree.nodes:
                if nn.type == 'TEX_IMAGE' and nn.image and 'diffuse' in nn.image.name.lower(): img = nn.image; break
        if img: break
    if img is None:
        for n in mt.node_tree.nodes:
            if n.type == 'TEX_IMAGE' and n.image: img = n.image; break
    nt = mt.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs["Roughness"].default_value = 0.6; nt.links.new(bsdf.outputs[0], out.inputs[0])
    if img is not None:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = img; nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
        if mt.name.lower().startswith(("hair", "eyebrow", "eyelash", "long", "braid")) or any(k in (img.filepath or "").lower() for k in ("hair", "eyebrow", "eyelash", "long01")):
            nt.links.new(t.outputs["Alpha"], bsdf.inputs["Alpha"]); mt.blend_method = 'HASHED'
    return img.name if img else None
for o in bpy.data.objects:
    if o.type == 'MESH':
        for mt in o.data.materials: print("mat", o.name, mt.name, "->", simplify(mt))
        for md in list(o.modifiers):
            if md.type == 'SUBSURF': o.modifiers.remove(md)
for o in list(bpy.data.objects):
    if o.type in ('CAMERA', 'LIGHT'): bpy.data.objects.remove(o)
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:
    if o.type in ('MESH', 'ARMATURE'): o.select_set(True)
fbx = f"{OUT}/ye_wenjie_face_v1.fbx"
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, apply_scale_options='FBX_SCALE_ALL', bake_space_transform=True,
                         object_types={'ARMATURE', 'MESH'}, use_mesh_modifiers=False, add_leaf_bones=False, bake_anim=False,
                         path_mode='COPY', embed_textures=True, mesh_smooth_type='FACE')
print("fbx MB", round(os.path.getsize(fbx) / 1e6, 1), "bones", len(rig.data.bones),
      "tris", sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in bpy.data.objects if o.type == 'MESH'))
bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}/ye_final_export.blend"); print("done")
