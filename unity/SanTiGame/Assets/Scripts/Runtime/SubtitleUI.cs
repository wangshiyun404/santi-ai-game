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
        // 2D 立绘（方向决定 2026-11-15：不做 3D 建模，角色的脸用锚点立绘呈现）：底部字幕左侧的头像面板 + 章节卡左侧大图
        Image _portraitBg, _portrait, _cardPortraitBg, _cardPortrait; Text _portraitName;
        float _portraitUntil, _portraitAlpha; string _portraitId;
        static readonly System.Collections.Generic.Dictionary<string, Sprite> _portraitCache = new();
        const float PortraitW = 300f, PortraitH = 400f;

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
            var hudBg = MakeImage(canvasGo.transform, "HudBg"); hudBg.color = new Color(0, 0, 0, 0.6f); hudBg.raycastTarget = false;
            var hb = hudBg.rectTransform; hb.anchorMin = hb.anchorMax = hb.pivot = new Vector2(0, 1); hb.anchoredPosition = new Vector2(24, -24); hb.sizeDelta = new Vector2(1140, 124);
            _title = MakeText(canvasGo.transform, "Title", 30, TextAnchor.UpperLeft, new Vector2(0, 1), new Vector2(40, -40), new Vector2(900, 60));
            _title.text = eraTitle;
            _objective = MakeText(canvasGo.transform, "Objective", 24, TextAnchor.UpperLeft, new Vector2(0, 1), new Vector2(40, -82), new Vector2(1100, 70));
            _objective.color = new Color(1f, 0.92f, 0.7f, 0.95f);
            _controlsBg = MakeImage(canvasGo.transform, "ControlsBg"); _controlsBg.color = new Color(0, 0, 0, 0.6f); _controlsBg.raycastTarget = false;
            var cb = _controlsBg.rectTransform; cb.anchorMin = cb.anchorMax = cb.pivot = new Vector2(1, 1); cb.anchoredPosition = new Vector2(-24, -24); cb.sizeDelta = new Vector2(800, 56);
            _controls = MakeText(canvasGo.transform, "Controls", 22, TextAnchor.UpperRight, new Vector2(1, 1), new Vector2(-34, -32), new Vector2(780, 40));
            _controls.color = new Color(1, 1, 1, 0.75f);
            _controls.text = "WASD 移动 · 鼠标转视角 · Shift 跑 · 靠近发光物按 E · Esc 放出鼠标";
            _controlsUntil = Time.time + 14f;

            _subtitle = MakeText(canvasGo.transform, "Subtitle", 38, TextAnchor.LowerCenter, new Vector2(0.5f, 0), new Vector2(0, 86), new Vector2(1500, 220));
            _subtitle.supportRichText = true;
            _hint = MakeText(canvasGo.transform, "Hint", 22, TextAnchor.LowerCenter, new Vector2(0.5f, 0), new Vector2(0, 40), new Vector2(900, 40));
            _hint.color = new Color(1, 1, 1, 0.6f);

            // 立绘面板：左下角，字幕显示期间与字幕同寿命；面板显示时字幕右移让位
            _portraitBg = MakeImage(canvasGo.transform, "PortraitBg"); _portraitBg.color = new Color(0.02f, 0.03f, 0.05f, 0.85f); _portraitBg.raycastTarget = false;
            var pb = _portraitBg.rectTransform; pb.anchorMin = pb.anchorMax = pb.pivot = new Vector2(0, 0); pb.anchoredPosition = new Vector2(36, 40); pb.sizeDelta = new Vector2(PortraitW + 16, PortraitH + 16 + 44);
            _portrait = MakeImage(_portraitBg.transform, "Portrait"); _portrait.raycastTarget = false; _portrait.preserveAspect = true;
            var pr = _portrait.rectTransform; pr.anchorMin = pr.anchorMax = pr.pivot = new Vector2(0.5f, 1); pr.anchoredPosition = new Vector2(0, -8); pr.sizeDelta = new Vector2(PortraitW, PortraitH);
            _portraitName = MakeText(_portraitBg.transform, "PortraitName", 26, TextAnchor.MiddleCenter, new Vector2(0.5f, 0), new Vector2(0, 22), new Vector2(PortraitW, 40));
            _portraitName.color = new Color(1f, 0.92f, 0.7f, 1f);
            SetPortraitAlpha(0f); _portraitBg.gameObject.SetActive(false);

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
            // 章节卡左侧立绘（有 portrait 时标题/正文整体右移 200）
            _cardPortraitBg = MakeImage(_card.transform, "CardPortraitBg"); _cardPortraitBg.color = new Color(0.08f, 0.09f, 0.12f, 1f); _cardPortraitBg.raycastTarget = false;
            var cpb = _cardPortraitBg.rectTransform; cpb.anchorMin = cpb.anchorMax = cpb.pivot = new Vector2(0.5f, 0.5f); cpb.anchoredPosition = new Vector2(-560, 10); cpb.sizeDelta = new Vector2(316, 416);
            _cardPortrait = MakeImage(_cardPortraitBg.transform, "CardPortrait"); _cardPortrait.raycastTarget = false; _cardPortrait.preserveAspect = true;
            var cpr = _cardPortrait.rectTransform; cpr.anchorMin = cpr.anchorMax = cpr.pivot = new Vector2(0.5f, 0.5f); cpr.anchoredPosition = Vector2.zero; cpr.sizeDelta = new Vector2(300, 400);
            _cardPortraitBg.gameObject.SetActive(false);
            SetCardAlpha(0f); _card.gameObject.SetActive(false);

            // 结束卡
            _end = MakeImage(canvasGo.transform, "End"); _end.color = new Color(0.03f, 0.04f, 0.07f, 1f); _end.raycastTarget = false; Stretch(_end.rectTransform);
            _endText = MakeText(_end.transform, "EndText", 34, TextAnchor.MiddleCenter, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(1400, 500));
            _endText.lineSpacing = 1.4f;
            _end.gameObject.SetActive(false);
        }

        void Update()
        {
            if (Time.time > _subtitleUntil) _subtitle.text = "";
            if (Time.time > _hintUntil) _hint.text = "";
            UpdatePortrait();
            _title.text = eraTitle;
            var cm = ClueManager.Instance;
            _objective.text = string.IsNullOrEmpty(objective) ? "" : $"目标：{objective}{(cm != null && cm.Total > 0 ? $"（{cm.DoneCount}/{cm.Total}）" : "")}";
            float cl = Mathf.Clamp01((_controlsUntil - Time.time) / 2f); var cc = _controls.color; cc.a = 0.75f * cl; _controls.color = cc; var cbc = _controlsBg.color; cbc.a = 0.6f * cl; _controlsBg.color = cbc;
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

        /// <summary>显示 2D 立绘（Resources/Portraits/&lt;id&gt;.png）于字幕左侧，seconds 后淡出。</summary>
        public void ShowPortrait(string id, string name, float seconds)
        {
            var sp = LoadPortrait(id); if (sp == null) return;
            _portrait.sprite = sp; _portraitName.text = name ?? ""; _portraitId = id;
            _portraitUntil = Time.time + seconds; _portraitBg.gameObject.SetActive(true);
        }

        void UpdatePortrait()
        {
            if (_portraitBg == null) return;
            bool want = Time.time < _portraitUntil && !cardShowing && !_endShown;
            float target = want ? 1f : 0f;
            _portraitAlpha = Mathf.MoveTowards(_portraitAlpha, target, Time.deltaTime / (want ? 0.3f : 0.5f));
            SetPortraitAlpha(_portraitAlpha);
            if (_portraitAlpha <= 0f && !want) _portraitBg.gameObject.SetActive(false);
            // 字幕让位：面板可见时字幕块右移、变窄
            float k = _portraitAlpha; var rt = _subtitle.rectTransform;
            rt.anchoredPosition = new Vector2(Mathf.Lerp(0f, 170f, k), 86f); rt.sizeDelta = new Vector2(Mathf.Lerp(1500f, 1240f, k), 220f);
            _hint.rectTransform.anchoredPosition = new Vector2(Mathf.Lerp(0f, 170f, k), 40f);
        }

        void SetPortraitAlpha(float a)
        {
            var c = _portraitBg.color; c.a = 0.85f * a; _portraitBg.color = c;
            var cp = _portrait.color; cp.a = a; _portrait.color = cp;
            var cn = _portraitName.color; cn.a = a; _portraitName.color = cn;
        }

        static Sprite LoadPortrait(string id)
        {
            if (string.IsNullOrEmpty(id)) return null;
            if (_portraitCache.TryGetValue(id, out var sp) && sp != null) return sp;
            var tex = Resources.Load<Texture2D>("Portraits/" + id);
            if (tex == null) { Debug.LogWarning("[SanTi] portrait missing: " + id); return null; }
            sp = Sprite.Create(tex, new Rect(0, 0, tex.width, tex.height), new Vector2(0.5f, 0.5f), 100f);
            _portraitCache[id] = sp; return sp;
        }
        public void ShowHint(string s) { _hint.text = s; _hintUntil = Time.time + 0.2f; }
        public void SetWhiteout(float a) { var c = _whiteout.color; c.a = a; _whiteout.color = c; }

        /// <summary>章节卡：淡入 0.5 s → 停留 → 淡出 0.7 s；期间锁输入；1 s 后按任意键可跳过。</summary>
        public void ShowCard(string title, string lines, float hold, string portrait = null) { StartCoroutine(CardRoutine(title, lines, hold, portrait)); }

        IEnumerator CardRoutine(string title, string lines, float hold, string portrait)
        {
            cardShowing = true; GameState.InputLocked = true;
            _cardTitle.text = title; _cardLines.text = lines; _card.gameObject.SetActive(true);
            var sp = LoadPortrait(portrait); bool hasP = sp != null;
            _cardPortraitBg.gameObject.SetActive(hasP); if (hasP) _cardPortrait.sprite = sp;
            // 有立绘：标题与正文右移、正文变窄，给左侧 316 px 的图让位
            _cardTitle.rectTransform.anchoredPosition = new Vector2(hasP ? 200f : 0f, 200f);
            _cardLines.rectTransform.anchoredPosition = new Vector2(hasP ? 200f : 0f, -60f);
            _cardLines.rectTransform.sizeDelta = new Vector2(hasP ? 1000f : 1300f, 300f);
            float t = 0; while (t < 0.5f) { t += Time.deltaTime; SetCardAlpha(t / 0.5f); yield return null; }
            SetCardAlpha(1f);
            t = 0; while (t < hold) { t += Time.deltaTime; if (t > 1f && Input.anyKeyDown) break; yield return null; }
            t = 0; while (t < 0.7f) { t += Time.deltaTime; SetCardAlpha(1f - t / 0.7f); yield return null; }
            SetCardAlpha(0f); _card.gameObject.SetActive(false);
            cardShowing = false; GameState.InputLocked = false;
        }

        void SetCardAlpha(float a)
        {
            var c = _card.color; c.a = a; _card.color = c;   // 不留透明度：URP 把 Overlay UI 合成进 HDR 缓冲再调色，0.93 的黑在亮场景里只像 50% 灰（E31 网页版截图）
            var ct = _cardTitle.color; ct.a = a; _cardTitle.color = ct;
            var cl = _cardLines.color; cl.a = 0.9f * a; _cardLines.color = cl;
            var cs = _cardSkip.color; cs.a = 0.55f * a; _cardSkip.color = cs;
            if (_cardPortrait != null) { var pc = _cardPortrait.color; pc.a = a; _cardPortrait.color = pc; var pbc = _cardPortraitBg.color; pbc.a = a; _cardPortraitBg.color = pbc; }
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
