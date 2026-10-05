"""读取 AnimeStudio 导出的 Legacy AnimationClip（Unity YAML 文本），给出各节点的变换曲线。

    clip = load(path) → {"length", "wrap", "rotation": {path: curve4}, "position": {path: curve3},
                          "scale": {path: curve3}, "euler": {path: curve3}, "float": [(path, attribute, classID, curve1)]}
    curveN = [{"time", "value": [..], "in": [..], "out": [..], "weighted": int}]

Unity AnimationCurve 关键帧之间是三次 Hermite：
    p(t) = h00·v0 + h10·dt·out0 + h01·v1 + h11·dt·in1，s = (t-t0)/dt
旋转曲线逐分量插值后再归一化。加权切线（weightedMode≠0）的 Bezier 形式未实现，遇到直接报错。
"""
import re


def _vec(text):
    """'{x: 1, y: 2, z: 3, w: 4}' 或标量 → 列表。"""
    text = text.strip()
    if text.startswith("{"):
        return [float(v) for _, v in re.findall(r"(\w+):\s*([-+0-9.eE]+|-?inf|nan)", text)]
    return [float(text)]


def _parse_curve_block(lines, i, indent):
    """从 'm_Curve:' 下一行开始读关键帧，返回 (keys, 下一行号)。"""
    keys = []
    cur = None
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        lead = len(line) - len(line.lstrip())
        if stripped and lead < indent:
            break
        if stripped.startswith("- serializedVersion"):
            cur = {}
            keys.append(cur)
        elif cur is not None and ":" in stripped:
            k, v = stripped.split(":", 1)
            v = v.strip()
            if k == "time":
                cur["time"] = float(v)
            elif k == "value":
                cur["value"] = _vec(v)
            elif k == "inSlope":
                cur["in"] = _vec(v)
            elif k == "outSlope":
                cur["out"] = _vec(v)
            elif k == "weightedMode":
                cur["weighted"] = int(v)
        i += 1
    return keys, i


def load(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    clip = {"rotation": {}, "position": {}, "scale": {}, "euler": {}, "float": [], "length": None, "wrap": 0}
    section = None
    i = 0
    pending = None
    while i < len(lines):
        s = lines[i].strip()
        m = re.match(r"(m_\w+Curves):\s*(\[\])?$", s)
        if m:
            section = {"m_RotationCurves": "rotation", "m_PositionCurves": "position", "m_ScaleCurves": "scale",
                       "m_EulerCurves": "euler", "m_FloatCurves": "float"}.get(m.group(1))
            i += 1
            continue
        if section and s == "m_Curve:":
            indent = len(lines[i]) - len(lines[i].lstrip())
            keys, i = _parse_curve_block(lines, i + 1, indent)
            pending = {"keys": keys}
            continue
        if section and pending is not None and s.startswith("attribute:"):
            pending["attribute"] = s.split(":", 1)[1].strip()
        if section and pending is not None and s.startswith("classID:"):
            pending["classID"] = int(s.split(":", 1)[1])
        if section and pending is not None and s.startswith("path:"):
            pending["path"] = s.split(":", 1)[1].strip()
            if section != "float":
                if any(k.get("weighted") for k in pending["keys"]):
                    raise ValueError("%s 的 %s 曲线带加权切线，未实现" % (path, pending["path"]))
                clip[section][pending["path"]] = pending["keys"]
                pending = None
        if section == "float" and pending is not None and "path" in pending and "classID" in pending:
            clip["float"].append((pending["path"], pending.get("attribute"), pending["classID"], pending["keys"]))
            pending = None
        if s.startswith("m_StopTime:"):
            clip["length"] = float(s.split(":", 1)[1])
        if s.startswith("m_WrapMode:"):
            clip["wrap"] = int(s.split(":", 1)[1])
        if re.match(r"m_(SampleRate|Bounds|ClipBindingConstant|AnimationClipSettings):", s):
            section = None
        i += 1
    return clip


def hermite(keys, t, comp):
    """按 Unity 规则求曲线在 t 处的第 comp 分量；t 超出范围时取端点（Clamp）。"""
    if not keys:
        raise ValueError("空曲线")
    if t <= keys[0]["time"]:
        return keys[0]["value"][comp]
    if t >= keys[-1]["time"]:
        return keys[-1]["value"][comp]
    for a, b in zip(keys, keys[1:]):
        if a["time"] <= t <= b["time"]:
            dt = b["time"] - a["time"]
            if dt <= 0:
                return b["value"][comp]
            m0, m1 = a["out"][comp], b["in"][comp]
            if abs(m0) == float("inf") or abs(m1) == float("inf"):
                return a["value"][comp]  # 阶跃切线：保持前一关键帧的值，与 Unity 相同
            s = (t - a["time"]) / dt
            s2, s3 = s * s, s * s * s
            return ((2 * s3 - 3 * s2 + 1) * a["value"][comp] + (s3 - 2 * s2 + s) * dt * m0
                    + (-2 * s3 + 3 * s2) * b["value"][comp] + (s3 - s2) * dt * m1)
    return keys[-1]["value"][comp]
