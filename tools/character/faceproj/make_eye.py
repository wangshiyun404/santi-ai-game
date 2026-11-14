# 生成叶文洁专用眼球贴图：在 MakeHuman brown_eye 基础上放大虹膜 1.3 倍并加深为深褐色（锚点图为大而深的虹膜）
import numpy as np, cv2, os, sys
D = os.path.expanduser("~/.config/blender/5.0/extensions/.user/user_default/mpfb/data/eyes/materials")
src = cv2.imread(f"{D}/brown_eye.png", cv2.IMREAD_UNCHANGED).astype(np.float32)
H, W = src.shape[:2]
SCALE = float(sys.argv[1]) if len(sys.argv) > 1 else 1.3
out = src.copy()
ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
for (cx, cy) in [(717, 307), (307, 717)]:
    # 自动找虹膜半径：沿水平线找从深色到巩膜的过渡
    row = src[int(cy), :, :3].mean(-1); r = 60
    while r < 220 and row[int(cx + r)] < 165: r += 1
    R = r - 20; Rn = R * SCALE
    d = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2); disc = d < Rn
    mx = cx + (xs - cx) / SCALE; my = cy + (ys - cy) / SCALE
    warped = cv2.remap(src, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    iris = d < R * SCALE * 0.98
    col = warped.copy()
    # 加深：虹膜区域乘以 0.5，并向深褐偏移；边缘（角膜缘环）更深
    k = np.clip((Rn - d) / (0.18 * Rn), 0, 1)[..., None]   # 边缘→中心 0→1
    lum = warped[..., :3].mean(-1); irisness = np.clip((170 - lum) / 70, 0, 1)[..., None]
    fac = 1 - irisness * (1 - (0.42 + 0.18 * k))
    dark = col[..., :3] * fac
    dark = dark * np.array([0.85, 0.75, 0.95])  # BGR：压一点绿/蓝，保持暖褐
    col[..., :3] = dark
    out[disc] = col[disc]
    print("iris radius", R, "->", Rn)
cv2.imwrite(f"{D}/ye_eye.png", np.clip(out, 0, 255).astype(np.uint8))
open(f"{D}/ye_eye.mhmat", "w").write(open(f"{D}/brown.mhmat").read().replace("brown_eye.png", "ye_eye.png").replace("name brown", "name ye_eye"))
print("saved", f"{D}/ye_eye.png")
