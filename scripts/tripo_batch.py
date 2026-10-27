"""
Tripo 批量生成 A 类资产。
用法:
  TRIPO_API_KEY=tsk_xxx python tripo_batch.py manifest.json [--only dish_tower,char_player] [--dry]
manifest.json 示例见 ../docs/tripo_manifest.json

接口（Tripo OpenAPI v2，兼容 v3.1 模型）:
  POST https://api.tripo3d.ai/v2/openapi/upload           multipart file → data.image_token
  POST https://api.tripo3d.ai/v2/openapi/task             {type, prompt | file, model_version, face_limit, quad, texture, pbr}
  GET  https://api.tripo3d.ai/v2/openapi/task/{task_id}   status: queued/running/success/failed..., output.pbr_model
模型版本: 道具 H3.1 = "v3.1-20260211"；角色低面四边面 = "P1-20260311"（Smart Mesh P 系列，可选 quad=True）
"""
import json, os, sys, time, mimetypes

API = "https://api.tripo3d.ai/v2/openapi"
KEY = os.environ.get("TRIPO_API_KEY", "")
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "..", "assets", "tripo")
os.makedirs(OUT, exist_ok=True)

def _req(method, url, data=None, files=None):
    import requests
    h = {"Authorization": f"Bearer {KEY}"} if KEY else {}   # 无 KEY 时依赖 HTTPS 代理注入鉴权
    r = requests.request(method, url, json=data if files is None else None, files=files, headers=h, timeout=180)
    if r.status_code >= 400:
        raise SystemExit(f"HTTP {r.status_code} {url}: {r.text[:500]}")
    res = r.json()
    if res.get("code", 0) != 0:
        raise SystemExit(f"Tripo error {res.get('code')}: {res.get('message')} — {res.get('suggestion','')}")
    return res

def upload_image(path):
    with open(path, "rb") as f:
        res = _req("POST", f"{API}/upload", files={"file": (os.path.basename(path), f, mimetypes.guess_type(path)[0] or "image/png")})
    return res["data"]["image_token"]

def create_task(item):
    payload = {"model_version": item.get("model_version", "v3.1-20260211"),
               "texture": item.get("texture", True), "pbr": item.get("pbr", True)}
    if item.get("face_limit"): payload["face_limit"] = item["face_limit"]
    if item.get("quad") and not payload["model_version"].startswith("P"): payload["quad"] = True
    if item.get("multiview"):
        payload["type"] = "multiview_to_model"
        payload["files"] = [{"type": "png", "file_token": upload_image(os.path.join(ROOT, "..", p))} for p in item["multiview"]]
    elif item.get("image"):
        payload["type"] = "image_to_model"
        payload["file"] = {"type": "png", "file_token": upload_image(os.path.join(ROOT, "..", item["image"]))}
        if item.get("prompt"): payload["prompt"] = item["prompt"]  # 部分版本支持图+文
    else:
        payload["type"] = "text_to_model"
        payload["prompt"] = item["prompt"]
        if item.get("negative_prompt"): payload["negative_prompt"] = item["negative_prompt"]
    res = _req("POST", f"{API}/task", data=payload)
    return res["data"]["task_id"]

def wait(task_id, every=6, timeout=1200):
    t0 = time.time()
    while time.time() - t0 < timeout:
        res = _req("GET", f"{API}/task/{task_id}")["data"]
        st = res["status"]
        if st == "success": return res
        if st in ("failed", "cancelled", "banned", "expired"): raise SystemExit(f"task {task_id} {st}: {res}")
        print(f"   {task_id[:8]} {st} {res.get('progress', 0)}%", flush=True)
        time.sleep(every)
    raise SystemExit("timeout " + task_id)

def download(url, path):
    import requests
    sess = requests.Session(); sess.trust_env = False   # 模型文件在独立存储域名上，签名 URL 无需鉴权，绕过凭据代理
    with sess.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(1 << 16): f.write(chunk)

def balance():
    return _req("GET", f"{API}/user/balance")["data"]

def main():
    args = sys.argv[1:]
    if args and args[0] == "--balance":
        print(balance()); return
    if args and args[0] == "--redownload":
        log = json.load(open(os.path.join(OUT, "tasks.json")))
        for name, it in log.items():
            res = _req("GET", f"{API}/task/{it['task_id']}")["data"]
            url = res["output"].get("pbr_model") or res["output"].get("model")
            if url: download(url, os.path.join(OUT, f"{name}.glb")); print("✓", name, res.get("consumed_credit"))
        return
    if not args: raise SystemExit(__doc__)
    manifest = json.load(open(args[0], encoding="utf-8"))
    only = None; dry = "--dry" in args
    if "--only" in args: only = set(args[args.index("--only") + 1].split(","))
    items = [i for i in manifest["assets"] if not only or i["name"] in only]
    if not KEY and not dry and not os.environ.get("HTTPS_PROXY"): raise SystemExit("TRIPO_API_KEY 未设置")
    print(f"{len(items)} assets")
    tasks = {}
    log_path = os.path.join(OUT, "tasks.json")
    log = json.load(open(log_path)) if os.path.exists(log_path) else {}
    for it in items:
        print(f"→ {it['name']}  [{it.get('model_version','v3.1-20260211')}]  {'img' if it.get('image') else 'txt'}", flush=True)
        if dry: continue
        try:
            tasks[it["name"]] = create_task(it)
        except SystemExit as e:
            print(f"! {it['name']} 创建失败: {e}", flush=True); continue
        log[it["name"]] = {"task_id": tasks[it["name"]]}; json.dump(log, open(log_path, "w"), indent=1)
    for name, tid in tasks.items():
        res = wait(tid)
        url = res["output"].get("pbr_model") or res["output"].get("model")
        log[name].update({"status": res["status"], "consumed_credit": res.get("consumed_credit"), "riggable": res["output"].get("riggable"), "url": url})
        json.dump(log, open(log_path, "w"), indent=1)
        dst = os.path.join(OUT, f"{name}.glb")
        try:
            download(url, dst)
            print(f"✓ {name} → {dst}  ({os.path.getsize(dst)//1024} KB)  credits={res.get('consumed_credit')}  riggable={res['output'].get('riggable')}")
        except Exception as e:
            print(f"! {name} 下载失败（URL 已记录在 tasks.json，可用 --redownload 重试）: {e}")
    print("done. 下一步: 在 Blender 中检查比例/朝向并导出覆盖 unity/SanTiGame/Assets/Models/<name>.glb")

if __name__ == "__main__":
    main()
