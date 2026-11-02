using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace SanTi
{
    /// <summary>跟踪线索完成度，驱动布局 JSON 中的 events。</summary>
    public partial class ClueManager : MonoBehaviour
    {
        public static ClueManager Instance { get; private set; }
        public List<EventData> events = new List<EventData>();
        public string nextSceneOnComplete;

        readonly List<Clue> _clues = new List<Clue>();
        readonly HashSet<string> _fired = new HashSet<string>();
        Transform _player;

        void Awake() { Instance = this; }
        void Start() { var p = GameObject.FindGameObjectWithTag("Player"); _player = p ? p.transform : null; }

        public void Register(Clue c) { if (!_clues.Contains(c)) { _clues.Add(c); _clues.Sort((a, b) => a.order.CompareTo(b.order)); } }

        // ---- REA Q10：目标与路标 ----
        IEnumerable<Clue> Active => GameState.Ending ? _clues.Where(c => c.final) : _clues;   // 尾声只剩"回到主控室"一件事
        public int Total => Active.Count();
        public int DoneCount => Active.Count(c => c.Done);
        /// <summary>下一条该去的线索：按布局顺序取第一条未完成的；关键线索放最后。</summary>
        public Clue Next => Active.FirstOrDefault(c => !c.Done && !c.final) ?? Active.FirstOrDefault(c => !c.Done);
        public bool OthersDone(Clue self) => GameState.Ending || _clues.All(c => c == self || c.Done);
        public string endText = "";

        public void OnClueDone(Clue c)
        {
            foreach (var e in events.Where(e => e.trigger == c.clueId)) Fire(e);
            if (_clues.All(x => x.Done))
                foreach (var e in events.Where(e => e.trigger == "all_clues_done")) Fire(e);
        }

        void Update()
        {
            if (_player == null) return;
            foreach (var e in events.Where(e => e.trigger == "player_reaches" && e.at != null && e.at.Length == 3))
            {
                var pos = new Vector3(e.at[0], e.at[1], e.at[2]);
                if (Vector3.Distance(_player.position, pos) < 6f) Fire(e);
            }
        }

        void Fire(EventData e)
        {
            if (_fired.Contains(e.id)) return;
            _fired.Add(e.id);
            Debug.Log($"[SanTi] Event fired: {e.id}");
            var listeners = FindObjectsByType<MonoBehaviour>(FindObjectsSortMode.None).OfType<IEventListener>();
            foreach (var l in listeners) l.OnEvent(e);
            if (!string.IsNullOrEmpty(e.loadScene))
            {
                if (GameState.Ending) StartCoroutine(EndRoutine());   // 尾声：主控台不再切幕，而是收束全局
                else StartCoroutine(SceneTransition.WhiteoutAndLoad(e.loadScene, Mathf.Max(1f, e.duration)));
            }
        }
    }

    public partial class ClueManager
    {
        System.Collections.IEnumerator EndRoutine()
        {
            GameState.InputLocked = true;
            yield return new WaitForSeconds(9f);   // 让尾声字幕读完
            SubtitleUI.Instance?.ShowEnd(string.IsNullOrEmpty(endText) ? "《三体游戏》\n\n按 R 重新开始" : endText);
        }
    }

    public interface IEventListener { void OnEvent(EventData e); }
}
