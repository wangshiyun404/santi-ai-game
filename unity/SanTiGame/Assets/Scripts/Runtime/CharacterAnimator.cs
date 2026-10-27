using UnityEngine;

namespace SanTi
{
    /// <summary>
    /// 驱动 Tripo 绑骨 + 重定向得到的 GLB 动画（glTFast 默认导入为 Legacy Animation，剪辑名 idle / walk / run）。
    /// 玩家：按 CharacterController 水平速度在 idle/walk/run 之间淡入淡出；NPC：循环 idle。
    /// </summary>
    public class CharacterAnimator : MonoBehaviour
    {
        public Animation anim;                 // 子物体上的 Legacy Animation 组件
        public CharacterController controller; // 玩家才有；NPC 留空
        public float walkThreshold = 0.3f;
        public float runThreshold = 3.5f;
        public float fade = 0.15f;

        string _current;

        void Start()
        {
            if (anim == null) anim = GetComponentInChildren<Animation>();
            if (anim == null) { enabled = false; return; }
            foreach (AnimationState s in anim) s.wrapMode = WrapMode.Loop;
            anim.playAutomatically = false;
            Play(Has("idle") ? "idle" : FirstClip());
        }

        void Update()
        {
            if (anim == null || controller == null) return;
            var v = controller.velocity; v.y = 0;
            float speed = v.magnitude;
            string target = speed > runThreshold && Has("run") ? "run" : speed > walkThreshold && Has("walk") ? "walk" : "idle";
            if (target != _current && Has(target)) Play(target);
        }

        bool Has(string clip) => anim != null && anim[clip] != null;
        string FirstClip() { foreach (AnimationState s in anim) return s.name; return null; }

        void Play(string clip)
        {
            if (string.IsNullOrEmpty(clip)) return;
            _current = clip;
            anim.CrossFade(clip, fade);
        }
    }
}
