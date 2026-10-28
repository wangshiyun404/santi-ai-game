using System.Collections.Generic;
using UnityEngine;

namespace SanTi
{
    /// <summary>
    /// 人列计算机：用 GPU 实例化绘制数万名举旗士兵，黑/白旗按"运算波"随时间翻转。
    /// 每个士兵 = 1 个 Matrix4x4；按旗色分两组，每 1023 个一批 DrawMeshInstanced。
    /// </summary>
    public class SoldierFormation : MonoBehaviour, IEventListener
    {
        public Mesh blackMesh; public Material blackMaterial;
        public Mesh whiteMesh; public Material whiteMaterial;
        public FormationData data;
        [Range(0.05f, 1f)] public float density = 1f;      // WebGL 可降到 0.33
        public bool computing = true;
        public float maxDrawDistance = 700f;

        struct Soldier { public Matrix4x4 m; public Vector3 pos; public int basePattern; }
        readonly List<Soldier> _soldiers = new List<Soldier>();
        readonly List<Matrix4x4> _black = new List<Matrix4x4>(1023);
        readonly List<Matrix4x4> _white = new List<Matrix4x4>(1023);
        bool _scatter; float _scatterT;

        void Start() { Build(); }

        public void Build()
        {
            _soldiers.Clear();
            if (data == null) return;
            var rng = new System.Random(42);
            foreach (var b in data.blocks)
            {
                int step = Mathf.Max(1, Mathf.RoundToInt(1f / Mathf.Sqrt(density)));
                for (int c = 0; c < b.cols; c += step)
                for (int r = 0; r < b.rows; r += step)
                {
                    var p = new Vector3(b.origin[0] + c * b.spacing, 0, b.origin[1] + r * b.spacing);
                    p.x += (float)(rng.NextDouble() - 0.5) * 0.15f; p.z += (float)(rng.NextDouble() - 0.5) * 0.15f;
                    int basePat = b.pattern switch
                    {
                        "black" => 0,
                        "white" => 1,
                        "rows" => r % 2,
                        _ => (c + r) % 2,
                    };
                    float yaw = (float)(rng.NextDouble() - 0.5) * 8f;   // 面向 +Z（高台/秦始皇一侧）
                    _soldiers.Add(new Soldier { pos = p, basePattern = basePat, m = Matrix4x4.TRS(p, Quaternion.Euler(0, yaw, 0), Vector3.one) });
                }
            }
            Debug.Log($"[SanTi] Formation built: {_soldiers.Count} soldiers");
        }

        void Update()
        {
            if (blackMesh == null || whiteMesh == null) return;
            var cam = Camera.main; if (cam == null) return;
            Vector3 camPos = cam.transform.position;
            float t = Time.time * data.flipWaveSpeed;
            if (_scatter) _scatterT += Time.deltaTime;

            _black.Clear(); _white.Clear();
            foreach (var s in _soldiers)
            {
                if ((s.pos - camPos).sqrMagnitude > maxDrawDistance * maxDrawDistance) continue;
                // 运算波：沿 x 方向的方波 + 行间相位差，像时钟脉冲扫过总线
                int flip = computing ? (Mathf.FloorToInt((s.pos.x * 0.08f + s.pos.z * 0.02f + t) * 0.5f) & 1) : 0;
                bool white = (s.basePattern ^ flip) == 1;
                Matrix4x4 m = s.m;
                if (_scatter)
                {   // 三日凌空：方阵溃散（随机抖散并下沉）
                    float k = Mathf.Clamp01(_scatterT / 40f);
                    var jitter = new Vector3(Mathf.PerlinNoise(s.pos.x, s.pos.z) - 0.5f, -k * 1.5f, Mathf.PerlinNoise(s.pos.z, s.pos.x) - 0.5f) * k * 6f;
                    m = Matrix4x4.TRS(s.pos + jitter, Quaternion.Euler(k * 70f * (Mathf.PerlinNoise(s.pos.x * 3, 0) - 0.5f), 0, 0), Vector3.one * (1f - k * 0.3f));
                }
                (white ? _white : _black).Add(m);
                if (_black.Count == 1023) Flush(_black, blackMesh, blackMaterial);
                if (_white.Count == 1023) Flush(_white, whiteMesh, whiteMaterial);
            }
            Flush(_black, blackMesh, blackMaterial);
            Flush(_white, whiteMesh, whiteMaterial);
        }

        void Flush(List<Matrix4x4> list, Mesh mesh, Material mat)
        {
            if (list.Count == 0) return;
            for (int sub = 0; sub < mesh.subMeshCount; sub++)
                Graphics.DrawMeshInstanced(mesh, sub, mat, list, null, UnityEngine.Rendering.ShadowCastingMode.Off, true);
            list.Clear();
        }

        public void OnEvent(EventData e)
        {
            if (e.id == "three_suns") { _scatter = true; computing = false; }
        }
    }
}
