# 第 3 步：用 MediaPipe FaceLandmarker 检测锚点图三视图与网格渲染图的 478 个关键点
# 用法: python3 03_landmarks.py <anchor_head_turnaround.png> <calibdir> <outdir>
import sys, os, json, cv2, numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
ANCHOR, CAL, OUT = sys.argv[1:4]; os.makedirs(OUT, exist_ok=True)
MODEL = "/tmp/mp/face_landmarker.task"
opts = vision.FaceLandmarkerOptions(base_options=python.BaseOptions(model_asset_path=MODEL), num_faces=1,
                                    output_face_blendshapes=False, output_facial_transformation_matrixes=True)
lm = vision.FaceLandmarker.create_from_options(opts)

def detect(img):
    res = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))
    if not res.face_landmarks: return None
    H, W = img.shape[:2]
    pts = np.array([[p.x * W, p.y * H, p.z * W] for p in res.face_landmarks[0]])
    return pts, np.array(res.facial_transformation_matrixes[0])

out = {}
# 锚点图：按三块裁切（正 / 3/4 / 侧）
A = cv2.imread(ANCHOR); H, W = A.shape[:2]
panels = {"front": (0, 590), "q34": (590, 1140), "left": (1140, W)}
for name, (x0, x1) in panels.items():
    crop = A[:, x0:x1]; cv2.imwrite(f"{OUT}/anchor_{name}.png", crop)
    r = detect(crop)
    if r is None: print("anchor", name, "NO FACE"); continue
    pts, M = r; out[f"anchor_{name}"] = {"pts": pts.tolist(), "size": [x1 - x0, H], "pose": M.tolist()}
    print("anchor", name, "yaw/pitch deg", np.degrees(np.arctan2(-M[2, 0], M[0, 0])).round(1))
for name in ["front", "q34", "left"]:
    if not os.path.exists(f"{CAL}/calib_{name}.png"): continue
    img = cv2.imread(f"{CAL}/calib_{name}.png"); r = detect(img)
    if r is None: print("calib", name, "NO FACE"); continue
    pts, M = r; out[f"calib_{name}"] = {"pts": pts.tolist(), "size": [img.shape[1], img.shape[0]], "pose": M.tolist()}
    print("calib", name, "detected")
json.dump(out, open(f"{OUT}/landmarks.json", "w"))

# 可视化
def draw(img, pts, path):
    im = img.copy()
    for x, y, _ in pts: cv2.circle(im, (int(x), int(y)), 1, (0, 255, 0), -1)
    cv2.imwrite(path, im)
for k, v in out.items():
    src = f"{OUT}/anchor_{k[7:]}.png" if k.startswith("anchor") else f"{CAL}/calib_{k[6:]}.png"
    draw(cv2.imread(src), np.array(v["pts"]), f"{OUT}/lm_{k}.jpg")

# 比例对比（正视）：以两眼外角距为 1
def ratios(p):
    p = np.array(p)[:, :2]
    eyeW = np.linalg.norm(p[33] - p[263])          # 外眼角距
    return {
        "脸宽(颧)/眼外角距": np.linalg.norm(p[234] - p[454]) / eyeW,
        "脸高(眉心→下巴)/眼外角距": np.linalg.norm(p[9] - p[152]) / eyeW,
        "内眼角距/眼外角距": np.linalg.norm(p[133] - p[362]) / eyeW,
        "鼻翼宽/眼外角距": np.linalg.norm(p[48] - p[278]) / eyeW,
        "嘴宽/眼外角距": np.linalg.norm(p[61] - p[291]) / eyeW,
        "鼻尖→上唇/眼外角距": np.linalg.norm(p[1] - p[0]) / eyeW,
        "下唇→下巴/眼外角距": np.linalg.norm(p[17] - p[152]) / eyeW,
        "眼高(左)/眼外角距": np.linalg.norm(p[159] - p[145]) / eyeW,
        "眼心→下巴/眼外角距": np.linalg.norm((p[33] + p[263]) / 2 - p[152]) / eyeW,
    }
if "anchor_front" in out and "calib_front" in out:
    ra, rc = ratios(out["anchor_front"]["pts"]), ratios(out["calib_front"]["pts"])
    print(f"{'指标':<22}{'锚点':>8}{'网格':>8}{'差%':>8}")
    for k in ra: print(f"{k:<22}{ra[k]:>8.3f}{rc[k]:>8.3f}{(rc[k]/ra[k]-1)*100:>+8.1f}")
