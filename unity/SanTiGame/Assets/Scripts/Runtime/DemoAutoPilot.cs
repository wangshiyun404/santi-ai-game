using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace SanTi
{
    /// <summary>
    /// 自动演示模式（录宣传片 / 课堂挂机演示用）：角色沿预设路点自己走完三幕，到线索处自动"按 E"。
    /// 启用条件：命令行含 -demo，或 WebGL URL 含 demo=1。事件时间线写到 ~/santi_demo_timeline.txt（用于后期对音）。
    /// </summary>
    public class DemoAutoPilot : MonoBehaviour
    {
        class Step { public Vector3 pos; public string clue; public float wait; public float? yaw; public float arrive = 1.2f; }
        float _lastProgressT; float _lastDist = float.MaxValue;

        static readonly Dictionary<string, Step[]> Routes = new()
        {
            ["scene_00_red_coast"] = new[]
            {
                new Step { pos = new Vector3(8, 0, 40), yaw = 200, wait = 3f },                     // 环视
                new Step { pos = new Vector3(-9.5f, 0, 35.5f), clue = "clue_reply", wait = 5f },    // 吉普车
                new Step { pos = new Vector3(0, 0, -8), clue = "clue_antenna", wait = 5f },         // 天线塔下
                new Step { pos = new Vector3(14, 0, 12) },
                new Step { pos = new Vector3(26.5f, 0, 13f), clue = "clue_control_room", wait = 4f, arrive = 2.5f }, // 控制台 → 白屏
            },
            ["scene_01_chaotic"] = new[]
            {
                new Step { pos = new Vector3(0, 0, -12), yaw = 150, wait = 3f },
                new Step { pos = new Vector3(-30, 0, -48) },
                new Step { pos = new Vector3(-35, 0, -56), clue = "clue_dehydration", wait = 5f },  // 脱水人
                new Step { pos = new Vector3(-70, 0, -60), clue = "clue_lakebed", wait = 5f, arrive = 2f }, // 干湖床
                new Step { pos = new Vector3(-37, 0, -157.5f), clue = "clue_slips", wait = 5f },    // 竹简
                new Step { pos = new Vector3(-41, 0, -165), clue = "clue_pyramid_follower", wait = 4f }, // 追随者 → 白屏
            },
            ["scene_02_computer"] = new[]
            {
                new Step { pos = new Vector3(120, 0, 0), yaw = 120, wait = 3f },
                new Step { pos = new Vector3(140, 0, -6), clue = "clue_von_neumann", wait = 5f },   // 高台下
                new Step { pos = new Vector3(129, 0, -10) },
                new Step { pos = new Vector3(129, 0, -34) },
                new Step { pos = new Vector3(143, 0, -33), clue = "clue_gate_soldier", wait = 5f }, // 石碑 1
                new Step { pos = new Vector3(143, 0, -57), clue = "clue_bus", wait = 5f },          // 石碑 2
                new Step { pos = new Vector3(129, 0, -57) },
                new Step { pos = new Vector3(129, 0, -8) },
                new Step { pos = new Vector3(147, 0, 4) },                                          // 坡道脚
                new Step { pos = new Vector3(147, 10, -10) },                                       // 坡道顶
                new Step { pos = new Vector3(146, 10, -18), clue = "clue_sword", wait = 8f },       // 青铜剑 → 三日凌空
            },
        };

        public static bool Enabled
        {
            get
            {
                foreach (var a in System.Environment.GetCommandLineArgs()) if (a == "-demo") return true;
                return Application.absoluteURL != null && Application.absoluteURL.Contains("demo=1");
            }
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Boot()
        {
            if (!Enabled || FindFirstObjectByType<DemoAutoPilot>() != null) return;
            var go = new GameObject("DemoAutoPilot");
            DontDestroyOnLoad(go);
            go.AddComponent<DemoAutoPilot>();
        }

        Step[] _steps; int _i; float _waitUntil; float _sceneT; bool _triggered;
        Transform _player; ThirdPersonController _ctrl; FollowCamera _cam;
        StreamWriter _log; float _t0;

        void Awake()
        {
            _t0 = Time.realtimeSinceStartup;
            try
            {
                string home = System.Environment.GetFolderPath(System.Environment.SpecialFolder.UserProfile);
                if (!string.IsNullOrEmpty(home)) { _log = new StreamWriter(Path.Combine(home, "santi_demo_timeline.txt"), false); _log.AutoFlush = true; }
            }
            catch { _log = null; }
            SceneManager.sceneLoaded += OnSceneLoaded;
            OnSceneLoaded(SceneManager.GetActiveScene(), LoadSceneMode.Single);
        }

        void OnDestroy() { SceneManager.sceneLoaded -= OnSceneLoaded; _log?.Close(); }

        void Log(string ev) { _log?.WriteLine($"{Time.realtimeSinceStartup - _t0:F2}\t{ev}"); }

        void OnSceneLoaded(Scene s, LoadSceneMode m)
        {
            Routes.TryGetValue(s.name, out _steps);
            _i = 0; _sceneT = Time.time; _triggered = false; _waitUntil = Time.time + 2f;
            _player = null; _ctrl = null; _cam = null;
            GameState.AutoMove = Vector2.zero;
            GameState.AutoYawEnabled = false;
            Log("scene\t" + s.name);
        }

        void Update()
        {
            if (_steps == null || _i >= _steps.Length) { GameState.AutoMove = Vector2.zero; return; }
            if (_player == null)
            {
                var p = GameObject.FindGameObjectWithTag("Player");
                if (p == null) return;
                _player = p.transform; _ctrl = p.GetComponent<ThirdPersonController>();
                if (_ctrl != null) _ctrl.walkSpeed = 4.5f;
                _cam = FindFirstObjectByType<FollowCamera>();
                Log("player_ready");
            }
            if (GameState.InputLocked || Time.time < _waitUntil) { GameState.AutoMove = Vector2.zero; return; }

            var step = _steps[_i];
            Vector3 d = step.pos - _player.position; d.y = 0;

            if (step.yaw.HasValue && d.magnitude < step.arrive)
            {
                // 原地环视：相机慢慢转到指定朝向
                GameState.AutoMove = Vector2.zero;
                GameState.AutoYawEnabled = true; GameState.AutoYaw = step.yaw.Value; GameState.AutoYawSpeed = 0.6f;
                if (!_triggered) { _triggered = true; _waitUntil = Time.time + step.wait; Log("look\t" + step.yaw.Value); return; }
                _triggered = false; _i++; _lastDist = float.MaxValue; _lastProgressT = Time.time; return;
            }

            if (d.magnitude > step.arrive)
            {
                // 卡住看门狗：3 秒内没有靠近目标 0.3 m，就视为到达（线索会直接触发）
                if (d.magnitude < _lastDist - 0.3f) { _lastDist = d.magnitude; _lastProgressT = Time.time; }
                else if (Time.time - _lastProgressT > 3f) { Log("stuck\t" + _i); _lastDist = float.MaxValue; _lastProgressT = Time.time; d = Vector3.zero; }
            }
            if (d.magnitude > step.arrive)
            {
                float worldAngle = Mathf.Atan2(d.x, d.z) * Mathf.Rad2Deg;
                float camYaw = _cam != null ? _cam.transform.eulerAngles.y : 0f;
                float a = (worldAngle - camYaw) * Mathf.Deg2Rad;
                GameState.AutoMove = new Vector2(Mathf.Sin(a), Mathf.Cos(a));
                GameState.AutoYawEnabled = true; GameState.AutoYaw = worldAngle; GameState.AutoYawSpeed = 1.5f;
                return;
            }

            GameState.AutoMove = Vector2.zero;
            if (!string.IsNullOrEmpty(step.clue) && !_triggered)
            {
                foreach (var c in FindObjectsByType<Clue>(FindObjectsSortMode.None))
                    if (c.clueId == step.clue && !c.Done) { c.Trigger(); Log("clue\t" + step.clue); break; }
                _triggered = true; _waitUntil = Time.time + Mathf.Max(0.5f, step.wait);
                return;
            }
            Log("reach\t" + _i);
            _triggered = false; _i++; _lastDist = float.MaxValue; _lastProgressT = Time.time;
        }
    }
}
