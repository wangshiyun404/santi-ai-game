#!/bin/bash
# 在 Mac 上录制自动演示：mac_record_demo.sh [秒数，默认 240] [--build]
# 产物：~/santi_demo.mov（原始录屏）、~/santi_demo_1080.m4v（压缩版）、~/santi_demo_timeline.txt（事件时间线）
SECS=${1:-240}
# 互斥锁：同一时刻只允许一个录制实例（E22：Terminal 曾把同一条命令执行两次，两个游戏实例互相遮挡）
LOCK="$HOME/.santi_record.lock"
if ! mkdir "$LOCK" 2>/dev/null; then echo "another record instance is running, exit"; exit 1; fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT
pgrep -f "三体：三体游戏" >/dev/null && pkill -f "三体：三体游戏"; sleep 1
MON=${SANTI_MONITOR:-1}   # 1=主显示器；2=第二块屏（录第二块屏时主屏可继续干活）
S="$HOME/santi_rec_status.txt"
ROOT="$HOME/santi-ai-game"
APP="$ROOT/unity/SanTiGame/Builds/macOS/三体：三体游戏.app"
if [ "$2" = "--build" ]; then
  U=/Applications/Unity/Hub/Editor/6000.3.27f1/Unity.app/Contents/MacOS/Unity
  cd "$ROOT" && git checkout -- unity/SanTiGame/ProjectSettings/ProjectVersion.txt 2>/dev/null
  echo "BUILD_START $(date +%T) $(git rev-parse --short HEAD)" > "$S"
  "$U" -batchmode -quit -projectPath "$ROOT/unity/SanTiGame" -executeMethod SanTi.Editor.Pipeline.BuildMac -logFile "$HOME/santi_mac.log"
  echo "build_rc=$?" >> "$S"
else
  echo "REC_PREP $(date +%T)" > "$S"
fi
rm -f "$HOME/santi_demo.mov" "$HOME/santi_demo_1080.m4v" "$HOME/santi_demo_timeline.txt"
echo "REC_START $(date +%T)" >> "$S"
screencapture -x -D "$MON" -V "$SECS" "$HOME/santi_demo.mov" &
SC=$!
sleep 1.5
open -n "$APP" --args -demo -screen-fullscreen 1 -monitor "$MON"
wait $SC
echo "REC_STOP $(date +%T)" >> "$S"
osascript -e 'tell application "三体：三体游戏" to quit' 2>/dev/null
sleep 2
pgrep -f "三体：三体游戏" >/dev/null && pkill -f "三体：三体游戏"
ls -l "$HOME/santi_demo.mov" >> "$S"
avconvert --preset PresetAppleM4V1080pHD --source "$HOME/santi_demo.mov" --output "$HOME/santi_demo_1080.m4v" >/dev/null 2>&1
ls -l "$HOME/santi_demo_1080.m4v" >> "$S"
cp "$HOME/santi_demo_timeline.txt" "$ROOT/review/demo_timeline.txt" 2>/dev/null
echo "REC_DONE $(date +%T)" >> "$S"
