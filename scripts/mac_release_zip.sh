#!/bin/bash
# 在 Mac 上：重新打包 macOS 版 → 压成 ~/Desktop/三体游戏_macOS.zip（供 GitHub Release 与课堂离线使用）
S="$HOME/santi_zip_status.txt"; ROOT="$HOME/santi-ai-game"
U=/Applications/Unity/Hub/Editor/6000.3.27f1/Unity.app/Contents/MacOS/Unity
cd "$ROOT" && git checkout -- unity/SanTiGame/ProjectSettings/ProjectVersion.txt 2>/dev/null
echo "BUILD_START $(date +%T) $(git rev-parse --short HEAD)" > "$S"
"$U" -batchmode -quit -projectPath "$ROOT/unity/SanTiGame" -executeMethod SanTi.Editor.Pipeline.BuildMac -logFile "$HOME/santi_mac.log"
echo "build_rc=$?" >> "$S"
APP="$ROOT/unity/SanTiGame/Builds/macOS/三体游戏.app"
[ -d "$APP" ] || { echo "NO_APP" >> "$S"; exit 1; }
rm -rf "$ROOT/unity/SanTiGame/Builds/macOS/三体：三体游戏.app"
rm -f "$HOME/Desktop/三体游戏_macOS.zip" "$HOME/Desktop/三体三体游戏_macOS.zip"
cd "$ROOT/unity/SanTiGame/Builds/macOS" && ditto -c -k --sequesterRsrc --keepParent "三体游戏.app" "$HOME/Desktop/三体游戏_macOS.zip"
ls -la "$HOME/Desktop/三体游戏_macOS.zip" >> "$S"; echo "ZIP_DONE $(date +%T)" >> "$S"
