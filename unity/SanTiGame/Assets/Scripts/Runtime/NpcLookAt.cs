using UnityEngine;

namespace SanTi
{
    /// <summary>REA 台账 Q6：NPC 在玩家进入半径内平滑转向玩家，离开后回到预设朝向。只转偏航。</summary>
    public class NpcLookAt : MonoBehaviour
    {
        public float radius = 9f;
        public float turnSpeedDeg = 140f;

        Transform _player; float _homeYaw;

        void Start()
        {
            _homeYaw = transform.eulerAngles.y;
            var p = GameObject.FindGameObjectWithTag("Player");
            _player = p != null ? p.transform : null;
        }

        void Update()
        {
            if (_player == null) return;
            Vector3 d = _player.position - transform.position; d.y = 0;
            float targetYaw = d.sqrMagnitude < radius * radius && d.sqrMagnitude > 0.01f ? Mathf.Atan2(d.x, d.z) * Mathf.Rad2Deg : _homeYaw;
            float yaw = Mathf.MoveTowardsAngle(transform.eulerAngles.y, targetYaw, turnSpeedDeg * Time.deltaTime);
            transform.rotation = Quaternion.Euler(0, yaw, 0);
        }
    }
}
