using System.Collections;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace SanTi
{
    /// <summary>
    /// 运行时自动创建的极简 UI（不依赖预制体）：
    /// 左上：纪元名 + 目标行（含进度）；右上：操作提示（进场 14 s）；底部：字幕（台词 + 灰色解说行）与交互提示；
    /// 章节卡（进场讲清你是谁/在哪/做什么，锁输入，按任意键跳过）；线索路标（屏幕空间，指向下一条线索并显示距离）；白屏遮罩；结束卡。
    /// REA Q10：玩家反馈"不知道剧情和游戏的关系、不知道怎么玩" → 把"前情 / 目标 / 去哪 / 为什么"四件事放到屏幕上。
    /// </summary>
    public class SubtitleUI : MonoBehaviour
    {
        public static SubtitleUI Instance { get; private set; }
        public string eraTitle = "";
        public string objective = "";
        public bool cardShowing;

        RectTransform _canvasRt;
        Text _title, _objective, _controls, _subtitle, _hint, _marker, _cardTitle, _cardLines, _cardSkip, _endText;
        Image _whiteout, _card, _end, _controlsBg;
        float _subtitleUntil, _hintUntil, _controlsUntil;
        bool _endShown;

        void Awake()
        {
            Instance = this;
            var canvasGo = new GameObject("Canvas", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            canvasGo.transform.SetParent(transform, false);
            var canvas = canvasGo.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            var scaler = canvasGo.GetComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920, 1080);
            _canvasRt = canvasGo.GetComponent<RectTransform>();

            _marker = MakeText(canvasGo.transform, "Marker", 26, TextAnchor.MiddleCenter, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(420, 40));
            _marker.color = new Color(1f, 0.85f, 0.45f, 0.95f);

            // 左上信息底板：半透明深色，保证纪元名/目标行在亮天空前可读（E30：第 13 轮真机 HUD 字贴天空发虚）
            var hudBg = MakeImage(canvasGo.transform, "HudBg"); hudBg.color = new Color(0, 0, 0, 0.42f); hudBg.raycastTarget = false;
            var hb = hudBg.rectTransform; hb.anchorMin = hb.anchorMax = hb.pivot = new Vector2(0, 1); hb.anchoredPosition = new Vector2(24, -24); hb.sizeDelta = new Vector2(1140, 124);
            _title = MakeText(canvasGo.transform, "Title", 30, TextAnchor.UpperLeft, new Vector2(0, 1), new Vector2(40, -40), new Vector2(900, 60));
            _title.text = eraTitle;
            _objective = MakeText(canvasGo.transform, "Objective", 24, TextAnchor.UpperLeft, new Vector2(0, 1), new Vector2(40, -82), new Vector2(1100, 70));
            _objective.color = new Color(1f, 0.92f, 0.7f, 0.95f);
            _controlsBg = MakeImage(canvasGo.transform, "ControlsBg"); _controlsBg.color = new Color(0, 0, 0, 0.42f); _controlsBg.raycastTarget = false;
            var cb = _controlsBg.rectTransform; cb.anchorMin = cb.anchorMax = cb.pivot = new Vector2(1, 1); cb.anchoredPosition = new Vector2(-24, -24); cb.sizeDelta = new Vector2(800, 56);
            _controls = MakeText(canvasGo.transform, "Controls", 22, TextAnchor.UpperRight, new Vector2(1, 1), new Vector2(-34, -32), new Vector2(780, 40));
            _controls.color = new Color(1, 1, 1, 0.75f);
            _controls.text = "WASD 移动 · 鼠标转视角 · Shift 跑 · 靠近发光物按 E · Esc 放出鼠标";
            _controlsUntil = Time.time + 14f;

            _subtitle = MakeText(canvasGo.transform, "Subtitle", 38, TextAnchor.LowerCenter, new Vector2(0.5f, 0), new Vector2(0, 86), new Vector2(1500, 220));
            _subtitle.supportRichText = true;
            _hint = MakeText(canvasGo.transform, "Hint", 22, TextAnchor.LowerCenter, new Vector2(0.5f, 0), new Vector2(0, 40), new Vector2(900, 40));
            _hint.color = new Color(1, 1, 1, 0.6f);

            _whiteout = MakeImage(canvasGo.transform, "Whiteout");
            _whiteout.color = new Color(1, 1, 1, 0);
            _whiteout.raycastTarget = false;
            Stretch(_whiteout.rectTransform);

            // 章节卡：深色全屏 + 标题 + 前情
            _card = MakeImage(canvasGo.transform, "Card"); _card.color = new Color(0.03f, 0.04f, 0.07f, 0f); _card.raycastTarget = false; Stretch(_card.rectTransform);
            // 标题块 (0,+200) 高 90 → 155..245；正文块 (0,-60) 高 300，UpperCenter 从 +90 向下排 → 与标题留 65 px（E30：第 13 轮真机标题压在正文第二行上）
            _cardTitle = MakeText(_card.transform, "CardTitle", 54, TextAnchor.MiddleCenter, new Vector2(0.5f, 0.5f), new Vector2(0, 200), new Vector2(1600, 90));
            _cardLines = MakeText(_card.transform, "CardLines", 32, TextAnchor.UpperCenter, new Vector2(0.5f, 0.5f), new Vector2(0, -60), new Vector2(1300, 300));
            _cardLines.lineSpacing = 1.35f;
            _cardSkip = MakeText(_card.transform, "CardSkip", 22, TextAnchor.LowerCenter, new Vector2(0.5f, 0), new Vector2(0, 60), new Vector2(600, 40));
            _cardSkip.text = "按任意键继续";
            SetCardAlpha(0f); _card.gameObject.SetActive(false);

            // 结束卡
            _end = MakeImage(canvasGo.transform, "End"); _end.color = new Color(0.03f, 0.04f, 0.07f, 0.92f); _end.raycastTarget = false; Stretch(_end.rectTransform);
            _endText = MakeText(_end.transform, "EndText", 34, TextAnchor.MiddleCenter, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(1400, 500));
            _endText.lineSpacing = 1.4f;
            _end.gameObject.SetActive(false);
        }

        void Update()
        {
            if (Time.time > _subtitleUntil) _subtitle.text = "";
            if (Time.time > _hintUntil) _hint.text = "";
            _title.text = eraTitle;
            var cm = ClueManager.Instance;
            _objective.text = string.IsNullOrEmpty(objective) ? "" : $"目标：{objective}{(cm != null && cm.Total > 0 ? $"（{cm.DoneCount}/{cm.Total}）" : "")}";
            float cl = Mathf.Clamp01((_controlsUntil - Time.time) / 2f); var cc = _controls.color; cc.a = 0.75f * cl; _controls.color = cc; var cbc = _controlsBg.color; cbc.a = 0.42f * cl; _controlsBg.color = cbc;
            UpdateMarker(cm);
            if (_endShown && Input.GetKeyDown(KeyCode.R)) { GameState.Ending = false; GameState.InputLocked = false; SceneManager.LoadScene("scene_00_red_coast"); }
        }

        /// <summary>线索路标：把下一条线索投影到屏幕，显示"» 名称 · 距离"；出屏时贴边并用 < > 指方向；靠近 4 m 内或有卡片时隐藏。</summary>
        void UpdateMarker(ClueManager cm)
        {
            var next = cm != null ? cm.Next : null; var cam = Camera.main;
            if (next == null || cam == null || cardShowing || _endShown) { _marker.text = ""; return; }
            Vector3 world = next.transform.position + Vector3.up * 2.2f;
            float dist = Vector3.Distance(cam.transform.position, world);
            if (dist < 4f) { _marker.text = ""; return; }
            Vector3 sp = cam.WorldToScreenPoint(world);
            bool behind = sp.z < 0; if (behind) { sp.x = Screen.width - sp.x; sp.y = Screen.height * 0.5f; }
            float mX = 160f, mY = 110f; bool offL = sp.x < mX, offR = sp.x > Screen.width - mX;
            sp.x = Mathf.Clamp(sp.x, mX, Screen.width - mX); sp.y = Mathf.Clamp(sp.y, mY, Screen.height - mY);
            RectTransformUtility.ScreenPointToLocalPointInRectangle(_canvasRt, sp, null, out var local);
            _marker.rectTransform.anchoredPosition = local;
            bool left = offL || (behind && sp.x < Screen.width * 0.5f), right = offR || (behind && sp.x >= Screen.width * 0.5f);
            string arrow = left ? "<  " : "", tail = right ? "  >" : "";
            _marker.text = $"{arrow}» {next.displayName} · {dist:0} m{tail}";
        }

        public void ShowSubtitle(string s, float seconds) { _subtitle.text = s; _subtitleUntil = Time.time + seconds; }
        public void ShowHint(string s) { _hint.text = s; _hintUntil = Time.time + 0.2f; }
        public void SetWhiteout(float a) { var c = _whiteout.color; c.a = a; _whiteout.color = c; }

        /// <summary>章节卡：淡入 0.5 s → 停留 → 淡出 0.7 s；期间锁输入；1 s 后按任意键可跳过。</summary>
        public void ShowCard(string title, string lines, float hold) { StartCoroutine(CardRoutine(title, lines, hold)); }

        IEnumerator CardRoutine(string title, string lines, float hold)
        {
            cardShowing = true; GameState.InputLocked = true;
            _cardTitle.text = title; _cardLines.text = lines; _card.gameObject.SetActive(true);
            float t = 0; while (t < 0.5f) { t += Time.deltaTime; SetCardAlpha(t / 0.5f); yield return null; }
            SetCardAlpha(1f);
            t = 0; while (t < hold) { t += Time.deltaTime; if (t > 1f && Input.anyKeyDown) break; yield return null; }
            t = 0; while (t < 0.7f) { t += Time.deltaTime; SetCardAlpha(1f - t / 0.7f); yield return null; }
            SetCardAlpha(0f); _card.gameObject.SetActive(false);
            cardShowing = false; GameState.InputLocked = false;
        }

        void SetCardAlpha(float a)
        {
            var c = _card.color; c.a = 0.93f * a; _card.color = c;
            var ct = _cardTitle.color; ct.a = a; _cardTitle.color = ct;
            var cl = _cardLines.color; cl.a = 0.9f * a; _cardLines.color = cl;
            var cs = _cardSkip.color; cs.a = 0.55f * a; _cardSkip.color = cs;
        }

        public void ShowEnd(string text)
        {
            _endShown = true; GameState.InputLocked = true;
            _endText.text = text; _end.gameObject.SetActive(true);
        }

        // WebGL 没有系统字体回退：内置 LegacyRuntime(Arial) 不含汉字，网页版所有中文都是空白（E31，部署校验发现）。
        // 随包带一份 Noto Sans CJK SC 子集（GB2312 一级字 + 全部文案，约 0.8 MB），Mac/Windows 同样用它，三端一致。
        static Font _uiFont;
        static Font UiFont
        {
            get
            {
                if (_uiFont == null) _uiFont = Resources.Load<Font>("Fonts/NotoSansCJKsc_subset");
                if (_uiFont == null) { Debug.LogWarning("[SanTi] CJK font missing, falling back to LegacyRuntime"); _uiFont = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"); }
                return _uiFont;
            }
        }

        static Text MakeText(Transform parent, string name, int size, TextAnchor anchor, Vector2 anchorPt, Vector2 pos, Vector2 sizeDelta)
        {
            var go = new GameObject(name, typeof(Text), typeof(Outline));
            go.transform.SetParent(parent, false);
            var t = go.GetComponent<Text>();
            t.font = UiFont;
            t.fontSize = size; t.alignment = anchor; t.color = Color.white;
            t.horizontalOverflow = HorizontalWrapMode.Wrap;
            t.raycastTarget = false;
            var rt = t.rectTransform;
            rt.anchorMin = rt.anchorMax = rt.pivot = anchorPt;
            rt.anchoredPosition = pos; rt.sizeDelta = sizeDelta;
            go.GetComponent<Outline>().effectColor = new Color(0, 0, 0, 0.7f);
            return t;
        }

        static Image MakeImage(Transform parent, string name)
        {
            var go = new GameObject(name, typeof(Image));
            go.transform.SetParent(parent, false);
            return go.GetComponent<Image>();
        }

        static void Stretch(RectTransform rt)
        {
            rt.anchorMin = Vector2.zero; rt.anchorMax = Vector2.one;
            rt.offsetMin = rt.offsetMax = Vector2.zero;
        }
    }
}
