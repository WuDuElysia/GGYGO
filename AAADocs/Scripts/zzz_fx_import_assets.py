"""把 .deps.json 里的贴图与网格导入用户正在打开的 UE 编辑器（经 MCP），并按 Unity 导入设置配置贴图。

    for 贴图 in deps:
        TextureTools.import_file(SHARED/Textures, Unity 名, png)
        set_properties: SRGB ← m_ColorSpace，AddressX/Y ← m_WrapMode，Filter ← m_FilterMode，
                        无 mip 的贴图 NoMipmaps，压缩用默认（特效贴图多为单通道遮罩，交给 UE 自动选格式）
    for 网格 in deps:
        StaticMeshTools.import_file(SHARED/Meshes, Unity 名, fbx)（zzz_mesh_fbx 生成，带顶点色与全部 UV）
同名资产已存在则跳过导入，只重设属性；Unity 名在游戏里全局唯一（同名不同 PathID 时报错，避免覆盖）。

用法：python zzz_fx_import_assets.py <a.deps.json> [b.deps.json ...]
输出：<deps 同目录>/ue_assets.json  PathID -> UE 资产路径
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ue_mcp import Mcp  # noqa: E402

SHARED = "/Game/Characters/Shared/FX/ZZZ"
TEX_DIR = SHARED + "/Textures"
MESH_DIR = SHARED + "/Meshes"
ASSET = "editor_toolset.toolsets.asset.AssetTools."
OBJ = "editor_toolset.toolsets.object.ObjectTools."
WRAP = {0: "TA_Wrap", 1: "TA_Clamp", 2: "TA_Mirror", 3: "TA_Clamp"}
FILTER = {0: "TF_Nearest", 1: "TF_Bilinear", 2: "TF_Trilinear"}


def ref(path):
    return {"refPath": "%s.%s" % (path, path.rsplit("/", 1)[1])}


def import_texture(m, name, png, settings):
    path = "%s/%s" % (TEX_DIR, name)
    if not m.tool(ASSET + "exists", path=path)["returnValue"]:
        m.tool("editor_toolset.toolsets.texture.TextureTools.import_file",
               folder_path=TEX_DIR, asset_name=name, source_file=png)
    ts = settings["m_TextureSettings"]
    if ts["m_WrapMode"] == 3:
        raise SystemExit("%s 使用 MirrorOnce 寻址，UE 没有对应模式" % name)
    if settings["m_ColorSpace"] not in (0, 1):
        raise SystemExit("%s m_ColorSpace=%r" % (name, settings["m_ColorSpace"]))
    # UE 导入会按内容把扭曲图猜成法线贴图（BC5、解码到 -1..1），Unity 里它们是普通贴图，压缩固定为 Default
    values = {"SRGB": settings["m_ColorSpace"] == 1, "CompressionSettings": "TC_Default",
              "AddressX": WRAP[ts["m_WrapMode"]], "AddressY": WRAP[ts["m_WrapMode"]],
              "Filter": FILTER[ts["m_FilterMode"]]}
    if not settings.get("m_MipMap", True):
        values["MipGenSettings"] = "TMGS_NoMipmaps"
    ok = m.tool(OBJ + "set_properties", instance=ref(path), values=json.dumps(values))
    back = json.loads(m.tool(OBJ + "get_properties", instance=ref(path), properties=list(values))["returnValue"])
    for k, v in values.items():
        if back.get(k) != v:
            raise SystemExit("%s.%s 设置失败：期望 %r 实际 %r（set 返回 %r）" % (path, k, v, back.get(k), ok))
    return path


def import_mesh(m, name, fbx):
    path = "%s/%s" % (MESH_DIR, name)
    if not m.tool(ASSET + "exists", path=path)["returnValue"]:
        m.tool("editor_toolset.toolsets.static_mesh.StaticMeshTools.import_file",
               folder_path=MESH_DIR, asset_name=name, source_file=fbx, import_materials=False,
               import_textures=False, combine_meshes=True)
    if not m.tool(ASSET + "exists", path=path)["returnValue"]:
        raise SystemExit("网格 %s 导入后不存在" % path)
    return path


def main():
    m = Mcp()
    for deps_path in sys.argv[1:]:
        deps = json.load(open(deps_path, encoding="utf-8"))
        out_path = Path(deps_path).with_name("ue_assets.json")
        out = json.load(open(out_path, encoding="utf-8")) if out_path.exists() else {}
        names = {}
        for pid, d in deps.items():
            if d["type"] not in ("Texture2D", "Mesh"):
                continue
            prev = names.setdefault((d["type"], d["name"]), pid)
            if prev != pid:
                raise SystemExit("%s %s 有两个不同 PathID（%s / %s）" % (d["type"], d["name"], prev, pid))
            if d["type"] == "Texture2D":
                png = next(f for f in d["files"] if f.endswith(".png"))
                js = next(f for f in d["files"] if f.endswith(".json"))
                out[pid] = import_texture(m, d["name"], png, json.load(open(js, encoding="utf-8")))
            else:
                fbx = next(f for f in d["files"] if f.endswith(".fbx"))
                out[pid] = import_mesh(m, d["name"], fbx)
            print(d["type"], d["name"], "->", out[pid])
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        # 只存本脚本动过的资产；编辑器可能同时被别的会话使用，不能顺带保存它们的未存改动
        m.tool(ASSET + "save_assets", asset_paths=sorted(set(out[pid] for pid in deps if pid in out)))


if __name__ == "__main__":
    main()
