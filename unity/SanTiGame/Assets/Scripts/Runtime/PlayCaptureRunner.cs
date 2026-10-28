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
                }
                _shotIdx++;
            }
            if (_shotIdx >= times.Length) { GameState.AutoMove = Vector2.zero; Next(); }
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
