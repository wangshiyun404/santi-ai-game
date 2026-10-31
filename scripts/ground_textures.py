"""REA 台账 Q5 第二批：生成三张可平铺的地面贴图（低多边形风格、低对比），供 SceneBuilder 给地面材质使用。
用法：python3 scripts/ground_textures.py  → unity/SanTiGame/Assets/Textures/Ground/*.png
"""
import numpy as np
from PIL import Image
import os
OUT = 'unity/SanTiGame/Assets/Textures/Ground'
N = 512
rng = np.random.default_rng(7)

def tile_noise(cells, octaves=4, persistence=0.55):
    """周期性值噪声：低分辨率随机格点 → 双线性放大（wrap），多倍频叠加，天然可平铺。"""
    acc = np.zeros((N, N)); amp = 1.0; total = 0
    for o in range(octaves):
        c = cells * 2 ** o
        g = rng.random((c, c))
        ys = (np.arange(N) / N) * c; xs = ys
        y0 = np.floor(ys).astype(int) % c; x0 = np.floor(xs).astype(int) % c
        fy = (ys - np.floor(ys))[:, None]; fx = (xs - np.floor(xs))[None, :]
        fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
        y1 = (y0 + 1) % c; x1 = (x0 + 1) % c
        v = (g[y0][:, x0] * (1 - fy) * (1 - fx) + g[y0][:, x1] * (1 - fy) * fx
             + g[y1][:, x0] * fy * (1 - fx) + g[y1][:, x1] * fy * fx)
        acc += v * amp; total += amp; amp *= persistence
    return acc / total

def save(name, rgb):
    Image.fromarray(np.clip(rgb * 255, 0, 255).astype(np.uint8)).save(f'{OUT}/{name}.png')
    print(name)

def mix(a, b, t):
    return a[None, None, :] * (1 - t[..., None]) + b[None, None, :] * t[..., None]

os.makedirs(OUT, exist_ok=True)
# 1) 红岸基地：红褐土 + 稀疏草斑（东北山地、秋）
n = tile_noise(6); n2 = tile_noise(24, 3)
soil_a = np.array([0.50, 0.36, 0.31]); soil_b = np.array([0.43, 0.30, 0.27]); grass = np.array([0.42, 0.40, 0.26])
img = mix(soil_a, soil_b, n)
img = img * (0.93 + 0.14 * n2[..., None])                       # 细颗粒
gmask = np.clip((tile_noise(10, 2) - 0.58) * 6, 0, 1) * 0.7       # 草斑（弱化，保持低对比）
img = img * (1 - gmask[..., None]) + grass[None, None, :] * gmask[..., None]
save('ground_red_coast', img)

# 2) 乱纪元：灰白沙地 + 龟裂暗纹
n = tile_noise(8); n2 = tile_noise(32, 2)
sand_a = np.array([0.80, 0.76, 0.69]); sand_b = np.array([0.70, 0.66, 0.59])
img = mix(sand_a, sand_b, n) * (0.95 + 0.10 * n2[..., None])
# 龟裂：周期 Voronoi 的 F2−F1 边界（多边形裂块网络）
pts = []
while len(pts) < 28:   # 最小间距采样：两粒种子过近会让 F2−F1 处处很小，出现大片污渍
    q = rng.random(2)
    if all(min(np.hypot(*(np.abs(q - p) - np.round(np.abs(q - p)))) for _ in [0]) > 0.11 for p in pts): pts.append(q)
pts = np.array(pts)
yy, xx = np.mgrid[0:N, 0:N] / N
d1 = np.full((N, N), 9.0); d2 = np.full((N, N), 9.0)
for oy in (-1, 0, 1):
    for ox in (-1, 0, 1):
        for p in pts:
            d = np.hypot(xx - (p[0] + ox), yy - (p[1] + oy))
            m = d < d1
            d2 = np.where(m, d1, np.minimum(d2, d)); d1 = np.where(m, d, d1)
edge = np.clip(1 - (d2 - d1) / 0.012, 0, 1)
crack = edge * 0.30 * (0.6 + 0.4 * tile_noise(16, 2))   # 裂缝深浅不均
img = img * (1 - crack[..., None])
save('ground_chaotic', img)

# 3) 人列计算机广场：灰色石板，带方格缝（给阵列尺度感）
n = tile_noise(8); n2 = tile_noise(40, 2)
st_a = np.array([0.58, 0.58, 0.57]); st_b = np.array([0.50, 0.50, 0.50])
img = mix(st_a, st_b, n) * (0.95 + 0.10 * n2[..., None])
T = 4  # 每张贴图 4×4 块石板
yy, xx = np.mgrid[0:N, 0:N]
line = ((yy % (N // T)) < 3) | ((xx % (N // T)) < 3)
img[line] *= 0.72
save('ground_plain', img)
