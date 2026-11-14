# 第 7 步：把锚点三视图按相机位姿投射到 UV 贴图：关键点驱动的分片仿射矫正 → 深度可见性 → 法线角权重融合 → 与基础皮肤贴图合成
# 用法: python3 07_compose.py <lmdir> <pnpdir> <bakedir> <base_skin.png> <outdir>
import sys, os, json, cv2, numpy as np, OpenEXR, Imath
from scipy.spatial import Delaunay
LMD, PNP, BAKE, BASE, OUT = sys.argv[1:6]; os.makedirs(OUT, exist_ok=True)
lms = json.load(open(f"{LMD}/landmarks.json")); lm3 = json.load(open(f"{LMD}/lm3d.json"))["front"]
cams = json.load(open(f"{PNP}/cams.json"))
P3 = np.array([p if p else [np.nan] * 3 for p in lm3]); valid3 = ~np.isnan(P3[:, 0])
pos = np.load(f"{BAKE}/position.npy"); nrm = np.load(f"{BAKE}/normal.npy")
TS = pos.shape[0]
baked = np.abs(pos[..., :3]).sum(-1) > 1e-6
P = pos[..., :3].reshape(-1, 3).astype(np.float64); N = (nrm[..., :3] * 2 - 1).reshape(-1, 3).astype(np.float64)
N /= (np.linalg.norm(N, axis=1, keepdims=True) + 1e-9)
MID = [10,151,9,8,168,6,197,195,5,4,1,19,94,2,164,0,11,12,13,14,15,16,17,18,200,199,175,152]
OVAL = [10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109]
LBROW = [70,63,105,66,107,55,65,52,53,46]; RBROW = [336,296,334,293,300,276,283,282,295,285]
LEYE = [33,7,163,144,145,153,154,155,133,173,157,158,159,160,161,246]; REYE = [362,382,381,380,374,373,390,249,263,466,388,387,386,385,384,398]
LIPS = [61,146,91,181,84,17,314,405,321,375,291,409,270,269,267,0,37,39,40,185]

def read_depth(path):
    f = OpenEXR.InputFile(path); h = f.header(); dw = h['dataWindow']
    W = dw.max.x - dw.min.x + 1; H = dw.max.y - dw.min.y + 1
    ch = [c for c in h['channels'] if 'Depth' in c or c.endswith('.Z') or c == 'Z'][0]
    return np.frombuffer(f.channel(ch, Imath.PixelType(Imath.PixelType.FLOAT)), dtype=np.float32).reshape(H, W).copy()

def piecewise_affine_warp(img, src_pts, dst_pts):
    """把 img 变形，使 src_pts 处的内容移动到 dst_pts。凸包外为恒等。返回变形后的图。"""
    H, W = img.shape[:2]
    # 外圈锚点（恒等），保证凸包外平滑过渡
    cx, cy = dst_pts.mean(0); r = np.linalg.norm(dst_pts - [cx, cy], axis=1).max()
    ring = np.array([[cx + 1.6 * r * np.cos(a), cy + 1.6 * r * np.sin(a)] for a in np.linspace(0, 2 * np.pi, 24, endpoint=False)])
    corners = np.array([[0, 0], [W - 1, 0], [0, H - 1], [W - 1, H - 1], [W / 2, 0], [W / 2, H - 1], [0, H / 2], [W - 1, H / 2]])
    S = np.vstack([src_pts, ring, corners]); Dp = np.vstack([dst_pts, ring, corners])
    tri = Delaunay(Dp)
    mapx = np.tile(np.arange(W, dtype=np.float32), (H, 1)); mapy = np.tile(np.arange(H, dtype=np.float32)[:, None], (1, W))
    ys, xs = np.mgrid[0:H, 0:W]; pix = np.stack([xs.ravel(), ys.ravel()], 1).astype(np.float64)
    simplex = tri.find_simplex(pix)
    ok = simplex >= 0
    T = tri.transform[simplex[ok]]            # (n,3,2)
    b = np.einsum('nij,nj->ni', T[:, :2], pix[ok] - T[:, 2]); bary = np.c_[b, 1 - b.sum(1)]
    vidx = tri.simplices[simplex[ok]]          # (n,3)
    srcxy = np.einsum('ni,nik->nk', bary, S[vidx])
    mx = mapx.ravel(); my = mapy.ravel(); mx[ok] = srcxy[:, 0]; my[ok] = srcxy[:, 1]
    return cv2.remap(img, mx.reshape(H, W).astype(np.float32), my.reshape(H, W).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

def poly_mask(shape, pts, dilate=0):
    m = np.zeros(shape[:2], np.uint8); cv2.fillConvexPoly(m, cv2.convexHull(pts.astype(np.int32)), 255)
    if dilate: m = cv2.dilate(m, np.ones((dilate, dilate), np.uint8))
    return m

def skin_mask(img):
    ycc = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    m = (ycc[..., 1] >= 133) & (ycc[..., 1] <= 178) & (ycc[..., 2] >= 77) & (ycc[..., 2] <= 130) & (ycc[..., 0] > 60)
    return (m * 255).astype(np.uint8)

col_sum = np.zeros((TS * TS, 3)); w_sum = np.zeros(TS * TS)
GAIN = {"front": 1.0, "q34": 0.9, "left": 0.45}
for view in ["front", "q34", "left"]:
    if view not in cams: continue
    c = cams[view]; K = np.array(c["K"]); R, _ = cv2.Rodrigues(np.array(c["rvec"])); t = np.array(c["tvec"]); W, H = c["size"]
    img = cv2.imread(f"{LMD}/anchor_{view}.png"); depth = read_depth(f"{BAKE}/depth_{view}_.exr")
    P2 = np.array(lms[f"anchor_{view}"]["pts"])[:, :2]
    # ---- 关键点选择（与 PnP 一致）----
    sel = [i for i in range(468) if valid3[i] and i not in set(OVAL[:9] + OVAL[-9:])]
    if view == "left": sel = [i for i in sel if P3[i, 0] > 0.004 or i in MID]
    if view == "q34": sel = [i for i in sel if P3[i, 0] > -0.03 or i in MID]
    proj, _ = cv2.projectPoints(P3[sel].astype(np.float32), np.array(c["rvec"]), t, K, None); proj = proj[:, 0]
    # 剔除残差过大的点（>12px）后做分片仿射，使图上关键点落到网格投影位置
    resid = np.linalg.norm(proj - P2[sel], axis=1); keep = resid < 12
    if view == "left":
        warped = img.copy()   # 侧视图关键点不可靠，不做矫正变形，仅靠约束相机 + 低权重参与融合
    else:
        warped = piecewise_affine_warp(img, P2[sel][keep], proj[keep])
    cv2.imwrite(f"{OUT}/warped_{view}.jpg", warped)
    # ---- 图像空间掩码：皮肤色 ∪ 五官多边形，限制在扩展脸区 + 颈部；排除深色头发 ----
    allproj, _ = cv2.projectPoints(P3[valid3].astype(np.float32), np.array(c["rvec"]), t, K, None); allproj = allproj[:, 0]
    full = np.full((478, 2), np.nan); full[valid3] = allproj
    def pts(ids): return full[[i for i in ids if valid3[i]]]
    fh = np.nanmax(full[:, 1]) - np.nanmin(full[:, 1])
    roi = poly_mask(img.shape, pts(OVAL), dilate=int(0.10 * fh))
    neck = pts(OVAL).copy(); neck[:, 1] += 0.22 * fh; roi = roi | poly_mask(img.shape, np.vstack([pts(OVAL), neck]))
    feat = np.zeros(img.shape[:2], np.uint8)
    for ids in (LBROW, RBROW, LEYE, REYE, LIPS): feat |= poly_mask(img.shape, pts(ids), dilate=int(0.04 * fh))
    sk = skin_mask(warped)
    mask = ((sk > 0) | (feat > 0)) & (roi > 0)
    # 眼球由独立网格承担：把锚点图里的虹膜/眼白排除出投射，避免把瞳孔印到眼窝皮肤上
    for ids in (LEYE, REYE):
        hole = poly_mask(img.shape, pts(ids), dilate=int(0.014 * fh) * 2 + 1)
        mask &= ~(hole > 0)
    mask = cv2.morphologyEx(mask.astype(np.uint8) * 255, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    mask = cv2.erode(mask, np.ones((5, 5), np.uint8))
    maskf = cv2.GaussianBlur(mask, (0, 0), 4).astype(np.float64) / 255.0
    cv2.imwrite(f"{OUT}/mask_{view}.jpg", (maskf * 255).astype(np.uint8))
    lipm = cv2.GaussianBlur(poly_mask(img.shape, pts(LIPS), dilate=int(0.012 * fh)), (0, 0), 2).astype(np.float64)[..., None] / 255.0
    hsv = cv2.cvtColor(warped, cv2.COLOR_BGR2HSV).astype(np.float64)
    hsv[..., 1] = np.clip(hsv[..., 1] * (1 + 0.2 * lipm[..., 0]), 0, 255); hsv[..., 2] = np.clip(hsv[..., 2] * (1 - 0.03 * lipm[..., 0]), 0, 255)
    warped = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    wimg = warped.astype(np.float64)[..., ::-1] / 255.0   # RGB 0..1
    for mirror in ([False, True] if view != "front" else [False]):
        S = np.diag([-1.0, 1.0, 1.0]) if mirror else np.eye(3)
        Pm = P @ S; Nm = N @ S
        Xc = Pm @ R.T + t; z = Xc[:, 2]
        front = z > 0.05
        u = K[0, 0] * Xc[:, 0] / np.where(front, z, 1) + K[0, 2]; v = K[1, 1] * Xc[:, 1] / np.where(front, z, 1) + K[1, 2]
        inside = front & (u >= 1) & (u <= W - 2) & (v >= 1) & (v <= H - 2)
        ui = np.clip(np.round(u).astype(int), 0, W - 1); vi = np.clip(np.round(v).astype(int), 0, H - 1)
        dz = depth[vi, ui]; visible = inside & (z < dz + 0.004)
        campos = -R.T @ t; dirv = campos - Pm; dirv /= (np.linalg.norm(dirv, axis=1, keepdims=True) + 1e-9)
        cosang = (Nm * dirv).sum(1)
        w = np.clip(cosang, 0, 1) ** 2 * visible * baked.ravel()
        # 采样（双线性）
        cols = cv2.remap(wimg.astype(np.float32), u.astype(np.float32).reshape(TS, TS), v.astype(np.float32).reshape(TS, TS), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT).reshape(-1, 3)
        mk = cv2.remap(maskf.astype(np.float32), u.astype(np.float32).reshape(TS, TS), v.astype(np.float32).reshape(TS, TS), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT).ravel()
        w = w * mk * GAIN[view] * (0.75 if mirror else 1.0)
        col_sum += cols * w[:, None]; w_sum += w
        print(f"{view}{' mirror' if mirror else ''}: visible texels {int(visible.sum())}, weighted {int((w > 0.05).sum())}")
proj_tex = np.zeros((TS * TS, 3)); nz = w_sum > 1e-6; proj_tex[nz] = col_sum[nz] / w_sum[nz, None]
proj_tex = proj_tex.reshape(TS, TS, 3); W_ = w_sum.reshape(TS, TS)
# ---- 与基础皮肤贴图合成（Blender 像素行从下往上，PNG 从上往下）----
base = cv2.imread(BASE)[..., ::-1].astype(np.float64) / 255.0
if base.shape[0] != TS: base = cv2.resize(base, (TS, TS), interpolation=cv2.INTER_AREA)
base = base[::-1]  # 转成 Blender 行序
alpha = np.clip((W_ - 0.05) / 0.25, 0, 1)
alpha = cv2.GaussianBlur(alpha, (0, 0), 3)
# 色彩匹配：用高权重区域的投影色 vs 基础贴图色，按通道做均值/标准差匹配，调整整张基础贴图（仅皮肤区）
hi = W_ > 0.5
if hi.sum() > 1000:
    lum = base.mean(-1); skinpix = np.clip((lum - 0.3) / 0.1, 0, 1)[..., None]
    adj = base.copy()
    for ch in range(3):
        mp, sp = proj_tex[..., ch][hi].mean(), proj_tex[..., ch][hi].std()
        mb, sb = base[..., ch][hi].mean(), base[..., ch][hi].std()
        adj[..., ch] = np.clip((base[..., ch] - mb) * (0.7 * sp / (sb + 1e-6) + 0.3) + mb + (mp - mb), 0, 1)
    base = base * (1 - skinpix) + adj * skinpix
    print("color match: proj mean", proj_tex[hi].mean(0).round(3), "base mean(after)", base[hi].mean(0).round(3))
final = base * (1 - alpha[..., None]) + proj_tex * alpha[..., None]
out8 = (np.clip(final[::-1], 0, 1) * 255).astype(np.uint8)
cv2.imwrite(f"{OUT}/ye_face_projected_diffuse.png", out8[..., ::-1])
cv2.imwrite(f"{OUT}/debug_weight.jpg", (np.clip(W_[::-1], 0, 1) * 255).astype(np.uint8))
cv2.imwrite(f"{OUT}/debug_proj.jpg", (np.clip(proj_tex[::-1], 0, 1) * 255).astype(np.uint8)[..., ::-1])
print("saved", f"{OUT}/ye_face_projected_diffuse.png")
