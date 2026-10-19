"""@file 静态 MeshRenderer 的离线源契约，不创建资产或播放资源。

@brief 消费已有 v2 组件描述和已转换 Mesh JSON，保留几何、材质槽及根内
变换。结果只表示源数据准备；材质执行、原根绑定和播放生命周期由实际
消费者建立，不能从网格存在、Legacy Clip 时长或录像秒数推导。
"""
import json
import math
from pathlib import Path

import zzz_fx_niagara as FN


class MeshContractError(ValueError):
    """必需的已解码静态网格数据无效或尚未具备。"""


def _integer(value, label, minimum=0):
    if type(value) is not int or value < minimum:
        raise MeshContractError(label + " 必须是有效整数")
    return value


def _numbers(values, label):
    if not isinstance(values, list) or any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
            for v in values):
        raise MeshContractError(label + " 必须是有限数值数组")
    return values


def _dependency(deps, pointer, expected_type):
    if not isinstance(pointer, dict) or type(pointer.get("m_PathID")) is not int:
        raise MeshContractError(expected_type + " 缺少准确源 PPtr")
    pid = str(pointer["m_PathID"])
    if pid == "0":
        raise MeshContractError(expected_type + " 源 PPtr=0；不能代入静态资源，需真实生成或绑定消费者")
    entry = deps.get(pid)
    if not entry or entry.get("type") != expected_type or entry.get("pathID") != pointer["m_PathID"]:
        raise MeshContractError(expected_type + " PPtr 未由已有依赖描述准确解析: " + pid)
    return pid, entry


def _geometry(entry):
    files = [Path(f) for f in entry.get("files", []) if str(f).lower().endswith(".json")]
    if len(files) != 1 or not files[0].is_file():
        raise MeshContractError("需要唯一已转换 Mesh JSON，不解析 Raw 或生成替代几何")
    data = json.loads(files[0].read_text(encoding="utf-8-sig"))
    count = _integer(data.get("m_VertexCount"), "m_VertexCount", 1)
    if len(_numbers(data.get("m_Vertices"), "m_Vertices")) != count * 3:
        raise MeshContractError("Mesh 顶点数量与 XYZ 数组不一致")
    if any(key not in data for key in ("m_Skin", "m_BindPose", "m_BoneNameHashes")):
        raise MeshContractError("需要明确的 Skin/BindPose/BoneNameHashes 源字段，不把缺字段当空值")
    if data.get("m_Skin") or data.get("m_BindPose") or data.get("m_BoneNameHashes"):
        raise MeshContractError("此消费者仅处理已烘焙的静态 Mesh，不退化骨骼网格")
    shapes = data.get("m_Shapes") or {}
    if any(shapes.get(k) for k in ("vertices", "shapes", "channels", "fullWeights")):
        raise MeshContractError("BlendShape 需要自己的形变消费者")
    indices = data.get("m_Indices")
    if not isinstance(indices, list) or not indices:
        raise MeshContractError("Mesh 缺少实际索引数组")
    for value in indices:
        _integer(value, "Mesh 索引")
    sections = data.get("m_SubMeshes")
    if not isinstance(sections, list) or not sections:
        raise MeshContractError("Mesh 缺少真实子网格")
    # 当前转换 JSON 不保留索引格式；不能猜 firstByte 的字宽。
    # 已证的单三角形子网格可完整核对，其它布局仍保留明确拒绝。
    if len(sections) != 1 or sections[0].get("firstByte") != 0:
        raise MeshContractError("多子网格索引字宽/范围尚无准确消费契约")
    section = sections[0]
    base = _integer(section.get("baseVertex"), "baseVertex")
    size = _integer(section.get("indexCount"), "indexCount", 1)
    if section.get("topology") != "Triangles" or size != len(indices) or size % 3:
        raise MeshContractError("需要完整三角形子网格及匹配索引范围")
    if any(i + base >= count for i in indices):
        raise MeshContractError("Mesh 索引超出实际顶点范围")
    channels = {}
    for key, widths in [("m_Normals", (3, 4)), ("m_Tangents", (4,)), ("m_Colors", (4,)),
                        *(("m_UV%d" % i, (2,)) for i in range(8))]:
        values = data.get(key)
        if values is None or values == []:
            continue
        _numbers(values, key)
        if len(values) not in [count * width for width in widths]:
            raise MeshContractError(key + " 数量与顶点数不一致")
        channels[key] = len(values) // count
    if not isinstance(entry.get("coordinateConversion"), str) or not entry["coordinateConversion"]:
        raise MeshContractError("已转换网格缺少明确坐标约定")
    return {"source_json": str(files[0]), "vertex_count": count, "index_count": size,
            "submeshes": sections, "vertex_channels": channels,
            "coordinate_conversion": entry.get("coordinateConversion")}


def _transform(path_nodes, clip):
    for node in path_nodes:
        for field, axes in (("pos", "xyz"), ("rot", "xyzw"), ("scale", "xyz")):
            _numbers([node[field][a] for a in axes], node["name"] + "." + field)
        q = node["rot"]
        if abs(sum(q[a] ** 2 for a in "xyzw") - 1.0) > .001:
            raise MeshContractError(node["name"] + " 源旋转不是单位四元数")
    chain = FN.node_chain(None, path_nodes, clip, "System.Age")
    if getattr(chain, "sheared", False):
        raise MeshContractError("静态 Mesh 完整几何的切变尚无矩阵消费路径")
    return {"space": "prefab_root_relative_unity_metres", "animated": chain.animated,
            "source_nodes": [{k: n[k] for k in ("name", "pos", "rot", "scale")} for n in path_nodes],
            "position_hlsl": chain.pos_h(), "rotation_hlsl": chain.quat_h(),
            "scale": list(chain.S), "temporaries": chain.temps,
            "root_actor_binding": "unresolved"}


def inspect(node, path_nodes, deps, clip=None):
    """准备一个静态源组件契约；不授予材质编译、播放或资产写入能力。

    @param path_nodes 从预制体根的子节点到此节点；根位姿属于生成消费者。
    @param deps 既有 v2 依赖描述，不读取不透明脚本、Shader 程序或 Raw。
    @param clip 已有 Legacy Animation 消费器的结果，沿现 System.Age 表达式。
    @return inspection_only 契约；保留所有材质槽，不合并相同 PPtr。
    """
    types = [c.get("type") for c in node.get("components", [])]
    if not node.get("componentListProof") or types.count("MeshFilter") != 1 or types.count("MeshRenderer") != 1:
        raise MeshContractError("需要明确且唯一的源 MeshFilter/MeshRenderer 组件证明")
    mesh = node.get("mesh")
    if not isinstance(mesh, dict) or mesh.get("enabled") is not True:
        raise MeshContractError("缺少启用 MeshRenderer 的已解码描述")
    pid, entry = _dependency(deps, mesh.get("mesh"), "Mesh")
    geometry = _geometry(entry)
    pointers = mesh.get("materials")
    if not isinstance(pointers, list) or not pointers:
        raise MeshContractError("启用 MeshRenderer 缺少实际材质槽")
    materials = []
    for slot, pointer in enumerate(pointers):
        material_pid, material = _dependency(deps, pointer, "Material")
        materials.append({"slot": slot, "submesh": 0, "pid": material_pid,
                          "source_pointer": pointer, "name": material.get("name"), "cab": material.get("cab")})
    # Unity 2019.4 MeshRenderer：多出的材质槽依次重绘最后一个子网格。
    # https://docs.unity3d.com/2019.4/Documentation/Manual/class-MeshRenderer.html
    return {"kind": "static_mesh_renderer_source_contract", "render_preflight": "inspection_only",
            "mesh": {"pid": pid, "name": entry.get("name"), "cab": entry.get("cab"), **geometry},
            "materials": materials, "transform": _transform(path_nodes, clip),
            "required_consumers": ["MeshRenderer geometry/material-slot execution",
                                   "matching source material program and renderer runtime parameters",
                                   "original prefab root binding and Follow/Fade/stop lifecycle"]}
