#!/bin/bash
# Mac 上：拉代码 → 重建三场景 → Play 模式盲审截图（含正面脸部特写）→ 打包到 ~/santi_review.zip
# 状态写到 ~/santi_verify_status.txt（只含计数与摘要，不含日志全文）
set -u
ROOT="$HOME/santi-ai-game"; U=/Applications/Unity/Hub/Editor/6000.3.27f1/Unity.app/Contents/MacOS/Unity
P="$ROOT/unity/SanTiGame"; S="$HOME/santi_verify_status.txt"; R="$HOME/santi_review"
cd "$ROOT" || exit 1
git checkout -- unity/SanTiGame/ProjectSettings/ProjectVersion.txt 2>/dev/null
git pull -q --rebase 2>>"$S"
echo "START $(date +%T) $(git rev-parse --short HEAD)" > "$S"
rm -rf "$R"; mkdir -p "$R"
"$U" -batchmode -quit -projectPath "$P" -executeMethod SanTi.Editor.Pipeline.BuildScenes -logFile "$HOME/santi_scenes.log"
echo "scenes_rc=$? built=$(grep -c '\[SanTi\] Built Assets' "$HOME/santi_scenes.log") snapped=$(grep -o 'ground-snapped [0-9/]*' "$HOME/santi_scenes.log" | tr '\n' ' ')" >> "$S"
echo "compile_errors=$(grep -c 'error CS' "$HOME/santi_scenes.log")" >> "$S"
grep -m3 'error CS' "$HOME/santi_scenes.log" | sed 's/^.*Assets/Assets/' >> "$S"
SANTI_REVIEW_DIR="$R" "$U" -batchmode -projectPath "$P" -executeMethod SanTi.Editor.Pipeline.PlayCapture -logFile "$HOME/santi_play.log"
echo "play_rc=$? shots=$(ls "$R" | wc -l | tr -d ' ') facewarn=$(grep -c 'FaceExpression' "$HOME/santi_play.log")" >> "$S"
grep -m3 'error CS\|Exception' "$HOME/santi_play.log" | cut -c1-160 >> "$S"
rm -f "$HOME/santi_review.zip"; (cd "$HOME" && zip -qr santi_review.zip santi_review)
echo "DONE $(date +%T) zip=$(stat -f %z "$HOME/santi_review.zip" 2>/dev/null)" >> "$S"
