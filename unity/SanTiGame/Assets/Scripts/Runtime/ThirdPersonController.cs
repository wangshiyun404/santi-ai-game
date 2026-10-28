using UnityEngine;

namespace SanTi
{
    /// <summary>第三人称移动：WASD 相对相机方向，无跳跃、无战斗。</summary>
    [RequireComponent(typeof(CharacterController))]
    public class ThirdPersonController : MonoBehaviour
    {
        public float walkSpeed = 2.6f;
        public float turnSmooth = 0.12f;
        public float gravity = -20f;
        public Transform cameraTransform;

        CharacterController _cc;
        float _turnVel;
        float _vy;

        void Awake()
        {
            _cc = GetComponent<CharacterController>();
            if (cameraTransform == null && Camera.main != null) cameraTransform = Camera.main.transform;
        }

        void Update()
        {
            if (GameState.InputLocked) { ApplyGravityOnly(); return; }

            float h = Input.GetAxisRaw("Horizontal");
            float v = Input.GetAxisRaw("Vertical");
            if (GameState.AutoMove != Vector2.zero) { h = GameState.AutoMove.x; v = GameState.AutoMove.y; }
            Vector3 input = new Vector3(h, 0, v).normalized;

            Vector3 move = Vector3.zero;
            if (input.sqrMagnitude > 0.01f)
            {
                float camYaw = cameraTransform != null ? cameraTransform.eulerAngles.y : 0f;
                float targetAngle = Mathf.Atan2(input.x, input.z) * Mathf.Rad2Deg + camYaw;
                float angle = Mathf.SmoothDampAngle(transform.eulerAngles.y, targetAngle, ref _turnVel, turnSmooth);
                transform.rotation = Quaternion.Euler(0, angle, 0);
                move = Quaternion.Euler(0, targetAngle, 0) * Vector3.forward * walkSpeed;
            }

            if (_cc.isGrounded && _vy < 0) _vy = -2f;
            _vy += gravity * Time.deltaTime;
            move.y = _vy;
            _cc.Move(move * Time.deltaTime);

            var anim = GetComponentInChildren<Animator>();
            if (anim != null) anim.SetFloat("Speed", input.sqrMagnitude > 0.01f ? 1f : 0f, 0.1f, Time.deltaTime);
        }

        void ApplyGravityOnly()
        {
            if (_cc.isGrounded && _vy < 0) _vy = -2f;
            _vy += gravity * Time.deltaTime;
            _cc.Move(new Vector3(0, _vy, 0) * Time.deltaTime);
        }
    }
}
