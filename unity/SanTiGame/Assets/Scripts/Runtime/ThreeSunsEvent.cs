using System.Collections;
using UnityEngine;

namespace SanTi
{
    /// <summary>三日凌空：三颗太阳升起，60 秒内世界被蒸发 → 白屏 → 回到红岸尾声。</summary>
    public class ThreeSunsEvent : MonoBehaviour, IEventListener
    {
        public Light sun;
        public Material sunMaterial;
        public string nextScene = "scene_00_red_coast";

        public void OnEvent(EventData e)
        {
            if (e.id == "three_suns") StartCoroutine(Run(Mathf.Max(20f, e.duration)));
        }

        IEnumerator Run(float duration)
        {
            GameState.InputLocked = false; // 允许缓慢行走
            var suns = new Transform[3];
            for (int i = 0; i < 3; i++)
            {
                var go = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                go.name = "Sun_" + i; Destroy(go.GetComponent<Collider>());
                go.transform.localScale = Vector3.one * (40f + i * 25f);
                if (sunMaterial) go.GetComponent<Renderer>().sharedMaterial = sunMaterial;
                go.transform.position = new Vector3(-200f + i * 250f, -60f, -900f);   // 山脉在 Unity -Z 侧（Blender +Y）
                suns[i] = go.transform;
            }
            SubtitleUI.Instance?.ShowSubtitle("三日凌空。", 6f);
            Color a0 = RenderSettings.ambientLight, f0 = RenderSettings.fogColor;
            float t = 0;
            while (t < duration)
            {
                t += Time.deltaTime; float k = t / duration;
                for (int i = 0; i < 3; i++)
                {
                    var p = suns[i].position; p.y = Mathf.Lerp(-60f, 320f + i * 60f, Mathf.SmoothStep(0, 1, Mathf.Clamp01(k * 1.6f - i * 0.15f)));
                    suns[i].position = p;
                }
                RenderSettings.ambientLight = Color.Lerp(a0, Color.white, k);
                RenderSettings.fogColor = Color.Lerp(f0, Color.white, k);
                RenderSettings.fogStartDistance = Mathf.Lerp(200f, 20f, k * k);
                if (sun) sun.intensity = Mathf.Lerp(1f, 6f, k);
                if (k > 0.75f) SubtitleUI.Instance?.SetWhiteout((k - 0.75f) / 0.25f);
                yield return null;
            }
            yield return SceneTransition.WhiteoutAndLoad(nextScene, 1.5f);
        }
    }
}
