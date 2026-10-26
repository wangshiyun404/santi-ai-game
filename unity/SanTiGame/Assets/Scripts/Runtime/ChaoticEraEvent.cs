using System.Collections;
using UnityEngine;

namespace SanTi
{
    /// <summary>乱纪元：太阳坠落 → 环境光由白昼转深蓝，大地结霜（材质颜色 lerp）。</summary>
    public class ChaoticEraEvent : MonoBehaviour, IEventListener
    {
        public Light sun;
        public Transform sunSphere;
        public Renderer ground;
        public Color nightAmbient = new Color(0.106f, 0.165f, 0.29f);
        public Color frostGround = new Color(0.72f, 0.79f, 0.85f);

        public void OnEvent(EventData e)
        {
            if (e.id == "sun_fall") StartCoroutine(SunFall(Mathf.Max(5f, e.duration)));
        }

        IEnumerator SunFall(float duration)
        {
            Color a0 = RenderSettings.ambientLight, f0 = RenderSettings.fogColor;
            Color g0 = ground ? ground.material.color : Color.white;
            float i0 = sun ? sun.intensity : 1f;
            Vector3 s0 = sunSphere ? sunSphere.position : Vector3.zero;
            float t = 0;
            while (t < duration)
            {
                t += Time.deltaTime; float k = Mathf.SmoothStep(0, 1, t / duration);
                RenderSettings.ambientLight = Color.Lerp(a0, nightAmbient, k);
                RenderSettings.fogColor = Color.Lerp(f0, nightAmbient, k);
                if (sun) { sun.intensity = Mathf.Lerp(i0, 0.15f, k); sun.color = Color.Lerp(Color.white, new Color(0.6f, 0.7f, 1f), k); }
                if (ground) ground.material.color = Color.Lerp(g0, frostGround, k);
                if (sunSphere) sunSphere.position = Vector3.Lerp(s0, new Vector3(s0.x, -80f, s0.z), k);
                yield return null;
            }
            SubtitleUI.Instance?.ShowSubtitle("乱纪元开始了。", 5f);
        }
    }
}
