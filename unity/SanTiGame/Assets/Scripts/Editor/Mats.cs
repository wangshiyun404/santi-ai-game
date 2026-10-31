using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace SanTi.Editor
{
    /// <summary>
    /// 材质规范化（第 5 轮盲审结论）：
    /// Tripo 导出的 glTF 材质带 metallicRoughness 贴图且 metallicFactor 默认 1，在 Unity 平光环境里整件发"镀铬银"，
    /// 角色和雷达天线都失真。这里把贴图材质统一转成 URP/Lit：保留 BaseMap / Normal，金属度归零、光滑度压低，并开启 GPU 实例化。
    /// B 类平涂材质（只有 baseColorFactor）原样保留。
    /// </summary>
    public static class Mats
    {
        const string MatDir = "Assets/Materials";
        const string SettingsDir = "Assets/Settings";
        const string TexDir = "Assets/Textures/Tripo";
        static readonly Dictionary<Material, Material> Cache = new();
        /// <summary>B 类平涂材质的颜色覆盖（asset/materialName → 颜色）。第 5 轮：乱纪元地面 22% 深色面片在 Unity 里成了巨型棋盘，压低对比。</summary>
        static readonly Dictionary<string, Color> ColorOverride = new()
        {
            { "ground_chaotic/crack", new Color(0.47f, 0.43f, 0.39f).gamma },   // 线性值≈dust(0.55) 的 85%；.gamma 与 glTFast 写入 _BaseColor 的 sRGB 约定一致
        };

        public static void ConvertRenderers(GameObject go, string assetName)
        {
            foreach (var r in go.GetComponentsInChildren<Renderer>(true))
            {
                var mats = r.sharedMaterials; bool changed = false;
                for (int i = 0; i < mats.Length; i++)
                {
                    var m = Convert(mats[i], assetName);
                    if (m != mats[i]) { mats[i] = m; changed = true; }
                }
                if (changed) r.sharedMaterials = mats;
            }
        }

        public static Material Convert(Material src, string assetName)
        {
            if (src == null) return null;
            if (Cache.TryGetValue(src, out var cached)) return cached;

            // 第 6 轮（WebGL 体积）：Tripo 贴图已由 scripts/strip_glb_textures.py 抽为外置 PNG（压缩 + mipmap），GLB 内不再含贴图
            var external = AssetDatabase.LoadAssetAtPath<Texture2D>($"{TexDir}/{assetName}_base.png");
            var baseTex = external != null ? external : GetTex(src, "baseColorTexture", "_BaseMap", "_MainTex");
            var mrTex = GetTex(src, "metallicRoughnessTexture", "_MetallicGlossMap");
            var normalTex = GetTex(src, "normalTexture", "_BumpMap");
            float metal = GetFloat(src, 1f, "metallicFactor", "_Metallic");
            bool hasOverride = ColorOverride.TryGetValue(assetName + "/" + src.name, out var overrideColor);
            bool needs = baseTex != null || mrTex != null || metal > 0.5f || hasOverride;
            if (!needs) { Cache[src] = src; return src; }

            Directory.CreateDirectory($"{MatDir}/Tripo");
            string path = $"{MatDir}/Tripo/{assetName}_{Sanitize(src.name)}.mat";
            var dst = AssetDatabase.LoadAssetAtPath<Material>(path);
            var lit = Shader.Find("Universal Render Pipeline/Lit");
            if (dst == null) { dst = new Material(lit); AssetDatabase.CreateAsset(dst, path); }
            else dst.shader = lit;

            dst.SetTexture("_BaseMap", baseTex);
            dst.SetColor("_BaseColor", hasOverride ? overrideColor : GetColor(src, Color.white, "baseColorFactor", "_BaseColor", "_Color"));
            dst.SetFloat("_Metallic", 0f);
            dst.SetFloat("_Smoothness", 0.25f);
            dst.SetTexture("_MetallicGlossMap", null); dst.DisableKeyword("_METALLICSPECGLOSSMAP");
            if (normalTex != null) { dst.SetTexture("_BumpMap", normalTex); dst.EnableKeyword("_NORMALMAP"); }
            else { dst.SetTexture("_BumpMap", null); dst.DisableKeyword("_NORMALMAP"); }
            dst.enableInstancing = true;
            EditorUtility.SetDirty(dst);
            Cache[src] = dst;
            return dst;
        }

        /// <summary>外置 Tripo 贴图导入设置：sRGB、mipmap、压缩（Crunch 质量 70）、最大 1024（主角 2048）；WebGL 构建体积从 145 MB 降到约 30 MB。</summary>
        public static void SetupTextureImporters()
        {
            if (!Directory.Exists(TexDir)) return;
            int n = 0;
            foreach (var file in Directory.GetFiles(TexDir, "*.png"))
            {
                var path = file.Replace('\\', '/');
                var ti = AssetImporter.GetAtPath(path) as TextureImporter;
                if (ti == null) continue;
                int maxSize = Path.GetFileName(path).StartsWith("char_player") ? 2048 : 1024;   // 第 10 轮：写实主角脸部需要 2048
                bool dirty = ti.maxTextureSize != maxSize || !ti.crunchedCompression || ti.textureCompression != TextureImporterCompression.Compressed;
                ti.textureType = TextureImporterType.Default; ti.sRGBTexture = true; ti.mipmapEnabled = true;
                ti.maxTextureSize = maxSize; ti.textureCompression = TextureImporterCompression.Compressed;
                ti.crunchedCompression = true; ti.compressionQuality = 70; ti.alphaIsTransparency = false;
                if (dirty) { ti.SaveAndReimport(); n++; }
            }
            Debug.Log($"[SanTi] Texture importers: {n} updated in {TexDir}");
        }

        /// <summary>全局后期：ACES 色调映射（压过曝）+ 轻 Bloom（发光面片/三日）+ 轻暗角。</summary>
        public static VolumeProfile PostFxProfile()
        {
            Directory.CreateDirectory(SettingsDir);
            string path = $"{SettingsDir}/PostFX.asset";
            var prof = AssetDatabase.LoadAssetAtPath<VolumeProfile>(path);
            if (prof != null) return prof;
            prof = ScriptableObject.CreateInstance<VolumeProfile>();
            AssetDatabase.CreateAsset(prof, path);
            var tm = prof.Add<Tonemapping>(true); tm.mode.Override(TonemappingMode.ACES);
            var bloom = prof.Add<Bloom>(true); bloom.intensity.Override(0.35f); bloom.threshold.Override(1.1f);
            var vig = prof.Add<Vignette>(true); vig.intensity.Override(0.18f);
            AssetDatabase.SaveAssets();
            return prof;
        }

        static Texture GetTex(Material m, params string[] names)
        { foreach (var n in names) if (m.HasProperty(n)) { var t = m.GetTexture(n); if (t != null) return t; } return null; }
        static float GetFloat(Material m, float def, params string[] names)
        { foreach (var n in names) if (m.HasProperty(n)) return m.GetFloat(n); return def; }
        static Color GetColor(Material m, Color def, params string[] names)
        { foreach (var n in names) if (m.HasProperty(n)) return m.GetColor(n); return def; }
        static string Sanitize(string s)
        { foreach (var c in Path.GetInvalidFileNameChars()) s = s.Replace(c, '_'); return s.Replace(' ', '_'); }
    }
}
