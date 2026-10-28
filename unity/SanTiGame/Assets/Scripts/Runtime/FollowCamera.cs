using UnityEngine;

namespace SanTi
{
    /// <summary>越肩跟随相机。默认距离 6 m、高 2.5 m、俯角 15°（PRD §6：让角色显小）。</summary>
    public class FollowCamera : MonoBehaviour
    {
        public Transform target;
        public float distance = 6f;
        public float height = 2.5f;
        public float pitch = 15f;
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

            // 防止穿地
            if (Physics.Raycast(pivot, (desired - pivot).normalized, out var hit, distance + 0.5f))
                desired = hit.point + hit.normal * 0.3f;

            transform.position = Vector3.Lerp(transform.position, desired, Time.deltaTime * smooth);
            transform.rotation = Quaternion.LookRotation(pivot - transform.position);
        }
    }
}
