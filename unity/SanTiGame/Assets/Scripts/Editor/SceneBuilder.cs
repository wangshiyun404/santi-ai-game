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
        const string FaceDir = "Assets/Models/Face";   // scripts/face_patches.py 生成的五官薄片
        const string AnimDir = "Assets/Models/Anim";   // Tripo 绑骨+动画 GLB（原始 1 m 归一化、朝向 +X），由 InstantiateCharacter 统一缩放/转向
        static readonly System.Collections.Generic.Dictionary<string, float> CharHeight = new()
        { { "char_player", 1.62f }, { "char_ye_wenjie", 1.62f }, { "char_follower", 1.65f }, { "char_von_neumann", 1.75f }, { "char_newton", 1.70f }, { "char_qin", 1.78f }, { "soldier_black", 1.75f }, { "soldier_white", 1.75f } };
        static readonly System.Collections.Generic.Dictionary<string, string> CharDisplayName = new()
        { { "char_ye_wenjie", "叶文洁" }, { "char_follower", "跟随者" }, { "char_von_neumann", "冯·诺依曼" }, { "char_newton", "牛顿" }, { "char_qin", "秦始皇" } };
        const string SceneDir = "Assets/Scenes";
        const string MatDir = "Assets/Materials";
        // 碰撞规则：大而不规则的用 MeshCollider；远景/装饰/发光面片不加碰撞（围栏若用 BoxCollider 会把整个高地封死）
        static readonly System.Collections.Generic.HashSet<string> MeshColliderAssets = new() { "platform", "cliff", "pyramid", "fence_ring", "dry_lakebed", "dish_tower" };
        static readonly System.Collections.Generic.HashSet<string> GroundLikeAssets = new() { "cliff", "platform", "dry_lakebed" };
        static readonly System.Collections.Generic.HashSet<string> NoCollider = new() { "cloud_sea", "window_lights", "sun_sphere", "mountains" };
        // 需要贴地的小物件（REA Q4）
        static readonly System.Collections.Generic.HashSet<string> SnapAssets = new() { "rock_small", "dehydrated_roll", "jeep", "bamboo_slips", "control_console", "sand_table", "bronze_sword", "flagpole" };

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

            // REA 台账 Q5：程序化天空（替代纯色背景），日色/地平线随场景光照
            {
                var skyShader = Shader.Find("Skybox/Procedural");
                if (skyShader != null)
                {
                    string skyPath = $"{MatDir}/sky_{sceneId}.mat";
                    var sky = AssetDatabase.LoadAssetAtPath<Material>(skyPath);
                    if (sky == null) { sky = new Material(skyShader); AssetDatabase.CreateAsset(sky, skyPath); }
                    var fogC = data.lighting?.fog != null ? ColorUtil.Hex(data.lighting.fog.color, Color.gray) : Color.gray;
                    sky.SetFloat("_SunSize", sceneId.Contains("scene_01") ? 0.02f : 0.04f);
                    sky.SetFloat("_AtmosphereThickness", sceneId.Contains("scene_00") ? 1.35f : sceneId.Contains("scene_01") ? 0.55f : 1.0f);
                    sky.SetColor("_SkyTint", Color.Lerp(new Color(0.5f, 0.5f, 0.5f), fogC, 0.5f));
                    sky.SetColor("_GroundColor", fogC);
                    sky.SetFloat("_Exposure", sceneId.Contains("scene_01") ? 1.1f : 1.0f);
                    EditorUtility.SetDirty(sky);
                    RenderSettings.skybox = sky; RenderSettings.sun = sun;
                }
            }

            // ---- 物件 ----
            GameObject player = null; Transform playerSpawn = null; Renderer groundRenderer = null; Transform sunSphere = null;
            var groundCols = new System.Collections.Generic.HashSet<Collider>();   // 贴地射线只认这些面（E22：曾贴到石碑顶上）
            var snapList = new System.Collections.Generic.List<GameObject>();
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
                ApplyGroundTexture(go, o.asset);   // REA Q5 第二批：地面可平铺贴图
                if (o.@static) { GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic); }

                // 碰撞：地面/平台/悬崖用 MeshCollider，其余用包围盒
                foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
                {
                    if (NoCollider.Contains(o.asset)) continue;
                    if (o.asset.StartsWith("ground") || MeshColliderAssets.Contains(o.asset))
                    {
                        var mc = mf.gameObject.AddComponent<MeshCollider>();
                        if (o.asset.StartsWith("ground") || GroundLikeAssets.Contains(o.asset)) groundCols.Add(mc);
                    }
                    else if (o.@static && mf.GetComponent<Collider>() == null) mf.gameObject.AddComponent<BoxCollider>();
                }
                if (o.asset.StartsWith("ground")) groundRenderer = go.GetComponentInChildren<Renderer>();
                if (o.role == "npc") { var cap = go.AddComponent<CapsuleCollider>(); cap.height = 1.7f; cap.center = new Vector3(0, 0.85f, 0); cap.radius = 0.35f; go.AddComponent<NpcLookAt>(); }
                if (o.role == "npc" || SnapAssets.Contains(o.asset)) snapList.Add(go);
                if (o.role == "sun") { sunSphere = go.transform; foreach (var c in go.GetComponentsInChildren<Collider>()) Object.DestroyImmediate(c); }

                if (!string.IsNullOrEmpty(o.clue))
                {
                    var cd = data.clues.FirstOrDefault(c => c.id == o.clue);
                    var clue = go.AddComponent<Clue>();
                    clue.clueId = o.clue; clue.subtitle = cd?.subtitle ?? o.clue; clue.narrationClip = cd?.narration;
                    clue.speaker = CharDisplayName.TryGetValue(o.asset, out var dn) ? dn : "";   // REA Q7：字幕前加说话人
                    clue.triggerRadius = o.asset == "pyramid" || o.asset == "dish_tower" || o.asset == "platform" ? 18f : 3.5f;
                }
            }

            // 未绑定到物件的线索：立一块可见的"石碑"标记（layout clues[].at 指定位置；否则放在出生点前方）
            int unboundIdx = 0;
            foreach (var cd in data.clues.Where(c => !data.objects.Any(o => o.clue == c.id)))
            {
                Vector3 pos = cd.at != null && cd.at.Length == 3 ? new Vector3(cd.at[0], cd.at[1], cd.at[2])
                    : (playerSpawn ? playerSpawn.position + playerSpawn.forward * (12f + 8f * unboundIdx) + playerSpawn.right * (unboundIdx % 2 == 0 ? -4f : 4f) : Vector3.zero);
                unboundIdx++;
                var go = new GameObject("Clue_" + cd.id); go.transform.SetParent(root);
                go.transform.position = pos;
                var stele = GameObject.CreatePrimitive(PrimitiveType.Cube); stele.name = "Stele";
                stele.transform.SetParent(go.transform); stele.transform.localPosition = new Vector3(0, 0.9f, 0); stele.transform.localScale = new Vector3(0.9f, 1.8f, 0.3f);
                stele.GetComponent<Renderer>().sharedMaterial = FlatMaterial("clue_stele", new Color(0.95f, 0.72f, 0.40f));
                var cap = GameObject.CreatePrimitive(PrimitiveType.Cube); cap.name = "Cap";
                cap.transform.SetParent(go.transform); cap.transform.localPosition = new Vector3(0, 1.95f, 0); cap.transform.localScale = new Vector3(1.1f, 0.3f, 0.5f);
                cap.GetComponent<Renderer>().sharedMaterial = FlatMaterial("clue_stele_dark", new Color(0.25f, 0.22f, 0.20f));
                var clue = go.AddComponent<Clue>(); clue.clueId = cd.id; clue.subtitle = cd.subtitle; clue.narrationClip = cd.narration; clue.triggerRadius = 5f;
                snapList.Add(go);
            }

            // REA 台账 Q4：小道具 / NPC / 石碑按布局 y=0 放置，而地面有起伏 → 向下射线贴地（包围盒底边贴到命中点）
            Physics.SyncTransforms();
            int snapped = 0;
            foreach (var go in snapList)
            {
                var own = go.GetComponentsInChildren<Collider>().ToList();
                own.ForEach(c => c.enabled = false);
                var from = go.transform.position + Vector3.up * 60f;
                // 只认地面类碰撞体（E22：此前射线先打到同位置的线索石碑顶部，脱水人卷悬在 2 m 高）
                RaycastHit hit = default; bool got = false;
                foreach (var h in Physics.RaycastAll(from, Vector3.down, 200f))
                    if (groundCols.Contains(h.collider) && (!got || h.point.y > hit.point.y)) { hit = h; got = true; }
                if (got)
                {
                    var rends = go.GetComponentsInChildren<Renderer>();
                    float bottom = go.transform.position.y;
                    if (rends.Length > 0) { var b = rends[0].bounds; foreach (var r in rends) b.Encapsulate(r.bounds); bottom = b.min.y; }
                    float dy = hit.point.y - bottom;
                    if (Mathf.Abs(dy) < 8f) { go.transform.position += Vector3.up * (dy - 0.02f); snapped++; }
                    if (Mathf.Abs(dy) > 0.5f) Debug.Log($"[SanTi] snap-dbg {go.name} pos={go.transform.position} hit={hit.collider.name}@{hit.point.y:F2} bottom={bottom:F2} dy={dy:F2}");
                }
                own.ForEach(c => c.enabled = true);
            }
            Debug.Log($"[SanTi] ground-snapped {snapped}/{snapList.Count} objects");

            // 高台坡道：让玩家能走上 platform（原模型台阶 5 m 高，角色上不去）
            var platformT = root.Find("Platform");
            var platRends = platformT ? platformT.GetComponentsInChildren<Renderer>() : new Renderer[0];
            if (platRends.Length > 0)
            {
                var b = platRends[0].bounds; foreach (var r in platRends) b.Encapsulate(r.bounds);
                float top = b.max.y; float angle = 30f;
                float len = top / Mathf.Sin(angle * Mathf.Deg2Rad);
                var ramp = GameObject.CreatePrimitive(PrimitiveType.Cube); ramp.name = "Platform_Ramp";
                ramp.transform.SetParent(root);
                ramp.transform.localScale = new Vector3(8f, 0.5f, len);
                ramp.transform.rotation = Quaternion.Euler(angle, 0, 0);           // 高端贴高台 +Z 侧边缘，沿 +Z 方向下坡到地面
                ramp.transform.position = new Vector3(b.center.x, top / 2f - 0.2f, b.max.z + len * Mathf.Cos(angle * Mathf.Deg2Rad) / 2f);
                ramp.GetComponent<Renderer>().sharedMaterial = platRends[0].sharedMaterial;
                GameObjectUtility.SetStaticEditorFlags(ramp, StaticEditorFlags.BatchingStatic);
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
            {   // 与 FollowCamera.LateUpdate 相同的初始解（REA Q2：拉近到 4.2 m / 俯角 10° / 高 1.9 m，让脸可辨认）
                var pivot = spawnPos + Vector3.up * (0.5f + 1.4f);
                var camPos = pivot - Quaternion.Euler(10f, spawnRot.eulerAngles.y, 0f) * Vector3.forward * 4.2f + Vector3.up * (1.9f - 1.4f);
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
                // 1 m 归一化 → 目标身高。REA 台账 Q1（E17 真机脸部特写定论）：绑骨模型 glTF 原始朝向 +X（E11），
                // glTFast 翻 X 轴后为 -X，绕 Y +90° → 脸朝 +Z（= 控制器 forward）。曾按低清抽帧 E02 误判为 -90°，被 E17 推翻。
                float h = 1f; var rends = inst.GetComponentsInChildren<Renderer>();
                if (rends.Length > 0) { var b = rends[0].bounds; foreach (var r in rends) b.Encapsulate(r.bounds); h = Mathf.Max(0.1f, b.size.y); }
                float target = CharHeight.TryGetValue(name, out var th) ? th : 1.7f;
                inst.transform.localScale = Vector3.one * (target / h);
                inst.transform.localRotation = Quaternion.Euler(0, 90f, 0);
                inst.transform.localPosition = Vector3.zero;
                var ca = root.AddComponent<CharacterAnimator>();
                ca.anim = inst.GetComponentInChildren<Animation>(); ca.controller = controller;
                // REA Q2：几何五官 + 表情（有 _face.glb 的角色）
                // 第 10 轮（REA Q9）：写实主角自带形变键（blink/jaw_open/smile/brows_up，scripts/hero_expressions.py），
                // 走 BlendShape 模式；几何薄片只给没有形变键的低模 NPC（写实脸 + 卡通薄片会很怪）。
                var smr = inst.GetComponentInChildren<SkinnedMeshRenderer>();
                bool hasBlend = smr != null && smr.sharedMesh != null && smr.sharedMesh.blendShapeCount > 0;
                var face = hasBlend ? null : AssetDatabase.LoadAssetAtPath<GameObject>($"{FaceDir}/{name}_face.glb");
                if (hasBlend || face != null) { var fe = root.AddComponent<FaceExpression>(); fe.facePrefab = face; }
            }
            else
            {
                var inst = (GameObject)PrefabUtility.InstantiatePrefab(staticPrefab);
                inst.transform.SetParent(root.transform); inst.transform.localPosition = Vector3.zero; inst.transform.localRotation = Quaternion.identity;
            }
            return root;
        }

        // REA 台账 Q5 第二批：scripts/ground_textures.py 生成的可平铺地面贴图。tile = 一张贴图覆盖的米数；planar = 用世界 XZ 重算 UV（圆柱 UV 的 cliff 顶面不可用）
        static readonly System.Collections.Generic.Dictionary<string, (string tex, float tile, bool planar)> GroundTex = new()
        {
            { "cliff", ("ground_red_coast", 10f, true) },
            { "ground_chaotic", ("ground_chaotic", 7f, false) },
            { "ground_plain", ("ground_plain", 8f, false) },
        };

        static void ApplyGroundTexture(GameObject go, string asset)
        {
            if (!GroundTex.TryGetValue(asset, out var g)) return;
            var tex = AssetDatabase.LoadAssetAtPath<Texture2D>($"Assets/Textures/Ground/{g.tex}.png");
            if (tex == null) { Debug.LogWarning($"[SanTi] ground texture missing: {g.tex}"); return; }
            var lit = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            Directory.CreateDirectory($"{MatDir}/Ground"); Directory.CreateDirectory("Assets/Generated");
            int k = 0;
            foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
            {
                var r = mf.GetComponent<Renderer>(); var mesh = mf.sharedMesh;
                if (r == null || mesh == null) continue;
                Vector2 tiling;
                if (g.planar)
                {
                    string mp = $"Assets/Generated/{asset}_{k}_planar.asset";
                    var copy = AssetDatabase.LoadAssetAtPath<Mesh>(mp);
                    if (copy == null)
                    {
                        copy = Object.Instantiate(mesh); copy.name = $"{asset}_{k}_planar";
                        var v = copy.vertices; var uv = new Vector2[v.Length]; var l2w = mf.transform.localToWorldMatrix;
                        for (int i = 0; i < v.Length; i++) { var w = l2w.MultiplyPoint3x4(v[i]); uv[i] = new Vector2(w.x, w.z) / g.tile; }
                        copy.uv = uv; AssetDatabase.CreateAsset(copy, mp);
                    }
                    mf.sharedMesh = copy; tiling = Vector2.one;
                }
                else
                {
                    var b = mesh.bounds.size;
                    tiling = new Vector2(Mathf.Max(1f, Mathf.Round(b.x / g.tile)), Mathf.Max(1f, Mathf.Round(b.z / g.tile)));
                }
                var mats = r.sharedMaterials;
                for (int i = 0; i < mats.Length; i++)
                {
                    string path = $"{MatDir}/Ground/{asset}_{k}_{i}.mat";
                    var m = AssetDatabase.LoadAssetAtPath<Material>(path);
                    if (m == null) { m = new Material(lit); AssetDatabase.CreateAsset(m, path); } else m.shader = lit;
                    m.SetTexture("_BaseMap", tex); m.SetTextureScale("_BaseMap", tiling);
                    m.SetColor("_BaseColor", i == 0 ? Color.white : new Color(0.94f, 0.94f, 0.94f));   // 子材质（乱纪元 crack 面片呈棋盘分布）只做极轻微明暗差，避免棋盘格
                    m.SetFloat("_Metallic", 0f); m.SetFloat("_Smoothness", 0.08f);
                    EditorUtility.SetDirty(m); mats[i] = m;
                }
                r.sharedMaterials = mats; k++;
            }
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
