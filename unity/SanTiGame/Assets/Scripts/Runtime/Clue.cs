using UnityEngine;

namespace SanTi
{
    /// <summary>线索物：玩家靠近后按 E 触发旁白与字幕。</summary>
    public class Clue : MonoBehaviour
    {
        public string clueId;
        [TextArea] public string subtitle;
        public string narrationClip;      // Resources/VO/<name>（不含扩展名）
        public float triggerRadius = 3.5f;
        public bool oneShot = true;

        public bool Done { get; private set; }
        Transform _player;
        Renderer[] _renderers;
        MaterialPropertyBlock _mpb;
        static readonly int EmissionId = Shader.PropertyToID("_EmissionColor");

        void Start()
        {
            var p = GameObject.FindGameObjectWithTag("Player");
            _player = p != null ? p.transform : null;
            _renderers = GetComponentsInChildren<Renderer>();
            _mpb = new MaterialPropertyBlock();
            ClueManager.Instance?.Register(this);
        }

        void Update()
        {
            if (_player == null || (Done && oneShot)) return;
            float d = Vector3.Distance(_player.position, transform.position);
            bool near = d < triggerRadius;

            // 低多边形"发光提示"：靠近时轻微自发光脉冲
            float glow = near ? 0.25f + 0.2f * Mathf.Sin(Time.time * 4f) : 0f;
            foreach (var r in _renderers)
            {
                r.GetPropertyBlock(_mpb);
                _mpb.SetColor(EmissionId, Color.white * glow);
                r.SetPropertyBlock(_mpb);
            }

            if (near) SubtitleUI.Instance?.ShowHint("按 E 查看");
            if (near && Input.GetKeyDown(KeyCode.E) && !GameState.InputLocked) Trigger();
        }

        public void Trigger()
        {
            Done = true;
            SubtitleUI.Instance?.ShowSubtitle(subtitle, 4f);
            if (!string.IsNullOrEmpty(narrationClip))
            {
                var clip = Resources.Load<AudioClip>("VO/" + System.IO.Path.GetFileNameWithoutExtension(narrationClip));
                if (clip != null) AudioSource.PlayClipAtPoint(clip, Camera.main != null ? Camera.main.transform.position : transform.position);
            }
            ClueManager.Instance?.OnClueDone(this);
        }

        void OnDrawGizmosSelected()
        {
            Gizmos.color = new Color(1, 0.8f, 0.2f, 0.4f);
            Gizmos.DrawWireSphere(transform.position, triggerRadius);
        }
    }
}
