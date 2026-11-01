using UnityEngine;

namespace SanTi
{
    /// <summary>线索物：玩家靠近后按 E 触发旁白与字幕。</summary>
    public class Clue : MonoBehaviour
    {
        public string clueId;
        [TextArea] public string subtitle;
        public string narrationClip;      // Resources/VO/<name>（不含扩展名）
        public string speaker;            // REA Q7：说话人（NPC 显示名；空=旁白）
        [TextArea] public string story;   // REA Q10：解说行（这句话在故事里意味着什么）
        public string displayName;        // 路标上显示的名字
        public bool final;                // 关键线索：其他线索看完才能触发
        public int order;                 // 布局中的顺序（路标按此顺序指引）
        [TextArea] public string endingSubtitle, endingStory;   // 尾声替换文案（scene_00 主控台）
        public float triggerRadius = 3.5f;
        public bool oneShot = true;

        public bool Done { get; private set; }
        Transform _player; bool _wasNear;
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

            bool gated = final && ClueManager.Instance != null && !ClueManager.Instance.OthersDone(this);
            if (near) SubtitleUI.Instance?.ShowHint(gated ? $"这是本幕的关键线索——先看完其他 {ClueManager.Instance.Total - 1} 处（{ClueManager.Instance.DoneCount}/{ClueManager.Instance.Total - 1}）" : "按 E 查看");
            if (near && !_wasNear) Sfx.Tick();   // REA Q7：进入交互范围时轻提示一次
            _wasNear = near;
            if (near && Input.GetKeyDown(KeyCode.E) && !GameState.InputLocked && !gated) Trigger();
        }

        public void Trigger()
        {
            Done = true;
            bool ending = GameState.Ending && !string.IsNullOrEmpty(endingSubtitle);
            string line = ending ? endingSubtitle : subtitle, expl = ending ? endingStory : story;
            // REA Q7/Q10：字幕 = 台词（带说话人）+ 灰色解说行；时长按总字数（中文约 4.5 字/秒），4–13 s
            float secs = Mathf.Clamp(1.5f + 0.22f * ((line?.Length ?? 0) + (expl?.Length ?? 0)), 4f, 13f);
            string text = string.IsNullOrEmpty(speaker) ? line : $"{speaker}：{line}";
            if (!string.IsNullOrEmpty(expl)) text += $"\n<size=28><color=#D8D8D8>{expl}</color></size>";
            SubtitleUI.Instance?.ShowSubtitle(text, secs);
            Sfx.Confirm();
            // 线索挂在 NPC 身上时切对话近景 + 表情（REA Q2）
            if (GetComponent<NpcLookAt>() != null)
            {
                GameState.FocusTarget = transform; GameState.FocusUntil = Time.time + secs + 0.5f;
                GetComponentInChildren<FaceExpression>()?.Say(secs);
            }
            if (!string.IsNullOrEmpty(narrationClip) && !ending)
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
