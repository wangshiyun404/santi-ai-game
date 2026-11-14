using UnityEditor;

namespace SanTi.Editor
{
    /// <summary>
    /// 立绘导入设置：Resources/Portraits 下的 PNG 是 600×800 的非 2 次幂图。
    /// Unity 默认会把它们缩放到最近的 2 次幂（512×1024），导致脸被拉长（第 14 轮真机 E37 发现）。
    /// 这里强制 NPOT 不缩放、不生成 mipmap、UI 用 sRGB、最大 1024。
    /// </summary>
    public class PortraitImporter : AssetPostprocessor
    {
        // 版本号变化会让 Unity 重新导入受此处理器影响的贴图（首次加入时已导入的立绘才能套上新设置）
        public override uint GetVersion() => 2;

        void OnPreprocessTexture()
        {
            if (!assetPath.Replace('\\', '/').Contains("/Resources/Portraits/")) return;
            var ti = (TextureImporter)assetImporter;
            ti.npotScale = TextureImporterNPOTScale.None;
            ti.mipmapEnabled = false;
            ti.sRGBTexture = true;
            ti.alphaIsTransparency = true;
            ti.wrapMode = UnityEngine.TextureWrapMode.Clamp;
            ti.maxTextureSize = 1024;
            ti.textureCompression = TextureImporterCompression.CompressedHQ;
        }
    }
}
