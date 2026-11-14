#!/bin/bash
# 一键：建基础体 → 标定渲染 → 关键点 → 射线 3D → PnP → 烘焙/深度 → 合成贴图 → 对照渲染
# 用法: bash run_all.sh <variants.json> <variant> <workdir> [render_samples]
cd "$(dirname "$0")"
VJ=$1; VN=$2; WD=$3; SMP=${4:-64}
ANCHOR=/home/user/workspace/ye_anchor/ye_head_turnaround.png
BASESKIN=/home/user/.config/blender/5.0/extensions/.user/user_default/mpfb/data/skins/ye_wenjie_fair/ye_wenjie_fair_diffuse.png
BPY=/tmp/bpyenv/bin/python
mkdir -p $WD
$BPY 01_build_base.py ../$VJ $VN $WD/base.blend 2>&1 | grep -E "NO TARGET|saved"
VIEWS=front,q34 $BPY 02_calib_render.py $WD/base.blend $WD/calib 2>&1 | grep -E "^done|Error"
python3 03_landmarks.py $ANCHOR $WD/calib $WD/lm 2>&1 | grep -v -E "^W0000|^INFO|^WARNING"
$BPY 04_raycast_lm.py $WD/base.blend $WD/calib/calib_meta.json $WD/lm/landmarks.json $WD/lm/lm3d.json 2>&1 | grep -E "hits|Error"
python3 05_pnp.py $WD/lm $WD/pnp | grep -v saved
$BPY 06_bake_depth.py $WD/base.blend $WD/pnp/cams.json $WD/bake 2048 2>&1 | grep -E "Error|Traceback"
python3 07_compose.py $WD/lm $WD/pnp $WD/bake $BASESKIN $WD/tex 2>&1 | grep -E "color|saved"
$BPY 08_render_compare.py $WD/base.blend $WD/pnp/cams.json $WD/tex/ye_face_projected_diffuse.png $WD/render $SMP no_browgeo 2>&1 | grep -E "done|Error|Traceback"
python3 - <<PY
from PIL import Image
for v in ['front','q34','left']:
    a=Image.open('$WD/lm/anchor_%s.png'%v).convert('RGB'); r=Image.open('$WD/render/render_%s.png'%v).convert('RGB')
    a=a.crop((0,120,a.width,760)); r=r.crop((0,120,r.width,760))
    s=Image.new('RGB',(a.width+r.width,640),'white'); s.paste(a,(0,0)); s.paste(r,(a.width,0)); s.save('$WD/render/cmp_%s.jpg'%v,quality=88)
print("compare sheets written")
PY
