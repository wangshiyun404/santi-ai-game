"""
主角重做（第 10 轮）：写实风格叶文洁。Tripo API v3。
流程：上传 4 视图(concept/ye_{front,left,back,right}.png) → multiview-to-model (v3.1, PBR, detailed 贴图, 30k 面)
  → 下载 assets/tripo/char_ye_hero.glb（原始）→ 本地检查朝向/脚向/比例（scripts/mesh_check.py）
  → rig(v3.0 biped mixamo) → retarget idle/walk/run (in place) → assets/tripo/anim/char_ye_hero_anim.glb
用法: pplx credentials run <openapi.tripo3d.ai 句柄> -- /tmp/bpyenv/bin/python scripts/tripo_hero.py [--stage gen|rig|anim] [--name char_ye_hero]
状态文件: assets/tripo/fix/hero_state.json（幂等）
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tripo_batch import _req, download
API3 = "https://openapi.tripo3d.ai/v3"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "assets", "tripo", "fix"); ANIM = os.path.join(ROOT, "assets", "tripo", "anim")
def _arg(flag, default):
    return sys.argv[sys.argv.index(flag)+1] if flag in sys.argv else default
NAME = _arg("--name", "char_ye_hero"); STAGE = _arg("--stage", "anim")
STATE_PATH = os.path.join(FIX, f"{NAME}_state.json")
st = json.load(open(STATE_PATH)) if os.path.exists(STATE_PATH) else {}
def save(): json.dump(st, open(STATE_PATH, "w"), indent=1)

def wait(tid, every=6, timeout=2400):
    t0 = time.time()
    while time.time() - t0 < timeout:
        res = _req("GET", f"{API3}/tasks/{tid}")["data"]
        if res["status"] == "success": return res
        if res["status"] in ("failed", "cancelled", "banned", "expired"): raise SystemExit(f"task {tid} {res['status']}: {res}")
        print(f"   {tid[:8]} {res['status']} {res.get('progress', 0)}%", flush=True); time.sleep(every)
    raise SystemExit("timeout " + tid)

def upload(path):
    import requests
    r = requests.post(f"{API3}/files", files={"file": (os.path.basename(path), open(path, "rb"), "image/png")}, timeout=180)
    j = r.json()
    if j.get("code", 0) != 0: raise SystemExit(f"upload error {j}")
    return j["data"]["file_token"]

views = ["front", "left", "back", "right"]
if "tokens" not in st:
    st["tokens"] = {v: upload(os.path.join(ROOT, "concept", f"ye_{v}.png")) for v in views}; save(); print("uploaded", st["tokens"])
if "gen_task" not in st:
    payload = {"inputs": [{v: st["tokens"][v]} for v in views], "model": "v3.1-20260211",
               "texture": True, "pbr": True, "texture_quality": "detailed", "geometry_quality": "standard",
               "face_limit": 30000, "texture_alignment": "original_image", "orientation": "align_image"}
    st["gen_task"] = _req("POST", f"{API3}/generation/multiview-to-model", payload)["data"]["task_id"]; save(); print("gen task", st["gen_task"])
if "gen_url" not in st:
    res = wait(st["gen_task"]); out = res.get("output", {})
    st["gen_url"] = out.get("model_url") or out.get("pbr_model") or out.get("model"); st["gen_render"] = out.get("rendered_image_url"); st["gen_credits"] = res.get("credits_consumed"); save()
    download(st["gen_url"], os.path.join(ROOT, "assets", "tripo", f"{NAME}.glb"))
    if st["gen_render"]:
        try: download(st["gen_render"], os.path.join(ROOT, "docs", "rea_evidence", f"E26_{NAME}_tripo_render.png"))
        except Exception as e: print("render dl fail", e)
    print("gen done, credits", st["gen_credits"])
if STAGE == "gen": raise SystemExit("stage gen done")
if "rig_task" not in st:
    payload = {"input": st["gen_task"], "out_format": "glb", "model": "v3.0-20260909", "rig_type": "biped", "spec": "mixamo"}
    st["rig_task"] = _req("POST", f"{API3}/animations/rig", payload)["data"]["task_id"]; save(); print("rig task", st["rig_task"])
if "rig_url" not in st:
    res = wait(st["rig_task"]); out = res.get("output", {})
    st["rig_url"] = out.get("model_url") or out.get("model") or out.get("pbr_model"); st["rig_credits"] = res.get("credits_consumed"); save()
    download(st["rig_url"], os.path.join(ANIM, f"{NAME}_rig.glb")); print("rig done, credits", st["rig_credits"])
if STAGE == "rig": raise SystemExit("stage rig done")
if "anim_task" not in st:
    payload = {"input": st["rig_task"], "out_format": "glb", "animations": ["preset:idle", "preset:walk", "preset:run"], "animate_in_place": True, "export_with_geometry": True}
    st["anim_task"] = _req("POST", f"{API3}/animations/retarget", payload)["data"]["task_id"]; save(); print("anim task", st["anim_task"])
if "anim_url" not in st:
    res = wait(st["anim_task"]); out = res.get("output", {})
    st["anim_url"] = out.get("model_url") or out.get("model") or out.get("pbr_model"); st["anim_credits"] = res.get("credits_consumed"); st["anim_output"] = out; save()
    download(st["anim_url"], os.path.join(ANIM, f"{NAME}_anim.glb")); print("anim done, credits", st["anim_credits"], list(out.keys()))
print("done")
