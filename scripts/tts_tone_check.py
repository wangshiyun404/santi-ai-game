"""TTS 发音核验（REA 第 8 轮固化）：faster-whisper 转写 + Praat 基频轮廓判断关键字声调。
用法: python3 scripts/tts_tone_check.py <wav/mp3...> --expect 文本 [--word 总 --tone 3]
  1) 转写文本须包含 --expect（或其去标点形式）；
  2) 若给出 --word，用 whisper 词级时间戳找到该字，提取基频(F0)：
     三声应为"低-降-（升）"：中段 F0 低于首尾且整体偏低；一声应"高-平"：标准差小、均值高。
"""
import sys, subprocess, numpy as np, wave, io, re
import parselmouth
from faster_whisper import WhisperModel
args=sys.argv[1:]; files=[a for a in args if a.endswith(('.wav','.mp3'))]
def opt(k,d=None): return args[args.index(k)+1] if k in args else d
expect=opt('--expect'); word=opt('--word'); tone=int(opt('--tone','0'))
def load16k(p):
    raw=subprocess.run(['ffmpeg','-loglevel','error','-i',p,'-ac','1','-ar','16000','-f','wav','-'],capture_output=True).stdout
    w=wave.open(io.BytesIO(raw)); a=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float32)/32768; return a
m=WhisperModel("small", device="cpu", compute_type="int8")
norm=lambda s: re.sub(r'[^\w]','',s)
for p in files:
    a=load16k(p)
    segs,_=m.transcribe(a, language='zh', beam_size=5, word_timestamps=True, initial_prompt='以下是普通话。')
    segs=list(segs); txt=''.join(s.text for s in segs)
    ok_txt = (norm(expect) in norm(txt)) if expect else True
    line=f'{p.split("/")[-1]:28s} ASR="{txt}"  文本{"✓" if ok_txt else "✗"}'
    if word:
        words=[w for s in segs for w in (s.words or [])]
        hit=[w for w in words if word in w.word]
        if hit:
            w=hit[0]; snd=parselmouth.Sound(a,16000).extract_part(from_time=max(0,w.start-0.02), to_time=w.end+0.02)
            f0=snd.to_pitch(time_step=0.005, pitch_floor=75, pitch_ceiling=400).selected_array['frequency']; f0=f0[f0>0]
            if len(f0)>=6:
                n=len(f0); a1,a2,a3=f0[:n//3].mean(),f0[n//3:2*n//3].mean(),f0[2*n//3:].mean()
                sd=f0.std()/f0.mean()
                shape='低-降-升(三声)' if (a2<a1 and a2<=a3*1.02) or (a3<a1*0.85) else ('高-平(一声)' if sd<0.06 else '其它')
                line+=f'  「{w.word.strip()}」F0 {a1:.0f}→{a2:.0f}→{a3:.0f} Hz, 相对标准差 {sd:.2f} → {shape}'
                if tone==3 and '三声' not in shape: ok_txt=False; line+='  ✗声调'
                if tone==1 and '一声' not in shape: ok_txt=False; line+='  ✗声调'
            else: line+='  (F0 点不足)'
        else: line+=f'  (词级时间戳里没找到「{word}」)'
    print(line)
