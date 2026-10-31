using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace SanTi
{
    /// <summary>
    /// 运行态盲审截图：按顺序加载各场景，在指定帧用主相机渲染到 PNG（能看到人列方阵、动画姿态、字幕等编辑态看不到的内容）。
    /// 由 Editor/Pipeline.PlayCapture 在进入 Play Mode 后创建；也可手动挂到场景里调试。
    /// </summary>
    public class PlayCaptureRunner : MonoBehaviour
    {
        public static System.Action OnFinished;

        public string outDir;
        public string[] scenePaths;
        public float[] times = { 1.0f, 4.0f, 9.0f };   // 场景内秒数；4 s 起自动前行，检查 walk 动画与碰撞
        public float walkFrom = 4.0f;
        public bool autoWalk = true;

        int _sceneIdx = -1, _shotIdx; float _t;

        void Awake() { DontDestroyOnLoad(gameObject); Application.targetFrameRate = 30; }
        void Start() { Next(); }

        void Next()
        {
            _sceneIdx++; _shotIdx = 0; _t = 0f;
            if (scenePaths == null || _sceneIdx >= scenePaths.Length) { Debug.Log("[SanTi] PlayCapture finished"); OnFinished?.Invoke(); enabled = false; return; }
            Debug.Log("[SanTi] PlayCapture loading " + scenePaths[_sceneIdx]);
            SceneManager.LoadScene(scenePaths[_sceneIdx]);
        }

        void LateUpdate()
        {
            if (_sceneIdx < 0 || _sceneIdx >= scenePaths.Length) return;
            _t += Time.deltaTime;
            GameState.AutoMove = (autoWalk && _t > walkFrom) ? new Vector2(0, 1) : Vector2.zero;

            if (_shotIdx < times.Length && _t >= times[_shotIdx])
            {
                var cam = Camera.main;
                if (cam != null)
                {
                    string id = Path.GetFileNameWithoutExtension(scenePaths[_sceneIdx]);
                    Shot(cam, Path.Combine(outDir, $"{id}_play_t{times[_shotIdx]:00.0}s.png"), 1600, 900);
                    FaceShot(cam, Path.Combine(outDir, $"{id}_face_t{times[_shotIdx]:00.0}s.png"));
                    if (_t > walkFrom) GaitShot(cam, Path.Combine(outDir, $"{id}_gait_t{times[_shotIdx]:00.0}s.png"));
                }
                _shotIdx++;
            }
            if (_shotIdx >= times.Length) { GameState.AutoMove = Vector2.zero; Next(); }
        }

        /// <summary>REA Q1/Q2 核验：从玩家正前方 1.3 m 拍脸（朝向 + 五官 + 表情）。</summary>
        static void FaceShot(Camera main, string file)
        {
            var p = GameObject.FindGameObjectWithTag("Player"); if (p == null) return;
            var go = new GameObject("FaceCam"); var c = go.AddComponent<Camera>();
            c.CopyFrom(main); c.fieldOfView = 30f; c.nearClipPlane = 0.05f;
            Vector3 head = p.transform.position + Vector3.up * 1.5f;
            go.transform.position = head + p.transform.forward * 1.3f + Vector3.up * 0.1f;
            go.transform.LookAt(head);
            Shot(c, file, 900, 900);
            Destroy(go);
        }

        /// <summary>REA Q1 步态核验：行走中从玩家右侧 2.2 m 拍全身侧视（前进方向 = 画面左）。脚尖与迈步应朝画面左。</summary>
        static void GaitShot(Camera main, string file)
        {
            var p = GameObject.FindGameObjectWithTag("Player"); if (p == null) return;
            var go = new GameObject("GaitCam"); var c = go.AddComponent<Camera>();
            c.CopyFrom(main); c.fieldOfView = 35f; c.nearClipPlane = 0.05f;
            Vector3 mid = p.transform.position + Vector3.up * 0.9f;
            go.transform.position = mid + p.transform.right * 2.2f;
            go.transform.LookAt(mid);
            Shot(c, file, 900, 900);
            Destroy(go);
        }

        public static void Shot(Camera cam, string file, int w, int h)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(file));
            var rt = new RenderTexture(w, h, 24, RenderTextureFormat.ARGB32) { antiAliasing = 4 };
            var prevRt = cam.targetTexture; var prevActive = RenderTexture.active;
            cam.targetTexture = rt; cam.Render();
            RenderTexture.active = rt;
            var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, w, h), 0, 0); tex.Apply();
            File.WriteAllBytes(file, tex.EncodeToPNG());
            cam.targetTexture = prevRt; RenderTexture.active = prevActive;
            Destroy(tex); rt.Release(); Destroy(rt);
            Debug.Log("[SanTi] play shot " + file);
        }
    }
}
