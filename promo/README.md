# 宣传片 / 使用说明视频 制作流程

1. Mac 上：`bash scripts/mac_record_demo.sh 245 --build`
   自动打包 macOS 版 → 以 `-demo` 参数全屏启动（DemoAutoPilot 自动走完三幕）→ `screencapture -V` 录屏 → `avconvert` 压成 1080p
   → `~/santi_demo_1080.m4v` + `~/santi_demo_timeline.txt`（事件时间线）。录制期间不要操作电脑。
2. 旁白：`vo/n0..n6.txt` 用 TTS 生成 `vo/n0..n6.mp3`（本次用 Gemini TTS，voice=charon）。
3. 合成：`python3 assemble.py santi_demo_1080.m4v timeline.txt <offset>`，offset = 时间线 t=0 对应的视频秒数
   （用白屏切场时刻对齐：clue_control_room 触发 + 3 s = 第二幕出现的那一帧）。
   脚本负责：裁掉菜单栏/通知区、长路程 2.5×/4× 快进、幕标题与操作提示字幕、旁白与游戏原声线索自动排期、片头片尾卡片。
