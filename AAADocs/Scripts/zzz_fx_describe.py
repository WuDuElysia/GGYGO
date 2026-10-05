"""把 .fx.json 打印成便于人工核对的摘要：每个粒子节点的时长、发射、形状、渲染模式和启用的模块。

用法：python zzz_fx_describe.py <file.fx.json>
"""
import json
import sys

RENDER_MODE = {0: "Billboard", 1: "Stretch", 2: "HorizontalBillboard", 3: "VerticalBillboard", 4: "Mesh", 5: "None"}
SHAPE = {0: "Sphere", 1: "SphereShell", 2: "Hemisphere", 3: "HemisphereShell", 4: "Cone", 5: "Box", 6: "Mesh",
         7: "ConeShell", 8: "ConeVolume", 9: "ConeVolumeShell", 10: "Circle", 11: "CircleEdge", 12: "SingleSidedEdge",
         13: "MeshRenderer", 14: "SkinnedMeshRenderer", 15: "BoxShell", 16: "BoxEdge", 17: "Donut", 18: "Rectangle",
         19: "Sprite", 20: "SpriteRenderer"}
SIM_SPACE = {0: "Local", 1: "World", 2: "Custom"}


def mmc(c):
    """MinMaxCurve 简写：state 0 常量，1 曲线，2 双曲线随机，3 双常量随机。"""
    s = c["minMaxState"]
    if s == 0:
        return "%.4g" % c["scalar"]
    if s == 3:
        return "rand(%.4g..%.4g)" % (c["minScalar"], c["scalar"])
    keys = [(round(k["time"], 3), round(k["value"], 3)) for k in c["maxCurve"]["m_Curve"]]
    tag = "curve" if s == 1 else "rcurve"
    return "%s*%.4g%s" % (tag, c["scalar"], keys[:6])


def describe(n, depth=0):
    pad = "  " * depth
    head = "%s%s%s" % (pad, n["name"], "" if n["active"] else " (inactive)")
    if "particle" in n:
        ps, rd = n["particle"]["system"], n["particle"]["renderer"]
        im = ps["InitialModule"]
        mods = [k for k, v in ps.items() if isinstance(v, dict) and v.get("enabled") and k != "InitialModule"]
        print(head)
        print(pad + "  dur=%.3g loop=%s delay=%s sim=%s scaling=%d  max=%d" % (
            ps["lengthInSec"], ps["looping"], mmc(ps["startDelay"]), SIM_SPACE.get(ps["moveWithTransform"]),
            ps["scalingMode"], im["maxNumParticles"]))
        print(pad + "  life=%s speed=%s size=%s rot=%s 3D=%s" % (
            mmc(im["startLifetime"]), mmc(im["startSpeed"]), mmc(im["startSize"]), mmc(im["startRotation"]), im["size3D"]))
        if "EmissionModule" in ps:
            em = ps["EmissionModule"]
            bursts = [(round(b["time"], 3), mmc(b["countCurve"]), b["cycleCount"]) for b in em["m_Bursts"]]
            print(pad + "  emit rate=%s bursts=%s" % (mmc(em["rateOverTime"]), bursts))
        if "ShapeModule" in ps:
            print(pad + "  shape=%s" % SHAPE.get(ps["ShapeModule"]["type"], ps["ShapeModule"]["type"]))
        mesh = rd["m_Mesh"]["m_PathID"]
        mats = [m["m_PathID"] for m in rd["m_Materials"]]
        print(pad + "  render=%s align=%d mesh=%s mats=%s streams=%s" % (
            RENDER_MODE.get(rd["m_RenderMode"], rd["m_RenderMode"]), rd["m_RenderAlignment"], mesh or "-", mats,
            rd["m_VertexStreams"] if rd["m_UseCustomVertexStreams"] else "default"))
        print(pad + "  modules=%s" % mods)
    else:
        extra = []
        if "mesh" in n:
            extra.append("mesh=%s mats=%s" % (n["mesh"]["mesh"]["m_PathID"], [m["m_PathID"] for m in n["mesh"]["materials"]]))
        if "animation" in n:
            extra.append("anim=%s" % [c["m_PathID"] for c in n["animation"]["clips"]])
        print(head + ("  " + " ".join(extra) if extra else ""))
    scripts = [s["script"].split(".")[-1] for s in n["scripts"]]
    if scripts:
        print(pad + "  scripts=%s" % scripts)
    for c in n["children"]:
        describe(c, depth + 1)


def main():
    fx = json.load(open(sys.argv[1], encoding="utf-8"))
    describe(fx["root"])


if __name__ == "__main__":
    main()
