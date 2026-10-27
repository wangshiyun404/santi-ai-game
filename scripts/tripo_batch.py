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
import json, os, sys, time, urllib.request, urllib.error, mimetypes, uuid

API = "https://api.tripo3d.ai/v2/openapi"
KEY = os.environ.get("TRIPO_API_KEY", "")
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "..", "assets", "tripo")
os.makedirs(OUT, exist_ok=True)

def _req(method, url, data=None, headers=None, raw=None, ctype=None):
    h = {"Authorization": f"Bearer {KEY}"}
    if headers: h.update(headers)
    body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
    if body is not None and raw is None: h["Content-Type"] = "application/json"
    if ctype: h["Content-Type"] = ctype
    r = urllib.request.Request(url, data=body, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code} {url}: {e.read().decode()[:500]}")

def upload_image(path):
    boundary = uuid.uuid4().hex
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f: content = f.read()
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{os.path.basename(path)}\"\r\n"
            f"Content-Type: {mime}\r\n\r\n").encode() + content + f"\r\n--{boundary}--\r\n".encode()
    res = _req("POST", f"{API}/upload", raw=body, ctype=f"multipart/form-data; boundary={boundary}")
    return res["data"]["image_token"]

def create_task(item):
    payload = {"model_version": item.get("model_version", "v3.1-20260211"),
               "texture": item.get("texture", True), "pbr": item.get("pbr", True)}
    if item.get("face_limit"): payload["face_limit"] = item["face_limit"]
    if item.get("quad"): payload["quad"] = True
    if item.get("image"):
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
    urllib.request.urlretrieve(url, path)

def main():
    args = sys.argv[1:]
    if not args: raise SystemExit(__doc__)
    manifest = json.load(open(args[0], encoding="utf-8"))
    only = None; dry = "--dry" in args
    if "--only" in args: only = set(args[args.index("--only") + 1].split(","))
    items = [i for i in manifest["assets"] if not only or i["name"] in only]
    if not KEY and not dry: raise SystemExit("TRIPO_API_KEY 未设置")
    print(f"{len(items)} assets")
    tasks = {}
    for it in items:
        print(f"→ {it['name']}  [{it.get('model_version','v3.1-20260211')}]  {'img' if it.get('image') else 'txt'}")
        if dry: continue
        tasks[it["name"]] = create_task(it)
    for name, tid in tasks.items():
        res = wait(tid)
        url = res["output"].get("pbr_model") or res["output"].get("model")
        dst = os.path.join(OUT, f"{name}.glb")
        download(url, dst)
        print(f"✓ {name} → {dst}  ({os.path.getsize(dst)//1024} KB)  riggable={res['output'].get('riggable')}")
    print("done. 下一步: 在 Blender 中检查比例/朝向并导出覆盖 unity/SanTiGame/Assets/Models/<name>.glb")

if __name__ == "__main__":
    main()
