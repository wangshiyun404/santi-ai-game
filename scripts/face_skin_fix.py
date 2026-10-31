"""REA Q2：叶文洁 Tripo 贴图脸部为紫色（E13）。按 face_patches.py 导出的脸部 UV 三角形做掩膜，
只把掩膜内偏紫的像素改为肤色（保留明暗），其余（裤子等同色相区域）不动。"""
import json, sys, colorsys
from PIL import Image, ImageDraw
import numpy as np
name = sys.argv[1]
src = f'unity/SanTiGame/Assets/Textures/Tripo/{name}_base.png'
im = Image.open(src).convert('RGB'); W, H = im.size
tris = json.load(open(f'assets/face/{name}_face_uv.json'))
mask = Image.new('L', (W, H), 0); d = ImageDraw.Draw(mask)
for t in tris:
    pts = [(u * W, (1 - v) * H) for u, v in t]
    d.polygon(pts, fill=255, outline=255)
m = np.asarray(mask) > 0
a = np.asarray(im).astype(np.float32) / 255
hsv = np.array([colorsys.rgb_to_hsv(*p) for p in a.reshape(-1, 3)]).reshape(a.shape)
h = hsv[..., 0] * 360; s = hsv[..., 1]; v = hsv[..., 2]
purple = (h > 230) & (h < 345) & (s > 0.12)
sel = m & purple
print(name, 'mask texels', int(m.sum()), 'purple in mask', int(sel.sum()))
out = a.copy()
skin_h, skin_s = 24 / 360, 0.38
for idx in zip(*np.where(sel)):
    vv = min(1.0, v[idx] * 1.12)
    out[idx] = colorsys.hsv_to_rgb(skin_h, skin_s * (0.8 + 0.4 * s[idx]), vv)
Image.fromarray((out * 255).astype(np.uint8)).save(src)
prev = Image.fromarray((out * 255).astype(np.uint8)).resize((512, 512)); prev.save(f'/tmp/{name}_fixed_prev.png')
