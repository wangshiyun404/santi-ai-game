# 第 5 步：用网格 3D 关键点 ↔ 锚点图 2D 关键点求解每个视图的相机位姿（PnP，焦距扫描），输出 Blender 相机矩阵并叠加可视化
# 用法: python3 05_pnp.py <lmdir> <outdir>
import sys, os, json, cv2, numpy as np
LMD, OUT = sys.argv[1:3]; os.makedirs(OUT, exist_ok=True)
lms = json.load(open(f"{LMD}/landmarks.json")); lm3 = json.load(open(f"{LMD}/lm3d.json"))["front"]
P3 = np.array([p if p else [np.nan] * 3 for p in lm3], dtype=np.float64)
valid3 = ~np.isnan(P3[:, 0])
# 不稳定的点：脸轮廓(面部椭圆)靠发际/耳侧的点、虹膜点
OVAL = [10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109]
IRIS = list(range(468, 478))
bad = set(OVAL[:9] + OVAL[-9:] + IRIS)  # 上半轮廓（发际附近）+ 虹膜
MID = [10, 151, 9, 8, 168, 6, 197, 195, 5, 4, 1, 19, 94, 2, 164, 0, 11, 12, 13, 14, 15, 16, 17, 18, 200, 199, 175, 152]
res = {}
for view in ["front", "q34", "left"]:
    key = f"anchor_{view}"
    if key not in lms: continue
    P2 = np.array(lms[key]["pts"])[:, :2]; W, H = lms[key]["size"]
    sel = [i for i in range(468) if valid3[i] and i not in bad]
    if view == "left":   # 只用她左侧（+X）与中线的点
        sel = [i for i in sel if P3[i, 0] > 0.004 or i in MID]
    if view == "q34":
        sel = [i for i in sel if P3[i, 0] > -0.03 or i in MID]
    obj = P3[sel].astype(np.float32); img = P2[sel].astype(np.float32)
    best = None
    FOCALS = [3.3 * W] if os.environ.get("FIX_FOCAL", "1") == "1" else np.linspace(0.8, 4.0, 33) * W   # 三视图同一虚拟镜头：固定焦距 3.3×W（≈119mm 等效），避免侧视图焦距漂移
    for f in FOCALS:
        K = np.array([[f, 0, W / 2], [0, f, H / 2], [0, 0, 1]], dtype=np.float64)
        ok, rvec, tvec, inl = cv2.solvePnPRansac(obj, img, K, None, reprojectionError=6.0, iterationsCount=300, flags=cv2.SOLVEPNP_EPNP)
        if not ok: continue
        ok, rvec, tvec = cv2.solvePnP(obj, img, K, None, rvec, tvec, True, cv2.SOLVEPNP_ITERATIVE)
        proj, _ = cv2.projectPoints(obj, rvec, tvec, K, None); err = np.linalg.norm(proj[:, 0] - img, axis=1)
        e = np.median(err)
        if best is None or e < best[0]: best = (e, f, rvec, tvec, err)
    if view == "left":
        # 侧视图：MediaPipe 在纯侧脸上关键点偏差大，自由 PnP 会把相机解成 45°。改为约束解：
        # 以正视相机为基准绕头部竖轴转 90°（她的左侧），只优化平移 + 小角度修正（强正则），鲁棒损失。
        from scipy.optimize import least_squares
        from scipy.spatial.transform import Rotation as Rot
        f = 3.3 * W; K = np.array([[f, 0, W / 2], [0, f, H / 2], [0, 0, 1]], dtype=np.float64)
        Rf, _ = cv2.Rodrigues(np.array(res["front"]["rvec"])); tf = np.array(res["front"]["tvec"])
        head = np.nanmean(P3[valid3], axis=0)                      # 头部中心（世界）
        Rz = Rot.from_euler('z', 90, degrees=True).as_matrix()    # 世界 Z 轴转 90°：相机从正前方转到她的左侧
        # 正视相机位置 → 绕头部中心旋转
        camf = -Rf.T @ tf; caml = head + Rz @ (camf - head)
        R0 = Rf @ Rz.T; t0 = -R0 @ caml
        use = [i for i in sel if i in MID or P3[i, 0] > 0.02]
        o3 = P3[use]; i2 = P2[use]
        def resid(x):
            dR = Rot.from_rotvec(x[:3]).as_matrix(); R_ = dR @ R0; t_ = t0 + x[3:6]
            pr, _ = cv2.projectPoints(o3.astype(np.float32), cv2.Rodrigues(R_)[0], t_, K, None)
            r = (pr[:, 0] - i2).ravel()
            return np.concatenate([r, 2500.0 * x[:3]])            # 角度强正则（弧度 ×2500 px）：锚点图就是正侧面，只允许几度修正
        sol = least_squares(resid, np.zeros(6), loss='soft_l1', f_scale=8.0)
        dR = Rot.from_rotvec(sol.x[:3]).as_matrix(); R_ = dR @ R0; t_ = t0 + sol.x[3:6]
        rvec = cv2.Rodrigues(R_)[0]; tvec = t_.reshape(3, 1)
        pr, _ = cv2.projectPoints(o3.astype(np.float32), rvec, tvec, K, None); err = np.linalg.norm(pr[:, 0] - i2, axis=1); e = np.median(err)
        print(f"left(constrained): yaw-dev {np.degrees(np.linalg.norm(sol.x[:3])):.1f}°  n={len(use)}")
        best = (e, f, rvec, tvec, err)
    e, f, rvec, tvec, err = best
    R, _ = cv2.Rodrigues(rvec); R = np.asarray(R); t = tvec.reshape(3)
    print(f"{view}: focal {f/W:.2f}×W  median err {e:.2f}px  mean {err.mean():.2f}  n={len(sel)}  dist {np.linalg.norm(t):.3f} m")
    # OpenCV → Blender 相机 matrix_world
    flip = np.diag([1, -1, -1]); Rb = flip @ R; tb = flip @ t
    Vb = np.eye(4); Vb[:3, :3] = Rb; Vb[:3, 3] = tb; cam_world = np.linalg.inv(Vb)
    K = np.array([[f, 0, W / 2], [0, f, H / 2], [0, 0, 1]])
    res[view] = {"K": K.tolist(), "rvec": rvec.reshape(3).tolist(), "tvec": t.tolist(), "cam_world": cam_world.tolist(),
                 "size": [W, H], "lens_mm": float(f * 36.0 / W)}
    # 叠加：把全部有效 3D 点投到锚点图上
    allp, _ = cv2.projectPoints(P3[valid3].astype(np.float32), rvec, tvec, K, None)
    im = cv2.imread(f"{LMD}/anchor_{view}.png")
    for (x, y) in P2[valid3]: cv2.circle(im, (int(x), int(y)), 2, (0, 255, 0), -1)   # 绿：图上检测
    for (x, y) in allp[:, 0]: cv2.circle(im, (int(x), int(y)), 2, (0, 0, 255), -1)   # 红：网格投影
    cv2.imwrite(f"{OUT}/pnp_{view}.jpg", im)
json.dump(res, open(f"{OUT}/cams.json", "w"), indent=1); print("saved cams.json")
