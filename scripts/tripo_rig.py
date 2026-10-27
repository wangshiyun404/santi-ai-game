"""
Tripo 自动绑骨 + 预设动画重定向（替代 Sac 流程里的 Auto-Rig Pro + Mixamo）。
用法:
  python tripo_rig.py [--only char_player,char_qin] [--anims idle,walk,run] [--dry]
流程（OpenAPI v3：/animations/rig-check, /animations/rig, /animations/retarget, /tasks/{id}）:
  1. animate_prerigcheck  (免费)  → riggable
  2. animate_rig          (25 积分) model_version v3.0-20260909, rig_type biped, spec mixamo
  3. animate_retarget     (10 积分/动画) animations ≤5, animate_in_place=True
输出: assets/tripo/anim/<name>_rig.glb, <name>_anim.glb ; 任务 id 写入 assets/tripo/anim_tasks.json
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tripo_batch import _req, download, OUT
API3 = "https://openapi.tripo3d.ai/v3"   # v3 专用端点（绑骨 v3.0 仅在 v3 提供）；凭据 handle: custom-cred:...@openapi.tripo3d.ai

def wait(task_id, every=6, timeout=1200):
    t0 = time.time()
    while time.time() - t0 < timeout:
        res = _req("GET", f"{API3}/tasks/{task_id}")["data"]
        st = res["status"]
        if st == "success": return res
        if st in ("failed", "cancelled", "banned", "expired"): raise SystemExit(f"task {task_id} {st}: {res}")
        print(f"   {task_id[:8]} {st} {res.get('progress', 0)}%", flush=True)
        time.sleep(every)
    raise SystemExit("timeout " + task_id)

ANIM_DIR = os.path.join(OUT, "anim"); os.makedirs(ANIM_DIR, exist_ok=True)
TASKS = json.load(open(os.path.join(OUT, "tasks.json"), encoding="utf-8"))
STATE_PATH = os.path.join(OUT, "anim_tasks.json")
STATE = json.load(open(STATE_PATH, encoding="utf-8")) if os.path.exists(STATE_PATH) else {}
def save(): json.dump(STATE, open(STATE_PATH, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

# 每个角色需要的动画
PLAN = {
    "char_player": ["idle", "walk", "run"],
    "char_ye_wenjie": ["idle"], "char_follower": ["idle"], "char_von_neumann": ["idle"], "char_qin": ["idle"],
    "soldier_black": ["idle"], "soldier_white": ["idle"],
}

def main():
    args = sys.argv[1:]
    only = None; dry = "--dry" in args
    if "--only" in args: only = args[args.index("--only") + 1].split(",")
    if "--anims" in args:
        a = args[args.index("--anims") + 1].split(",")
        for k in PLAN: PLAN[k] = a
    for name, anims in PLAN.items():
        if only and name not in only: continue
        src = TASKS[name]["task_id"]
        st = STATE.setdefault(name, {"model_task": src})
        print(f"\n== {name}  model_task={src[:8]}  anims={anims}", flush=True)
        if dry: continue
        # 1. 预检查
        if "riggable" not in st:
            tid = _req("POST", f"{API3}/animations/rig-check", {"input": src})["data"]["task_id"]
            res = wait(tid); st["riggable"] = res.get("output", {}).get("riggable"); save()
        print(f"   riggable={st['riggable']}")
        if st["riggable"] is False: print("   ✗ 不可绑骨，跳过"); continue
        # 2. 绑骨
        if "rig_task" not in st:
            payload = {"input": src, "out_format": "glb", "model": "v3.0-20260909", "rig_type": "biped", "spec": "mixamo"}
            st["rig_task"] = _req("POST", f"{API3}/animations/rig", payload)["data"]["task_id"]; save()
            print(f"   rig task {st['rig_task'][:8]} 已创建", flush=True)
        if "rig_url" not in st:
            res = wait(st["rig_task"])
            out = res.get("output", {}); st["rig_url"] = out.get("model") or out.get("pbr_model") or out.get("model_url")
            st["rig_credits"] = res.get("credits_consumed") or res.get("consumed_credit"); save()
            download(st["rig_url"], os.path.join(ANIM_DIR, f"{name}_rig.glb"))
            print(f"   ✓ rig → {name}_rig.glb  credits={st['rig_credits']}", flush=True)
        # 3. 重定向动画
        if "anim_task" not in st:
            payload = {"input": st["rig_task"], "out_format": "glb",
                       "animations": [f"preset:{a}" for a in anims], "animate_in_place": True, "export_with_geometry": True}
            st["anim_task"] = _req("POST", f"{API3}/animations/retarget", payload)["data"]["task_id"]; st["anims"] = anims; save()
            print(f"   retarget task {st['anim_task'][:8]} 已创建", flush=True)
        if "anim_url" not in st:
            res = wait(st["anim_task"])
            out = res.get("output", {}); st["anim_output"] = out
            st["anim_url"] = out.get("model") or out.get("pbr_model") or out.get("model_url")
            st["anim_credits"] = res.get("credits_consumed") or res.get("consumed_credit"); save()
            download(st["anim_url"], os.path.join(ANIM_DIR, f"{name}_anim.glb"))
            print(f"   ✓ anim → {name}_anim.glb  credits={st['anim_credits']}  output_keys={list(out.keys())}", flush=True)
    print("\ndone.")

if __name__ == "__main__":
    main()
