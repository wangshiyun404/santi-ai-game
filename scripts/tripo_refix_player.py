"""
REA 第 8 轮：主角"倒着跑"的根因是 Tripo 原始网格的双脚朝 −X、脸朝 +X（脚反装），
自动绑骨以脚为前向，重定向出的 walk/run 因而相对脸部是倒着跑。
流程：本地镜像脚部（assets/tripo/fix/char_player_feetfix.glb，见 docs/REA_逆向台账.md E23）
  → 上传 /v3/files → rig-check → rig(v3.0 biped mixamo, 25 积分) → retarget idle/walk/run (10 积分/个)
  → 下载 assets/tripo/anim/char_player_v2_rig.glb / char_player_v2_anim.glb
用法: pplx credentials run <openapi.tripo3d.ai 句柄> -- /tmp/bpyenv/bin/python scripts/tripo_refix_player.py [--glb fix.glb --state upload2.json --out v3] [--rig-only]
状态文件: assets/tripo/fix/upload.json（幂等，可重跑续传）
第 2 次（只镜像脚不够，Tripo 仍判前向为 −X）：--glb assets/tripo/fix/char_player_bodyfix.glb --state assets/tripo/fix/upload_body.json --out v3
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tripo_batch import _req, download
API3 = "https://openapi.tripo3d.ai/v3"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "assets", "tripo", "fix"); ANIM = os.path.join(ROOT, "assets", "tripo", "anim")
def _arg(flag, default):
    return sys.argv[sys.argv.index(flag)+1] if flag in sys.argv else default
GLB = _arg("--glb", os.path.join(FIX, "char_player_feetfix.glb")); STATE_PATH = _arg("--state", os.path.join(FIX, "upload.json")); OUT = _arg("--out", "v2")
RIG_ONLY = "--rig-only" in sys.argv
st = json.load(open(STATE_PATH)) if os.path.exists(STATE_PATH) else {}
def save(): json.dump(st, open(STATE_PATH, "w"), indent=1)

def wait(tid, every=5, timeout=1500):
    t0 = time.time()
    while time.time() - t0 < timeout:
        res = _req("GET", f"{API3}/tasks/{tid}")["data"]
        if res["status"] == "success": return res
        if res["status"] in ("failed", "cancelled", "banned", "expired"): raise SystemExit(f"task {tid} {res['status']}: {res}")
        print(f"   {tid[:8]} {res['status']} {res.get('progress', 0)}%", flush=True); time.sleep(every)
    raise SystemExit("timeout " + tid)

if "file_token" not in st:
    import requests
    r = requests.post(f"{API3}/files", files={"file": (os.path.basename(GLB), open(GLB, "rb"), "model/gltf-binary")}, timeout=180)
    st["file_token"] = r.json()["data"]["file_token"]; save()
if "rig_task" not in st:
    payload = {"input": st["file_token"], "out_format": "glb", "model": "v3.0-20260909", "rig_type": "biped", "spec": "mixamo"}
    st["rig_task"] = _req("POST", f"{API3}/animations/rig", payload)["data"]["task_id"]; save(); print("rig task", st["rig_task"])
if "rig_url" not in st:
    res = wait(st["rig_task"]); out = res.get("output", {})
    st["rig_url"] = out.get("model") or out.get("pbr_model") or out.get("model_url"); st["rig_credits"] = res.get("credits_consumed"); save()
    download(st["rig_url"], os.path.join(ANIM, f"char_player_{OUT}_rig.glb")); print("rig done, credits", st["rig_credits"])
if RIG_ONLY: raise SystemExit("rig-only: stop before retarget")
if "anim_task" not in st:
    payload = {"input": st["rig_task"], "out_format": "glb", "animations": ["preset:idle", "preset:walk", "preset:run"], "animate_in_place": True, "export_with_geometry": True}
    st["anim_task"] = _req("POST", f"{API3}/animations/retarget", payload)["data"]["task_id"]; save(); print("anim task", st["anim_task"])
if "anim_url" not in st:
    res = wait(st["anim_task"]); out = res.get("output", {})
    st["anim_url"] = out.get("model") or out.get("pbr_model") or out.get("model_url"); st["anim_credits"] = res.get("credits_consumed"); st["anim_output"] = out; save()
    download(st["anim_url"], os.path.join(ANIM, f"char_player_{OUT}_anim.glb")); print("anim done, credits", st["anim_credits"], list(out.keys()))
print("done")
