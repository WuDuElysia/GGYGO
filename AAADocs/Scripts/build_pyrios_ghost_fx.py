"""@file build_pyrios_ghost_fx.py
@brief 首个 03_02 静态残影的完整 UE 对应资源计划与显式宿主构建。

默认 CLI 只读。资源专项不调用完整 Prefab preflight，不获得动作准入。
所有绘制由单 NS 拥有；创建者负责预览实例的 DeactivateImmediate 和
DestroyComponent。原 cue、Root TRS、Age、Follow、动态 Fade 和 Stop 未证。
"""
import argparse
import hashlib
import itertools
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import zzz_fx_niagara as FN
import zzz_fx_mesh_renderer as MR
import zzz_unity_anim as UA
import zzz_fx_import_assets as IA
import zzz_mesh_fbx as FBX
from zzz_fx_asset_session import AssetSession, version_name
from zzz_fx_build import walk, dependency_file
from zzz_fx_niagara_ue import AS, COMPILE, NS, EmitterMeshBuilder
import nap_avatar_simple_material_plan as MP

SCHEMA = "pyrios_ghost_resource_ue_v1"
SOURCE_NAME = "Eff_Pyrois_Attack_Normal_03_02_Hit"
MESH_PID = "-5464513165259661287"
MESH_REVISION = "normal03_static_geometry_r1"
TEXTURE_PIDS = ("8348973968083319186", "-2525522941621002874", "-7386911108408904686")
POSITION_TOLERANCE_CM = .01
UV_TOLERANCE = 2e-6
COLOR_TOLERANCE = 1 / 255
NORMAL_TOLERANCE_DEGREES = .01


class NativeToolsets:
    """标准 Editor 内的公开 ToolsetRegistry 调用，避免 HTTP 回调自身 GT。

    只消费本批同步工具；不启动宿主、注册工具、泵帧或等待异步工具。
    非同步结果保留到 pending，调用者须交回实际在途状态，禁止重试叠写。
    """
    PREFIXES = ("NiagaraToolsets.NiagaraToolset_System.",
                "GGYGOEditor.GGYGONiagaraCompileLibrary.",
                "editor_toolset.toolsets.asset.AssetTools.",
                "editor_toolset.toolsets.texture.TextureTools.",
                "editor_toolset.toolsets.object.ObjectTools.")

    def __init__(self, unreal):
        if unreal is None or not hasattr(unreal, "ToolsetRegistry"):
            raise ValueError("残影原生构建需要标准 Editor 的公开 ToolsetRegistry")
        self.native, self.pending = unreal, None

    def tool(self, name, **arguments):
        if self.pending is not None:
            raise RuntimeError("残影上一次原生工具仍由本 session 持有；不重试或叠加调用")
        if not name.startswith(self.PREFIXES) and name != "EditorToolset.EditorAppToolset.IsPIERunning":
            raise ValueError("残影批次未支持的原生工具: " + name)
        toolset, method = name.rsplit(".", 1)
        result = self.native.ToolsetRegistry.execute_tool(
            toolset, method, json.dumps(arguments, ensure_ascii=False, allow_nan=False))
        if not result.is_complete:
            self.pending = result
            raise RuntimeError("残影原生工具尚未同步完成，保留在途结果，不重试: " + name)
        if result.error:
            raise RuntimeError("残影原生工具失败: " + name + " " + result.error)
        value = json.loads(result.value)
        if not isinstance(value, dict) or "returnValue" not in value:
            raise RuntimeError("残影原生工具未返回准确结果对象: " + name)
        return value


class ReadOnlyToolsets:
    """验证阶段仅准许准确 getter；即使后继误用 Builder 也不能写包。"""
    TOOLS = {NS + name for name in (
        "GetSystemSummary", "GetSystemData", "GetEmitterTopology", "GetEmitterData",
        "GetModuleInputValues", "GetRendererData", "GetSystemCompileState")}
    TOOLS |= {COMPILE + "ReadSystemState", AS + "exists",
              "EditorToolset.EditorAppToolset.IsPIERunning"}

    def __init__(self, client):
        if client is None:
            raise ValueError("残影只读验证需要显式工具接口")
        self.client = client

    def tool(self, name, **arguments):
        if name not in self.TOOLS:
            raise ValueError("残影只读验证拒绝修改或未支持的工具: " + name)
        return self.client.tool(name, **arguments)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def ue_vector(values, scale=1):
    """既有 Niagara 源空间契约 C=(-X,Z,Y)，原生导入仍须实际读回证明。"""
    x, y, z = values
    return [-x * scale, z * scale, y * scale]


def geometry_corners(data):
    """@return 按源三角形绕序保留的完整角点；不焊接或重建几何。"""
    channels = [i for i in range(8) if data.get("m_UV%d" % i)]
    count = data["m_VertexCount"]
    normal_width = len(data["m_Normals"]) // count
    vertices = []
    for i in range(count):
        n = ue_vector(data["m_Normals"][i * normal_width:i * normal_width + 3])
        length = math.sqrt(sum(v * v for v in n))
        if length <= 1e-12:
            raise ValueError("残影源法线无效: " + str(i))
        vertices.append({"position": ue_vector(data["m_Vertices"][i * 3:i * 3 + 3], 100),
                         "normal": [v / length for v in n],
                         "color": data["m_Colors"][i * 4:i * 4 + 4],
                         "uv": [[data["m_UV%d" % c][i * 2], 1 - data["m_UV%d" % c][i * 2 + 1]]
                                for c in channels]})
    base = data["m_SubMeshes"][0]["baseVertex"]
    indices = data["m_Indices"]
    return channels, [[vertices[indices[k + j] + base] for j in range(3)]
                      for k in range(0, len(indices), 3)]


def resource_bounds(contract, data, outline_width_cm):
    nodes = contract["transform"]["source_nodes"]
    chain = FN.node_chain(None, nodes, None, "System.Age")
    p, q = ue_vector(chain.P, 100), [-chain.Q[0], chain.Q[2], chain.Q[1], chain.Q[3]]
    scale = [chain.S[0], chain.S[2], chain.S[1]]
    _, triangles = geometry_corners(data)
    positions = []
    for triangle in triangles:
        for corner in triangle:
            offset = FN.qrot(q, [v * s for v, s in zip(corner["position"], scale)])
            positions.append([v + o for v, o in zip(p, offset)])
    # WPO 的公开 UE 参数按世界厘米外扩；固定 bounds 同时覆盖表面和描边。
    padding = outline_width_cm + POSITION_TOLERANCE_CM
    return {"min": [min(p[i] for p in positions) - padding for i in range(3)],
            "max": [max(p[i] for p in positions) + padding for i in range(3)]}


def make_plan(prefab_source, dependency_source, *, revision, ue_parameters=None, mesh_source=None,
              mesh_winding="reflected", mesh_revision=None):
    """@return 包含导入、材质、源槽实际绘制、固定 bounds 的只读机器计划。
    @param revision 公开 UE 资源版本；不是原动作或素材游戏版本。
    @param mesh_source 调用者明确提供的转换 FBX；不自动转换或替换旧文件。
    @param mesh_winding reflected 保留普通 FBX 转换；source 为本 UE 网格的原索引绕序。
    @param mesh_revision 显式网格资源版本；省略时保留既有版本与目标，不覆盖失败产物。
    """
    if mesh_winding not in ("reflected", "source") or (mesh_winding == "source" and mesh_source is None):
        raise ValueError("残影源绕序需要明确转换 FBX；不修改旧来源的消费方式")
    if mesh_revision is not None and (not isinstance(mesh_revision, str) or not mesh_revision.strip()):
        raise ValueError("显式网格资源版本必须为非空字符串")
    prefab, deps = read(prefab_source), read(dependency_source)
    if prefab.get("schemaVersion") != 2 or prefab.get("name") != SOURCE_NAME:
        raise ValueError("本资源专项只接受已定位的 Normal_03_02，不扩其它根")
    root = prefab["root"]
    animation = root.get("animation")
    if (not animation or animation.get("playAutomatically") is not True
            or animation.get("wrapMode") not in (0, 1)
            or animation["default"] not in animation["clips"]):
        raise ValueError("默认 Legacy 来源尚未具备准确消费契约")
    clip_file = dependency_file(deps, animation["default"]["m_PathID"], ".anim")
    clip = UA.load(clip_file)
    if clip["wrap"] not in (0, 1) or clip["float"]:
        raise ValueError("默认 Legacy 动态属性/循环尚无资源消费者")
    rows = [(node, path) for node, path, active in walk(root) if active and node.get("mesh")]
    if len(rows) != 1:
        raise ValueError("首残影需要唯一已定位 MeshRenderer；其它组件不自动准入")
    node, path = rows[0]
    contract = MR.inspect(node, path, deps, clip)
    if contract["mesh"]["pid"] != MESH_PID or contract["transform"]["animated"]:
        raise ValueError("本资源仅支持已证固定 002 姿态，不猜原动作点时钟")
    if mesh_winding == "source":
        # 原 FbxFactory SourceModel 的坐标读回为 C=(-X,Z,Y)，索引按文件保留。
        # 因此本消费契约在导出端保留源绕序，全部属性一同映射，不重排读回。
        contract["mesh"]["coordinate_conversion"] = (
            "UE FbxFactory C=(-X,Z,Y), preserve Unity triangle winding; FBX Y-up position/normal "
            "reflect X, positions x100 cm; all attributes follow exported corners")
    channels = contract["mesh"]["vertex_channels"]
    if any(k not in channels for k in ("m_Normals", "m_Tangents", "m_Colors", "m_UV0", "m_UV2")):
        raise ValueError("残影必需源顶点流不完整")
    mesh_override = {MESH_PID: Path(mesh_source).resolve()} if mesh_source is not None else None
    mesh_import = IA.plan_imports([dependency_source], revision=MESH_REVISION if mesh_revision is None else mesh_revision,
                                 selected_pids=[MESH_PID],
                                 mesh_sources=mesh_override)
    textures = IA.plan_imports([dependency_source], revision=revision, selected_pids=TEXTURE_PIDS)
    material_pids = {m["pid"] for m in contract["materials"]}
    if material_pids != {MP.MATERIAL_PID}:
        raise ValueError("源材质槽未由本次 NapAvatarSimple 消费者准确覆盖")
    material_file = deps[MP.MATERIAL_PID]["nativeJson"]
    material_plan = MP.make_plan(material_file, dependency_source, texture_targets=textures["assets"],
                                 revision=revision, ue_parameters=ue_parameters)
    material_bindings = material_plan["bindings"][MP.MATERIAL_PID]
    transform = contract["transform"]
    spec = {"name": "GhostMesh", "source_mode": "Emitter", "local_space": True,
            "lifecycle": "owner_destroy_only", "emitter_spawn": [
                ["Emitter.GhostPosition", "Position", FN.ue_pos_h(transform["position_hlsl"])],
                ["Emitter.GhostOrientation", "Quat", FN.ue_quat_h(transform["rotation_hlsl"])],
                ["Emitter.GhostScale", "Vector", FN.ue_scale_h(FN.f3(transform["scale"]))],
                ["Emitter.GhostVelocity", "Vector", "float3(0.0, 0.0, 0.0)"]], "renderers": []}
    for source_slot in contract["materials"]:
        for role in ("outline", "surface"):
            spec["renderers"].append({"source_slot": source_slot["slot"], "source_submesh": source_slot["submesh"],
                "source_material_pid": source_slot["pid"], "role": role, "sort": len(spec["renderers"]),
                "mesh": mesh_import["assets"][MESH_PID], "material": material_bindings[role]})
    EmitterMeshBuilder.validate_specs([spec])
    data = read(contract["mesh"]["source_json"])
    params = {n: material_plan["materials"][0]["params"][n]["value"] for n in MP.UE_DEFAULTS}
    source_params = material_plan["materials"][0]["params"]
    outline_width = abs(source_params["_Outline"]["value"] * source_params["_OutlineWidth"]["value"]
                        * params["UE_OutlineWidthCm"])
    bounds = resource_bounds(contract, data, outline_width)
    EmitterMeshBuilder.validate_bounds(bounds)
    imported = {"entries": {**mesh_import["entries"], **textures["entries"]},
                "assets": {**mesh_import["assets"], **textures["assets"]},
                "targets": sorted(mesh_import["targets"] + textures["targets"])}
    files = [prefab_source, dependency_source, clip_file, contract["mesh"]["source_json"], material_file]
    files += [i["source"] for i in imported["entries"].values()]
    files += [i["native"] for i in material_plan["textures"].values()]
    source_files = {str(Path(p).resolve()): sha(p) for p in files}
    identity = {"schema": SCHEMA, "revision": revision, "specs": [spec], "bounds": bounds,
                "source_files": source_files, "material_plan": material_plan}
    system = "/Game/Characters/Player/Pyrios/FX/Skill/" + version_name("NS_" + SOURCE_NAME + "_Ghost_UE", identity)
    plan = {"schema": SCHEMA, "mode": "resource_only", "revision": revision, "ue_parameters": params,
            "prefab_source": str(Path(prefab_source).resolve()), "dependency_source": str(Path(dependency_source).resolve()),
            "source_files": source_files, "source_contract": contract, "imports": imported,
            "material_plan": material_plan, "system": system, "specs": [spec], "fixed_bounds": bounds,
            "targets": sorted(set(imported["targets"] + material_plan["targets"] + [system])),
            "ownership": {"draw_owner": "one NiagaraSystem", "instance_owner": "explicit preview caller",
                "stop": "DeactivateImmediate then DestroyComponent", "auto_finish": False,
                "source_stop": "unresolved", "preview_scale": "unit scale; bounds valid for planned material parameters"},
            "limitations": {"full_prefab_preflight": "not performed", "action_integration": "not admitted",
                "visual_calibrated": False, "source_runtime_certified": False,
                "geometry_native_verified": False, "native_tangents": "UE FBX build; original tangent execution unverified",
                "native_normals": "source normal.xyz compared; original normal.w execution unverified",
                "geometry_render_data_verified": False,
                "source_root_binding": "unresolved; prefab root serialized placement is not actor offset",
                "source_clip_length": "not cue, age binding, fade or stop",
                "unresolved": material_plan["unresolved_source_runtime"]}}
    if mesh_source is not None:
        plan["mesh_source"] = str(Path(mesh_source).resolve())
    if mesh_winding != "reflected":
        plan["mesh_winding"] = mesh_winding
    if mesh_revision is not None:
        plan["mesh_revision"] = mesh_revision
    return plan


def validate_plan(plan):
    """重新核源文件和完整计划；所有无效输入在第一笔原生调用前失败。"""
    if not isinstance(plan, dict) or plan.get("schema") != SCHEMA or plan.get("mode") != "resource_only":
        raise ValueError("未知残影资源模式；不接受动作/全 Prefab 准入")
    for path, expected in plan["source_files"].items():
        if sha(path) != expected:
            raise ValueError("资源源文件已改变: " + path)
    expected = make_plan(plan["prefab_source"], plan["dependency_source"], revision=plan["revision"],
                         ue_parameters=plan["ue_parameters"], mesh_source=plan.get("mesh_source"),
                         mesh_winding=plan.get("mesh_winding", "reflected"), mesh_revision=plan.get("mesh_revision"))
    if plan != expected:
        raise ValueError("残影完整资源计划与真实源契约不一致")
    return plan


def verify_mesh_fbx(plan):
    """导入前核对已声明 Mesh JSON 对应的规范转换文件，不解析或写出 FBX。

    复用既有转换器在内存中生成确定文本，验证全部角点属性和映射声明。
    文件换行和 UTF-8 BOM 不参与格式差异；其它转换器的格式明确未支持。
    @return 源格式证据；不代替 UE 绕序、SourceModel 或 RenderData 验证。
    """
    item = plan["imports"]["entries"][MESH_PID]
    source_json = Path(plan["source_contract"]["mesh"]["source_json"]).resolve()
    mesh_bytes = source_json.read_bytes()
    mesh_sha = hashlib.sha256(mesh_bytes).hexdigest()
    if mesh_sha != plan["source_files"][str(source_json)]:
        raise ValueError("残影 Mesh JSON 在格式检查前已改变: " + str(source_json))
    fbx_bytes = Path(item["source"]).read_bytes()
    fbx_sha = hashlib.sha256(fbx_bytes).hexdigest()
    if fbx_sha != item["identity"]["source_sha256"]:
        raise ValueError("残影 FBX 在格式检查前已改变: " + item["source"])
    winding = plan.get("mesh_winding", "reflected")
    if winding not in ("reflected", "source"):
        raise ValueError("残影 FBX 绕序合同未支持")
    expected = FBX.build(json.loads(mesh_bytes.decode("utf-8-sig")), reverse_winding=winding == "reflected")
    actual = fbx_bytes.decode("utf-8-sig").replace("\r\n", "\n")
    if actual != expected:
        raise ValueError("残影 FBX 与源 JSON 的规范角点转换合同不一致，拒绝导入；"
                         "请明确提供已核对的 --mesh-source，不覆盖旧源: " + item["source"])
    return {"source_format_verified": True, "source_fbx_sha256": fbx_sha,
            "source_json_sha256": mesh_sha,
            "canonical_text_sha256": hashlib.sha256(expected.encode("utf-8")).hexdigest(),
            "converter_sha256": sha(FBX.__file__), "mesh_winding": winding,
            "geometry_native_verified": False}


def compare_geometry(source_triangles, native_triangles):
    """逐三角匹配绕序、位置、法线、全部 UV 和 RGBA；保留重复三角数量。"""
    if len(native_triangles) != len(source_triangles):
        raise RuntimeError("残影原生三角形数量与源不同")
    cells = defaultdict(set)
    def cell(p):
        return tuple(math.floor(v / (POSITION_TOLERANCE_CM * 2)) for v in p)
    for i, triangle in enumerate(source_triangles):
        for vertex in triangle:
            cells[cell(vertex["position"])].add(i)
    remaining = set(range(len(source_triangles)))
    errors = [0., 0., 0., 0.]
    for tid, triangle in enumerate(native_triangles):
        if len(triangle) != 3:
            raise RuntimeError("残影原生角点不完整")
        c = cell(triangle[0]["position"])
        candidates = set().union(*(cells.get(tuple(a + b for a, b in zip(c, delta)), set())
                                  for delta in itertools.product((-1, 0, 1), repeat=3))) & remaining
        matched = False
        for index in sorted(candidates):
            for offset in range(3):
                metrics = [0., 0., 0., 0.]
                for j, actual in enumerate(triangle):
                    original = source_triangles[index][(j + offset) % 3]
                    streams = [("position", 3), ("normal", 3), ("color", 4)]
                    if any(len(actual[k]) != width for k, width in streams) or len(actual["uv"]) != len(original["uv"]):
                        raise RuntimeError("残影原生顶点流不完整")
                    if any(len(uv) != 2 for uv in actual["uv"]):
                        raise RuntimeError("残影原生 UV 流不完整")
                    flat = actual["position"] + actual["normal"] + actual["color"] + sum(actual["uv"], [])
                    if any(not math.isfinite(v) for v in flat):
                        raise RuntimeError("残影原生顶点流非有限数值")
                    normal_length = math.sqrt(sum(v * v for v in actual["normal"]))
                    if normal_length <= 1e-12:
                        raise RuntimeError("残影原生法线无效")
                    metrics[0] = max(metrics[0], *(abs(a - b) for a, b in zip(actual["position"], original["position"])))
                    dot = sum(a * b for a, b in zip(actual["normal"], original["normal"])) / normal_length
                    metrics[1] = max(metrics[1], math.degrees(math.acos(max(-1., min(1., dot)))))
                    metrics[2] = max(metrics[2], *(abs(a - b) for u, v in zip(actual["uv"], original["uv"]) for a, b in zip(u, v)))
                    metrics[3] = max(metrics[3], *(abs(a - b) for a, b in zip(actual["color"], original["color"])))
                if all(e <= limit for e, limit in zip(metrics, (POSITION_TOLERANCE_CM, NORMAL_TOLERANCE_DEGREES,
                                                              UV_TOLERANCE, COLOR_TOLERANCE))):
                    remaining.remove(index)
                    errors = [max(a, b) for a, b in zip(errors, metrics)]
                    matched = True
                    break
            if matched:
                break
        if not matched:
            raise RuntimeError("残影原生三角形/绕序/属性未准确匹配源: " + str(tid))
    return {"triangles": len(source_triangles), "corners": len(source_triangles) * 3,
            "max_position_error_cm": errors[0], "max_normal_angle_degrees": errors[1],
            "max_uv_error": errors[2], "max_color_error": errors[3]}


def read_geometry(unreal, item, contract):
    """显式标准宿主只读 SourceModel；失败不改 settings 或改成近似成功。"""
    mesh = unreal.load_asset(item["path"])
    if not isinstance(mesh, unreal.StaticMesh) or mesh.get_path_name() != item["path"] + "." + item["name"]:
        raise RuntimeError("残影原生网格身份不同")
    dynamic = unreal.DynamicMesh()
    options = unreal.GeometryScriptCopyMeshFromAssetOptions(
        apply_build_settings=False, request_tangents=False, use_build_scale=False)
    lod = unreal.GeometryScriptMeshReadLOD(lod_type=unreal.GeometryScriptLODType.SOURCE_MODEL, lod_index=0)
    result = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(mesh, dynamic, options, lod)
    if result != (dynamic, unreal.GeometryScriptOutcomePins.SUCCESS):
        raise RuntimeError("残影原生 SourceModel 复制失败")
    query = unreal.GeometryScript_MeshQueries
    channels, expected = geometry_corners(read(contract["mesh"]["source_json"]))
    if (query.get_has_triangle_id_gaps(dynamic) or not query.get_has_triangle_normals(dynamic)
            or not query.get_has_vertex_colors(dynamic) or query.get_num_uv_sets(dynamic) != len(channels)):
        raise RuntimeError("残影原生 SourceModel 缺少完整拓扑/法线/颜色/UV")
    def vec(v):
        return [v.x, v.y, v.z]
    triangles = []
    for tid in range(dynamic.get_triangle_count()):
        valid, *ps = query.get_triangle_positions(dynamic, tid)
        copied, *ns, has_normals = query.get_triangle_normals(dynamic, tid)
        colored, *cs, has_colors = query.get_triangle_vertex_colors(dynamic, tid)
        material_id, material_valid = unreal.GeometryScript_Materials.get_triangle_material_id(dynamic, tid)
        if not valid or copied != dynamic or colored != dynamic or not has_normals or not has_colors or not material_valid or material_id != 0:
            raise RuntimeError("残影原生角点/源 section 不完整: " + str(tid))
        uvs = []
        for channel in channels:
            u1, u2, u3, valid_uv = query.get_triangle_u_vs(dynamic, channel, tid)
            if not valid_uv:
                raise RuntimeError("残影原生 UV 不完整: " + str((tid, channel)))
            uvs.append([[v.x, v.y] for v in (u1, u2, u3)])
        triangles.append([{"position": vec(ps[i]), "normal": vec(ns[i]),
            "color": [cs[i].r, cs[i].g, cs[i].b, cs[i].a], "uv": [u[i] for u in uvs]} for i in range(3)])
    return {"mesh": item["path"], "source_fbx_sha256": item["identity"]["source_sha256"],
            "source_json_sha256": sha(contract["mesh"]["source_json"]), "source_model": True,
            "uv_channels": channels, "verified": True, **compare_geometry(expected, triangles)}


def build(plan, session, *, unreal):
    """@param session 统筹另授精确包清单、独占宿主后由调用者分配的 AssetSession。
    @param unreal 同一标准 Editor 的原生接口；本工具不启动/连接或播放 UE。
    @return 原生资源编译/保存结果；动作、可见结果与冷读须另验。
    """
    validate_plan(plan)
    if unreal is None or set(plan["targets"]) != session.targets or session.created:
        raise ValueError("需要显式标准宿主和此完整批次的全新独占 session")
    from build_nap_avatar_simple_materials import NapAvatarSimpleBuilder
    # 在第一笔导入前先核其它消费者，避免缺 API/输入时产生不必要新包。
    NapAvatarSimpleBuilder.validate_plan(plan["material_plan"])
    for api in ("GeometryScript_AssetUtils", "GeometryScript_MeshQueries", "GeometryScript_Materials"):
        if not hasattr(unreal, api):
            raise ValueError("残影必需标准原生接口不存在: " + api)
    source_format = verify_mesh_fbx(plan)
    IA.apply_imports(plan["imports"], session, unreal=unreal)
    geometry = read_geometry(unreal, plan["imports"]["entries"][MESH_PID], plan["source_contract"])
    bindings = NapAvatarSimpleBuilder(session, unreal=unreal).build(plan["material_plan"])
    if bindings != plan["material_plan"]["bindings"]:
        raise RuntimeError("残影实际材质绑定与有序源槽不同")
    compile_state = EmitterMeshBuilder(session).build_system(plan["system"], plan["specs"], fixed_bounds=plan["fixed_bounds"])
    session.save(plan["targets"])
    return {"resource_built": True, "system": plan["system"], "source_format": source_format,
            "geometry": geometry, "compile": compile_state,
            "saved": sorted(session.saved), "action_integrated": False, "visual_verified": False,
            "cold_read_verified": False, "ownership": plan["ownership"]}


def verify(plan, *, mcp, unreal):
    """只读已存在完整资源批次，不构建、编译、保存或实例化效果。

    @param mcp 调用者分配的同一标准 Editor 工具接口。
    @return 加载资源的真实读回；冷宿主、保存包字节及可见结果由调用者另证。
    原生编译/Ready 暂未收束时明确失败，不循环等待或偷偷修复。
    """
    validate_plan(plan)
    from build_nap_avatar_simple_materials import NapAvatarSimpleBuilder
    NapAvatarSimpleBuilder.validate_plan(plan["material_plan"])
    if unreal is None:
        raise ValueError("残影只读验证需要显式标准宿主")
    for api in ("GeometryScript_AssetUtils", "GeometryScript_MeshQueries", "GeometryScript_Materials"):
        if not hasattr(unreal, api):
            raise ValueError("残影必需标准原生接口不存在: " + api)
    source_format = verify_mesh_fbx(plan)
    client = ReadOnlyToolsets(mcp)
    if client.tool("EditorToolset.EditorAppToolset.IsPIERunning")["returnValue"] is not False:
        raise RuntimeError("残影资源读回需要已分配的非 PIE 窗口")
    missing = [path for path in plan["targets"]
               if client.tool(AS + "exists", path=path)["returnValue"] is not True]
    if missing:
        raise RuntimeError("残影整批资源尚未完整存在: " + ", ".join(missing))
    geometry = read_geometry(unreal, plan["imports"]["entries"][MESH_PID], plan["source_contract"])
    materials = NapAvatarSimpleBuilder(None, unreal=unreal).verify(plan["material_plan"])
    if materials["material_binding_readback_verified"] is not True or materials["bindings"] != plan["material_plan"]["bindings"]:
        raise RuntimeError("残影只读材质结果与有序源槽绑定不同")
    niagara = EmitterMeshBuilder(mcp=client).verify_system(
        plan["system"], plan["specs"], fixed_bounds=plan["fixed_bounds"])
    return {"resource_readback_verified": True, "system": plan["system"], "targets": plan["targets"],
            "source_format": source_format, "geometry": geometry, "materials": materials, "niagara": niagara,
            "cold_read_verified": False, "saved_package_bytes_verified": False,
            "action_integrated": False, "visual_verified": False, "ownership": plan["ownership"]}


def verify_in_editor(plan, *, unreal, expected_editor_pid):
    """仅在协调分配的准确宿主内读回，不启动或连接编辑器。"""
    if type(expected_editor_pid) is not int or expected_editor_pid <= 0 or os.getpid() != expected_editor_pid:
        raise ValueError("残影只读入口不在已分配的准确 Editor PID 内")
    if unreal is None or Path(unreal.Paths.project_dir()).resolve() != Path(__file__).resolve().parents[2]:
        raise ValueError("残影只读入口未加载本准确 GGYGO 工程")
    client = NativeToolsets(unreal)
    try:
        return verify(plan, mcp=client, unreal=unreal)
    except Exception as error:
        error.ghost_client = client
        raise


def build_in_editor(plan, *, unreal, approved_targets, expected_editor_pid):
    """既有标准 Editor 的显式入口；只在另授原生窗口/包清单后调用。

    @param expected_editor_pid 调用者已协调的实际宿主；不自动选择用户窗口。
    @param approved_targets 本完整机器计划另授的精确包路径，非目录通配。
    """
    validate_plan(plan)
    if type(expected_editor_pid) is not int or expected_editor_pid <= 0 or os.getpid() != expected_editor_pid:
        raise ValueError("残影原生入口不在已分配的准确 Editor PID 内")
    if unreal is None or Path(unreal.Paths.project_dir()).resolve() != Path(__file__).resolve().parents[2]:
        raise ValueError("残影原生入口未加载本准确 GGYGO 工程")
    client = NativeToolsets(unreal)
    session = None
    try:
        session = AssetSession(client, plan["targets"], approved_targets)
        return build(plan, session, unreal=unreal)
    except Exception as error:
        # 调用者保留实际新包/保存集及可能在途的原生 result，不丢失失败归属。
        error.ghost_client = client
        if session is not None:
            error.ghost_session = session
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prefab_source")
    parser.add_argument("dependency_source")
    parser.add_argument("--revision", required=True)
    parser.add_argument("--ue-parameters", type=Path)
    parser.add_argument("--mesh-source", type=Path, help="明确选择已核对的转换 FBX；不生成或覆盖源")
    parser.add_argument("--mesh-winding", choices=("reflected", "source"), default="reflected",
                        help="转换文件的明确绕序；source 需要 --mesh-source")
    parser.add_argument("--mesh-revision", help="显式新网格资源版本；省略时保留既有目标")
    args = parser.parse_args()
    try:
        plan = make_plan(args.prefab_source, args.dependency_source, revision=args.revision,
                         ue_parameters=read(args.ue_parameters) if args.ue_parameters else None,
                         mesh_source=args.mesh_source, mesh_winding=args.mesh_winding, mesh_revision=args.mesh_revision)
        verify_mesh_fbx(plan)
    except (ValueError, KeyError, OSError) as error:
        print(json.dumps({"resource_planned": False, "error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(plan, ensure_ascii=False, allow_nan=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
