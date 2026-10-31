using System.Collections.Generic;
using UnityEngine;

namespace SanTi
{
    /// <summary>
    /// REA 台账 Q2：Tripo 角色贴图没有五官。scripts/face_patches.py 在 Blender 里沿脸面生成薄片（眼白/瞳孔/闭眼线/眉/嘴线/张嘴），
    /// 导出 Assets/Models/Face/&lt;name&gt;_face.glb；本组件在运行时把这些薄片挂到 Head 骨骼上
    /// （薄片与蒙皮网格同处绑定空间：child.local = bindposes[head]），再按状态切换可见性做表情：
    /// 随机眨眼、说话（张嘴/闭嘴交替）、惊讶（睁大眼 + 张嘴）。
    /// </summary>
    public class FaceExpression : MonoBehaviour
    {
        public GameObject facePrefab;   // SceneBuilder 赋值（glTFast 导入的 _face.glb）
        public float blinkMin = 2.5f, blinkMax = 5.5f, blinkDur = 0.13f;

        readonly Dictionary<string, Transform> _parts = new();
        float _nextBlink, _blinkUntil, _talkUntil, _surpriseUntil, _mouthFlip;
        bool _ready;

        void Start()
        {
            if (facePrefab == null) { enabled = false; return; }
            var smr = GetComponentInChildren<SkinnedMeshRenderer>();
            if (smr == null || smr.bones == null || smr.sharedMesh == null) { enabled = false; return; }
            int h = -1;
            for (int i = 0; i < smr.bones.Length; i++)
            {
                var b = smr.bones[i]; if (b == null) continue;
                string n = b.name.ToLowerInvariant();
                if (n.EndsWith("head") || n.EndsWith(":head")) { h = i; break; }
            }
            if (h < 0) { Debug.LogWarning($"[SanTi] FaceExpression: no Head bone on {name}"); enabled = false; return; }
            var head = smr.bones[h];
            var bind = smr.sharedMesh.bindposes[h];

            var inst = Instantiate(facePrefab);
            inst.name = "Face";
            var rootW2L = inst.transform.worldToLocalMatrix;
            foreach (var mf in inst.GetComponentsInChildren<MeshFilter>(true))
            {
                var node = mf.transform;
                Matrix4x4 nodeM = rootW2L * node.localToWorldMatrix;   // 节点在预制体根空间的矩阵（通常为单位阵）
                // 薄片顶点在模型空间（原点在脚下）。把网格重心移到节点原点，表情缩放才会绕薄片自身中心进行，而不是绕脚下原点。
                var mesh = Instantiate(mf.sharedMesh);
                Vector3 c = mesh.bounds.center;
                var vs = mesh.vertices;
                for (int i = 0; i < vs.Length; i++) vs[i] -= c;
                mesh.vertices = vs; mesh.RecalculateBounds();
                Matrix4x4 local = bind * nodeM * Matrix4x4.Translate(c);
                var go = new GameObject(node.name);
                go.transform.SetParent(head, false);
                go.transform.localPosition = local.GetPosition();
                go.transform.localRotation = local.rotation;
                go.transform.localScale = local.lossyScale;
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var mr = go.AddComponent<MeshRenderer>();
                var srcR = node.GetComponent<MeshRenderer>();
                mr.sharedMaterials = srcR != null ? srcR.sharedMaterials : new Material[0];
                mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                _parts[node.name] = go.transform;
            }
            Destroy(inst);
            _ready = _parts.Count > 0;
            _nextBlink = Time.time + Random.Range(blinkMin, blinkMax);
            Apply();
        }

        void Update()
        {
            if (!_ready) return;
            float t = Time.time;
            if (t > _nextBlink) { _blinkUntil = t + blinkDur; _nextBlink = t + Random.Range(blinkMin, blinkMax); }
            if (t < _talkUntil && t > _mouthFlip) _mouthFlip = t + Random.Range(0.08f, 0.16f);
            Apply();
        }

        void Apply()
        {
            float t = Time.time;
            bool closed = t < _blinkUntil;
            bool surprised = t < _surpriseUntil;
            bool talking = t < _talkUntil;
            bool mouthOpen = surprised || (talking && Mathf.FloorToInt((_mouthFlip - t) * 12f) % 2 == 0);
            Show("eye_white_L", !closed); Show("eye_white_R", !closed);
            Show("pupil_L", !closed); Show("pupil_R", !closed);
            Show("eye_closed_L", closed); Show("eye_closed_R", closed);
            Show("mouth_open", mouthOpen); Show("mouth_line", !mouthOpen);
            float s = surprised ? 1.25f : 1f;
            Scale("eye_white_L", s); Scale("eye_white_R", s);
            Scale("brow_L", surprised ? 1.15f : 1f); Scale("brow_R", surprised ? 1.15f : 1f);
        }

        void Show(string part, bool on) { if (_parts.TryGetValue(part, out var tr) && tr.gameObject.activeSelf != on) tr.gameObject.SetActive(on); }
        void Scale(string part, float k) { if (_parts.TryGetValue(part, out var tr)) tr.localScale = Vector3.Lerp(tr.localScale, _baseScale(tr) * k, 0.3f); }
        readonly Dictionary<Transform, Vector3> _base = new();
        Vector3 _baseScale(Transform tr) { if (!_base.TryGetValue(tr, out var v)) { v = tr.localScale; _base[tr] = v; } return v; }

        public void Say(float seconds) { _talkUntil = Time.time + seconds; }
        public void Surprise(float seconds) { _surpriseUntil = Time.time + seconds; }

        /// <summary>剧情事件调用：玩家角色惊讶。</summary>
        public static void PlayerSurprise(float seconds)
        {
            var p = GameObject.FindGameObjectWithTag("Player");
            if (p != null) p.GetComponentInChildren<FaceExpression>()?.Surprise(seconds);
        }
    }
}
