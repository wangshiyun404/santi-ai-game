using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace SanTi
{
    /// <summary>跟踪线索完成度，驱动布局 JSON 中的 events。</summary>
    public class ClueManager : MonoBehaviour
    {
        public static ClueManager Instance { get; private set; }
        public List<EventData> events = new List<EventData>();
        public string nextSceneOnComplete;

        readonly List<Clue> _clues = new List<Clue>();
        readonly HashSet<string> _fired = new HashSet<string>();
        Transform _player;

        void Awake() { Instance = this; }
        void Start() { var p = GameObject.FindGameObjectWithTag("Player"); _player = p ? p.transform : null; }

        public void Register(Clue c) { if (!_clues.Contains(c)) _clues.Add(c); }

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
                StartCoroutine(SceneTransition.WhiteoutAndLoad(e.loadScene, Mathf.Max(1f, e.duration)));
        }
    }

    public interface IEventListener { void OnEvent(EventData e); }
}
