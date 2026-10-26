using System.Collections;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace SanTi
{
    public static class SceneTransition
    {
        public static IEnumerator WhiteoutAndLoad(string scene, float duration)
        {
            GameState.InputLocked = true;
            float t = 0;
            while (t < duration)
            {
                t += Time.deltaTime;
                SubtitleUI.Instance?.SetWhiteout(Mathf.SmoothStep(0, 1, t / duration));
                yield return null;
            }
            GameState.InputLocked = false;
            SceneManager.LoadScene(scene);
        }
    }
}
