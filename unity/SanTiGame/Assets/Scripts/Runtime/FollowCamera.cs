using UnityEngine;

namespace SanTi
{
    /// <summary>越肩跟随相机。REA Q2：距离 4.2 m、高 1.9 m、俯角 10°（原 6 m/15° 让脸不足 20 px）；对话时切越肩近景看 NPC。</summary>
    public class FollowCamera : MonoBehaviour
    {
        public Transform target;
        public float distance = 4.2f;
        public float height = 1.9f;
        public float pitch = 10f;
        public float focusDistance = 2.6f;
        public float yawSensitivity = 2.5f;
        public float pitchSensitivity = 1.5f;
        public float minPitch = -5f, maxPitch = 60f;
        public float smooth = 8f;

        float _yaw;

        void Start()
        {
            if (target != null) _yaw = target.eulerAngles.y;
            Cursor.lockState = CursorLockMode.Locked;
            Cursor.visible = false;
        }

        void LateUpdate()
        {
            if (target == null) return;
            if (GameState.AutoYawEnabled)
            {
                _yaw = Mathf.LerpAngle(_yaw, GameState.AutoYaw, 1f - Mathf.Exp(-GameState.AutoYawSpeed * Time.deltaTime));
                pitch = Mathf.Lerp(pitch, 12f, Time.deltaTime);
            }
            else if (!GameState.InputLocked)
            {
                _yaw += Input.GetAxis("Mouse X") * yawSensitivity;
                pitch = Mathf.Clamp(pitch - Input.GetAxis("Mouse Y") * pitchSensitivity, minPitch, maxPitch);
            }
            if (Input.GetKeyDown(KeyCode.Escape))
            {
                Cursor.lockState = Cursor.lockState == CursorLockMode.Locked ? CursorLockMode.None : CursorLockMode.Locked;
                Cursor.visible = !Cursor.visible;
            }

            Quaternion rot = Quaternion.Euler(pitch, _yaw, 0);
            Vector3 pivot = target.position + Vector3.up * 1.4f;
            Vector3 desired = pivot - rot * Vector3.forward * distance + Vector3.up * (height - 1.4f);
            float smoothK = smooth;

            // 对话近景：越过玩家肩膀看 NPC 的脸
            var focus = GameState.FocusTarget;
            if (focus != null && Time.time < GameState.FocusUntil)
            {
                Vector3 npcHead = focus.position + Vector3.up * 1.55f;
                Vector3 toPlayer = target.position - focus.position; toPlayer.y = 0;
                if (toPlayer.sqrMagnitude < 0.01f) toPlayer = -target.forward;
                toPlayer.Normalize();
                Vector3 side = Vector3.Cross(Vector3.up, toPlayer);
                desired = target.position + Vector3.up * 1.7f + toPlayer * (focusDistance * 0.55f) + side * 0.9f;
                pivot = Vector3.Lerp(npcHead, target.position + Vector3.up * 1.5f, 0.3f);
                smoothK = 4f;
            }
            else if (focus != null) GameState.FocusTarget = null;

            // 防止穿地
            if (Physics.Raycast(pivot, (desired - pivot).normalized, out var hit, distance + 0.5f))
                desired = hit.point + hit.normal * 0.3f;

            transform.position = Vector3.Lerp(transform.position, desired, Time.deltaTime * smoothK);
            transform.rotation = Quaternion.LookRotation(pivot - transform.position);
        }
    }
}
