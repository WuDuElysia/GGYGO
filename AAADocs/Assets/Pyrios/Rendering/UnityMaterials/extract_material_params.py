"""
从 ZZZ AnimStudio 导出的材质 JSON 中提取关键 UE 材质参数
用法: python extract_material_params.py
输出: material_params.txt
"""

import json
import os
import glob

MATERIAL_DIR = os.path.dirname(__file__)

# 对 UE PBR 标准有意义的参数白名单
RELEVANT_FLOATS = {
    "_BumpScale", "_Cutoff", "_Cull", "_Glossiness", "_Metallic",
    "_Emission", "_Anisotropy", "_FresnelWidth", "_AlphaClip",
    "_DarkAOScale", "_OcclusionStrength", "_SmoothnessTextureChannel",
    "_BlendMode", "_DstBlend", "_SrcBlend", "_ZWrite", "_ZTest",
    "_MatCap", "_MatCapFX", "_DoubleSided",
    "_HardLight", "_HardLightWidth",
    "_BrightMultiplier", "_AmbientColorScale",
    "_Parallax", "_DetailNormalMapScale",
    "_MaterialNum", "_ModelSize",
}

RELEVANT_COLORS = {
    "_Color", "_EmissionColor", "_AmbientColor",
    "_BlockColorA", "_BlockColorB", "_BlockColorC", "_BlockColorD",
}

RELEVANT_TEXTURES = {
    "_MainTex", "_LightTex", "_BlockMaskTex", "_ChannelMixTex",
    "_CharacterRampTex", "_MatCap2DArray",
    "_MaskTex", "_DissolveTex", "_DissolveRampTex", "_DistortionTex",
}

def glossiness_to_roughness(g): return round(1.0 - g, 3)

def parse_material(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    name = os.path.splitext(os.path.basename(filepath))[0]
    result = {"name": name, "shader": data["m_Shader"]["Name"]}
    props = data.get("m_SavedProperties", {})

    # 贴图
    textures = {}
    for key, val in props.get("m_TexEnvs", {}).items():
        tex = val.get("m_Texture", {})
        if not tex.get("IsNull", True):
            textures[key] = tex["Name"]
    result["textures"] = {k: textures[k] for k in RELEVANT_TEXTURES if k in textures}

    # 浮点
    floats = {}
    for key, val in props.get("m_Floats", {}).items():
        if key in RELEVANT_FLOATS and val != 0.0:
            floats[key] = val
    result["floats"] = floats

    # 颜色
    colors = {}
    for key, val in props.get("m_Colors", {}).items():
        if key in RELEVANT_COLORS:
            c = (round(val["r"], 3), round(val["g"], 3), round(val["b"], 3), round(val["a"], 3))
            if c != (0,0,0,0) and c != (1,1,1,1):
                colors[key] = c
    result["colors"] = colors

    return result


def ue_mapping(mat):
    """生成 UE 材质设置建议"""
    f = mat["floats"]
    c = mat.get("colors", {})

    roughness = glossiness_to_roughness(f.get("_Glossiness", 1.0))
    metallic = f.get("_Metallic", 0.0)
    twosided = f.get("_Cull", 0) == 2

    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"材质: {mat['name']}")
    lines.append(f"Shader: {mat['shader']}")
    lines.append(f"{'='*60}")

    lines.append(f"\n--- 贴图 ---")
    for k, v in mat["textures"].items():
        ue_name = {"_MainTex": "Base Color", "_LightTex": "Normal Map",
                   "_BlockMaskTex": "Block Mask", "_ChannelMixTex": "Channel Mix",
                   "_CharacterRampTex": "Ramp", "_MatCap2DArray": "MatCap Array"}.get(k, k)
        lines.append(f"  {ue_name}: {v}")

    lines.append(f"\n--- UE 材质属性 ---")
    lines.append(f"  Base Color Tint: {c.get('_Color', (1,1,1,1))}")
    lines.append(f"  Roughness: {roughness}  (from Glossiness={f.get('_Glossiness', 1.0)})")
    lines.append(f"  Metallic: {metallic}")
    lines.append(f"  Two Sided: {'YES' if twosided else 'NO'}")
    lines.append(f"  Normal Intensity: {f.get('_BumpScale', 1.0)}")
    lines.append(f"  Anisotropy: {f.get('_Anisotropy', 0.0)}")
    lines.append(f"  Emissive: {f.get('_Emission', 0.0)}")
    lines.append(f"  AO Scale: {f.get('_DarkAOScale', 1.0)}")

    if mat.get("floats", {}).get("_MatCap", 0) > 0:
        lines.append(f"  ⚠ MatCap 已启用 → UE 需要自行实现 MatCap 节点")

    if mat["name"].endswith("FX01") or "Particles" in mat["shader"]:
        lines.append(f"\n--- 特效参数 (FX) ---")
        for k, v in sorted(f.items()):
            if k not in RELEVANT_FLOATS:
                continue
            lines.append(f"  {k}: {v}")
        for k, v2 in sorted(c.items()):
            lines.append(f"  {k}: {v2}")

    lines.append(f"\n--- 其他非零参数 ---")
    for k, v in sorted(f.items()):
        if k not in RELEVANT_FLOATS:
            lines.append(f"  {k}: {v}")

    return "\n".join(lines)


def main():
    json_files = glob.glob(os.path.join(MATERIAL_DIR, "MAT_*.json"))
    results = []

    for fp in sorted(json_files):
        mat = parse_material(fp)
        results.append(ue_mapping(mat))

    output = os.path.join(MATERIAL_DIR, "material_params.txt")
    with open(output, 'w', encoding='utf-8') as f:
        f.write("\n".join(results))

    print(f"提取完成 → {output}")
    print("\n".join(results))


if __name__ == "__main__":
    main()
