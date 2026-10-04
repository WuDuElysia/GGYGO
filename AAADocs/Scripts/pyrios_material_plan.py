"""Pyrios 表面材质的纯数据规划（不依赖 Unreal）。

把 AnimeStudio 导出的 NapAvatarStandard 材质 JSON 换算成 M_Pyrois_Toon 的 MI 参数：
- Custom 节点的输入表来自 nap_avatar_toon_inputs.json（由 gen_nap_avatar_hlsl.py 生成）；
- 材质属性一律以 float4 传入，Float 放在 x 分量；Properties 中声明为 Color 的属性按 Unity 线性工程
  的上传规则做 Gamma->Linear（<=1 用 sRGB 曲线，>1 用 pow 2.2），Vector 原样；
- MatCap 打包数组（_MatCapTexID_* 等）在游戏里由运行时脚本按组填写，这里按同样的组顺序重建；
- 场景/角色级的全局参数不在材质里，来自 AAADocs/Assets/Pyrios/Rendering/Pyrios_Toon_Globals.json。

master 只实现 Pyrios 三个材质用到的分支；源材质开启未实现的特性时 load_plan 报错。
"""
import json
import math
from pathlib import Path

SUFFIXES = ("Body_1", "Body_2", "Weapon01")
SLOT_INSTANCES = {"MAT_Pyrois_" + s: "MI_Pyrois_" + s for s in SUFFIXES}
INPUTS_PATH = Path(__file__).resolve().with_name("nap_avatar_toon_inputs.json")
SHADER_NAME = "miHoYo/Character/NapAvatarStandard"
GROUP_SUFFIX = ("", "2", "3", "4", "5")  # 材质组 0..4 对应属性后缀
MATCAP_UNASSIGNED = 100.0                # shader 中 TexID >= 50 视为该组没有 MatCap

TEXTURE_SOURCES = {"MainTex": "_MainTex", "LightTex": "_LightTex",
                   "OtherDataTex": "_OtherDataTex", "OtherDataTex2": "_OtherDataTex2"}

REQUIRED_VALUES = {
    "_DoubleSided": 0.0,     # 背面 UV 需要 TEXCOORD3，导出网格没有
    "_SymmetryUV": 0.0,      # 同上
    "_UseOverlayTex": 0.0,   # 叠加贴图未接入
    "_Cull": 2.0,            # UE 材质按单面生成
}
for _s in GROUP_SUFFIX:
    REQUIRED_VALUES["_MatCapRefract" + _s] = 0.0  # 折射 MatCap 需要 Unity UV 空间的偏移，未实现


def number(v, label):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ValueError("Expected finite number: " + label)
    return float(v)


def unity_gamma_to_linear(v):
    if v <= 0.04045:
        return v / 12.92
    if v < 1.0:
        return ((v + 0.055) / 1.055) ** 2.4
    return v ** 2.2


def color(v, label):
    if not isinstance(v, dict) or not {"r", "g", "b", "a"}.issubset(v):
        raise ValueError("Expected RGBA object: " + label)
    return tuple(number(v[c], label + "." + c) for c in ("r", "g", "b", "a"))


def texture_name(entry, label, required=False):
    tex = entry.get("m_Texture", {})
    if tex.get("IsNull", True):
        if required:
            raise ValueError("Required texture is null: " + label)
        return None
    name = tex.get("Name")
    if not isinstance(name, str) or not name or any(c in name for c in "/\\."):
        raise ValueError("Invalid texture name: " + label)
    return name


def load_inputs(path=INPUTS_PATH):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["inputs"], set(data["color_properties"])


def material_value(props, name, colors):
    if name in props["m_Floats"]:
        return (number(props["m_Floats"][name], name), 0.0, 0.0, 0.0)
    if name in props["m_Colors"]:
        c = color(props["m_Colors"][name], name)
        if name in colors:
            c = tuple(unity_gamma_to_linear(x) for x in c[:3]) + (c[3],)
        return c
    raise ValueError("Material property missing: " + name)


def material_plan(data, inputs, colors):
    props = data["m_SavedProperties"]
    if data.get("m_Shader", {}).get("Name") != SHADER_NAME:
        raise ValueError("Unexpected shader for %s" % data.get("m_Name"))
    for key, want in REQUIRED_VALUES.items():
        got = number(props["m_Floats"].get(key, want), key)
        if got != want:
            raise ValueError("%s: %s=%s, master only implements %s" % (data["m_Name"], key, got, want))
    params = {i["name"]: material_value(props, i["name"], colors) for i in inputs if i["kind"] == "material"}
    textures = {slot: texture_name(props["m_TexEnvs"].get(src, {}), src, True)
                for slot, src in TEXTURE_SOURCES.items()}
    matcap_on = number(props["m_Floats"].get("_MatCap", 0.0), "_MatCap") > 0.5
    for g, s in enumerate(GROUP_SUFFIX, 1):
        tex = texture_name(props["m_TexEnvs"].get("_MatCapTex" + s, {}), "_MatCapTex" + s)
        textures["MatCapTex%d" % g] = tex
        f = props["m_Floats"]
        slice_index = float(g - 1) if (matcap_on and tex) else MATCAP_UNASSIGNED
        params["MC_Refract%d" % g] = color(props["m_Colors"]["_RefractParam" + s], "_RefractParam" + s)
        params["MC_Tint%d" % g] = material_value(props, "_MatCapColorTint" + s, colors)
        params["MC_A%d" % g] = (slice_index, number(f["_MatCapColorBurst" + s], "burst"),
                                number(f["_MatCapAlphaBurst" + s], "alpha"), number(f["_MatCapUSpeed" + s], "u"))
        params["MC_B%d" % g] = (number(f["_MatCapVSpeed" + s], "v"), number(f["_MatCapBlendMode" + s], "mode"),
                                number(f["_MatCapRefract" + s], "refract"), number(f["_RefractDepth" + s], "depth"))
    return params, textures


def load_globals(path, inputs):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    expected = {i["name"] for i in inputs if i["kind"] == "global"} | \
               {i["name"] for i in inputs if i["kind"] == "extra" and not i["name"].startswith("MC_")}
    values = {k: v for k, v in data.items() if not k.startswith("//")}
    if set(values) != expected:
        raise ValueError("Globals keys differ: missing %s, unknown %s" % (
            sorted(expected - set(values)), sorted(set(values) - expected)))
    result = {}
    for k, v in values.items():
        if not isinstance(v, list) or len(v) != 4:
            raise ValueError("Global needs four values: " + k)
        result[k] = tuple(number(x, k) for x in v)
    return result


def load_plan(json_dir, globals_path, inputs_path=INPUTS_PATH):
    inputs, colors = load_inputs(inputs_path)
    materials, params, textures = {}, {}, {}
    for suffix in SUFFIXES:
        data = json.loads((Path(json_dir) / ("MAT_Pyrois_" + suffix + ".json")).read_text(encoding="utf-8"))
        if data.get("m_Name") != "MAT_Pyrois_" + suffix:
            raise ValueError("Source material name mismatch: " + suffix)
        materials[suffix] = data
        params[suffix], textures[suffix] = material_plan(data, inputs, colors)
    names = sorted({t for tex in textures.values() for t in tex.values() if t})
    return {"inputs": inputs, "materials": materials, "params": params, "textures": textures,
            "texture_names": names, "globals": load_globals(globals_path, inputs)}


class BuildJournal:
    """Records partial writes; never claims rollback or disk success on failure."""
    def __init__(self):
        self.modified, self.saved = [], []

    def touch(self, path):
        if path not in self.modified:
            self.modified.append(path)

    def save(self, path, callback):
        if not callback():
            raise RuntimeError("Asset save failed: " + path)
        if path not in self.saved:
            self.saved.append(path)

    def report(self, status, error=None):
        return {"status": status, "modified_or_attempted": list(self.modified), "saved": list(self.saved),
                "unsaved_or_failed": [p for p in self.modified if p not in self.saved], "error": error}


if __name__ == "__main__":
    here = Path(__file__).resolve()
    plan = load_plan(here.parents[2] / "Content/Characters/Player/Pyrios/Materials",
                     here.parents[1] / "Assets/Pyrios/Rendering/Pyrios_Toon_Globals.json")
    for suffix in SUFFIXES:
        print(suffix, plan["textures"][suffix])
        for k in ("_ShallowColor", "_ShadowColor2", "MC_A2", "MC_B2", "MC_Tint2"):
            print("  ", k, tuple(round(x, 4) for x in plan["params"][suffix][k]))
