# 叶文洁皮肤：以 skins01_cc0 包的 onlytheghosts_young_eurasian_female 为底（自然唇、无浓妆），
# 饱和度 +10%、略暖，唇部加低不透明度淡玫瑰色；输出到 MPFB 用户数据 skins/ye_wenjie_skin
import os
from PIL import Image, ImageEnhance, ImageDraw, ImageFilter
import numpy as np
D=os.path.expanduser("~/.config/blender/5.0/extensions/.user/user_default/mpfb/data")
src=f"{D}/skins/onlytheghosts_young_eurasian_female"; dst=f"{D}/skins/ye_wenjie_skin"; os.makedirs(dst,exist_ok=True)
b=Image.open(f"{src}/young_eurasian_female_diffuse.png").convert('RGB')
b=ImageEnhance.Color(b).enhance(1.10)
a=np.array(b).astype(float)*np.array([1.02,0.99,0.96]); b=Image.fromarray(np.clip(a,0,255).astype('uint8'))
mask=Image.new('L',b.size,0); ImageDraw.Draw(mask).ellipse((1850-48,1045-70,1850+48,1045+70),fill=255); mask=mask.filter(ImageFilter.GaussianBlur(14))
b=Image.composite(Image.blend(b,Image.new('RGB',b.size,(190,95,100)),0.28),b,mask)
b.save(f"{dst}/ye_wenjie_diffuse.png")
m=open(f"{src}/onlytheghosts_young_eurasian_female.mhmat").read().replace('young_eurasian_female_diffuse.png','ye_wenjie_diffuse.png').replace('name onlytheghosts_young_eurasian_female','name ye_wenjie_skin')
open(f"{dst}/ye_wenjie_skin.mhmat",'w').write(m); print("ok")
