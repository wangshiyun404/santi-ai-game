using UnityEngine;

namespace SanTi
{
    /// <summary>
    /// REA Q10：每一幕开场放章节卡（你是谁 / 在哪 / 要做什么），并把目标行写进 HUD。
    /// 三日凌空后回到红岸时改用尾声卡（GameState.Ending）。
    /// </summary>
    public class StoryDirector : MonoBehaviour
    {
        public IntroData intro, ending;
        public float hold = 6.5f;
        public static float holdOverride = -1f;   // 盲审截图时缩短章节卡（PlayCaptureRunner 设置）

        void Start()
        {
            var ui = SubtitleUI.Instance; if (ui == null) return;
            var d = GameState.Ending && ending != null ? ending : intro;
            if (d == null) return;
            ui.objective = d.objective ?? "";
            if (!string.IsNullOrEmpty(d.title)) ui.ShowCard(d.title, d.lines ?? "", holdOverride > 0 ? holdOverride : hold);
        }
    }
}
