#!/usr/bin/env python3
"""
第 6 轮（WebGL 体积）：Unity 工程内的 Tripo GLB 自带 3 张 2048² 贴图（基础色 / 金属粗糙 / 法线），
Unity 把它们当未压缩 RGBA32 打包，首个 WebGL 构建 145 MB（贴图占 96%）。

本脚本把每个 GLB 的「基础色」贴图抽出为 PNG（角色/主体 1024，道具 512），写到
unity/SanTiGame/Assets/Textures/Tripo/<asset>_base.png，然后从 GLB 中删掉全部 images/textures/samplers
及材质贴图引用，并重建二进制缓冲（只保留 accessor 引用的 bufferView）。
Unity 侧 Mats.Convert 优先使用外置 PNG 作为 _BaseMap（压缩 + mipmap），金属粗糙/法线贴图不再使用（低模风格无需）。

原始 GLB 保留在 assets/tripo/ 下，本脚本只改 Unity 工程里的副本。幂等：已无 images 的 GLB 跳过。
"""
import io, json, os, struct, sys, glob
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
U = os.path.join(ROOT, "unity", "SanTiGame", "Assets")
TEX_DIR = os.path.join(U, "Textures", "Tripo")
HI = {"char_ye_wenjie", "char_newton", "char_von_neumann", "char_qin", "char_follower",
      "dish_tower", "jeep", "control_console", "sand_table", "pyramid"}   # 1024；其余 512
XHI = {"char_player"}   # 第 10 轮：写实主角（Tripo 4096² 基础色，脸只占图集一小块）→ 2048，Unity 侧 Crunch 压缩


def read_glb(path):
    f = open(path, "rb").read()
    assert f[:4] == b"glTF", path
    jl = struct.unpack("<I", f[12:16])[0]
    j = json.loads(f[20:20 + jl])
    off = 20 + jl
    bin_ = b""
    if off < len(f):
        bl = struct.unpack("<I", f[off:off + 4])[0]
        assert f[off + 4:off + 8] == b"BIN\x00"
        bin_ = f[off + 8:off + 8 + bl]
    return j, bin_


def write_glb(path, j, bin_):
    js = json.dumps(j, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    bin_ += b"\x00" * ((4 - len(bin_) % 4) % 4)
    total = 12 + 8 + len(js) + 8 + len(bin_)
    with open(path, "wb") as o:
        o.write(b"glTF" + struct.pack("<II", 2, total))
        o.write(struct.pack("<I", len(js)) + b"JSON" + js)
        o.write(struct.pack("<I", len(bin_)) + b"BIN\x00" + bin_)


def view_bytes(j, bin_, idx):
    bv = j["bufferViews"][idx]
    o = bv.get("byteOffset", 0)
    return bin_[o:o + bv["byteLength"]]


def process(path):
    name = os.path.splitext(os.path.basename(path))[0]
    j, bin_ = read_glb(path)
    if not j.get("images"):
        return None
    # 1. 抽基础色
    base_img = None
    for m in j.get("materials", []):
        pbr = m.get("pbrMetallicRoughness", {})
        if "baseColorTexture" in pbr and base_img is None:
            tex = j["textures"][pbr["baseColorTexture"]["index"]]
            base_img = j["images"][tex["source"]]
    out_png = os.path.join(TEX_DIR, f"{name}_base.png")
    if base_img is not None and not os.path.exists(out_png):
        data = view_bytes(j, bin_, base_img["bufferView"])
        im = Image.open(io.BytesIO(data)).convert("RGBA")
        size = 2048 if name in XHI else 1024 if name in HI else 512
        if max(im.size) > size:
            im = im.resize((size, size), Image.LANCZOS)
        if im.getextrema()[3] == (255, 255):
            im = im.convert("RGB")
        im.save(out_png, optimize=True)
    # 2. 删贴图引用
    for m in j.get("materials", []):
        pbr = m.get("pbrMetallicRoughness", {})
        pbr.pop("baseColorTexture", None); pbr.pop("metallicRoughnessTexture", None)
        for k in ("normalTexture", "occlusionTexture", "emissiveTexture"):
            m.pop(k, None)
        # 基础色因子保持（Tripo 为 1,1,1,1）；金属度置 0 以免无贴图时变镜面
        pbr["metallicFactor"] = 0.0
        pbr.setdefault("roughnessFactor", 0.8)
    for k in ("images", "textures", "samplers"):
        j.pop(k, None)
    # 3. 只保留 accessor 用到的 bufferView，重建 BIN
    used = []
    for a in j.get("accessors", []):
        if "bufferView" in a and a["bufferView"] not in used:
            used.append(a["bufferView"])
        sp = a.get("sparse")
        if sp:
            for key in ("indices", "values"):
                bvi = sp[key]["bufferView"]
                if bvi not in used: used.append(bvi)
    remap = {}
    new_views, new_bin = [], bytearray()
    for old in used:
        bv = j["bufferViews"][old]
        chunk = view_bytes(j, bin_, old)
        while len(new_bin) % 4: new_bin.append(0)
        nb = {k: v for k, v in bv.items() if k not in ("byteOffset", "buffer")}
        nb["buffer"] = 0; nb["byteOffset"] = len(new_bin); nb["byteLength"] = len(chunk)
        new_bin += chunk
        remap[old] = len(new_views); new_views.append(nb)
    for a in j.get("accessors", []):
        if "bufferView" in a: a["bufferView"] = remap[a["bufferView"]]
        sp = a.get("sparse")
        if sp:
            for key in ("indices", "values"): sp[key]["bufferView"] = remap[sp[key]["bufferView"]]
    j["bufferViews"] = new_views
    j["buffers"] = [{"byteLength": len(new_bin)}]
    before = os.path.getsize(path)
    write_glb(path, j, bytes(new_bin))
    return before, os.path.getsize(path), out_png if base_img is not None else None


def main():
    os.makedirs(TEX_DIR, exist_ok=True)
    paths = sorted(glob.glob(os.path.join(U, "Models", "*.glb")) + glob.glob(os.path.join(U, "Models", "Anim", "*.glb")))
    # 角色贴图优先从 Anim 版抽（游戏实际用 Anim 版；两者同一材质/贴图）
    paths.sort(key=lambda p: (0 if "/Anim/" in p else 1, p))
    for p in paths:
        r = process(p)
        if r:
            print(f"{os.path.relpath(p, ROOT)}: {r[0]//1024} KB -> {r[1]//1024} KB  tex={os.path.basename(r[2]) if r[2] else '-'}")
    print("done")


if __name__ == "__main__":
    main()
