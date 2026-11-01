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
        public IntroData intro;        // 章节卡：进场时讲清"你是谁、在哪、要做什么"（REA Q10）
        public IntroData ending;       // 仅 scene_00：三日凌空后回到红岸时用的尾声卡
    }

    [Serializable]
    public class IntroData
    {
        public string title;           // 如 "第一幕 · 红岸基地 1971"
        public string lines;           // 两三句前情（\n 换行）
        public string objective;
        public string endText;    // 仅尾声：结束卡文字（按 R 重新开始）
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
        public string story;      // 解说行：这句台词在《三体》里意味着什么（字幕第二行，灰色小字）
        public bool final;        // 本幕的"关键线索"：其他线索看完才能触发（触发后切幕）
        public string endingSubtitle;  // 尾声时替换台词（仅 scene_00 主控台）
        public string endingStory;
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
