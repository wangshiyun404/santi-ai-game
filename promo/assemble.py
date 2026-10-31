"""把 Mac 录屏 + 时间线 + 旁白 + 卡片 组装成宣传/教程视频。
用法：python3 assemble.py <game.m4v> <timeline.txt> <offset_sec>  （offset = 时间线 t=0 对应的视频秒数）
"""
import sys, subprocess, json, os, glob
from PIL import Image

SRC, TL, OFF = sys.argv[1], sys.argv[2], float(sys.argv[3])
OUT = sys.argv[4] if len(sys.argv) > 4 else "三体三体游戏_宣传与教程.mp4"
W, H, FPS = 1920, 1080, 30
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONTB = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"
VO = "/home/user/workspace/santi/unity/SanTiGame/Assets/Resources/VO"

# ---- 读时间线 ----
ev = []
for line in open(TL, encoding="utf-8"):
    p = line.rstrip("\n").split("\t")
    if len(p) >= 2: ev.append((float(p[0]), p[1], p[2] if len(p) > 2 else ""))
def first(kind, val=None):
    for t, k, v in ev:
        if k == kind and (val is None or v == val): return t
    return None
t_scene1 = first("scene", "scene_01_chaotic"); t_scene2 = first("scene", "scene_02_computer")
t_sword = first("clue", "clue_sword")
t_end = t_sword + 3 + 60 + 4           # 三日凌空 60 s + 回到红岸几秒
t_lake = first("clue", "clue_lakebed"); t_slips = first("clue", "clue_slips")
t_bus = first("clue", "clue_bus")
print("scene1", t_scene1, "scene2", t_scene2, "sword", t_sword)

# ---- 剪辑计划：(t_start, t_end, speed) 按游戏时间 t ----
plan = [
    (1.0, t_lake + 5, 1.0),                        # 红岸 + 乱纪元前半（t<1 是启动黑屏）
    (t_lake + 5, t_slips - 1.5, 2.5),              # 去竹简的长路 加速
    (t_slips - 1.5, t_bus + 5, 1.0),
    (t_bus + 5, t_sword - 6, 2.5),                 # 回程 + 上坡 加速
    (t_sword - 6, t_sword + 14, 1.0),              # 剑 + 三日凌空开始
    (t_sword + 14, t_sword + 52, 4.0),             # 升起过程 加速
    (t_sword + 52, t_end, 1.0),                    # 白光 + 回到红岸
]
INTRO, OUTRO = 5.0, 12.0
def V(t):
    """游戏时间 → 成片时间"""
    v = INTRO
    for a, b, sp in plan:
        if t <= a: break
        v += (min(t, b) - a) / sp
    return v
total = V(t_end) + OUTRO
print("total", round(total, 1))

# ---- 视频：卡片 + 分段 ----
fc = []
fc.append(f"[1:v]scale={W}:{H},format=yuv420p,loop=loop={int(INTRO*FPS)}:size=1:start=0,trim=duration={INTRO},setpts=PTS-STARTPTS,fade=t=out:st={INTRO-0.6}:d=0.6[intro]")
fc.append(f"[2:v]scale={W}:{H},format=yuv420p,loop=loop={int(OUTRO*FPS)}:size=1:start=0,trim=duration={OUTRO},setpts=PTS-STARTPTS,fade=t=in:st=0:d=0.8[outro]")
segs = []
for i, (a, b, sp) in enumerate(plan):
    # 裁掉顶部菜单栏/通知（约 3.5%），再放回 16:9
    fc.append(f"[0:v]trim=start={OFF+a:.3f}:end={OFF+b:.3f},setpts=(PTS-STARTPTS)/{sp},crop=iw*0.922:ih*0.83:iw*0.039:ih*0.12,scale={W}:{H},fps={FPS},format=yuv420p[g{i}]")
    segs.append(f"[g{i}]")
fc.append("[intro]" + "".join(segs) + f"[outro]concat=n={len(plan)+2}:v=1:a=0[cat]")

# ---- 字幕/说明覆盖 ----
def esc(s): return s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\\\\\'").replace(",", "\\,").replace("[", "\\[").replace("]", "\\]")
caps = []  # (start, end, text, style)
def cap(v0, v1, text, style="tip"): caps.append((v0, v1, text, style))
# 幕标题（左上）
cap(V(0.5), V(0.5) + 6, "第一幕 · 红岸基地 1971", "title")
cap(V(t_scene1 + 0.5), V(t_scene1 + 0.5) + 6, "第二幕 · 乱纪元 · 脱水", "title")
cap(V(t_scene2 + 0.5), V(t_scene2 + 0.5) + 6, "第三幕 · 人列计算机", "title")
cap(V(t_sword + 10), V(t_sword + 10) + 6, "结局 · 三日凌空", "title")
# 操作提示（底部左）
cap(V(first("reach", "1")), V(first("reach", "1")) + 12, "W A S D 移动   鼠标 转动视角", "tip")
cap(V(first("clue", "clue_antenna")) - 3, V(first("clue", "clue_antenna")) + 5, "靠近发光的物件 → 按 E 查看线索", "tip")
cap(V(first("clue", "clue_control_room")) - 6, V(first("clue", "clue_control_room")) + 2, "关键线索：触发后白屏切到下一幕", "tip")
cap(V(first("clue", "clue_dehydration")) - 2, V(first("clue", "clue_dehydration")) + 5, "线索 1/4  脱水人", "tip")
cap(V(t_lake) - 1, V(t_lake) + 5, "线索 2/4  干湖床中央", "tip")
cap(V(t_slips) - 1, V(t_slips) + 5, "线索 3/4  金字塔前的竹简", "tip")
cap(V(first("clue", "clue_pyramid_follower")) - 1, V(first("clue", "clue_pyramid_follower")) + 3, "线索 4/4  追随者 → 进入第三幕", "tip")
cap(V(first("clue", "clue_von_neumann")) - 1, V(first("clue", "clue_von_neumann")) + 5, "线索 1/4  高台下（18 米内自动可按 E）", "tip")
cap(V(first("clue", "clue_gate_soldier")) - 1, V(first("clue", "clue_gate_soldier")) + 5, "线索 2/4  方阵前的石碑", "tip")
cap(V(t_bus) - 1, V(t_bus) + 5, "线索 3/4  方阵之间的石碑", "tip")
cap(V(t_sword) - 5, V(t_sword) + 6, "线索 4/4  从坡道上高台 → 青铜剑", "tip")
cap(V(t_lake + 6), V(t_slips - 1.5), "2.5× 快进", "speed")
cap(V(t_bus + 6), V(t_sword - 6), "2.5× 快进", "speed")
cap(V(t_sword + 15), V(t_sword + 52), "4× 快进", "speed")

# 同一位置的字幕不得在时间上重叠（第 9 版曾出现两条 tip 叠在一起）：后一条开始前 0.3 s 结束前一条
for style in ("tip", "title", "speed"):
    idx = [i for i, c in enumerate(caps) if c[3] == style]
    idx.sort(key=lambda i: caps[i][0])
    for a, b in zip(idx, idx[1:]):
        v0, v1, text, st = caps[a]
        if v1 > caps[b][0] - 0.3: caps[a] = (v0, max(v0 + 1.5, caps[b][0] - 0.3), text, st)
        if caps[a][1] <= caps[a][0]: print("WARN caption dropped", text)
caps = [c for c in caps if c[1] > c[0]]
draw = "[cat]"
chain = []
for i, (v0, v1, text, style) in enumerate(caps):
    if style == "title":
        d = f"drawtext=fontfile='{FONTB}':text='{esc(text)}':fontsize=54:fontcolor=white:x=70:y=70:box=1:boxcolor=black@0.45:boxborderw=18:enable='between(t,{v0:.2f},{v1:.2f})':alpha='if(lt(t,{v0+0.5:.2f}),(t-{v0:.2f})/0.5,if(gt(t,{v1-0.5:.2f}),({v1:.2f}-t)/0.5,1))'"
    elif style == "speed":
        d = f"drawtext=fontfile='{FONT}':text='{esc(text)}':fontsize=34:fontcolor=white@0.85:x=w-tw-60:y=70:box=1:boxcolor=black@0.4:boxborderw=12:enable='between(t,{v0:.2f},{v1:.2f})'"
    else:
        d = f"drawtext=fontfile='{FONT}':text='{esc(text)}':fontsize=44:fontcolor=white:x=70:y=h-th-150:box=1:boxcolor=black@0.5:boxborderw=16:enable='between(t,{v0:.2f},{v1:.2f})'"
    chain.append(d)
fc.append(draw + ",".join(chain) + "[vout]")

# ---- 音频：旁白 + 游戏原声线索 ----
nar = {  # 文件 → 成片时间
    "vo/n0.mp3": 0.0,
    "vo/n1.mp3": V(first("clue", "clue_reply")) + 3.6,
    "vo/n2.mp3": V(first("clue", "clue_antenna")) + 4.8,
    "vo/n3.mp3": V(t_scene1) + 3.0,
    "vo/n4.mp3": V(t_scene2) + 2.5,
    "vo/n5.mp3": V(t_sword) + 9.5,
    "vo/n6.mp3": V(t_end) + 0.8,
}
def dur(f): return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]).decode().strip())
busy = [(s, s + dur(f)) for f, s in nar.items()]
game_vo = {"clue_reply": "vo_00_do_not_answer.wav", "clue_antenna": "vo_00_redcoast.wav", "clue_control_room": "vo_00_transmit.wav",
           "clue_dehydration": "vo_01_dehydration.wav", "clue_lakebed": "vo_01_chaotic_begins.wav", "clue_pyramid_follower": "vo_01_follower.wav",
           "clue_gate_soldier": "vo_02_gate.wav", "clue_bus": "vo_02_bus.wav", "clue_von_neumann": "vo_02_computer.wav"}
clips = dict(nar)
for t, k, v in ev:
    if k == "clue" and v in game_vo:
        s = V(t) + (1.3 if v == "clue_antenna" else 0.5); f = os.path.join(VO, game_vo[v]); e = s + dur(f)
        if any(not (e < b0 + 0.25 or s > b1 - 0.25) for b0, b1 in busy): print("skip game vo (overlap)", v); continue
        clips[f] = s
inputs = ["-i", SRC, "-loop", "1", "-i", "card_intro.png", "-loop", "1", "-i", "card_outro.png"]
amix = []
for j, (f, s) in enumerate(clips.items()):
    inputs += ["-i", f]
    idx = 3 + j
    vol = 1.0 if f.startswith("vo/") else 0.9
    fc.append(f"[{idx}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={vol},adelay={int(s*1000)}|{int(s*1000)}[a{j}]")
    amix.append(f"[a{j}]")
fc.append("".join(amix) + f"amix=inputs={len(amix)}:duration=longest:normalize=0,apad=whole_dur={total:.2f},atrim=duration={total:.2f}[aout]")

open("filter.txt", "w").write(";\n".join(fc))
cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs, "-filter_complex_script", "filter.txt",
       "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", OUT]
print(" ".join(cmd)[:300])
subprocess.run(cmd, check=True)
json.dump({"caps": caps, "nar": nar, "total": total}, open("edit_plan.json", "w"), ensure_ascii=False, indent=1)
print("done", OUT)
