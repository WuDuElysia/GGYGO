"""@file build_bh3_kevin_fx.py
@brief Kevin 原创 FX 配方与 create-only 制作入口；默认 CLI 仅输出离线计划。

Root 在已分配的标准 Editor 制作窗调用 iter_apply(plan, mcp, unreal,
approved_packages)。复用现有 Niagara 作者桥及宿主资源边界，不启动 Editor、
不播放、不接 Montage、不修改现有资产；失败的新包保留现场。
原图只提供冰火配色/轮廓参考，所有粒子、材质、参数均为项目创作。
"""
import argparse
import copy
import hashlib
import importlib
import json
import math
import re
import sys
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[1] / "Assets/BH3/KevinDemonBattle/BH3_Kevin_FX_Config.json"
ROOT = "/Game/Characters/Boss/Kevin/DemonBattle/FX/"
PLANE = "/Engine/BasicShapes/Plane.Plane"
SHAPES = {"halo": 0, "facet": 1, "streak": 2, "ribbon": 3, "warning": 4, "broken_ring": 5}
MASK_CODE = """
float2 p = UV * 2.0 - 1.0;
float r = length(p);
float aa = max(fwidth(r), 0.003);
float edge = max(Control.y, 0.025);
float ring = 1.0 - smoothstep(edge, edge + aa, abs(r - (1.0-edge)));
float disc = 1.0 - smoothstep(0.0, 1.0, r);
float theta = atan2(p.y, p.x);
if (Shape < 0.5) return disc*disc;
if (Shape < 1.5) return 1.0 - smoothstep(0.72, 1.0, abs(p.x)*1.6 + abs(p.y));
if (Shape < 2.5) return pow(saturate(1.0-abs(p.x)), 2.0) * saturate(1.0-abs(p.y));
if (Shape < 3.5) return pow(saturate(1.0-abs(p.y)), 1.8);
float sector = 1.0-smoothstep(Control.x*0.5-aa, Control.x*0.5+aa, abs(theta));
if (Shape < 4.5) {
    if (Control.z > 1.5) {
        float rim = 1.0-smoothstep(1.0-edge, 1.0, max(abs(p.x), abs(p.y)));
        float inner = 1.0-smoothstep(1.0-edge*2.0, 1.0-edge, max(abs(p.x), abs(p.y)));
        return saturate(rim-inner)*0.9 + rim*0.07;
    }
    float border = Control.z > 0.5 ?
        1.0-smoothstep(edge, edge+aa, abs(abs(theta)-Control.x*0.5)*r) : 0.0;
    float fill = (1.0-smoothstep(0.96, 1.0, r))*0.055;
    return saturate((ring + border*(1.0-smoothstep(0.97,1.0,r)) + fill)*sector);
}
float fracture = smoothstep(0.12, 0.22, abs(sin(theta*6.0 + r*1.8)));
return ring * fracture * sector;
"""


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value, positive=False):
    return type(value) in (int, float) and math.isfinite(value) and (value > 0 if positive else True)


def signature(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()[:12]


def asset_path(folder, name, recipe):
    return ROOT + folder + "/" + name + "_" + signature(recipe)


def object_path(package):
    return package + "." + package.rsplit("/", 1)[1]


def load_helper(name):
    """仅在同步导入期间抑制共享源码的pyc写入，原Python标志/搜索路径完整归还。"""
    previous_flag, previous_path = sys.dont_write_bytecode, list(sys.path)
    try:
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        return importlib.import_module(name)
    finally:
        sys.dont_write_bytecode = previous_flag
        sys.path[:] = previous_path


def load_config(path=CONFIG):
    config = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    require(config["schema"] == "GGYGO.KevinFX/v1" and config["authorship"] == "project_authored",
            "需要明确的 Kevin 项目原创配置")
    require(config["asset_root"] + "/" == ROOT, "制作范围必须是 Kevin 独立 FX 根")
    for palette in config["palettes"].values():
        require(all(len(palette[k]) == 3 and all(finite(v) and v >= 0 for v in palette[k])
                    for k in ("color_linear", "core_linear")), "配色必须是有限非负线性RGB")
    for key, effect in config["effects"].items():
        require(re.fullmatch(r"[A-Za-z][A-Za-z0-9]+", key) is not None, "无效效果键: " + key)
        require(effect["anchor"] in ("weapon", "root", "ground", "impact", "projectile"), "效果缺明确挂点用途: " + key)
        require(1 <= len(effect["layers"]) <= 3, "每效果限1至3层: " + key)
        for layer in effect["layers"]:
            require(layer["kind"] in ("sprite", "ground", "ribbon") and layer["shape"] in SHAPES,
                    "不支持的明确绘制形状: " + key)
            require(layer["palette"] in config["palettes"], "配色未定义: " + key)
            require(finite(layer["life"], True) and finite(layer["gain"]) and layer["gain"] >= 0,
                    "寿命/亮度不是有限合法值: " + key)
            require(finite(layer.get("rate", 0)) and layer.get("rate", 0) >= 0,
                    "生成率无效: " + key)
            require(type(layer.get("burst", 0)) is int and layer.get("burst", 0) >= 0,
                    "爆发数无效: " + key)
            require(layer.get("rate", 0) > 0 or layer.get("burst", 0) > 0, "缺真实粒子生成: " + key)
            require(type(layer.get("loop", False)) is bool, "循环选择必须明确为布尔值")
            if layer["kind"] == "ribbon":
                require(finite(layer["width"], True) and effect["anchor"] in ("weapon", "projectile"),
                        "拖尾缺真实武器/弹体挂点")
            else:
                require(len(layer["size"]) == 2 and all(finite(v, True) for v in layer["size"]),
                        "粒子尺寸无效: " + key)
                require(all(finite(layer.get(k, 0)) for k in ("speed", "spread"))
                        and finite(layer.get("grow", 1), True), "运动/缩放参数无效: " + key)
    if config["actions"]:
        source_path = Path(path).parent / config["animation_configuration"]
        current = json.loads(source_path.read_text(encoding="utf-8-sig"))
        contracts = {
            "skill": {row["id"]: row for row in current["skill_assemblies"]},
            "presentation": {row["id"]: row for row in current.get("presentation_contracts", [])}}
        for action in config["actions"]:
            kind = action.get("contract_kind", "skill")
            skill = contracts[kind][action["action_id"]]
            duration = skill["expected_duration_seconds"]
            windows = [[row["start_seconds"], row["end_seconds"]] for row in skill.get("hit_windows", [])]
            require(action["montage"] == skill["montage"] and action["based_on_hit_windows"] == windows
                    and action["based_on_duration_seconds"] == duration
                    and action["enable_gate"] == skill.get("enable_gate", ""),
                    "Animation实际组合/窗口已变化，先更新对应FX参数: " + action["action_id"])
            if kind == "presentation":
                require(action["trigger"] == skill["trigger"] == "real_landed_only"
                        and action["movement_mode"] == skill["movement_mode"] == "presentation_only_no_CMC_curve_execution"
                        and action["section"] == skill["section"] and action["damage_mode"] == "none",
                        "落地表现必须消费真实Landed契约，不能触发CMC曲线或伤害")
            require(all(0 <= row["window_seconds"][0] < row["window_seconds"][1] <= duration
                        for row in action["phases"]), "FX相位离开原Montage范围: " + action["action_id"])
            phases = {row["phase_id"]: row for row in skill["animation_phases"]}
            require(all(all(row[field] == phases[row["phase_id"]][field]
                        for field in ("window_seconds", "timing_basis", "begin_event_tag", "end_event_tag"))
                        for row in action["phases"]), "Animation阶段合同已变化: " + action["action_id"])
    if config.get("audio_configuration"):
        audio = json.loads((Path(path).parent / config["audio_configuration"]).read_text(encoding="utf-8-sig"))
        actions = {row["action_id"]: row for row in audio["actions"]}
        for action_id, cue in config["hit_cues"].items():
            sounds = [row["target"] for row in audio["sound_cues"] if row["event_id"] == cue["audio_hit_event_id"]]
            require(actions[action_id]["hit_event_id"] == cue["audio_hit_event_id"] and sounds == [cue["sound"]],
                    "Audio真实命中声映射已变化，先更新对应Cue: " + action_id)
    return config


def geometry_parameters(geometry):
    """危险几何是 Combat 输入；返回单位平面缩放和材质解析形状，不扩大实际范围。"""
    require(geometry.get("basis") == "combat_configuration", "预警缺实际 Combat 几何来源")
    shape = geometry["shape"]
    if shape in ("circle", "sector"):
        radius = geometry["radius_cm"]
        require(finite(radius, True), "危险半径无效")
        angle = geometry["angle_degrees"] if shape == "sector" else 360.0
        require(finite(angle, True) and angle <= 360, "危险夹角无效")
        return [radius / 50.0, radius / 50.0, 1.0], [math.radians(angle), 0.035, float(shape == "sector"), 0.0]
    require(shape == "line", "只接受已制作的 circle/sector/line 几何")
    length, width = geometry["length_cm"], geometry["width_cm"]
    require(finite(length, True) and finite(width, True), "危险长宽无效")
    return [length / 100.0, width / 100.0, 1.0], [math.tau, 0.035, 2.0, 0.0]


def make_plan(config):
    """离线构造真实制作单元及播放配置；无窗口的库效果仍可单独制作。"""
    material_recipe = {"mask": MASK_CODE, "revision": config["revision"], "unlit": True}
    masters = {mode: asset_path("Materials", "M_Kevin_" + mode, {**material_recipe, "mode": mode})
               for mode in ("Additive", "Warning")}
    materials = {shape: asset_path("Materials", "MI_Kevin_" + shape,
                 {**material_recipe, "shape": shape}) for shape in SHAPES}
    plan = {"schema": "GGYGO.KevinFXAuthoring/v1", "authorship": "project_authored",
            "masters": masters, "materials": materials, "systems": {}, "action_windows": [],
            "runtime_or_visual_verified": False}
    for key, effect in config["effects"].items():
        recipe = {"effect": effect, "palettes": config["palettes"], "materials": materials,
                  "revision": config["revision"]}
        plan["systems"][key] = {"package": asset_path("Systems", "NS_Kevin_" + key, recipe),
                                "effect": copy.deepcopy(effect), "control": [math.tau, 0.035, 0.0, 0.0]}
    seen, event_pairs = set(), {}
    for action in config["actions"]:
        for phase in action["phases"]:
            key = (action["action_id"], phase["phase_id"])
            require(key not in seen, "动作/阶段键重复: " + repr(key))
            seen.add(key)
            expected_basis = ("project_real_landed_recovery_not_original_event"
                              if action.get("contract_kind") == "presentation"
                              else "project_source_FK_candidate_not_original_game_event")
            require(phase["timing_basis"] == expected_basis,
                    "不能把设计时点冒称原版时点")
            begin, end = phase["window_seconds"]
            require(finite(begin) and finite(end) and 0 <= begin < end, "FX窗口无效: " + repr(key))
            begin_tag = phase.get("begin_event_tag", config["playback"]["begin_event_tag"])
            end_tag = phase.get("end_event_tag", config["playback"]["end_event_tag"])
            require(re.fullmatch(r"Event\.Montage\.Kevin\.[A-Za-z0-9_]+\.FX\.[A-Za-z0-9_]+\.Begin", begin_tag)
                    and re.fullmatch(r"Event\.Montage\.Kevin\.[A-Za-z0-9_]+\.FX\.[A-Za-z0-9_]+\.End", end_tag),
                    "FX阶段需明确独立的Begin/End标签对")
            montage_key = action.get("montage", action["action_id"])
            used = event_pairs.setdefault(montage_key, set())
            require(not used.intersection((begin_tag, end_tag)),
                    "原Task按整Montage要求标签唯一；多相位必须声明独立标签对: " + repr(key))
            used.update((begin_tag, end_tag))
            effect = config["effects"][phase["effect"]]
            require(effect["anchor"] not in ("impact", "projectile"),
                    "真命中/真弹体效果不从Montage时间表假触发")
            system = plan["systems"][phase["effect"]]
            transform = copy.deepcopy(phase["local_transform"])
            for field in ("translation", "rotation_degrees", "scale"):
                require(len(transform[field]) == 3 and all(finite(v) for v in transform[field]), "TRS不完整")
            require(all(v > 0 for v in transform["scale"]), "不接受奇异/负缩放")
            if effect.get("geometry_required"):
                scale, control = geometry_parameters(phase["geometry"])
                require(transform["scale"] == [1, 1, 1], "危险几何缩放只由Combat尺寸写一次")
                transform["scale"] = scale
                if control != system["control"]:
                    recipe = {"base": system["package"], "control": control}
                    variant = ":".join(key)
                    system = {**copy.deepcopy(system), "control": control,
                              "package": asset_path("Systems", "NS_Kevin_" + phase["effect"], recipe)}
                    plan["systems"][variant] = system
            require(phase["space"] in ("World", "Attached"), "播放空间未指定")
            require((effect["anchor"] != "weapon" or phase["space"] == "Attached" and phase["socket_name"]),
                    "武器效果必须消费已验证的原Socket")
            plan["action_windows"].append({"action_id": key[0], "phase_id": key[1],
                "window_seconds": [begin, end], "timing_basis": phase["timing_basis"],
                "montage": action["montage"], "enable_gate": action.get("enable_gate", ""),
                "mode": "MontageWindow", "system": None,
                "system_units": [{"system": system["package"], "field_settings": {"mode": "NoCustomField"}}],
                "begin_event_tag": begin_tag, "end_event_tag": end_tag,
                "queued": True, "no_merge_on_concurrent_play": True,
                "space": phase["space"], "socket_name": phase["socket_name"], "local_transform": transform,
                "normal_stop_mode": effect["normal_stop"], "abort_stop_mode": "DestroyImmediately",
                "remote_seek_delta_seconds": config["playback"]["remote_seek_delta_seconds"],
                "remote_max_sim_time_seconds": config["playback"]["remote_max_sim_time_seconds"]})
            if action.get("contract_kind") == "presentation":
                plan["action_windows"][-1].update(trigger=action["trigger"], movement_mode=action["movement_mode"],
                                                  section=action["section"], damage_mode="none")
    plan["hit_cues"] = {action_id: {**row, "system": plan["systems"][row["effect"]]["package"],
        "package": asset_path("Cues", "GC_Kevin_" + action_id + "Hit", {"source": row,
                    "system": plan["systems"][row["effect"]]["package"]})}
        for action_id, row in config["hit_cues"].items()}
    plan["projectile_visuals"] = {key: {**copy.deepcopy(row), "system": plan["systems"][row["effect"]]["package"]}
                                  for key, row in config["projectile_visuals"].items()}
    plan["cue_search_root"] = ROOT + "Cues"
    plan["packages"] = sorted(set(masters.values()) | set(materials.values()) |
                              {row["package"] for row in plan["systems"].values()} |
                              {row["package"] for row in plan["hit_cues"].values()})
    plan["palettes"] = copy.deepcopy(config["palettes"])
    plan["required_gameplay_tags"] = sorted({row[key] for row in plan["action_windows"]
        for key in ("begin_event_tag", "end_event_tag")} | {row["tag"] for row in plan["hit_cues"].values()})
    return plan


def vector(values, kind="float3"):
    return kind + "(" + ",".join(repr(float(v)) for v in values) + ")"


def emitter_spec(index, layer, control, plan):
    """世界点拖尾不重写出生位置；运动碎片使用原 Niagara Age 作解析位置，无第二时钟。"""
    kind, life = layer["kind"], float(layer["life"])
    palette = plan["palettes"][layer["palette"]]
    color = vector([v * layer["gain"] for v in palette["color_linear"]] + [1], "float4")
    core = vector([v * layer["gain"] for v in palette["core_linear"]] + [1], "float4")
    rate = layer.get("rate", 0)
    continuous = layer.get("loop", rate > 0)
    local = layer.get("local_space", kind == "ground")
    # 地面预警保持常亮，由原作者窗销毁；轮换粒子不在寿命尾重复淡入/淡出。
    alpha = "1.0" if continuous and (kind == "ground" or local) else "saturate(1.0-Particles.NormalizedAge)"
    spawn = [["Particles.Age", "Float", "0.0"], ["Particles.NormalizedAge", "Float", "0.0"],
             ["Particles.Lifetime", "Float", repr(life)], ["Particles.Alive", "Bool", "true"],
             ["Particles.Color", "LinearColor", core], ["Particles.Velocity", "Vector", "float3(0,0,0)"],
             ["Particles.DynamicMaterialParameter", "Vector4", vector(control, "float4")]]
    shade = color if local and continuous else "lerp(%s,%s,saturate(Particles.NormalizedAge*2.0))" % (core, color)
    update = [["Particles.Color", "LinearColor", "(%s*float4(1,1,1,%s))" % (shade, alpha)]]
    common = {"name": "KevinLayer%d" % index, "path": "project_authored/" + layer["shape"],
              "local_space": local, "loop": continuous, "duration": 1.0 if continuous else life, "delay": 0,
              "rate": rate, "bursts": [[0, layer["burst"]]] if layer.get("burst") else [],
              "spawn": spawn, "update": update, "requirements": []}
    renderer = {"kind": "mesh" if kind == "ground" else "sprite", "material": plan["materials"][layer["shape"]],
                "sort": 0, "sort_mode": "None", "sort_attribute": None, "field_renderer": None,
                "additional_wpo_bounds_radius_cm": 0.0}
    if kind == "ribbon":
        spawn += [["Particles.Position", "Position", "Engine.Owner.Position"],
                  ["Particles.RibbonWidth", "Float", repr(float(layer["width"]))],
                  ["Particles.RibbonTwist", "Float", "0.0"]]
        renderer["kind"] = "kevin_weapon_ribbon"
        return {**common, "renderer": renderer}
    if kind == "ground":
        spawn += [["Particles.Position", "Position", "float3(0,0,0)"],
                  ["Particles.MeshOrientation", "Quat", "float4(0,0,0,1)"],
                  ["Particles.Scale", "Vector", vector([layer["size"][0]/100, layer["size"][1]/100, 1])]]
        size = vector([layer["size"][0]/100, layer["size"][1]/100, 1])
        update += [["Particles.Scale", "Vector", "(%s*lerp(1.0,%s,Particles.NormalizedAge))" %
                    (size, repr(float(layer.get("grow", 1))))]]
        renderer.update(mesh="/Engine/BasicShapes/Plane", pivot_offset=[0, 0, 0], pivot_space="Mesh")
    else:
        spread, speed = layer["spread"], layer["speed"]
        spawn += [["Particles.KevinAngle", "Float", "frac(float(Engine.ExecIndex)*0.61803399+System.Age*0.731)*6.2831853"],
                  ["Particles.KevinDirection", "Vector", "normalize(float3(cos(Particles.KevinAngle),sin(Particles.KevinAngle),0.3+frac(Particles.KevinAngle*1.71)))"],
                  ["Particles.KevinBirth", "Position", ("float3(0,0,0)" if local else "Engine.Owner.Position")
                   + "+Particles.KevinDirection*%s" % repr(float(spread))],
                  ["Particles.Position", "Position", "Particles.KevinBirth"],
                  ["Particles.Velocity", "Vector", "Particles.KevinDirection*%s" % repr(float(speed))],
                  ["Particles.SpriteSize", "Vector2", vector(layer["size"], "float2")],
                  ["Particles.SpriteRotation", "Float", "Particles.KevinAngle*57.2957795"]]
        # Velocity 在上面的零初值后由本形状唯一填写；保赋值批没有重复输出。
        spawn = [row for row in spawn if row[0] != "Particles.Velocity" or row[2] != "float3(0,0,0)"]
        common["spawn"] = spawn
        update += [["Particles.Position", "Position", "Particles.KevinBirth+Particles.Velocity*Particles.Age"]]
        renderer.update(facing_mode="FaceCamera", alignment="Unaligned", pivot_uv=[0.5, 0.5], subuv={"animated": False})
    return {**common, "renderer": renderer}


class KevinSession:
    """本次 Kevin create-only 包所有者；只实现既有 NiagaraBuilder 所需制作接口。"""
    def __init__(self, mcp, native, packages, approved):
        self.m, self.native = mcp, native
        self.targets, self.created, self.saved = set(packages), set(), set()
        require(self.targets == set(approved), "需要本批完整准确包写集")
        require(all(p.startswith(ROOT) and re.fullmatch(r"/Game/[A-Za-z0-9_/]+", p) for p in self.targets),
                "包写集离开 Kevin FX")
        self.check_editor()
        dirty = {str(p.get_name()) for p in native.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        require(not self.targets & dirty, "目标含用户未保存包")
        conflicts = [p for p in sorted(self.targets) if native.EditorAssetLibrary.does_asset_exist(p)]
        require(not conflicts, "保留已有版本，拒绝覆盖: " + repr(conflicts))

    def check_editor(self):
        require(self.m.tool("EditorToolset.EditorAppToolset.IsPIERunning")["returnValue"] is False,
                "只能在 Root 指定的非 PIE 资产制作窗执行")

    def begin_create(self, path):
        self.check_editor()
        require(path in self.targets and path not in self.created, "非本批或重复创建: " + path)
        require(not self.native.EditorAssetLibrary.does_asset_exist(path), "预检后已有资产出现: " + path)

    def created_asset(self, path):
        require(path in self.targets, "越界创建: " + path)
        self.created.add(path)

    def require_created(self, path):
        require(path in self.created, "不得修改已有/非自有包: " + path)

    def save(self, paths):
        self.check_editor()
        for path in paths:
            self.require_created(path)
            def save_owned():
                obj = self.native.load_asset(path)
                require(obj is not None and obj.get_path_name() == object_path(path), "保存身份不符")
                require(self.native.EditorAssetLibrary.save_loaded_asset(obj, only_if_is_dirty=False), "保存失败: " + path)
            self.m.run_native_sync("kevin_fx_save:" + path, save_owned)
            self.saved.add(path)


def build_materials(plan, session):
    """新建两种 Unlit master 及参数实例；原图作为参考，不读取/导入正文。"""
    configure_native_custom = load_helper("zzz_fx_material_ue").configure_native_custom
    u, m = session.native, session.m
    mel = u.MaterialEditingLibrary
    tools = u.AssetToolsHelpers.get_asset_tools()

    def create(path, cls, factory):
        folder, name = path.rsplit("/", 1)
        obj = tools.create_asset(name, folder, cls, factory)
        require(isinstance(obj, cls) and obj.get_path_name() == object_path(path), "新资产身份不符: " + path)
        session.created_asset(path)
        return obj

    def add(mat, cls, x, y):
        node = mel.create_material_expression(mat, cls, x, y)
        require(node is not None, "不能创建材质节点: " + cls.__name__)
        return node

    def connect(left, output, right, input_name):
        require(mel.connect_material_expressions(left, output, right, input_name), "材质输入连接失败: " + input_name)

    for mode, path in plan["masters"].items():
        session.begin_create(path)
        def author_master():
            mat = create(path, u.Material, u.MaterialFactoryNew())
            mat.set_editor_properties({"blend_mode": u.BlendMode.BLEND_ADDITIVE if mode == "Additive" else u.BlendMode.BLEND_TRANSLUCENT,
                "shading_model": u.MaterialShadingModel.MSM_UNLIT, "two_sided": True,
                "used_with_niagara_sprites": True, "used_with_niagara_mesh_particles": True,
                "used_with_niagara_ribbons": True})
            uv = add(mat, u.MaterialExpressionTextureCoordinate, -800, 0)
            color = add(mat, u.MaterialExpressionParticleColor, -800, 200)
            control = add(mat, u.MaterialExpressionDynamicParameter, -800, 400)
            shape = add(mat, u.MaterialExpressionScalarParameter, -800, 600)
            shape.set_editor_properties({"parameter_name": "Shape", "default_value": 0.0})
            mask = add(mat, u.MaterialExpressionCustom, -300, 0)
            configure_native_custom(u, mask, ["UV", "Shape", "Control"], MASK_CODE, "CMOT_Float1",
                "Kevin项目原创解析遮罩；危险几何由Combat配置",
                native_sync=lambda _label, operation: operation())
            connect(uv, "", mask, "UV")
            connect(shape, "", mask, "Shape")
            connect(control, "RGBA", mask, "Control")
            opacity = add(mat, u.MaterialExpressionMultiply, 0, 200)
            connect(mask, "", opacity, "A")
            connect(color, "A", opacity, "B")
            require(mel.connect_material_property(opacity, "", u.MaterialProperty.MP_OPACITY), "Opacity接线失败")
            require(mel.connect_material_property(color, "RGB", u.MaterialProperty.MP_EMISSIVE_COLOR), "Emissive接线失败")
            errors = mel.recompile_material(mat)
            require(errors is not None and not errors, "材质编译未通过: " + repr(errors))
            stats = mel.get_statistics(mat)
            require(stats.num_pixel_shader_instructions > 0, "材质缺有效Surface编译统计")
            return mat
        m.run_native_sync("kevin_fx_material:" + path, author_master)
        session.save([path])
    for shape, path in plan["materials"].items():
        session.begin_create(path)
        def author_instance():
            instance = create(path, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
            master = u.load_asset(plan["masters"]["Warning" if shape == "warning" else "Additive"])
            require(isinstance(master, u.Material), "缺本批准确Master")
            mel.set_material_instance_parent(instance, master)
            mel.set_material_instance_scalar_parameter_value(instance, "Shape", float(SHAPES[shape]))
            require(mel.get_material_instance_scalar_parameter_value(instance, "Shape") == SHAPES[shape], "形状参数读回失败")
        m.run_native_sync("kevin_fx_instance:" + path, author_instance)
        session.save([path])


def make_builder(session):
    """在 Kevin 作者脚本声明普通武器Ribbon，复用既有原生UniqueID配置与严格读回。"""
    load_helper("zzz_fx_niagara")
    helper = load_helper("zzz_fx_niagara_ue")
    NiagaraBuilder, COMPILE = helper.NiagaraBuilder, helper.COMPILE

    class KevinBuilder(NiagaraBuilder):
        def __init__(self):
            super().__init__(session, unreal=session.native)
            self.kevin_ribbons = []

        @staticmethod
        def validate_spec(spec):
            if spec["renderer"]["kind"] != "kevin_weapon_ribbon":
                return NiagaraBuilder.validate_spec(spec)
            require(spec["local_space"] is False and spec["loop"] is True and not spec["requirements"],
                    "武器Ribbon必须保世界出生点和原窗控制生成")
            writes = {row[0]: row[1] for row in spec["spawn"]}
            require(all(writes.get(name) == kind for name, kind in {
                "Particles.Position": "Position", "Particles.RibbonWidth": "Float", "Particles.RibbonTwist": "Float",
                "Particles.Color": "LinearColor", "Particles.Lifetime": "Float"}.items()), "Ribbon缺必要typed粒子流")
            require(not any(row[0] == "Particles.Position" for row in spec["update"]), "拖尾不能重写历史点")

        def build_renderer(self, name, renderer):
            if renderer["kind"] != "kevin_weapon_ribbon":
                super().build_renderer(name, renderer)
                return
            self.ns("SetEmitterData", emitter=self.loc(name), emitterData={"propertyValues": json.dumps(
                {"AttributesToPreserve": ["Particles.UniqueID"]})})
            added = self.ns("AddRenderer", newRendererLocation=self.loc(name),
                rendererClass={"refPath": "/Script/Niagara.NiagaraRibbonRendererProperties"})
            ref = self.loc(name, renderer=added["rendererIndex"])
            properties = {"Material": object_path(renderer["material"]), "FacingMode": "Screen", "Shape": "Plane",
                "TessellationMode": "Disabled", "bUseGPUInit": False, "MaxNumRibbons": 1,
                "PositionBinding": self.attribute_binding("Particles.Position"),
                "VelocityBinding": self.attribute_binding("Particles.Velocity"),
                "ColorBinding": self.attribute_binding("Particles.Color"),
                "NormalizedAgeBinding": self.attribute_binding("Particles.NormalizedAge"),
                "RibbonWidthBinding": self.attribute_binding("Particles.RibbonWidth"),
                "RibbonTwistBinding": self.attribute_binding("Particles.RibbonTwist"),
                "DynamicMaterialBinding": self.attribute_binding("Particles.DynamicMaterialParameter")}
            self.ns("SetRendererData", renderer=ref, rendererData={"propertyValues": json.dumps(properties)})
            self.verify_properties(properties, json.loads(self.ns("GetRendererData", rendererRef=ref)["propertyValues"]), name)
            state = self._author_tool(COMPILE+"ConfigureRibbonUniqueID", system=self.sref,
                emitterName=name, rendererIndex=ref["rendererIndex"], ribbonIdAttribute="")["returnValue"]
            self.verify_ribbon_unique_id(state, name, ref["rendererIndex"], "")
            require(state.get("bApplied") is True, "Ribbon未实际配置原生UniqueID")
            self.kevin_ribbons.append((name, ref, properties))

        def verify_renderer_bindings(self, specs):
            super().verify_renderer_bindings(specs)
            for name, ref, properties in self.kevin_ribbons:
                self.verify_properties(properties, json.loads(self.ns("GetRendererData", rendererRef=ref)["propertyValues"]), name)
                state = self._author_tool(COMPILE+"ReadRibbonUniqueIDState", system=self.sref,
                    emitterName=name, rendererIndex=ref["rendererIndex"])["returnValue"]
                self.verify_ribbon_unique_id(state, name, ref["rendererIndex"], "")
                require(state.get("bReady") is True and state.get("bInt32LinkOrderAccessorValid") is True
                        and state.get("bFloatLinkOrderAccessorValid") is False, "Ribbon编译缓存未采用真实Int32出生顺序")
    return KevinBuilder()


def gameplay_tag(native, name):
    tag = native.GameplayTag()
    require(tag.import_text('(TagName="' + name + '")') is True
            and native.GameplayTagLibrary.is_gameplay_tag_valid(tag)
            and str(native.GameplayTagLibrary.get_tag_name(tag)) == name,
            "需要原配置作者先注册真实Tag: " + name)
    return tag


def build_hit_cues(plan, session):
    """真HitResult经既有通用Cue机制分发；Kevin资源和标签属于可编辑BP资产。"""
    u = session.native
    parent = u.load_class(None, "/Script/GGYGO.GGYGOGameplayCueNotify_HitImpact")
    require(parent is not None, "缺原生通用HitImpact Cue类")
    tools = u.AssetToolsHelpers.get_asset_tools()
    for row in plan["hit_cues"].values():
        path = row["package"]
        tag = gameplay_tag(u, row["tag"])
        session.begin_create(path)
        def author_cue():
            folder, name = path.rsplit("/", 1)
            factory = u.BlueprintFactory()
            factory.set_editor_property("parent_class", parent)
            bp = tools.create_asset(name, folder, u.Blueprint, factory)
            require(isinstance(bp, u.Blueprint) and bp.get_path_name() == object_path(path), "Hit Cue创建身份不符")
            session.created_asset(path)
            generated = bp.generated_class()
            require(generated is not None, "Cue工厂未生成原类")
            cdo = u.get_default_object(generated)
            cdo.set_editor_property("GameplayCueTag", tag)
            mode_name = {"HitResult": "HIT_RESULT", "ParametersLocation": "PARAMETERS_LOCATION",
                         "TargetCenter": "TARGET_CENTER"}[row["location_mode"]]
            cdo.set_editor_property("LocationMode", getattr(u.GGYGOHitImpactLocationMode, mode_name))
            cdo.set_editor_property("NoSurfacePolicy", u.GGYGOHitImpactNoSurfacePolicy.GENERIC)
            cdo.set_editor_property("SurfaceEffects", [])
            # 两元素都是本项目显式通用命中反馈；不把无表面或未匹配表面当作原材质分流。
            cdo.set_editor_property("bAllowUnmatchedSurfaceGeneric", True)
            effect = cdo.get_editor_property("DefaultEffect")
            system = u.load_asset(row["system"])
            require(isinstance(system, u.NiagaraSystem), "Cue缺本批原NS")
            sound = u.load_asset(row["sound"]) if row["sound"] else None
            require(not row["sound"] or isinstance(sound, u.SoundBase), "Cue显式声音不存在/类型不符")
            effect.set_editor_property("ImpactEffect", system)
            effect.set_editor_property("ImpactSound", sound)
            cdo.set_editor_property("DefaultEffect", effect)
            u.BlueprintEditorLibrary.compile_blueprint(bp)
            require(bp.get_editor_property("status") == u.BlueprintStatus.BS_UP_TO_DATE, "Cue蓝图编译未干净通过")
            actual = u.get_default_object(bp.generated_class())
            require(str(u.GameplayTagLibrary.get_tag_name(actual.get_editor_property("GameplayCueTag"))) == row["tag"]
                    and actual.get_editor_property("LocationMode") == getattr(u.GGYGOHitImpactLocationMode, mode_name)
                    and actual.get_editor_property("DefaultEffect").get_editor_property("ImpactEffect") == system
                    and actual.get_editor_property("DefaultEffect").get_editor_property("ImpactSound") == sound,
                    "Cue编译后原Tag/位置模式/NS/声音读回不符")
        session.m.run_native_sync("kevin_fx_hit_cue:" + path, author_cue)
        session.save([path])
        # GameplayCueName 是引擎的 AssetRegistrySearchable 镜像；经公开 AssetData 读回实际路由键。
        cue_data = u.EditorAssetLibrary.find_asset_data(path)
        require(u.AssetRegistryHelpers.get_tag_value(cue_data, "GameplayCueName") == row["tag"],
                "Cue 保存后的 AssetRegistry 路由 Tag 不符: " + path)


def iter_apply(plan, mcp, unreal, approved_packages, *, retained_material_packages=(), retained_system_packages=()):
    """在 Root 制作窗创建批准的包，可只读复用本计划先前保存的完整材质阶段。"""
    require(plan["schema"] == "GGYGO.KevinFXAuthoring/v1", "计划schema不符")
    require(all(callable(getattr(mcp, name, None)) for name in
                ("tool", "run_native_sync", "run_niagara_authoring_batch", "is_niagara_authoring_batch_active")),
            "需要Root现有同步作者/资源边界，不自建连接或第二调度")
    retained_paths = tuple(retained_material_packages or ())
    retained = set(retained_paths)
    targets = set(plan["packages"])
    if retained:
        masters = set(plan["masters"].values())
        instances = set(plan["materials"].values())
        require(len(masters) == 2 and len(instances) == 6 and len(retained_paths) == len(retained) == 8
                and retained == masters | instances, "只读材质必须恰为本计划的两Master和六MI")
        require(len(targets) == 43 and retained <= targets, "只读材质与本窗35个写包必须合为原43包")
        targets -= retained
    retained_systems = set(retained_system_packages)
    systems_by_package = {row["package"]: row for row in plan["systems"].values()}
    require(len(retained_systems) == len(retained_system_packages)
            and retained_systems <= systems_by_package.keys(), "续作系统必须属于当前准确配方")
    targets -= retained_systems
    require(isinstance(mcp.run_native_sync("kevin_fx_plane_load", lambda: unreal.load_object(None, PLANE)),
                       unreal.StaticMesh), "缺明确只读的Engine Plane")
    session = KevinSession(mcp, unreal, targets, approved_packages)
    COMPILE = load_helper("zzz_fx_niagara_ue").COMPILE
    make_builder(session)
    require(mcp.tool(COMPILE+"AuthoringReadSupport")["returnValue"] is True,
            "原加载软件缺Niagara作者桥，未开始创建包")
    support = mcp.tool(COMPILE+"ReadRibbonUniqueIDSupport")["returnValue"]
    require(support.get("bSupported") is True and not support.get("error")
            and support.get("rendererClass") == "/Script/Niagara.NiagaraRibbonRendererProperties",
            "原软件缺真实Ribbon UniqueID支持，未开始创建包")
    require(mcp.run_native_sync("kevin_hit_cue_parent_load", lambda: unreal.load_class(
        None, "/Script/GGYGO.GGYGOGameplayCueNotify_HitImpact")) is not None, "原软件缺命中Cue父类")
    for mode in {row["location_mode"] for row in plan["hit_cues"].values()}:
        name = {"HitResult": "HIT_RESULT", "ParametersLocation": "PARAMETERS_LOCATION", "TargetCenter": "TARGET_CENTER"}[mode]
        require(hasattr(unreal.GGYGOHitImpactLocationMode, name), "原软件缺所选命中位置模式")
    for tag in plan["required_gameplay_tags"]:
        gameplay_tag(unreal, tag)
    for row in plan["hit_cues"].values():
        if row["sound"]:
            sound = mcp.run_native_sync("kevin_hit_audio_load:" + row["sound"], lambda: unreal.load_asset(row["sound"]))
            require(isinstance(sound, unreal.SoundBase) and sound.get_path_name() == object_path(row["sound"]),
                    "Audio所属命中SoundCue必须先制作并归还: " + row["sound"])
    if retained:
        def read_retained_material(package):
            asset = unreal.load_asset(package)
            expected_class = unreal.Material if package in masters else unreal.MaterialInstanceConstant
            require(isinstance(asset, expected_class) and asset.get_path_name() == object_path(package),
                    "已保存材质身份不符: " + package)
            _read_material_structure(package, asset, plan, unreal, {})
            _require_clean_retained_material(package, unreal)
            return asset

        for package in sorted(masters) + sorted(instances):
            asset = mcp.run_native_sync("kevin_fx_retained_material:" + package,
                                        lambda package=package: read_retained_material(package))
            if package in masters:
                _complete_retained_master(package, asset, mcp, unreal)
        yield {"stage": "materials_retained", "packages": sorted(retained)}
    else:
        build_materials(plan, session)
        yield {"stage": "materials_created", "packages": sorted(session.saved)}
    if retained_systems:
        dirty = {str(p.get_name()) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        require(not retained_systems & dirty, "续作系统含未保存改动，拒绝复用")
        helper = load_helper("zzz_fx_niagara_ue")
        call = lambda name, **args: mcp.tool(name, **args)["returnValue"]
        template = unreal.load_object(None, helper.DEFAULT_SYSTEM)
        require(isinstance(template, unreal.NiagaraSystem), "缺原 Factory System 模板")
        template_stacks = _cold_system_stacks(call, helper, helper.DEFAULT_SYSTEM)
        for package in sorted(retained_systems):
            asset = unreal.load_asset(package)
            require(isinstance(asset, unreal.NiagaraSystem) and asset.get_path_name() == object_path(package),
                    "续作系统类型或路径不符: " + package)
            _cold_system(package, systems_by_package[package], plan, call, helper, {}, template_stacks)
        yield {"stage": "systems_retained", "packages": sorted(retained_systems)}
    results, done = {}, set(retained_systems)
    for key, system in plan["systems"].items():
        if system["package"] in done:
            continue
        specs = [emitter_spec(i, row, system["control"], plan)
                 for i, row in enumerate(system["effect"]["layers"])]
        results[key] = yield from make_builder(session).iter_build_system(system["package"], specs)
        done.add(system["package"])
        yield {"stage": "system_created", "effect": key, "package": system["package"]}
    build_hit_cues(plan, session)
    require(session.saved == session.targets, "本批包尚未全部制作保存")
    return {"created_packages": sorted(session.created), "saved_packages": sorted(session.saved),
            "retained_material_packages": sorted(retained),
            "retained_system_packages": sorted(retained_systems),
            "systems": results, "action_windows": plan["action_windows"],
            "hit_cues": plan["hit_cues"], "projectile_visuals": plan["projectile_visuals"],
            "montage_written": False, "runtime_or_visual_verified": False}


def _cold_field(value, name):
    """仅折叠原生JSON成员的大小写；缺字段拒绝，不补默认值。"""
    keys = [key for key in value if key.casefold() == name.casefold()]
    require(len(keys) == 1, "Cold缺少唯一原生字段: " + name)
    return value[keys[0]]


def _cold_properties(value):
    return json.loads(_cold_field(value, "propertyValues"))


def _cold_stack(call, helper, ref, script, assignments, modules):
    """读取原有序栈及输入；这里只消费Getter，不创建Builder/作者会话。"""
    loc = {**ref, "scriptName": script}
    topology = call(helper.NS + "GetScriptStackTopology", scriptRef=loc)
    actual = _cold_field(topology, "modules")
    expected = modules + [(None, [(name, helper.NiagaraBuilder.hlsl(expr), kind)])
                          for name, kind, expr in assignments]
    require(len(actual) == len(expected), "Cold栈模块数不符: " + script)
    facts = []
    for row, (asset, inputs) in zip(actual, expected):
        name = _cold_field(row, "moduleName")
        require(_cold_field(row, "enabled") is True, "Cold发现禁用模块: " + name)
        assignment = _cold_field(row, "bIsSetParametersModule")
        require(assignment is (asset is None), "Cold模块/赋值类型不符: " + name)
        if asset is not None:
            helper.NiagaraBuilder.verify_properties({"refPath": asset}, _cold_field(row, "moduleScript"), name)
        values = call(helper.NS + "GetModuleInputValues", moduleRef={**loc, "moduleName": name})
        require(_cold_field(values, "moduleName") == name, "Cold输入原模块身份不符")
        declared = _cold_field(row, "inputs")
        entries = _cold_field(values, "inputs")
        if asset is None:
            require(len(entries) == len(inputs) == len(declared), "Cold赋值存在额外/缺失输入: " + name)
        selected = []
        for input_name, value, kind in inputs:
            found = [x for x in entries if _cold_field(x, "name") == input_name]
            schema = [x for x in declared if _cold_field(x, "name") == input_name]
            require(len(found) == len(schema) == 1, "Cold缺少唯一输入: " + name + ":" + input_name)
            helper.NiagaraBuilder.verify_properties(value, _cold_field(found[0], "value"), name + ":" + input_name)
            if kind is not None:
                helper.NiagaraBuilder.verify_properties({"classStructOrEnum": {"refPath": helper.TYPES[kind]}},
                    _cold_field(schema[0], "type"), name + ":" + input_name)
            selected.append({"schema": schema[0], "value": found[0]})
        facts.append({"module": name, "asset": _cold_field(row, "moduleScript"),
                      "assignment": assignment, "inputs": selected, "all_input_values": entries})
    return facts


def _cold_emitter_modules(spec, helper):
    nb = helper.NiagaraBuilder
    def enum(asset, member):
        return {"struct": {"refPath": helper.ENUM}, "value": {
            "enum": {"refPath": asset + "." + asset.rsplit("/", 1)[1]},
            "enumName": asset.rsplit("/", 1)[1] + "::" + member}}
    state = [("Life Cycle Mode", enum("/Niagara/Enums/ENiagaraEmitterLifeCycleMode", "NewEnumerator1"), None),
             ("Loop Behavior", enum("/Niagara/Enums/ENiagara_EmitterStateOptions",
                                    "NewEnumerator0" if spec["loop"] else "NewEnumerator1"), None),
             ("Loop Duration", nb.num("Float", spec["duration"]), None)]
    result = [("/Niagara/Modules/Emitter/EmitterState.EmitterState", state)]
    for time, count in spec["bursts"]:
        result.append(("/Niagara/Modules/Emitter/SpawnBurst_Instantaneous.SpawnBurst_Instantaneous",
                       [("Spawn Count", nb.num("Int32", count), None), ("Spawn Time", nb.num("Float", time), None)]))
    if spec["rate"] > 0:
        result.append(("/Niagara/Modules/Emitter/SpawnRate.SpawnRate",
                       [("SpawnRate", nb.num("Float", spec["rate"]), None)]))
    return result


def _cold_system_stacks(call, helper, system_ref):
    """读Factory保留的System栈语义；不比较新拷贝节点的临时GUID/对象路径。"""
    result = {}
    for script in ("SystemSpawnScript", "SystemUpdateScript"):
        ref = {"system": {"refPath": system_ref}, "scriptName": script}
        topology = call(helper.NS + "GetScriptStackTopology", scriptRef=ref)
        require(_cold_field(topology, "scriptName") == script, "Cold原System栈身份不符")
        modules = []
        for module in _cold_field(topology, "modules"):
            name = _cold_field(module, "moduleName")
            values = call(helper.NS + "GetModuleInputValues", moduleRef={**ref, "moduleName": name})
            modules.append({"enabled": _cold_field(module, "enabled"), "moduleScript": _cold_field(module, "moduleScript"),
                "assignment": _cold_field(module, "bIsSetParametersModule"), "inputs": _cold_field(values, "inputs")})
        result[script] = modules
    return result


def _cold_system(package, system, plan, call, helper, facts, template_stacks):
    ref = {"system": {"refPath": object_path(package)}}
    # 原getter允许进行合法加载/缓存初始化；不调用Complete/ForceCompile或自建等待。
    before = call(helper.COMPILE + "ReadAuthoringCompilationSettings", **ref)
    facts["compilation_settings_before"] = before
    native = call(helper.COMPILE + "ReadSystemState", **ref)
    facts["native_state"] = native
    facts["system_properties"] = _cold_properties(call(helper.NS + "GetSystemData", **ref))
    facts["system_stacks"] = _cold_system_stacks(call, helper, object_path(package))
    helper.NiagaraBuilder.verify_properties(template_stacks, facts["system_stacks"], package + ".FactorySystemStack")
    specs = [emitter_spec(i, row, system["control"], plan) for i, row in enumerate(system["effect"]["layers"])]
    specs, _ = helper.NiagaraBuilder.lower_native_emitter_specs(specs)
    summary = call(helper.COMPILE + "AuthoringGetSystemSummary", **ref)
    require(_cold_field(summary, "bSucceeded") is True and not _cold_field(summary, "error"), "Cold NS身份读取失败")
    require(_cold_field(summary, "systemPath") == object_path(package), "Cold NS原对象路径不符")
    facts["identity"] = summary
    actual_names = [_cold_field(x, "emitterName") for x in _cold_field(summary, "emitters")]
    require(actual_names == [x["name"] for x in specs], "Cold准确Emitter有序集合不符")
    variables = call(helper.NS + "GetUserVariables", **ref)["userVariables"]
    facts["user_variables"] = variables
    wpo = [x for x in variables if x["name"] == helper.NiagaraBuilder.WPO_BOUNDS_PARAMETER]
    require(len(wpo) == 1, "Cold缺唯一WPO边界参数")
    helper.NiagaraBuilder.verify_properties({"type": {"classStructOrEnum": {"refPath": helper.TYPES["Float"]}},
        "defaultValue": helper.NiagaraBuilder.num("Float", 0.0)}, wpo[0], package)
    emitters = facts["emitters"] = []
    for spec in specs:
        name, rd = spec["name"], spec["renderer"]
        emitter = {"name": name, "stacks": {}}
        emitters.append(emitter)
        loc = {**ref, "emitterName": name}
        data = call(helper.COMPILE + "AuthoringGetEmitterData", **loc)
        emitter["identity"] = data
        require(_cold_field(data, "bSucceeded") is True and not _cold_field(data, "error"), "Cold Emitter读取失败: " + name)
        properties = _cold_properties(data)
        helper.NiagaraBuilder.verify_properties({"Name": name, "bLocalSpace": spec["local_space"],
            "SimTarget": "CPUSim", "InterpolatedSpawnMode": "RunUpdateScript"}, properties, name)
        ids = _cold_field(properties, "bRequiresPersistentIDs")
        require(type(ids) is bool and (not spec.get("requires_persistent_ids") or ids), "Cold Persistent IDs事实缺失/不符")
        identities = call(helper.COMPILE + "AuthoringGetRendererIdentities", **loc)
        renderers = _cold_field(identities, "renderers")
        require(len(renderers) == 1, "Cold Renderer数量不是1: " + name)
        klass = {"mesh": "NiagaraMeshRendererProperties", "sprite": "NiagaraSpriteRendererProperties",
                 "kevin_weapon_ribbon": "NiagaraRibbonRendererProperties"}[rd["kind"]]
        renderer_class = "/Script/Niagara." + klass
        require(_cold_field(renderers[0], "rendererClass") == renderer_class, "Cold真实Renderer类型不符")
        renderer = call(helper.COMPILE + "AuthoringGetRendererData", **loc, rendererIndex=0)
        emitter["renderer"] = renderer
        require(_cold_field(renderer, "bSucceeded") is True and not _cold_field(renderer, "error"), "Cold Renderer属性读取失败")
        actual = _cold_properties(renderer)
        bind = helper.NiagaraBuilder.attribute_binding
        bindings = {"PositionBinding": ("Position", "Position"), "ColorBinding": ("Color", "LinearColor"),
                    "DynamicMaterialBinding": ("DynamicMaterialParameter", "Vector4")}
        expected = {"SourceMode": "Particles", "SortOrderHint": rd["sort"], "SortMode": rd["sort_mode"]}
        if rd["kind"] == "mesh":
            expected.update(Meshes=[{"Mesh": object_path(rd["mesh"]), "PivotOffset": dict(zip("xyz", rd["pivot_offset"])),
                                    "PivotOffsetSpace": rd["pivot_space"]}], bOverrideMaterials=True,
                            OverrideMaterials=[{"ExplicitMat": object_path(rd["material"])}])
            bindings.update(ScaleBinding=("Scale", "Vector"), MeshOrientationBinding=("MeshOrientation", "Quat"))
        elif rd["kind"] == "sprite":
            expected.update(Material=object_path(rd["material"]), FacingMode=rd["facing_mode"], Alignment=rd["alignment"],
                            PivotInUVSpace=dict(zip("xy", rd["pivot_uv"])), SubImageSize={"x": 1, "y": 1},
                            bSubImageBlend=False, bRemoveHMDRollInVR=False, PixelCoverageMode="Disabled")
            bindings.update(SpriteSizeBinding=("SpriteSize", "Vector2"), SpriteRotationBinding=("SpriteRotation", "Float"))
        else:
            expected = {"Material": object_path(rd["material"]), "FacingMode": "Screen", "Shape": "Plane",
                        "TessellationMode": "Disabled", "bUseGPUInit": False, "MaxNumRibbons": 1}
            bindings.update(VelocityBinding=("Velocity", "Vector"), NormalizedAgeBinding=("NormalizedAge", "Float"),
                            RibbonWidthBinding=("RibbonWidth", "Float"), RibbonTwistBinding=("RibbonTwist", "Float"))
            require(_cold_field(properties, "AttributesToPreserve") == ["Particles.UniqueID"], "Cold Ribbon未保留UniqueID")
        expected.update({key: bind("Particles." + field) for key, (field, _) in bindings.items()})
        helper.NiagaraBuilder.verify_properties(expected, actual, name + ".Renderer")
        layout = call(helper.COMPILE + "ReadEmitterDataSetAttributes", **loc)
        emitter["compiled_data_set"] = layout
        require(_cold_field(layout, "bReady") is True and not _cold_field(layout, "error"), "Cold实际编译DataSet未Ready: " + name)
        require(_cold_field(layout, "emitterHandleId") == _cold_field(data, "emitterHandleId"), "Cold DataSet原Emitter身份不符")
        attrs = {_cold_field(x, "name"): _cold_field(x, "typePath") for x in _cold_field(layout, "attributes")}
        for key, (field, kind) in bindings.items():
            require(attrs.get(field) == helper.TYPES[kind], "Cold缺真实Renderer typed DataSet: " + field)
            binding = _cold_field(actual, key)
            require(_cold_field(binding, "bBindingExistsOnSource") is True
                    and _cold_field(binding, "bIsCachedParticleValue") is True, "Cold Renderer缓存未绑定原字段: " + key)
        if rd["kind"] == "sprite":
            motion = call(helper.COMPILE + "ReadSpriteMotionState", **loc, rendererIndex=0)
            emitter["sprite_native_bindings"] = motion
            require(_cold_field(motion, "bReady") is True and not _cold_field(motion, "error")
                    and _cold_field(motion, "emitterHandleId") == _cold_field(data, "emitterHandleId")
                    and _cold_field(motion, "rendererPath") == _cold_field(renderer, "rendererPath")
                    and _cold_field(motion, "rendererClass") == renderer_class
                    and _cold_field(motion, "sourceMode") == "Particles", "Cold Sprite实际编译身份未闭合")
            current = {_cold_field(row, "propertyName"): row for row in _cold_field(motion, "currentBindings")}
            for key in ("PositionBinding", "SpriteSizeBinding", "SpriteRotationBinding"):
                row = current[key]
                field, kind = bindings[key]
                require(_cold_field(row, "attribute") == "Particles." + field
                        and _cold_field(row, "dataSetAttribute") == field
                        and _cold_field(row, "typePath") == helper.TYPES[kind]
                        and _cold_field(row, "bLayoutValid") is True, "Cold Sprite Native VF当前字段未有效绑定: " + key)
        for script, assignments, modules in (
            ("EmitterSpawnScript", spec.get("emitter_spawn", []), []),
            ("EmitterUpdateScript", spec.get("emitter_update", []), _cold_emitter_modules(spec, helper)),
            ("ParticleSpawnScript", spec["spawn"], []),
            ("ParticleUpdateScript", spec["update"], [("/Niagara/Modules/Update/Lifetime/ParticleState.ParticleState", [])])):
            emitter["stacks"][script] = _cold_stack(call, helper, loc, script, assignments, modules)
        ribbon = None
        if rd["kind"] == "kevin_weapon_ribbon":
            ribbon = call(helper.COMPILE + "ReadRibbonUniqueIDState", **loc, rendererIndex=0)
            emitter["ribbon_unique_id"] = ribbon
            require(_cold_field(ribbon, "bReady") is True and not _cold_field(ribbon, "error")
                    and _cold_field(ribbon, "emitterHandleId") == _cold_field(data, "emitterHandleId")
                    and _cold_field(ribbon, "rendererPath") == _cold_field(renderer, "rendererPath")
                    and _cold_field(ribbon, "uniqueIdTypePath") == helper.TYPES["Int"]
                    and _cold_field(ribbon, "bInt32LinkOrderAccessorValid") is True
                    and _cold_field(ribbon, "bFloatLinkOrderAccessorValid") is False
                    and _cold_field(ribbon, "bInt32RibbonIdAccessorValid") is False
                    and _cold_field(ribbon, "bFullRibbonIdAccessorValid") is False,
                    "Cold Ribbon真实Int32 UniqueID/原缓存未闭合")
        emitter.update({"persistent_ids_enabled": ids,
            "persistent_ids_required_by_recipe": bool(spec.get("requires_persistent_ids")),
            "renderer_class": renderer_class, "ribbon_unique_id": ribbon})
    diagnostics = call(helper.COMPILE + "ReadSystemCompileDiagnostics", **ref)
    compile_state = helper.NiagaraBuilder.compile_state_from_diagnostics(package, diagnostics)
    helper.NiagaraBuilder.verify_compile_state(package, compile_state)
    native = call(helper.COMPILE + "ReadSystemState", **ref)
    facts["native_state"] = native
    facts["compile_diagnostics"] = diagnostics
    helper.NiagaraBuilder.verify_native_compilation(package, native)
    require(_cold_field(native, "bNativeReady") is True and _cold_field(native, "bCompilationPending") is False
            and _cold_field(native, "bNeedsCompileRequest") is False and _cold_field(native, "bActiveCompilations") is False,
            "Cold当前Native未就绪，不请求编译/等待")
    after = call(helper.COMPILE + "ReadAuthoringCompilationSettings", **ref)
    require(before == after and _cold_field(after, "bSucceeded") is True
            and _cold_field(after, "bUsesRapidIterationParameters") is True, "Cold编译表示读取不符/被改变")
    facts["compilation_settings"] = after
    return facts


def _read_mi_base_overrides(asset, facts):
    overrides = asset.get_editor_property("base_property_overrides")
    facts["base_property_overrides"] = overrides.export_text()
    # 原生可把继承值写回 payload；使用真实覆盖旗标决定是否有实例覆盖。
    override_flags = (
        "bOverride_OpacityMaskClipValue", "bOverride_BlendMode", "bOverride_ShadingModel",
        "bOverride_DitheredLODTransition", "bOverride_CastDynamicShadowAsMasked", "bOverride_TwoSided",
        "bOverride_bIsThinSurface", "bOverride_OutputTranslucentVelocity", "bOverride_bHasPixelAnimation",
        "bOverride_bEnableTessellation", "bOverride_DisplacementScaling", "bOverride_bEnableDisplacementFade",
        "bOverride_DisplacementFadeRange", "bOverride_MaxWorldPositionOffsetDisplacement",
        "bOverride_CompatibleWithLumenCardSharing", "bOverride_UsageFlags",
    )
    values, errors = {}, {}
    facts["base_property_override_flags"] = values
    facts["base_property_override_read_errors"] = errors
    for name in (*override_flags, "UsageFlags"):
        expected_type = int if name in ("bOverride_UsageFlags", "UsageFlags") else bool
        try:
            value = overrides.get_editor_property(name)
        except Exception as error:
            errors[name] = f"{type(error).__name__}: {error}"
            continue
        if type(value) is not expected_type:
            errors[name] = f"需要{expected_type.__name__}，实际{type(value).__name__}"
            values[name] = repr(value)
            continue
        values[name] = value

    # bOverride_UsageFlags 是 uint32 覆盖掩码，UsageFlags 是可继承的值。
    if errors or any(values[name] for name in override_flags):
        raise ValueError("Cold MI Base存在启用覆盖或字段未完整读回: "
                         + repr({"flags": values, "read_errors": errors, "export": facts["base_property_overrides"]}))


def _read_material_structure(package, asset, plan, u, facts):
    mel = u.MaterialEditingLibrary
    props = lambda obj, names: {name: obj.get_editor_property(name) for name in names}
    if isinstance(asset, u.MaterialInstanceConstant):
        shape = next(k for k, value in plan["materials"].items() if value == package)
        parent = asset.get_editor_property("parent")
        expected_parent = plan["masters"]["Warning" if shape == "warning" else "Additive"]
        require(parent is not None and parent.get_path_name() == object_path(expected_parent), "Cold MI Parent不符")
        scalar = list(asset.get_editor_property("scalar_parameter_values"))
        require(len(scalar) == 1 and str(scalar[0].get_editor_property("parameter_info").get_editor_property("name")) == "Shape"
                and scalar[0].get_editor_property("parameter_value") == SHAPES[shape], "Cold MI Shape持久覆盖不符")
        info = scalar[0].get_editor_property("parameter_info")
        require(info.get_editor_property("association") == u.MaterialParameterAssociation.GLOBAL_PARAMETER
                and info.get_editor_property("index") == -1, "Cold MI Shape不在原Global参数域")
        require(not asset.get_editor_property("vector_parameter_values") and not asset.get_editor_property("texture_parameter_values")
                and not mel.get_static_switch_parameter_names(asset), "Cold MI存在未声明参数/静态置换")
        _read_mi_base_overrides(asset, facts)

        state = u.GGYGOMaterialAuthorLibrary.read_material_instance_resource_for_authoring(asset)
        require(isinstance(state, u.GGYGOMaterialInstanceResourceState), "MI资源未返回原生读回状态: " + repr(state))
        resource = props(state, ("readback_complete", "instance_path", "parent_path", "resource_material_path",
                                 "shader_platform", "has_static_permutation_resource", "shares_parent_resource", "error"))
        facts["material_instance_resource"] = resource
        require(resource["readback_complete"] is True and resource["instance_path"] == object_path(package)
                and resource["parent_path"] == resource["resource_material_path"] == object_path(expected_parent)
                and resource["has_static_permutation_resource"] is False and resource["shares_parent_resource"] is True
                and not resource["error"], "MI未证明共享原Parent资源且无自有静态置换: " + repr(resource))
        facts.update({"parent": parent.get_path_name(), "shape_override": SHAPES[shape], "scalar_override_count": len(scalar),
                "has_static_permutation_resource": resource["has_static_permutation_resource"],
                "shader_resource_mode": "declared_parent_without_static_permutation"})
        return facts
    require(isinstance(asset, u.Material), "Cold材质类型不是原Master或MI")
    mode = next(k for k, value in plan["masters"].items() if value == package)
    properties = props(asset, ["blend_mode", "shading_model", "two_sided", "used_with_niagara_sprites",
                               "used_with_niagara_mesh_particles", "used_with_niagara_ribbons"])
    require(properties["blend_mode"] == (u.BlendMode.BLEND_ADDITIVE if mode == "Additive" else u.BlendMode.BLEND_TRANSLUCENT)
            and properties["shading_model"] == u.MaterialShadingModel.MSM_UNLIT
            and all(properties[k] is True for k in properties if k not in ("blend_mode", "shading_model")), "Cold Master属性不符")
    classes = [u.MaterialExpressionTextureCoordinate, u.MaterialExpressionParticleColor,
               u.MaterialExpressionDynamicParameter, u.MaterialExpressionScalarParameter,
               u.MaterialExpressionCustom, u.MaterialExpressionMultiply]
    expressions = list(mel.get_material_expressions(asset))
    require(len(expressions) == len(classes), "Cold Master节点数量不符")
    nodes = []
    for klass in classes:
        found = [x for x in expressions if x.get_class() == klass.static_class()]
        require(len(found) == 1, "Cold Master缺唯一节点: " + klass.__name__)
        nodes.append(found[0])
    uv, color, control, shape, mask, multiply = nodes
    for node, names in ((uv, ["coordinate_index", "u_tiling", "v_tiling", "un_mirror_u", "un_mirror_v"]),
                        (control, ["parameter_index"])):
        defaults = u.get_default_object(node.get_class())
        require(all(node.get_editor_property(name) == defaults.get_editor_property(name) for name in names),
                "Cold UV/动态材质流偏离原生创建默认值")
    require(str(shape.get_editor_property("parameter_name")) == "Shape" and shape.get_editor_property("default_value") == 0.0,
            "Cold Master Shape定义不符")
    require(mask.get_editor_property("code") == MASK_CODE and mask.get_editor_property("output_type") == u.CustomMaterialOutputType.CMOT_FLOAT1,
            "Cold Master真实Custom代码/类型不符")
    require([str(x.get_editor_property("input_name")) for x in mask.get_editor_property("inputs")] == ["UV", "Shape", "Control"]
            and not mask.get_editor_property("additional_outputs"), "Cold Custom输入/输出声明不符")
    edges = []
    for target, sources in ((mask, [(uv, ""), (shape, ""), (control, "RGBA")]), (multiply, [(mask, ""), (color, "A")])):
        require(list(mel.get_inputs_for_material_expression(asset, target)) == [x for x, _ in sources], "Cold材质持久输入连线不符")
        for source, output in sources:
            actual = mel.get_input_node_output_name_for_material_expression(target, source)
            expected = output if output else mel.get_material_expression_output_names(source)[0]
            require(type(actual) is str and actual == expected, "Cold材质输出针不符/ABI未证")
            edges.append({"from": source.get_path_name(), "output": actual, "to": target.get_path_name()})
    for prop, source, output in ((u.MaterialProperty.MP_OPACITY, multiply, ""), (u.MaterialProperty.MP_EMISSIVE_COLOR, color, "RGB")):
        require(mel.get_material_property_input_node(asset, prop) == source, "Cold材质表面输出不符")
        actual = mel.get_material_property_input_node_output_name(asset, prop)
        require(actual == (output if output else mel.get_material_expression_output_names(source)[0]), "Cold材质表面输出针不符")
        edges.append({"from": source.get_path_name(), "output": actual, "material_property": str(prop)})
    facts.update({"properties": {k: str(v) if type(v) is not bool else v for k, v in properties.items()},
        "nodes": [{"path": n.get_path_name(), "class": n.get_class().get_path_name()} for n in nodes],
        "custom_code": mask.get_editor_property("code"), "edges": edges})
    require(not mel.get_texture_parameter_names(asset) and not mel.get_vector_parameter_names(asset)
            and {str(x) for x in mel.get_scalar_parameter_names(asset)} == {"Shape"}, "Cold Master参数集合不符")
    return facts


def _read_master_shader_map(asset, u, facts):
    """读取当前RHI已有资源。原生失败时Python丢弃out字段，具体错误留原UE日志。"""
    readiness = u.GGYGOProjectedDecalRendererProperties.read_material_compilation_for_authoring(asset)
    if not isinstance(readiness, tuple) or len(readiness) != 3:
        facts["shader_map_readback"] = readiness
        raise ValueError("当前RHI ShaderMap未取得Ready三元组，原返回为"
                         + repr(readiness) + "，详见原UE日志")
    complete, errors, error = readiness
    compile_errors = list(errors)
    facts["shader_map_readback"] = [complete, compile_errors, error]
    require(complete is True and not compile_errors and not error,
            "当前RHI ShaderMap未Ready: " + repr(facts["shader_map_readback"]))
    facts.update(current_rhi_shader_map_complete=complete, compile_errors=compile_errors)


def _require_clean_retained_material(package, u):
    dirty = {str(p.get_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    require(package not in dirty, "已保存材质有未保存改动: " + package)


def _complete_retained_master(package, asset, mcp, u):
    """仅Author完成原EditorWorld平台上该Master的现有原生派生资源。"""
    expected_material = object_path(package)

    def complete():
        world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        require(world is not None, "已保存Master编译缺原EditorWorld: " + package)
        world_path = world.get_path_name()
        state = u.GGYGOProjectedDecalRendererProperties.complete_material_compilation_for_authoring(asset, world)
        require(isinstance(state, u.GGYGOMaterialCompilationState),
                "已保存Master编译没有返回原生状态: " + repr(state))
        snapshot = state.export_text()
        # 返栈预算检查前保留原始状态，包括原生失败和实际编译错误。
        u.log("Kevin FX Author Master ShaderMap " + snapshot)
        return state, world_path, snapshot

    state, world_path, snapshot = mcp.run_native_sync("material_compilation:" + expected_material, complete)
    require(state.get_editor_property("ready") is True
            and state.get_editor_property("material_path") == expected_material
            and state.get_editor_property("resource_material_path") == expected_material
            and state.get_editor_property("world_path") == world_path
            and not state.get_editor_property("compile_errors") and not state.get_editor_property("error"),
            "已保存Master当前World原生编译未就绪: " + snapshot)

    def read_back():
        _read_master_shader_map(asset, u, {})
        _require_clean_retained_material(package, u)

    mcp.run_native_sync("kevin_fx_retained_master_shader_map:" + package, read_back)


def _cold_hit_cue(package, bp, row, u, facts):
    facts["compiled_blueprint_ready"] = isinstance(bp, u.Blueprint) and bp.get_editor_property("status") == u.BlueprintStatus.BS_UP_TO_DATE
    require(isinstance(bp, u.Blueprint) and bp.get_editor_property("status") == u.BlueprintStatus.BS_UP_TO_DATE,
            "Cold HitCue不是已持久编译的Blueprint")
    generated = bp.generated_class()
    require(generated is not None and generated.get_path_name() == object_path(package) + "_C", "Cold Cue生成类身份不符")
    parent = u.load_class(None, "/Script/GGYGO.GGYGOGameplayCueNotify_HitImpact")
    cdo, base = u.get_default_object(generated), u.get_default_object(parent)
    require(bp.get_blueprint_parent_class() == parent, "Cold Cue持久父类不符")
    tag = cdo.get_editor_property("GameplayCueTag")
    mode = {"HitResult": "HIT_RESULT", "ParametersLocation": "PARAMETERS_LOCATION", "TargetCenter": "TARGET_CENTER"}[row["location_mode"]]
    require(u.GameplayTagLibrary.is_gameplay_tag_valid(tag) and str(u.GameplayTagLibrary.get_tag_name(tag)) == row["tag"]
            and u.AssetRegistryHelpers.get_tag_value(u.EditorAssetLibrary.find_asset_data(package), "GameplayCueName") == row["tag"]
            and cdo.get_editor_property("LocationMode") == getattr(u.GGYGOHitImpactLocationMode, mode)
            and cdo.get_editor_property("NoSurfacePolicy") == u.GGYGOHitImpactNoSurfacePolicy.GENERIC
            and cdo.get_editor_property("bAllowUnmatchedSurfaceGeneric") is True
            and not cdo.get_editor_property("SurfaceEffects"), "Cold Cue Tag/位置/表面策略不符")
    effect = cdo.get_editor_property("DefaultEffect")
    system, sound = effect.get_editor_property("ImpactEffect"), effect.get_editor_property("ImpactSound")
    require(system is not None and system.get_path_name() == object_path(row["system"])
            and ((sound is None and row["sound"] is None) or sound is not None and sound.get_path_name() == object_path(row["sound"])),
            "Cold Cue持久NS/Sound引用不符")
    burst = cdo.get_editor_property("BurstEffects").export_text()
    require(burst == base.get_editor_property("BurstEffects").export_text(), "Cold Cue存在额外继承Burst表现")
    facts.update({"blueprint": bp.get_path_name(), "generated_class": generated.get_path_name(), "tag": row["tag"],
            "location_mode": str(cdo.get_editor_property("LocationMode")), "surface_policy": "Generic",
            "impact_effect": system.get_path_name(), "impact_sound": sound.get_path_name() if sound else None,
            "inherited_burst_effects": burst})
    return facts


def cold_read(plan, mcp, unreal, expected_packages):
    """新Cold进程的43包持久回读。可发生原生合法加载/缓存初始化，不编译/保存/泵帧。

    NativeReady和当前RHI ShaderMap是本次getter事实，不能外推到GPU绘制/动作/网络。
    所有关键结构及实际就绪都闭合才readback_complete；缺项逐包保留，不调用制作修复。
    """
    require(plan["schema"] == "GGYGO.KevinFXAuthoring/v1", "Cold计划schema不符")
    expected = list(expected_packages)
    require(len(expected) == len(set(expected)) and set(expected) == set(plan["packages"]), "Cold准确包集合不符")
    load_helper("zzz_fx_niagara")
    helper = load_helper("zzz_fx_niagara_ue")
    allowed = {helper.NS + x for x in ("GetScriptStackTopology", "GetModuleInputValues", "GetUserVariables", "GetSystemData")}
    allowed |= {helper.COMPILE + x for x in ("ReadAuthoringCompilationSettings", "ReadSystemState", "ReadSystemCompileDiagnostics",
        "AuthoringGetSystemSummary", "AuthoringGetEmitterData", "AuthoringGetRendererIdentities", "AuthoringGetRendererData",
        "ReadEmitterDataSetAttributes", "ReadRibbonUniqueIDState", "ReadSpriteMotionState")}
    external_failure = False
    def call(name, **arguments):
        nonlocal external_failure
        require(name in allowed, "Cold拒绝未列入的工具: " + name)
        try:
            result = mcp.tool(name, **arguments)
        except Exception:
            external_failure = True  # 原工具/资源门拒绝后不继续查询或叠加在途调用。
            raise
        require(isinstance(result, dict) and "returnValue" in result, "Cold工具没有真实同步返回")
        return result["returnValue"]
    def dirty():
        return {"content": sorted(str(p.get_name()) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()),
                "maps": sorted(str(p.get_name()) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())}
    sync = getattr(mcp, "run_native_sync", None)
    def read(label, operation):
        nonlocal external_failure
        if not callable(sync):
            return operation()
        operation_error = None
        def invoke():
            nonlocal operation_error
            try:
                return operation()
            except Exception as error:
                operation_error = error
                raise
        try:
            return sync("kevin_fx_cold:" + label, invoke)
        except Exception as error:
            if error is not operation_error:
                external_failure = True  # 同步边界前/后失败属于原资源门，不借后续资产继续执行。
            raise
    before = read("dirty_before", dirty)
    report = {"readback_complete": False, "structure_readback_complete": False, "native_readiness_complete": False,
              "errors": [], "saved": [], "assets": {}, "expected_packages": sorted(expected),
              "explicit_compile_requested": False, "frames_pumped": 0,
              "native_loading_and_data_processing_view_model_initialization_allowed": True,
              "gpu_draw_verified": False, "runtime_verified": False, "network_verified": False}
    systems = {r["package"]: r for r in plan["systems"].values()}
    cues = {r["package"]: r for r in plan["hit_cues"].values()}
    report["assets"] = {package: {"read_attempted": False, "structure_verified": False, "facts": {}} for package in expected}
    try:
        def read_template():
            template = unreal.load_object(None, helper.DEFAULT_SYSTEM)
            require(isinstance(template, unreal.NiagaraSystem) and template.get_path_name() == helper.DEFAULT_SYSTEM,
                    "Cold准确Factory System依赖不可读")
            return _cold_system_stacks(call, helper, helper.DEFAULT_SYSTEM)
        template_stacks = read("factory_system_stacks", read_template)
        report["factory_system_stack_reference"] = {"system": helper.DEFAULT_SYSTEM, "stacks": template_stacks}
    except Exception as error:
        report["errors"].append({"dependency": helper.DEFAULT_SYSTEM, "type": type(error).__name__, "error": str(error)})
        report["dirty_before"] = before
        report["dirty_after"] = None if external_failure else read("dirty_after_dependency_failure", dirty)
        report["external_boundary_failed"] = external_failure
        return report
    for package in expected:
        record = report["assets"][package]
        record["read_attempted"] = True
        try:
            def read_package():
                asset = unreal.load_asset(package)
                require(asset is not None and asset.get_path_name() == object_path(package), "Cold准确资产不存在: " + package)
                record["class"] = asset.get_class().get_path_name()
                if package in systems:
                    require(isinstance(asset, unreal.NiagaraSystem), "Cold NS类型不符")
                    record["kind"] = "niagara_system"
                    _cold_system(package, systems[package], plan, call, helper, record["facts"], template_stacks)
                elif package in cues:
                    record["kind"] = "hit_cue"
                    _cold_hit_cue(package, asset, cues[package], unreal, record["facts"])
                else:
                    record["kind"] = "material"
                    _read_material_structure(package, asset, plan, unreal, record["facts"])
                    record["structure_verified"] = True
                    if package in plan["masters"].values():
                        _read_master_shader_map(asset, unreal, record["facts"])
                    return
                record["structure_verified"] = True
            read(package, read_package)
        except Exception as error:
            report["errors"].append({"package": package, "type": type(error).__name__, "error": str(error)})
            if external_failure:
                break
    facts = {key: row["facts"] for key, row in report["assets"].items()}
    def native_ready(value):
        if not isinstance(value, dict):
            return False
        lower = {key.casefold(): item for key, item in value.items()}
        return (all(lower.get(key) is True for key in ("bsystemvalid", "bnativeready", "bvmattributesequal"))
                and all(lower.get(key) is False for key in ("bcompilationpending", "bneedscompilerequest", "bactivecompilations")))
    ready = (all(native_ready(facts[p].get("native_state")) for p in systems)
             and all(facts[p].get("current_rhi_shader_map_complete") is True for p in plan["masters"].values())
             and all(facts[p].get("shader_resource_mode") == "declared_parent_without_static_permutation" for p in plan["materials"].values())
             and all(facts[p].get("compiled_blueprint_ready") is True for p in cues))
    after = None if external_failure else read("dirty_after", dirty)
    report["dirty_before"], report["dirty_after"] = before, after
    report["external_boundary_failed"] = external_failure
    if after is not None and before != after:
        report["errors"].append({"error": "Cold读回改变了dirty集合，未保存/清理这些原对象"})
    structure = all(row["structure_verified"] is True for row in report["assets"].values()) and before == after
    report.update(readback_complete=structure and ready and not report["errors"],
                  structure_readback_complete=structure, native_readiness_complete=ready)
    return report


readback = cold_read


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    args = parser.parse_args()
    print(json.dumps(make_plan(load_config(args.config)), ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
