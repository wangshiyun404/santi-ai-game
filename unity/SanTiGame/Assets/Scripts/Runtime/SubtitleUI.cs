using UnityEngine;
using UnityEngine.UI;

namespace SanTi
{
    /// <summary>极简 UI：左上纪元名、底部字幕、提示、白屏遮罩。运行时自动创建，不依赖预制体。</summary>
    public class SubtitleUI : MonoBehaviour
    {
        public static SubtitleUI Instance { get; private set; }
        public string eraTitle = "";

        Text _title, _subtitle, _hint;
        Image _whiteout;
        float _subtitleUntil, _hintUntil;

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

            _whiteout = MakeImage(canvasGo.transform, "Whiteout");
            _whiteout.color = new Color(1, 1, 1, 0);
            _whiteout.raycastTarget = false;
            Stretch(_whiteout.rectTransform);

            _title = MakeText(canvasGo.transform, "Title", 30, TextAnchor.UpperLeft, new Vector2(0, 1), new Vector2(40, -40), new Vector2(800, 60));
            _title.text = eraTitle;
            _subtitle = MakeText(canvasGo.transform, "Subtitle", 38, TextAnchor.LowerCenter, new Vector2(0.5f, 0), new Vector2(0, 90), new Vector2(1400, 120));
            _hint = MakeText(canvasGo.transform, "Hint", 22, TextAnchor.LowerCenter, new Vector2(0.5f, 0), new Vector2(0, 40), new Vector2(600, 40));
            _hint.color = new Color(1, 1, 1, 0.6f);
        }

        void Update()
        {
            if (Time.time > _subtitleUntil) _subtitle.text = "";
            if (Time.time > _hintUntil) _hint.text = "";
            _title.text = eraTitle;
        }

        public void ShowSubtitle(string s, float seconds) { _subtitle.text = s; _subtitleUntil = Time.time + seconds; }
        public void ShowHint(string s) { _hint.text = s; _hintUntil = Time.time + 0.2f; }
        public void SetWhiteout(float a) { var c = _whiteout.color; c.a = a; _whiteout.color = c; }

        static Text MakeText(Transform parent, string name, int size, TextAnchor anchor, Vector2 anchorPt, Vector2 pos, Vector2 sizeDelta)
        {
            var go = new GameObject(name, typeof(Text), typeof(Outline));
            go.transform.SetParent(parent, false);
            var t = go.GetComponent<Text>();
            t.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            t.fontSize = size; t.alignment = anchor; t.color = Color.white;
            t.horizontalOverflow = HorizontalWrapMode.Wrap;
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
