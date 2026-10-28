using UnityEngine;

namespace SanTi
{
    public static class GameState
    {
        /// <summary>事件播放（白屏、三日凌空）期间锁定输入。</summary>
        public static bool InputLocked;
        /// <summary>自动移动输入（运行态截图 / 演示用），非零时覆盖键盘。</summary>
        public static Vector2 AutoMove;
    }
}
