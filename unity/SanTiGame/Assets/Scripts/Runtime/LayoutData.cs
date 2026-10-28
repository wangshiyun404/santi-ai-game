using System;
using System.Collections.Generic;
using UnityEngine;

namespace SanTi
{
    /// <summary>与 layouts/scene_XX.json 对应的数据结构（由 Blender build_assets.py 生成）。</summary>
    [Serializable]
    public class LayoutData
    {
        public string scene;
        public string title;
        public List<LayoutObject> objects = new List<LayoutObject>();
        public LightingData lighting;
        public FormationData formation;
        public List<ClueData> clues = new List<ClueData>();
        public List<EventData> events = new List<EventData>();
    }

    [Serializable]
    public class LayoutObject
    {
        public string asset;
        public string name;
        public float[] position;
        public float[] rotation;
        public float[] scale;
        public bool @static;
        public string clue;
        public string role;

        public Vector3 Position => new Vector3(position[0], position[1], position[2]);
        public Quaternion Rotation => Quaternion.Euler(rotation[0], rotation[1], rotation[2]);
        public Vector3 Scale => new Vector3(scale[0], scale[1], scale[2]);
    }

    [Serializable]
    public class FogData { public string color; public float start; public float end; }

    [Serializable]
    public class LightingData
    {
        public float[] sunAngle;
        public float intensity = 1f;
        public string sunColor;
        public string ambient;
        public FogData fog;
    }

    [Serializable]
    public class FormationBlock
    {
        public float[] origin;   // Blender (x, y) → Unity (x, z)
        public int cols;
        public int rows;
        public float spacing = 1.2f;
        public string pattern;   // checker | rows | black | white
    }

    [Serializable]
    public class FormationData
    {
        public string blackAsset;
        public string whiteAsset;
        public List<FormationBlock> blocks = new List<FormationBlock>();
        public float flipWaveSpeed = 6f;
    }

    [Serializable]
    public class ClueData
    {
        public string id;
        public string subtitle;
        public string narration;
        public float[] at;        // 可选：未绑定物件的"地点线索"放置位置（Unity 坐标）
    }

    [Serializable]
    public class EventData
    {
        public string id;
        public string trigger;    // player_reaches | all_clues_done | <clueId>
        public float[] at;
        public float duration;
        public string loadScene;
    }

    public static class ColorUtil
    {
        public static Color Hex(string hex, Color fallback)
        {
            if (string.IsNullOrEmpty(hex)) return fallback;
            return ColorUtility.TryParseHtmlString(hex, out var c) ? c : fallback;
        }
    }
}
