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
    /// 菜单 SanTi → Build Scene From Layout…
    /// 读取 Assets/StreamingAssets/layouts/scene_XX.json，自动在 Unity 中搭建场景：
    /// 导入 GLB（glTFast 导入为 Prefab）→ 按位置/旋转/缩放实例化 → 光照/雾/色板 → 玩家与相机 → 线索与事件 → 保存 .unity 场景。
    /// 这一环对应 Sac 管线里 "Opus 5.5 通过 Unity MCP 下场搭建"；这里改成可重复执行的确定性脚本。
    /// </summary>
    public static class SceneBuilder
    {
        const string LayoutDir = "Assets/StreamingAssets/layouts";
        const string ModelDir = "Assets/Models";
        const string AnimDir = "Assets/Models/Anim";   // Tripo 绑骨+动画 GLB（原始 1 m 归一化、朝向 -X），由 InstantiateCharacter 统一缩放/转向
        static readonly System.Collections.Generic.Dictionary<string, float> CharHeight = new()
        { { "char_player", 1.72f }, { "char_ye_wenjie", 1.62f }, { "char_follower", 1.65f }, { "char_von_neumann", 1.75f }, { "char_newton", 1.70f }, { "char_qin", 1.78f }, { "soldier_black", 1.75f }, { "soldier_white", 1.75f } };
        const string SceneDir = "Assets/Scenes";
        const string MatDir = "Assets/Materials";
        // 碰撞规则：大而不规则的用 MeshCollider；远景/装饰/发光面片不加碰撞（围栏若用 BoxCollider 会把整个高地封死）
        static readonly System.Collections.Generic.HashSet<string> MeshColliderAssets = new() { "platform", "cliff", "pyramid", "fence_ring", "dry_lakebed", "dish_tower" };
        static readonly System.Collections.Generic.HashSet<string> NoCollider = new() { "cloud_sea", "window_lights", "sun_sphere", "mountains" };

        [MenuItem("SanTi/Build Scene From Layout/scene_00_red_coast")] static void B0() => Build("scene_00_red_coast");
        [MenuItem("SanTi/Build Scene From Layout/scene_01_chaotic")] static void B1() => Build("scene_01_chaotic");
        [MenuItem("SanTi/Build Scene From Layout/scene_02_computer")] static void B2() => Build("scene_02_computer");
        [MenuItem("SanTi/Build All Scenes")]
        public static void BuildAll() { foreach (var f in Directory.GetFiles(LayoutDir, "scene_*.json")) Build(Path.GetFileNameWithoutExtension(f)); }

        public static void Build(string sceneId)
        {
            string jsonPath = Path.Combine(LayoutDir, sceneId + ".json");
            if (!File.Exists(jsonPath)) { Debug.LogError("Layout not found: " + jsonPath); return; }
            var data = JsonUtility.FromJson<LayoutData>(File.ReadAllText(jsonPath));
            Directory.CreateDirectory(SceneDir); Directory.CreateDirectory(MatDir);

            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var root = new GameObject("Layout_" + sceneId).transform;

            // ---- 光照 ----
            var sunGo = new GameObject("Sun");
            var sun = sunGo.AddComponent<Light>();
            sun.type = LightType.Directional; sun.shadows = LightShadows.Soft;
            if (data.lighting != null)
            {
                var a = data.lighting.sunAngle ?? new[] { 50f, 0f, 30f };
                // Blender 太阳欧拉角(近似) → Unity：俯仰取 90-x，偏航取 z
                sunGo.transform.rotation = Quaternion.Euler(90f - a[0], 180f - a[2], 0f);   // Blender 太阳 (rx,0,rz) → Unity，见 scripts/coords.py sun_to_unity
                // 第 5 轮盲审：线性色彩空间下 ×0.6 仍过曝（乱纪元一片白），改为 ×0.5 并封顶 2.0；阴影面全黑 → 环境光改三色并提亮
                sun.intensity = Mathf.Clamp(data.lighting.intensity * 0.5f, 0.3f, 1.0f);
                sun.color = ColorUtil.Hex(data.lighting.sunColor, Color.white);
                var amb = ColorUtil.Hex(data.lighting.ambient, Color.gray);
                // 第 6 轮：环境光峰值随太阳强度反向调整（直射 1.0 → 环境 0.3；黄昏 0.6 → 0.5），使地面辐照度 ≈1 不再过曝
                float ambTarget = Mathf.Clamp(1.0f - sun.intensity * 0.7f, 0.25f, 0.5f);
                float k = Mathf.Min(2.0f, ambTarget / Mathf.Max(0.05f, Mathf.Max(amb.r, Mathf.Max(amb.g, amb.b))));
                RenderSettings.ambientMode = AmbientMode.Trilight;
                RenderSettings.ambientSkyColor = amb * k;
                RenderSettings.ambientEquatorColor = amb * (k * 0.75f);
                RenderSettings.ambientGroundColor = amb * (k * 0.45f);
                if (data.lighting.fog != null)
                {
                    RenderSettings.fog = true; RenderSettings.fogMode = FogMode.Linear;
                    RenderSettings.fogColor = ColorUtil.Hex(data.lighting.fog.color, Color.gray);
                    RenderSettings.fogStartDistance = data.lighting.fog.start; RenderSettings.fogEndDistance = data.lighting.fog.end;
                }
            }

            // ---- 物件 ----
            GameObject player = null; Transform playerSpawn = null; Renderer groundRenderer = null; Transform sunSphere = null;
            foreach (var o in data.objects)
            {
                if (o.role == "player_spawn") { playerSpawn = new GameObject("PlayerSpawn").transform; playerSpawn.SetParent(root); playerSpawn.SetPositionAndRotation(o.Position, o.Rotation); continue; }

                GameObject go;
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>($"{ModelDir}/{o.asset}.glb");
                GameObject charGo = o.role == "npc" && CharHeight.ContainsKey(o.asset) ? InstantiateCharacter(o.asset, null) : null;
                if (charGo != null) go = charGo;
                else if (prefab != null) go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                else
                {   // 占位：Tripo 资产未就绪时用胶囊
                    go = GameObject.CreatePrimitive(PrimitiveType.Capsule);
                    go.transform.localScale = new Vector3(0.5f, 0.85f, 0.5f);
                    go.GetComponent<Renderer>().sharedMaterial = FlatMaterial("placeholder", new Color(0.2f, 0.2f, 0.22f));
                }
                go.name = o.name; go.transform.SetParent(root);
                Mats.ConvertRenderers(go, o.asset);
                go.transform.SetPositionAndRotation(o.Position, o.Rotation);
                go.transform.localScale = o.Scale;
                if (o.@static) { GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic); }

                // 碰撞：地面/平台/悬崖用 MeshCollider，其余用包围盒
                foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
                {
                    if (NoCollider.Contains(o.asset)) continue;
                    if (o.asset.StartsWith("ground") || MeshColliderAssets.Contains(o.asset))
                        mf.gameObject.AddComponent<MeshCollider>();
                    else if (o.@static && mf.GetComponent<Collider>() == null) mf.gameObject.AddComponent<BoxCollider>();
                }
                if (o.asset.StartsWith("ground")) groundRenderer = go.GetComponentInChildren<Renderer>();
                if (o.role == "npc") { var cap = go.AddComponent<CapsuleCollider>(); cap.height = 1.7f; cap.center = new Vector3(0, 0.85f, 0); cap.radius = 0.35f; }
                if (o.role == "sun") { sunSphere = go.transform; foreach (var c in go.GetComponentsInChildren<Collider>()) Object.DestroyImmediate(c); }

                if (!string.IsNullOrEmpty(o.clue))
                {
                    var cd = data.clues.FirstOrDefault(c => c.id == o.clue);
                    var clue = go.AddComponent<Clue>();
                    clue.clueId = o.clue; clue.subtitle = cd?.subtitle ?? o.clue; clue.narrationClip = cd?.narration;
                    clue.triggerRadius = o.asset == "pyramid" || o.asset == "dish_tower" || o.asset == "platform" ? 18f : 3.5f;
                }
            }

            // 未绑定到物件的线索：放在出生点附近作为"地点线索"
            foreach (var cd in data.clues.Where(c => !data.objects.Any(o => o.clue == c.id)))
            {
                var go = new GameObject("Clue_" + cd.id); go.transform.SetParent(root);
                go.transform.position = (playerSpawn ? playerSpawn.position : Vector3.zero) + new Vector3(Random.Range(-15f, 15f), 0, Random.Range(10f, 30f));
                var clue = go.AddComponent<Clue>(); clue.clueId = cd.id; clue.subtitle = cd.subtitle; clue.narrationClip = cd.narration; clue.triggerRadius = 5f;
            }

            // ---- 玩家 + 相机 ----
            player = new GameObject("Player") { tag = "Player" };
            var cc = player.AddComponent<CharacterController>(); cc.height = 1.7f; cc.center = new Vector3(0, 0.85f, 0); cc.radius = 0.3f;
            GameObject body = InstantiateCharacter("char_player", cc);
            if (body != null)
            {
                body.name = "Body_CharPlayer";
                Mats.ConvertRenderers(body, "char_player");
                body.transform.SetParent(player.transform); body.transform.localPosition = Vector3.zero; body.transform.localRotation = Quaternion.identity;
            }
            else
            {
                body = GameObject.CreatePrimitive(PrimitiveType.Capsule); body.name = "Body_Placeholder"; Object.DestroyImmediate(body.GetComponent<Collider>());
                body.transform.SetParent(player.transform); body.transform.localPosition = new Vector3(0, 0.85f, 0); body.transform.localScale = new Vector3(0.5f, 0.85f, 0.5f);
                body.GetComponent<Renderer>().sharedMaterial = FlatMaterial("cloak", new Color(0.23f, 0.2f, 0.17f));
            }
            var spawnPos = playerSpawn ? playerSpawn.position : Vector3.zero;
            var spawnRot = playerSpawn ? Quaternion.Euler(0, playerSpawn.eulerAngles.y, 0) : Quaternion.identity;
            player.transform.SetPositionAndRotation(spawnPos + Vector3.up * 0.05f, spawnRot);   // 贴地放置（运行时由重力接管）
            var ctrl = player.AddComponent<ThirdPersonController>();

            var camGo = new GameObject("Main Camera") { tag = "MainCamera" };
            var cam = camGo.AddComponent<Camera>(); camGo.AddComponent<AudioListener>();
            cam.fieldOfView = 50f; cam.farClipPlane = 2000f;
            var camData = camGo.AddComponent<UniversalAdditionalCameraData>();
            camData.renderPostProcessing = true; camData.antialiasing = AntialiasingMode.FastApproximateAntialiasing;
            var volGo = new GameObject("PostFX"); var vol = volGo.AddComponent<Volume>(); vol.isGlobal = true; vol.sharedProfile = Mats.PostFxProfile();
            var follow = camGo.AddComponent<FollowCamera>(); follow.target = player.transform;
            ctrl.cameraTransform = camGo.transform;
            {   // 与 FollowCamera.LateUpdate 相同的初始解：俯角 15°、距 6 m、高 2.5 m，使编辑态 Game 视图即为开场镜头
                var pivot = spawnPos + Vector3.up * (0.5f + 1.4f);
                var camPos = pivot - Quaternion.Euler(15f, spawnRot.eulerAngles.y, 0f) * Vector3.forward * 6f + Vector3.up * (2.5f - 1.4f);
                camGo.transform.SetPositionAndRotation(camPos, Quaternion.LookRotation(pivot - camPos));
            }

            // ---- 管理器 / UI / 事件 ----
            var mgrGo = new GameObject("GameManager");
            var mgr = mgrGo.AddComponent<ClueManager>(); mgr.events = data.events;
            var ui = mgrGo.AddComponent<SubtitleUI>(); ui.eraTitle = data.title;

            if (sceneId == "scene_01_chaotic")
            {
                var ev = mgrGo.AddComponent<ChaoticEraEvent>(); ev.sun = sun; ev.ground = groundRenderer; ev.sunSphere = sunSphere;
            }
            if (sceneId == "scene_02_computer" && data.formation != null)
            {
                var f = mgrGo.AddComponent<SoldierFormation>(); f.data = data.formation;
                AssignMeshMat($"{ModelDir}/{data.formation.blackAsset}.glb", out f.blackMesh, out f.blackMaterial);
                AssignMeshMat($"{ModelDir}/{data.formation.whiteAsset}.glb", out f.whiteMesh, out f.whiteMaterial);
                if (f.blackMaterial) f.blackMaterial.enableInstancing = true;
                if (f.whiteMaterial) f.whiteMaterial.enableInstancing = true;
                var ts = mgrGo.AddComponent<ThreeSunsEvent>(); ts.sun = sun; ts.sunMaterial = FlatMaterial("sun_emissive", Color.white, emissive: true);
            }

            string scenePath = $"{SceneDir}/{sceneId}.unity";
            EditorSceneManager.SaveScene(scene, scenePath);
            AddToBuildSettings(scenePath);
            Debug.Log($"[SanTi] Built {scenePath}: {data.objects.Count} objects, {data.clues.Count} clues, {data.events.Count} events");
        }

        static void AssignMeshMat(string glbPath, out Mesh mesh, out Material mat)
        {
            mesh = null; mat = null;
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(glbPath);
            if (prefab == null) { Debug.LogWarning("Missing GLB: " + glbPath); return; }
            var mf = prefab.GetComponentInChildren<MeshFilter>(); var mr = prefab.GetComponentInChildren<MeshRenderer>();
            mesh = mf ? mf.sharedMesh : null; mat = mr ? Mats.Convert(mr.sharedMaterial, Path.GetFileNameWithoutExtension(glbPath)) : null;
        }

        /// <summary>
        /// 实例化角色：优先 Assets/Models/Anim/&lt;name&gt;.glb（Tripo 绑骨动画，Legacy Animation，剪辑 idle/walk/run），
        /// 否则退回 Assets/Models/&lt;name&gt;.glb（静态 T-Pose）。返回带 CharacterAnimator 的父物体；两者都没有时返回 null。
        /// </summary>
        static GameObject InstantiateCharacter(string name, CharacterController controller)
        {
            var animPrefab = AssetDatabase.LoadAssetAtPath<GameObject>($"{AnimDir}/{name}.glb");
            var staticPrefab = AssetDatabase.LoadAssetAtPath<GameObject>($"{ModelDir}/{name}.glb");
            if (animPrefab == null && staticPrefab == null) return null;
            var root = new GameObject(name);
            if (animPrefab != null)
            {
                var inst = (GameObject)PrefabUtility.InstantiatePrefab(animPrefab);
                inst.transform.SetParent(root.transform);
                // Tripo 重定向输出会带一个 Icosphere 辅助网格，去掉
                foreach (var t in inst.GetComponentsInChildren<Transform>(true))
                    if (t != null && t.name.StartsWith("Icosphere")) { Object.DestroyImmediate(t.gameObject); break; }
                // 1 m 归一化 → 目标身高；原始朝向 -X（glTFast 翻转 X 轴后）→ 绕 Y +90° 面向 +Z
                float h = 1f; var rends = inst.GetComponentsInChildren<Renderer>();
                if (rends.Length > 0) { var b = rends[0].bounds; foreach (var r in rends) b.Encapsulate(r.bounds); h = Mathf.Max(0.1f, b.size.y); }
                float target = CharHeight.TryGetValue(name, out var th) ? th : 1.7f;
                inst.transform.localScale = Vector3.one * (target / h);
                inst.transform.localRotation = Quaternion.Euler(0, 90f, 0);
                inst.transform.localPosition = Vector3.zero;
                var ca = root.AddComponent<CharacterAnimator>();
                ca.anim = inst.GetComponentInChildren<Animation>(); ca.controller = controller;
            }
            else
            {
                var inst = (GameObject)PrefabUtility.InstantiatePrefab(staticPrefab);
                inst.transform.SetParent(root.transform); inst.transform.localPosition = Vector3.zero; inst.transform.localRotation = Quaternion.identity;
            }
            return root;
        }

        static Material FlatMaterial(string name, Color c, bool emissive = false)
        {
            string path = $"{MatDir}/{name}.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m != null) return m;
            var shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            m = new Material(shader) { color = c };
            if (emissive) { m.EnableKeyword("_EMISSION"); m.SetColor("_EmissionColor", Color.white * 4f); }
            AssetDatabase.CreateAsset(m, path);
            return m;
        }

        static void AddToBuildSettings(string scenePath)
        {
            var scenes = EditorBuildSettings.scenes.ToList();
            if (scenes.Any(s => s.path == scenePath)) return;
            scenes.Add(new EditorBuildSettingsScene(scenePath, true));
            // 红岸序章放第一个
            scenes = scenes.OrderBy(s => s.path.Contains("scene_00") ? 0 : 1).ThenBy(s => s.path).ToList();
            EditorBuildSettings.scenes = scenes.ToArray();
        }
    }
}
