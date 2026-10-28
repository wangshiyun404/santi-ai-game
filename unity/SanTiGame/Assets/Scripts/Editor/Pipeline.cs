using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace SanTi.Editor
{
    /// <summary>
    /// 无头流水线（供命令行 -batchmode -executeMethod 调用，也可在菜单 SanTi 下手动执行）：
    ///   SetupProject  → 建立 URP 资产并指定给 Graphics/Quality，设置玩家与 WebGL 参数，重导 Models（让 glTFast 用 URP 着色器）
    ///   BuildScenes   → SetupProject + SceneBuilder.BuildAll
    ///   CaptureReview → 逐场景打开，按 FollowCamera 规则放相机，渲染 PNG 到 review/unity/（供盲审）
    ///   BuildWebGL    → 打 WebGL 包到 Builds/WebGL
    /// 命令行：Unity -batchmode -quit -projectPath &lt;proj&gt; -executeMethod SanTi.Editor.Pipeline.BuildScenes -logFile &lt;log&gt;
    /// </summary>
    public static class Pipeline
    {
        const string SettingsDir = "Assets/Settings";
        const string SceneDir = "Assets/Scenes";

        // ---------- 1. 工程设置 ----------
        [MenuItem("SanTi/Pipeline/1 Setup Project (URP + Player)")]
        public static void SetupProject()
        {
            Directory.CreateDirectory(SettingsDir);
            var rendererPath = $"{SettingsDir}/URP_Renderer.asset";
            var assetPath = $"{SettingsDir}/URP_Asset.asset";

            var rendererData = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(rendererPath);
            if (rendererData == null)
            {
                rendererData = ScriptableObject.CreateInstance<UniversalRendererData>();
                AssetDatabase.CreateAsset(rendererData, rendererPath);
            }
            var urp = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(assetPath);
            if (urp == null)
            {
                urp = UniversalRenderPipelineAsset.Create(rendererData);
                AssetDatabase.CreateAsset(urp, assetPath);
            }
            // 低多边形 + 远景雾：阴影距离拉远一点，开 HDR 让发光面片有光晕余地
            urp.shadowDistance = 150f;
            urp.supportsHDR = true;
            urp.msaaSampleCount = 4;
            EditorUtility.SetDirty(urp);

            bool wasUrp = GraphicsSettings.defaultRenderPipeline == urp;
            GraphicsSettings.defaultRenderPipeline = urp;
            int lvl = QualitySettings.GetQualityLevel();
            for (int i = 0; i < QualitySettings.names.Length; i++) { QualitySettings.SetQualityLevel(i, false); QualitySettings.renderPipeline = urp; }
            QualitySettings.SetQualityLevel(lvl, false);

            PlayerSettings.productName = "三体：三体游戏";
            PlayerSettings.companyName = "SanTi AI Lab (非官方同人改编，原著 © 刘慈欣)";
            PlayerSettings.colorSpace = ColorSpace.Linear;
            PlayerSettings.defaultScreenWidth = 1280; PlayerSettings.defaultScreenHeight = 720;
            PlayerSettings.WebGL.compressionFormat = WebGLCompressionFormat.Gzip;
            PlayerSettings.WebGL.decompressionFallback = true;          // 任意静态托管都能跑（不依赖 Content-Encoding 头）
            PlayerSettings.WebGL.dataCaching = true;
            PlayerSettings.WebGL.exceptionSupport = WebGLExceptionSupport.ExplicitlyThrownExceptionsOnly;
            PlayerSettings.WebGL.memorySize = 512;
            PlayerSettings.runInBackground = true;
            PlayerSettings.SetScriptingBackend(NamedBuildTarget.WebGL, ScriptingImplementation.IL2CPP);
            PlayerSettings.SetIl2CppCompilerConfiguration(NamedBuildTarget.WebGL, Il2CppCompilerConfiguration.Release);

            AssetDatabase.SaveAssets();

            // glTFast 在导入时按当前管线挑着色器：首次导入发生在 URP 指定之前 → 必须重导一次
            if (!wasUrp)
            {
                Debug.Log("[SanTi] URP assigned; reimporting Assets/Models so glTFast materials use URP shaders");
                AssetDatabase.ImportAsset("Assets/Models", ImportAssetOptions.ImportRecursive | ImportAssetOptions.ForceUpdate);
            }
            AssetDatabase.Refresh();
            Debug.Log("[SanTi] SetupProject done");
        }

        // ---------- 2. 场景 ----------
        [MenuItem("SanTi/Pipeline/2 Build Scenes")]
        public static void BuildScenes()
        {
            SetupProject();
            SceneBuilder.BuildAll();
            AssetDatabase.SaveAssets();
            Debug.Log("[SanTi] BuildScenes done: " + string.Join(", ", EditorBuildSettings.scenes.Select(s => s.path)));
        }

        // ---------- 3. 盲审截图 ----------
        [MenuItem("SanTi/Pipeline/3 Capture Review Shots")]
        public static void CaptureReview()
        {
            string outDir = Environment.GetEnvironmentVariable("SANTI_REVIEW_DIR");
            if (string.IsNullOrEmpty(outDir)) outDir = Path.GetFullPath(Path.Combine(Application.dataPath, "../../../review/unity"));
            Directory.CreateDirectory(outDir);

            foreach (var scenePath in Directory.GetFiles(SceneDir, "scene_*.unity").OrderBy(p => p))
            {
                string id = Path.GetFileNameWithoutExtension(scenePath);
                EditorSceneManager.OpenScene(scenePath, OpenSceneMode.Single);
                var player = GameObject.FindWithTag("Player");
                var cam = Camera.main ?? UnityEngine.Object.FindFirstObjectByType<Camera>();
                if (cam == null) { Debug.LogWarning("[SanTi] no camera in " + id); continue; }
                Vector3 p = player ? player.transform.position : Vector3.zero;
                float yaw = player ? player.transform.eulerAngles.y : 0f;

                // a) 玩家视角（与 FollowCamera 一致）
                Place(cam, p + Vector3.up * 1.4f, Quaternion.Euler(15f, yaw, 0f), 6f, 2.5f - 1.4f);
                Shot(cam, Path.Combine(outDir, id + "_a_player.png"), 1600, 900);
                // b) 玩家视角向左/右各 60°（看周围有没有穿模/漂浮）
                Place(cam, p + Vector3.up * 1.4f, Quaternion.Euler(12f, yaw - 60f, 0f), 6f, 1.1f);
                Shot(cam, Path.Combine(outDir, id + "_b_left.png"), 1600, 900);
                Place(cam, p + Vector3.up * 1.4f, Quaternion.Euler(12f, yaw + 60f, 0f), 6f, 1.1f);
                Shot(cam, Path.Combine(outDir, id + "_c_right.png"), 1600, 900);
                // d) 高空俯瞰（整体布局、朝向、地面贴合）
                Place(cam, p, Quaternion.Euler(45f, yaw, 0f), 80f, 0f);
                Shot(cam, Path.Combine(outDir, id + "_d_overview.png"), 1600, 900);
                // e) 低角度贴地（专查悬浮/陷地）
                Place(cam, p + Vector3.up * 0.3f, Quaternion.Euler(2f, yaw + 30f, 0f), 10f, 0f);
                Shot(cam, Path.Combine(outDir, id + "_e_ground.png"), 1600, 900);
            }
            Debug.Log("[SanTi] CaptureReview done → " + outDir);
        }

        static void Place(Camera cam, Vector3 pivot, Quaternion rot, float distance, float extraHeight)
        {
            Vector3 pos = pivot - rot * Vector3.forward * distance + Vector3.up * extraHeight;
            cam.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(pivot - pos));
        }

        static void Shot(Camera cam, string file, int w, int h)
        {
            var rt = new RenderTexture(w, h, 24, RenderTextureFormat.ARGB32) { antiAliasing = 4 };
            var prevRt = cam.targetTexture; var prevActive = RenderTexture.active;
            cam.targetTexture = rt;
            cam.Render();
            RenderTexture.active = rt;
            var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, w, h), 0, 0); tex.Apply();
            File.WriteAllBytes(file, tex.EncodeToPNG());
            cam.targetTexture = prevRt; RenderTexture.active = prevActive;
            UnityEngine.Object.DestroyImmediate(tex); rt.Release(); UnityEngine.Object.DestroyImmediate(rt);
            Debug.Log("[SanTi] shot " + file);
        }

        // ---------- 4. WebGL ----------
        [MenuItem("SanTi/Pipeline/4 Build WebGL")]
        public static void BuildWebGL()
        {
            var scenes = EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).ToArray();
            if (scenes.Length == 0) { Debug.LogError("[SanTi] no scenes in build settings; run BuildScenes first"); return; }
            string outDir = Environment.GetEnvironmentVariable("SANTI_WEBGL_DIR");
            if (string.IsNullOrEmpty(outDir)) outDir = Path.GetFullPath(Path.Combine(Application.dataPath, "../Builds/WebGL"));
            Directory.CreateDirectory(outDir);
            var opts = new BuildPlayerOptions { scenes = scenes, locationPathName = outDir, target = BuildTarget.WebGL, options = BuildOptions.None };
            var report = BuildPipeline.BuildPlayer(opts);
            Debug.Log($"[SanTi] WebGL build {report.summary.result}: {report.summary.totalSize / 1024 / 1024} MB, {report.summary.totalErrors} errors, {report.summary.totalTime.TotalMinutes:F1} min → {outDir}");
            if (report.summary.result != UnityEditor.Build.Reporting.BuildResult.Succeeded) EditorApplication.Exit(1);
        }
    }
}
