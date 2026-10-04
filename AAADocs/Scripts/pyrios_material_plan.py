"""Pure source validation for the Pyrios asset builder (no Unreal dependency)."""
import json
import math

SUFFIXES = ("Body_1", "Body_2", "Weapon01")
SLOT_INSTANCES = {"MAT_Pyrois_" + s: "MI_Pyrois_" + s for s in SUFFIXES}
SCALARS = {"EmissionStrength", "SpecStrength", "RimStrength", "Glossiness", "MetallicScale",
           "BumpScale", "NormalYSign", "UseMatCapMask", "SceneLightStrength", "KeyLightVisibility",
           "DiffuseGain", "SpecularGain", "RimGain", "MatCapGain", "AmbientFloor", "DiffuseBiasScale",
           "RampLow", "RampHigh", "RoughnessFloor"}
VECTORS = {"LightingTint", "KeyLightDirectionWS", "KeyLightColor", "EmissionColor", "RimGlowShadowColor"}


def number(v, label):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ValueError("Expected finite number: " + label)
    return float(v)


def color(v, label):
    if not isinstance(v, dict) or not {"r", "g", "b", "a"}.issubset(v):
        raise ValueError("Expected RGBA object: " + label)
    for c in ("r", "g", "b", "a"):
        number(v[c], label + "." + c)


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


def load_plan(json_dir, calibration_path):
    calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
    if not isinstance(calibration.get("shared"), dict) or set(calibration) - {"shared", *SUFFIXES}:
        raise ValueError("Invalid calibration sections")
    materials, resolved, textures = {}, {}, {"Eff_Matcap_125"}
    for suffix in SUFFIXES:
        data = json.loads((json_dir / ("MAT_Pyrois_" + suffix + ".json")).read_text(encoding="utf-8"))
        if data.get("m_Name") != "MAT_Pyrois_" + suffix:
            raise ValueError("Source material name mismatch: " + suffix)
        p = data["m_SavedProperties"]
        for name in ("_MainTex", "_LightTex", "_OtherDataTex", "_OtherDataTex2"):
            textures.add(texture_name(p["m_TexEnvs"][name], suffix + name, True))
        for name, v in p["m_Floats"].items():
            number(v, suffix + name)
        for i in range(1, 6):
            end = "" if i == 1 else str(i)
            for prefix in ("_ShallowColor", "_ShadowColor", "_SpecularColor", "_RimGlowLightColor"):
                color(p["m_Colors"][prefix + end], suffix + prefix + end)
            tint = p["m_Colors"].get("_MatCapColorTint" + end)
            if tint is not None:
                color(tint, suffix + "MatCapTint" + end)
            name = texture_name(p["m_TexEnvs"].get("_MatCapTex" + end, {}), suffix + "MatCap" + end)
            if name:
                textures.add(name)
        for name in ("_EmissionColor", "_RimGlowShadowColor"):
            color(p["m_Colors"][name], suffix + name)
        settings = dict(calibration["shared"])
        settings.update(calibration.get(suffix, {}))
        for name, v in settings.items():
            if name in VECTORS:
                if not isinstance(v, list) or len(v) != 4:
                    raise ValueError("Calibration vector needs four values: " + name)
                for channel in v:
                    number(channel, name)
            elif name in SCALARS:
                number(v, name)
            else:
                raise ValueError("Unknown calibration parameter: " + name)
        low, high = settings.get("RampLow", .38), settings.get("RampHigh", .7)
        if not 0 <= low < high <= 1:
            raise ValueError("Ramp thresholds must satisfy 0 <= low < high <= 1")
        if not 0 < settings.get("RoughnessFloor", .18) <= 1:
            raise ValueError("RoughnessFloor must be in (0, 1]")
        materials[suffix], resolved[suffix] = data, settings
    return {"materials": materials, "calibration": resolved, "textures": sorted(textures)}


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
