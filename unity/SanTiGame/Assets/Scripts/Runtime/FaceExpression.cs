using System.Collections.Generic;
using UnityEngine;

namespace SanTi
{
    /// <summary>
    /// REA 台账 Q2：Tripo 角色贴图没有五官。scripts/face_patches.py 在 Blender 里沿脸面生成薄片（眼白/瞳孔/闭眼线/眉/嘴线/张嘴），
    /// 导出 Assets/Models/Face/&lt;name&gt;_face.glb；本组件在运行时把这些薄片挂到 Head 骨骼上
    /// （薄片与蒙皮网格同处绑定空间：child.local = bindposes[head]），再按状态切换可见性做表情：
    /// 随机眨眼、说话（张嘴/闭嘴交替）、惊讶（睁大眼 + 张嘴）。
    /// 第 10 轮（REA Q9）：写实主角改用 BlendShape 模式——网格自带形变键 blink / jaw_open / smile / brows_up
    /// （scripts/hero_expressions.py 生成，glTFast 导入为 SkinnedMeshRenderer 的 BlendShape），按同样的状态机平滑驱动权重；
    /// 另加轻微的呼吸/视线微动（头骨随机小角度偏转），避免"站着像木偶"。
    /// </summary>
    public class FaceExpression : MonoBehaviour
    {
        public GameObject facePrefab;   // SceneBuilder 赋值（glTFast 导入的 _face.glb）
        public float blinkMin = 2.5f, blinkMax = 5.5f, blinkDur = 0.13f;

        readonly Dictionary<string, Transform> _parts = new();
        float _nextBlink, _blinkUntil, _talkUntil, _surpriseUntil, _mouthFlip;
        bool _ready;

        // ---- BlendShape 模式 ----
        SkinnedMeshRenderer _smr; int _bBlink = -1, _bJaw = -1, _bSmile = -1, _bBrows = -1; bool _blend;
        float _wBlink, _wJaw, _wSmile, _wBrows;
        Transform _head; Quaternion _headBase; Vector3 _lookSeed;

        void Start()
        {
            var smr = GetComponentInChildren<SkinnedMeshRenderer>();
            if (smr == null || smr.bones == null || smr.sharedMesh == null) { enabled = false; return; }
            if (smr.sharedMesh.blendShapeCount > 0)
            {
                _smr = smr; var mesh = smr.sharedMesh;
                for (int i = 0; i < mesh.blendShapeCount; i++)
                {
                    string n = mesh.GetBlendShapeName(i).ToLowerInvariant();
                    if (n.EndsWith("blink")) _bBlink = i; else if (n.EndsWith("jaw_open")) _bJaw = i; else if (n.EndsWith("smile")) _bSmile = i; else if (n.EndsWith("brows_up")) _bBrows = i;
                }
                _blend = _bBlink >= 0 || _bJaw >= 0;
                foreach (var b in smr.bones) { if (b != null && b.name.ToLowerInvariant().EndsWith("head")) { _head = b; break; } }
                _lookSeed = new Vector3(Random.value * 100f, Random.value * 100f, 0);
                _ready = _blend; _nextBlink = Time.time + Random.Range(blinkMin, blinkMax);
                if (!_ready) enabled = false;
                return;
            }
            if (facePrefab == null) { enabled = false; return; }
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
            if (_blend) ApplyBlend(); else Apply();
        }

        void ApplyBlend()
        {
            float t = Time.time, dt = Time.deltaTime;
            bool closed = t < _blinkUntil, surprised = t < _surpriseUntil, talking = t < _talkUntil;
            bool mouthOpen = surprised || (talking && Mathf.FloorToInt((_mouthFlip - t) * 12f) % 2 == 0);
            // 目标权重（0–100）：眨眼快、嘴/眉慢；惊讶张嘴 70、说话 35–55 抖动
            float tBlink = closed ? 100f : 0f;
            float tJaw = surprised ? 70f : mouthOpen ? Random.Range(35f, 55f) : 0f;
            float tBrows = surprised ? 100f : 0f;
            float tSmile = (!surprised && !talking) ? 18f : 0f;   // 平时带一点点柔和的微笑，避免面无表情
            _wBlink = Mathf.MoveTowards(_wBlink, tBlink, dt * 1400f);
            _wJaw = Mathf.Lerp(_wJaw, tJaw, 1f - Mathf.Exp(-dt * 18f));
            _wBrows = Mathf.Lerp(_wBrows, tBrows, 1f - Mathf.Exp(-dt * 10f));
            _wSmile = Mathf.Lerp(_wSmile, tSmile, 1f - Mathf.Exp(-dt * 3f));
            if (_bBlink >= 0) _smr.SetBlendShapeWeight(_bBlink, _wBlink);
            if (_bJaw >= 0) _smr.SetBlendShapeWeight(_bJaw, _wJaw);
            if (_bBrows >= 0) _smr.SetBlendShapeWeight(_bBrows, _wBrows);
            if (_bSmile >= 0) _smr.SetBlendShapeWeight(_bSmile, _wSmile);
        }

        void LateUpdate()
        {
            // 头部微动（在动画求值之后叠加）：慢速 Perlin 噪声 ±3°，说话/惊讶时幅度略大
            if (!_blend || _head == null) return;
            float t = Time.time; float amp = (t < _talkUntil || t < _surpriseUntil) ? 4.5f : 2.5f;
            float yaw = (Mathf.PerlinNoise(_lookSeed.x, t * 0.18f) - 0.5f) * 2f * amp;
            float pitch = (Mathf.PerlinNoise(_lookSeed.y, t * 0.23f) - 0.5f) * 2f * amp * 0.6f;
            _head.localRotation = _head.localRotation * Quaternion.Euler(pitch, yaw, 0);
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
