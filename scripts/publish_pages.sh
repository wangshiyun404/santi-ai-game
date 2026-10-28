#!/usr/bin/env bash
# 把 dist/webgl 发布到 gh-pages 分支（GitHub Pages 根目录）。源码分支保持私有不动。
# 每次在 gh-pages 现有历史上追加一次提交（不改写历史）。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/dist/webgl"
TMP="$(mktemp -d)"
cd "$ROOT"
if git ls-remote --exit-code --heads origin gh-pages >/dev/null 2>&1; then
  git fetch -q origin gh-pages
  git worktree add -q "$TMP" FETCH_HEAD
  cd "$TMP" && git checkout -q -B gh-pages
else
  git worktree add -q --detach "$TMP"
  cd "$TMP" && git checkout -q --orphan gh-pages && git rm -rfq . >/dev/null 2>&1 || true
fi
find . -mindepth 1 -maxdepth 1 ! -name .git -exec rm -r {} +
cp -R "$SRC"/. .
touch .nojekyll
git add -A
git commit -qm "pages: $(git -C "$ROOT" rev-parse --short HEAD) $(date +%F)" || echo "nothing changed"
git push -q origin gh-pages
cd "$ROOT" && git worktree remove --force "$TMP"
echo "published gh-pages"
