using UnityEngine;

namespace SanTi
{
    /// <summary>REA 台账 Q7：交互反馈音。运行时合成短音，不依赖音频资源（WebGL 体积不变）。</summary>
    public static class Sfx
    {
        static AudioClip _confirm, _tick;
        static AudioSource _src;

        static AudioSource Src()
        {
            if (_src != null) return _src;
            var go = new GameObject("Sfx"); Object.DontDestroyOnLoad(go);
            _src = go.AddComponent<AudioSource>(); _src.spatialBlend = 0f; _src.volume = 0.6f;
            return _src;
        }

        static AudioClip Tone(string name, float f0, float f1, float dur)
        {
            int sr = 44100, n = Mathf.CeilToInt(sr * dur);
            var data = new float[n];
            for (int i = 0; i < n; i++)
            {
                float t = i / (float)sr, u = i / (float)n;
                float f = Mathf.Lerp(f0, f1, u);
                float env = Mathf.Sin(Mathf.PI * u);                 // 起止平滑
                data[i] = Mathf.Sin(2f * Mathf.PI * f * t) * env * 0.5f + Mathf.Sin(4f * Mathf.PI * f * t) * env * 0.12f;
            }
            var clip = AudioClip.Create(name, n, 1, sr, false); clip.SetData(data, 0);
            return clip;
        }

        /// <summary>线索触发：两音上行。</summary>
        public static void Confirm()
        {
            if (_confirm == null) _confirm = Tone("sfx_confirm", 660f, 990f, 0.16f);
            Src().PlayOneShot(_confirm);
        }

        /// <summary>靠近可交互物时的轻提示（节流由调用方负责）。</summary>
        public static void Tick()
        {
            if (_tick == null) _tick = Tone("sfx_tick", 880f, 880f, 0.05f);
            Src().PlayOneShot(_tick, 0.35f);
        }
    }
}
