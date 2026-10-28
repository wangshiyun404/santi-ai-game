#!/bin/bash
# 在 Mac 上一键：重建三场景 → WebGL 构建 → 同步到 dist/webgl（保留 index.html，重新给 loader.js 打补丁）→ 提交推送。
# 用法：cd ~/santi-ai-game && git pull && bash scripts/mac_rebuild_webgl.sh
set -u
ROOT="$HOME/santi-ai-game"
U=/Applications/Unity/Hub/Editor/6000.3.27f1/Unity.app/Contents/MacOS/Unity
P="$ROOT/unity/SanTiGame"
S="$HOME/santi_status.txt"
cd "$ROOT" || exit 1
git checkout -- unity/SanTiGame/ProjectSettings/ProjectVersion.txt 2>/dev/null
echo "START $(date +%T) $(git rev-parse --short HEAD)" > "$S"
"$U" -batchmode -quit -projectPath "$P" -executeMethod SanTi.Editor.Pipeline.BuildScenes -logFile "$HOME/santi_scenes.log"
echo "scenes_rc=$?" >> "$S"
"$U" -batchmode -quit -projectPath "$P" -executeMethod SanTi.Editor.Pipeline.BuildWebGL -logFile "$HOME/santi_webgl.log"
echo "webgl_rc=$?" >> "$S"
if [ -f Builds/WebGL/Build/WebGL.data.unityweb ]; then
  cp Builds/WebGL/Build/WebGL.data.unityweb Builds/WebGL/Build/WebGL.framework.js.unityweb Builds/WebGL/Build/WebGL.wasm.unityweb dist/webgl/Build/
  python3 - <<'EOF'
s = open('Builds/WebGL/Build/WebGL.loader.js').read()
s = s.replace('void 0===window.caches', 'void 0===function(){try{return window.caches}catch(e){return void 0}}()')
open('dist/webgl/Build/WebGL.loader.js', 'w').write(s)
EOF
  ls -l dist/webgl/Build >> "$S"
  git add dist/webgl && git commit -qm "dist/webgl: 重建 $(date +%F_%T)" && git push -q && echo "PUSHED $(git rev-parse --short HEAD)" >> "$S"
else
  echo "NO_BUILD_OUTPUT" >> "$S"
fi
echo "DONE $(date +%T)" >> "$S"
