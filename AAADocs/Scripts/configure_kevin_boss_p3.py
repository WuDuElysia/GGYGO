"""@file Kevin P3 场景作者入口。
@brief 预检实际场地，配置既有玩家/Encounter、主灯Tag与导航，精确保存P3。

导入不执行UE操作。Root在获准同窗调用preflight、apply、request_navigation_build、
readback、save_scene；新宿主可消费cold_read。
导航未完成时由原宿主等待原生制作，不在这里注册Tick、启动PIE或轮询。
调用方持有完整输入保护及准确备份；本入口只修改P3地图，不制作Boss/玩家资产。
"""

import copy
import hashlib
import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_P3_Scene_Config.json"
MAP = "/Game/Map/BH3/L_KevinBoss_P3"
NAV_AGENT_COUNT = 31


def require(condition, reason):
    if not condition:
        raise RuntimeError("Kevin P3：" + reason)


def receipt(path):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return dict(path=str(path), bytes=path.stat().st_size,
                sha256=digest.hexdigest())


def package_file(package):
    require(package.startswith("/Game/"), "依赖不在项目Content：" + package)
    stem = ROOT / "Content" / package.removeprefix("/Game/")
    return stem.with_suffix(".umap" if package == MAP else ".uasset")


def path_of(obj):
    return obj.get_path_name() if obj is not None else None


def xyz(value):
    return [float(value.x), float(value.y), float(value.z)]


def nav_data_config(u, actor):
    """通过原生导出读取未向 Python 暴露的 NavDataConfig。"""
    output = ROOT / "Saved/Codex/KevinBossAssembly_20261111" / (actor.get_name() + ".t3d")
    output.parent.mkdir(parents=True, exist_ok=True)
    task = u.AssetExportTask()
    for key, value in dict(object=actor, exporter=u.ObjectExporterT3D(), filename=str(output),
                           automated=True, prompt=False, replace_identical=True).items():
        task.set_editor_property(key, value)
    require(u.Exporter.run_asset_export_task(task), "导航配置原生导出失败：" + path_of(actor))
    rows = [line.strip().removeprefix("NavDataConfig=") for line in output.read_text(encoding="utf-8-sig").splitlines()
            if line.strip().startswith("NavDataConfig=")]
    require(len(rows) == 1, "导航配置原生导出缺失或重复：" + path_of(actor))
    config = u.NavDataConfig()
    require(config.import_text(rows[0]), "导航配置原生解析失败：" + path_of(actor))
    return config


def dirty(u):
    loading = u.EditorLoadingAndSavingUtils
    return sorted({p.get_name() for p in loading.get_dirty_map_packages()
                   + loading.get_dirty_content_packages()})


def read_config():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    require(cfg["schema"] == "GGYGO.KevinP3Scene/v1" and cfg["map"] == MAP, "场景配置身份不符")
    for name in ("player_spawn_xy_cm", "boss_spawn_xy_cm"):
        require(len(cfg[name]) == 2 and all(math.isfinite(v) for v in cfg[name]), name + "无效")
    require(cfg["air_clearance_cm"] >= 1730.08, "场地净空低于已知源竖向范围")
    nav = cfg["navigation"]
    for pair in [nav["center_xy_cm"], nav["extent_xy_cm"], cfg["floor_contact_z_range_cm"]] + cfg["air_footprint_xy_cm"]:
        require(len(pair) == 2 and all(math.isfinite(v) for v in pair), "场地/导航二维参数无效")
    require(all(value > 0 for value in nav["extent_xy_cm"]) and nav["below_floor_cm"] >= 0
            and cfg["floor_contact_z_range_cm"][0] < cfg["floor_contact_z_range_cm"][1], "场地/导航范围无效")
    require(cfg["air_footprint_xy_cm"] and len(nav["query_extent_cm"]) == 3
            and all(math.isfinite(value) and value > 0 for value in nav["query_extent_cm"]), "净空采样/导航查询范围无效")
    return cfg


def dependency_packages():
    """只查这张图及实际装配根的硬引用元数据，供Root组装完整父保护；不扫描Content。"""
    import unreal as u

    cfg = read_config()
    pending = [MAP] + [cfg[k].split(".")[0] for k in ("game_mode_class", "experience", "player_pawn_data",
                                                                  "boss_definition", "boss_pawn_data", "boss_pawn_class")]
    options = u.AssetRegistryDependencyOptions()
    options.set_editor_property("include_hard_package_references", True)
    for name in ("include_soft_package_references", "include_searchable_names",
                 "include_hard_management_references", "include_soft_management_references"):
        options.set_editor_property(name, False)
    registry = u.AssetRegistryHelpers.get_asset_registry()
    visited = set()
    while pending:
        package = pending.pop()
        if package in visited:
            continue
        visited.add(package)
        pending.extend(str(value) for value in registry.get_dependencies(package, options) or [])
    return sorted(visited)


def host(u, allow_map_dirty=False):
    require(not u.EditorLevelLibrary.get_pie_worlds(True), "任何PIE均须结束后才可制作场景")
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    world = editor.get_editor_world()
    require(world is not None and world.get_path_name() == MAP + ".L_KevinBoss_P3",
            "须由Root显式打开已保存P3，不在入口中换图")
    if not allow_map_dirty:
        require(MAP not in dirty(u), "P3含未归属的未保存修改，保留并拒绝制作")
    return world, u.get_editor_subsystem(u.EditorActorSubsystem)


def sources():
    return [receipt(path) for path in (Path(__file__), CONFIG,
            ROOT / "AAADocs/Scripts/restore_bh3_stage_environment.py",
            ROOT / "AAADocs/Scripts/bh3_stage_environment_source.py",
            ROOT / "AAADocs/Scripts/import_bh3_stages.py", ROOT / "Config/DefaultEngine.ini",
            ROOT / read_config()["motion_envelope_evidence"])]


def context(u, cfg, allow_map_dirty=False):
    world, editor = host(u, allow_map_dirty)
    actors = editor.get_all_level_actors()

    def selected(name, cls):
        expected = world.get_path_name() + ":PersistentLevel." + name
        matches = [actor for actor in actors if actor.get_path_name() == expected]
        require(len(matches) == 1 and isinstance(matches[0], cls)
                and matches[0].get_world() == world, "缺少指定同World对象/类型：" + expected)
        return matches[0]

    def load(package):
        obj = u.load_asset(package)
        require(obj is not None, "缺少依赖：" + package)
        return obj

    player_start = selected(cfg["player_start_actor"], u.PlayerStart)
    encounter = selected(cfg["encounter_actor"], u.GGYGOBossEncounter)
    support = selected(cfg["support_actor"], u.StaticMeshActor)
    light = selected(cfg["key_light_actor"], u.DirectionalLight)
    require(all(abs(value-1.0) < 1e-6 for actor in (player_start, encounter) for value in xyz(actor.get_actor_scale3d())),
            "出生Actor不是单位缩放，须先明确胶囊/轨迹缩放政策，不按小胶囊推导")
    require(len([a for a in actors if isinstance(a, u.PlayerStart)]) == 1,
            "PlayerStart不唯一，不自动替换其它出生点")
    require(len([a for a in actors if isinstance(a, u.GGYGOBossEncounter)]) == 1,
            "Encounter不唯一，不自动删除其它战斗入口")
    gm_class = u.load_class(None, cfg["game_mode_class"])
    require(gm_class is not None, "玩家GameMode未就绪")
    gm = u.get_default_object(gm_class)
    experience = gm.get_experience()
    require(experience is not None and path_of(experience) == cfg["experience"],
            "既有GameMode实际Experience不符：actual=" + str(path_of(experience)) + " expected=" + cfg["experience"])
    player_data = load(cfg["player_pawn_data"])
    require(player_data in list(experience.get_editor_property("SquadMembers")),
            "现有Experience未包含指定可控玩家PawnData")
    definition = load(cfg["boss_definition"])
    boss_data = load(cfg["boss_pawn_data"])
    require(isinstance(definition, u.GGYGOBossDefinition) and isinstance(boss_data, u.GGYGOPawnData),
            "BossDefinition/PawnData真实类型不符")
    initial_form = definition.get_editor_property("InitialFormTag").export_text()
    forms = [form for form in definition.get_editor_property("Forms")
             if form.get_editor_property("FormTag").export_text() == initial_form]
    require(len(forms) == 1 and forms[0].get_editor_property("AvatarPawnData") == boss_data,
            "BossAI 的初始形态与 PawnData 尚未接齐")
    boss_class = boss_data.get_editor_property("PawnClass")
    require(path_of(boss_class) == cfg["boss_pawn_class"], "Boss实际PawnClass不符")
    comp = support.static_mesh_component
    require(path_of(comp.get_editor_property("static_mesh")) == cfg["support_mesh"] + ".SM_KevinBossP3_PawnSupport",
            "自有PawnSupport网格身份不符")
    require(comp.get_collision_enabled() == u.CollisionEnabled.QUERY_ONLY
            and comp.get_collision_response_to_channel(u.CollisionChannel.ECC_PAWN) == u.CollisionResponseType.ECR_BLOCK
            and comp.get_collision_response_to_channel(u.CollisionChannel.ECC_CAMERA) == u.CollisionResponseType.ECR_IGNORE
            and not comp.get_editor_property("visible") and comp.get_editor_property("hidden_in_game"),
            "原PawnSupport碰撞/隐藏契约不符，不自动重造地面")
    key = u.Name(cfg["key_light_tag"])
    light_component = light.get_component_by_class(u.DirectionalLightComponent)
    require(light_component is not None and not light.get_editor_property("hidden")
            and light_component.get_editor_property("visible")
            and light_component.get_editor_property("affects_world")
            and light_component.get_editor_property("intensity") > 0,
            "指定原主灯未提供有效照明；不改其它灯或替换来源")
    tagged = [a for a in actors if key in [u.Name(str(t)) for t in a.get_editor_property("tags")]]
    require(all(a == light for a in tagged), "主灯Tag已被其它Actor占用")
    require([u.Name(str(t)) for t in light.get_editor_property("tags")].count(key) <= 1,
            "原主灯Tag有原生Name等价重复")
    return dict(cfg=cfg, world=world, editor=editor, actors=actors, ws=world.get_world_settings(),
                player_start=player_start, encounter=encounter, support=support, support_comp=comp,
                light=light, gm_class=gm_class, experience=experience, player_data=player_data,
                definition=definition, boss_data=boss_data, boss_class=boss_class)


def native_fields(u, ctx):
    nav_cfg = ctx["ws"].get_editor_property("NavigationSystemConfig")
    require(nav_cfg is not None and nav_cfg.get_outer() == ctx["ws"],
            "WorldSettings须有自有实例NavigationSystemConfig，不写共享CDO")
    selector = nav_cfg.get_editor_property("SupportedAgentsMask")
    nav = u.NavigationSystemV1.get_navigation_system(ctx["world"])
    require(nav is not None, "当前World没有真实NavigationSystem")
    live_selector = nav.get_editor_property("SupportedAgentsMask")
    return dict(game_mode=path_of(ctx["ws"].get_editor_property("default_game_mode")),
                definition=path_of(ctx["encounter"].get_editor_property("BossDefinition")),
                spawn_on_begin_play=ctx["encounter"].get_editor_property("bSpawnOnBeginPlay"),
                seed=ctx["encounter"].get_editor_property("EncounterSeed"),
                support_navigation=ctx["support_comp"].get_editor_property("bCanEverAffectNavigation"),
                nav_config=path_of(nav_cfg), nav_agent=str(nav_cfg.get_editor_property("DefaultAgentName")),
                nav_mask=[bool(selector.get_editor_property("bSupportsAgent" + str(i))) for i in range(NAV_AGENT_COUNT)],
                live_nav_agent=str(nav.get_editor_property("DefaultAgentName")),
                live_nav_mask=[bool(live_selector.get_editor_property("bSupportsAgent" + str(i))) for i in range(NAV_AGENT_COUNT)])


def navigation_agents(u, world, cfg, capsule):
    nav = u.NavigationSystemV1.get_navigation_system(world)
    require(nav is not None, "当前World没有真实NavigationSystem；须先明确关卡导航配置")
    profiles = list(nav.get_editor_property("SupportedAgents"))
    global_profiles = list(u.get_default_object(u.NavigationSystemV1).get_editor_property("SupportedAgents"))
    rows = [dict(index=i, name=str(p.get_editor_property("Name")),
                 radius=float(p.get_editor_property("AgentRadius")),
                 height=float(p.get_editor_property("AgentHeight"))) for i, p in enumerate(profiles)]
    global_rows = [dict(index=i, name=str(p.get_editor_property("Name")),
                        radius=float(p.get_editor_property("AgentRadius")),
                        height=float(p.get_editor_property("AgentHeight"))) for i, p in enumerate(global_profiles)]
    legacy = cfg["navigation"]["preserved_default_agent"]
    require(legacy["index"] == 0 and global_profiles, "项目SupportedAgents缺少原Default")
    # PostInitProperties同步profile实际类/PreferredNavData并回写Editor CDO；
    # 只同步本地期望结构到同一预期类，再比较全部字段，不改实际CDO。
    original_default = type(global_profiles[0])()
    expected_nav_class = original_default.get_editor_property("NavDataClass")
    require(expected_nav_class is not None, "原Default的预期导航类尚未解析")
    original_default.set_editor_property("PreferredNavData", u.SystemLibrary.get_soft_class_path(expected_nav_class))
    default_preserved = (global_rows[0] == dict(index=0, name=legacy["name"],
                                               radius=legacy["radius_cm"], height=legacy["height_cm"])
                         and global_profiles[0].export_text() == original_default.export_text())
    chosen = [row for row in rows if u.Name(row["name"]) == u.Name(cfg["navigation"]["agent_name"])]
    ready = (default_preserved and len(chosen) == 1 and chosen[0]["index"] == cfg["navigation"]["agent_index"]
             and chosen[0]["radius"] == cfg["navigation"]["agent_radius_cm"] >= capsule["radius_cm"]
             and chosen[0]["height"] == cfg["navigation"]["agent_height_cm"] >= capsule["half_height_cm"] * 2)
    return dict(profiles=rows, global_profiles=global_rows, default_preserved=default_preserved,
                actual_default=global_profiles[0].export_text(), expected_default=original_default.export_text(),
                selected=chosen[0] if len(chosen) == 1 else None, ready=ready,
                required_radius_cm=capsule["radius_cm"], required_height_cm=capsule["half_height_cm"] * 2,
                missing=None if ready else "原Default或KevinBoss实际配置不符；须新宿主读回已冻结项目配置，不改Recast实例AgentRadius")


def preflight():
    """只读真实场景/配置/胶囊查询；返回apply消费的同窗前像，不签运行通过。"""
    import unreal as u
    import restore_bh3_stage_environment as stage

    cfg = read_config()
    require(hasattr(u.PropertyAccessChangeNotifyMode, "ALWAYS"), "World导航配置的原生Always属性通知未暴露")
    for cls, methods in ((u.NavigationSystemV1, ("on_navigation_bounds_updated", "project_point_to_navigation",
                                              "find_path_to_location_synchronously", "is_navigation_being_built",
                                              "is_navigation_being_built_or_locked")),
                         (u.Actor, ("set_actor_location", "set_actor_rotation", "set_actor_scale3d", "get_actor_bounds")),
                         (u.SystemLibrary, ("execute_console_command",)),
                         (u.EditorLoadingAndSavingUtils, ("save_map",))):
        require(all(callable(getattr(cls, name, None)) for name in methods), "实际制作API未暴露：" + str(cls))
    original_dirty = dirty(u)
    ctx = context(u, cfg)
    # 原生 getter 等待该网格异步 BodySetup 释放；原生胶囊查询必须在碰撞数据就绪后执行。
    complexity = u.get_editor_subsystem(u.StaticMeshEditorSubsystem).get_collision_complexity(
        ctx["support_comp"].get_editor_property("static_mesh"))
    require(ctx["support"].get_actor_enable_collision()
            and complexity == u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE,
            "P3 支撑体未启用既定三角面 Pawn 碰撞")
    before = dict(editor_pid=os.getpid(), sources=sources(), map_file=receipt(package_file(MAP)),
                  geometry=stage.map_geometry_state(u), fields=native_fields(u, ctx), dirty=original_dirty)
    player_class = ctx["player_data"].get_editor_property("PawnClass")
    player_move, player_capsule = stage.support_capsule_cdo(u, player_class)
    boss_move, boss_capsule = stage.support_capsule_cdo(u, ctx["boss_class"])
    require(cfg["air_clearance_cm"] >= 1730.08 + 2*boss_capsule["half_height_cm"],
            "净空未包含已知竖轨及真实完整胶囊高度")
    for cls in (player_class, ctx["boss_class"]):
        capsule_component = u.get_default_object(cls).get_editor_property("CapsuleComponent")
        require(all(abs(value-1.0) < 1e-6 for value in xyz(capsule_component.get_relative_transform().scale3d)),
                "胶囊组件存在额外缩放，须按实际缩放重新制定空间配置：" + path_of(cls))
    origin, extent = ctx["support"].get_actor_bounds(False, False)
    bounds = dict(min=[a-b for a, b in zip(xyz(origin), xyz(extent))],
                  max=[a+b for a, b in zip(xyz(origin), xyz(extent))])
    support = dict(component=path_of(ctx["support_comp"]))
    spawns, issues = {}, []
    for role, movement, capsule in (("player", player_move, player_capsule), ("boss", boss_move, boss_capsule)):
        diagnostic = {}
        try:
            spawns[role] = stage.support_spawn_candidate(u, ctx["world"], support, capsule, movement,
                                                        cfg[role + "_spawn_xy_cm"], bounds, diagnostic)
            floor_z = spawns[role]["floor_sweep"]["hit"]["location_cm"][2] - capsule["half_height_cm"]
            if not cfg["floor_contact_z_range_cm"][0] <= floor_z <= cfg["floor_contact_z_range_cm"][1]:
                issues.append(dict(role=role, error="出生候选落在高台/墙顶", floor_z_cm=floor_z))
        except (RuntimeError, stage.source.SourceError) as error:
            issues.append(dict(role=role, error=str(error), diagnostic=diagnostic))
    columns = []
    for xy in cfg["air_footprint_xy_cm"]:
        point = [a+b for a, b in zip(cfg["boss_spawn_xy_cm"], xy)]
        diagnostic = {}
        try:
            ground = stage.support_spawn_candidate(u, ctx["world"], support, boss_capsule, boss_move, point, bounds, diagnostic)
        except (RuntimeError, stage.source.SourceError) as error:
            columns.append(dict(xy_cm=point, clear=False, error=str(error), diagnostic=diagnostic))
            continue
        center = ground["location_cm"]
        floor_z = ground["floor_sweep"]["hit"]["location_cm"][2] - boss_capsule["half_height_cm"]
        if not cfg["floor_contact_z_range_cm"][0] <= floor_z <= cfg["floor_contact_z_range_cm"][1]:
            columns.append(dict(xy_cm=point, clear=False, error="净空候选落在高台/墙顶，须调整场地配置", floor_z_cm=floor_z))
            continue
        top_center = center[:2] + [floor_z + cfg["air_clearance_cm"] - boss_capsule["half_height_cm"]]
        query = stage.support_sweep(u, ctx["world"], boss_capsule, boss_move, center, top_center)
        columns.append(dict(xy_cm=point, clear=query["hit"] is None, query=query))
    nav = navigation_agents(u, ctx["world"], cfg, boss_capsule)
    owner = u.Name(cfg["owner_tag"])
    volumes = [a for a in ctx["actors"] if isinstance(a, u.NavMeshBoundsVolume)]
    require(all(owner in [u.Name(str(t)) for t in a.get_editor_property("tags")] for a in volumes)
            and len(volumes) <= 1, "存在未归属或重复NavBounds，须明确原生前像后再配置")
    nav_data = [a for a in ctx["actors"] if isinstance(a, u.RecastNavMesh)]
    require(len(nav_data) <= 1 and all(u.Name(str(nav_data_config(u, a).get_editor_property("Name")))
            == u.Name(cfg["navigation"]["agent_name"]) for a in nav_data),
            "已有其它agent导航数据，先交Root核准确关卡导航迁移范围")
    dependencies = {cfg[name] for name in ("support_mesh", "experience", "player_pawn_data", "boss_definition", "boss_pawn_data")}
    dependencies.update((cfg["game_mode_class"].split(".")[0], cfg["boss_pawn_class"].split(".")[0],
                         path_of(player_class).split(".")[0]))
    before["dependencies"] = [receipt(package_file(p)) for p in sorted(dependencies)]
    require(dirty(u) == original_dirty, "只读预检引起dirty差集，保留现场，不制作/保存")
    before_bytes = len(json.dumps(before, ensure_ascii=False).encode("utf-8"))
    require(before_bytes <= cfg["native_before_max_bytes"],
            "原生前像实际" + str(before_bytes) + "B超过预留" + str(cfg["native_before_max_bytes"]) + "B，交Root核预算")
    return dict(phase="ready_for_authoring" if not issues and nav["ready"] and all(c["clear"] for c in columns) else "prerequisites_missing",
                before=before, before_bytes=before_bytes, spawns=spawns, columns=columns, navigation=nav,
                issues=issues,
                nav_bounds_actor=path_of(volumes[0]) if volumes else None,
                boss_capsule=boss_capsule, player_capsule=player_capsule,
                clearance_scope=cfg["air_clearance_scope"], actual_spawn_verified=False,
                actual_cmc_landing_verified=False, playable_verified=False)


def add_tag(u, actor, tag):
    before = list(actor.get_editor_property("tags"))
    name = u.Name(tag)
    require([u.Name(str(t)) for t in before].count(name) <= 1, "Actor Tag有原生Name重复：" + path_of(actor))
    if name not in [u.Name(str(t)) for t in before]:
        actor.modify(True)
        actor.set_editor_property("tags", before + [name])


def set_bounds(u, volume, center, extent):
    volume.modify(True)
    origin, actual = volume.get_actor_bounds(False, False)
    require(all(v > 0 for v in xyz(actual)), "原生Volume工厂未制作有效Brush，不伪造导航边界")
    scale = xyz(volume.get_actor_scale3d())
    volume.set_actor_scale3d(u.Vector(*[s*want/have for s, want, have in zip(scale, extent, xyz(actual))]))
    origin, actual = volume.get_actor_bounds(False, False)
    location = xyz(volume.get_actor_location())
    volume.set_actor_location(u.Vector(*[p+want-have for p, want, have in zip(location, center, xyz(origin))]), False, False)
    origin, actual = volume.get_actor_bounds(False, False)
    require(max(abs(a-b) for a, b in zip(xyz(origin), center)) < 1
            and max(abs(a-b) for a, b in zip(xyz(actual), extent)) < 1, "NavBounds实际范围不符")


def protect_geometry(u, stage, ctx, before):
    expected = copy.deepcopy(before["geometry"])
    actual = stage.map_geometry_state(u)
    allowed = {path_of(ctx[k]): k for k in ("player_start", "encounter", "light")}
    cfg = ctx["cfg"]
    for actor in ctx["editor"].get_all_level_actors():
        if isinstance(actor, u.NavMeshBoundsVolume) and path_of(actor) in expected["actors"]:
            require(u.Name(cfg["owner_tag"]) in [u.Name(str(t)) for t in actor.get_editor_property("tags")],
                    "已有导航边界不属于本作者")
            allowed[path_of(actor)] = "nav_bounds"
    for path in set(actual["actors"]) - set(expected["actors"]):
        actor = next(a for a in ctx["editor"].get_all_level_actors() if path_of(a) == path)
        if isinstance(actor, u.NavMeshBoundsVolume):
            require(u.Name(cfg["owner_tag"]) in [u.Name(str(t)) for t in actor.get_editor_property("tags")],
                    "新增导航边界没有本作者身份：" + path)
        else:
            require(isinstance(actor, u.RecastNavMesh)
                    and u.Name(str(nav_data_config(u, actor).get_editor_property("Name")))
                    == u.Name(cfg["navigation"]["agent_name"]), "制作新增了非指定agent导航Actor：" + path)
        del actual["actors"][path]
    for path, role in allowed.items():
        tag = u.Name(cfg["key_light_tag"] if role == "light" else cfg["owner_tag"])
        tags_before = [u.Name(value) for value in expected["actors"][path]["tags"]]
        desired = tags_before + ([tag] if tag not in tags_before else [])
        require([u.Name(value) for value in actual["actors"][path]["tags"]] == desired,
                "制作修改了声明外Tag：" + path)
        actual["actors"][path]["tags"] = expected["actors"][path]["tags"]
        if role in ("player_start", "encounter", "nav_bounds"):
            actual["actors"][path]["world_transform"] = expected["actors"][path]["world_transform"]
            actor = next(a for a in ctx["editor"].get_all_level_actors() if path_of(a) == path)
            root = path_of(actor.get_editor_property("RootComponent"))
            actual["actors"][path]["components"][root]["relative_transform"] = expected["actors"][path]["components"][root]["relative_transform"]
    stage.verify_geometry_state(actual, expected)


def apply(prepared):
    """消费ready预检及准确前像，只改P3；导航制作请求不冒充就绪或保存。"""
    import unreal as u
    import restore_bh3_stage_environment as stage

    require(prepared["phase"] == "ready_for_authoring", "预检缺口尚未收口")
    cfg = read_config()
    ctx = context(u, cfg)
    before = prepared["before"]
    require(os.getpid() == before["editor_pid"], "apply必须消费同一获准Editor的预检前像")
    require(sources() == before["sources"] and receipt(package_file(MAP)) == before["map_file"], "源码/地图前像已变化")
    require(all(receipt(item["path"]) == item for item in before["dependencies"]), "实际消费依赖已变化")
    stage.verify_geometry_state(stage.map_geometry_state(u), before["geometry"])
    require(native_fields(u, ctx) == before["fields"] and dirty(u) == before["dirty"], "原生配置/dirty前像已变化")
    require(navigation_agents(u, ctx["world"], cfg, prepared["boss_capsule"]) == prepared["navigation"],
            "原生导航agent前像已变化，须重新预检")
    ctx["ws"].modify(True)
    ctx["ws"].set_editor_property("default_game_mode", ctx["gm_class"])
    nav_cfg = ctx["ws"].get_editor_property("NavigationSystemConfig")
    selector = type(nav_cfg.get_editor_property("SupportedAgentsMask"))()
    index = prepared["navigation"]["selected"]["index"]
    require(0 <= index < NAV_AGENT_COUNT, "支持agent超关卡原生mask范围")
    for i in range(NAV_AGENT_COUNT):
        selector.set_editor_property("bSupportsAgent" + str(i), i == index)
    nav_cfg.modify(True)
    nav_cfg.set_editor_property("SupportedAgentsMask", selector)
    nav_cfg.set_editor_property("DefaultAgentName", u.Name(cfg["navigation"]["agent_name"]))
    # 嵌套字段修改不会执行Configure；通知WorldSettings原属性，由其原生
    # PostEditChangeProperty重建本World导航并筛选agent。不改CDO/引擎配置。
    ctx["ws"].set_editor_property("NavigationSystemConfig", nav_cfg,
                                 notify_mode=u.PropertyAccessChangeNotifyMode.ALWAYS)
    nav = u.NavigationSystemV1.get_navigation_system(ctx["world"])
    require(nav is not None, "原生WorldSettings配置通知未生成导航实例")
    refreshed = native_fields(u, ctx)
    require(refreshed["nav_mask"] == refreshed["live_nav_mask"] == [i == index for i in range(NAV_AGENT_COUNT)]
            and u.Name(refreshed["nav_agent"]) == u.Name(refreshed["live_nav_agent"]) == u.Name(cfg["navigation"]["agent_name"]),
            "WorldSettings原生通知未实际应用指定agent，不继续制作")
    for role, key in (("player", "player_start"), ("boss", "encounter")):
        actor = ctx[key]
        actor.modify(True)
        actor.set_actor_location(u.Vector(*prepared["spawns"][role]["location_cm"]), False, False)
        actor.set_actor_rotation(u.Rotator(pitch=0.0, yaw=cfg[role+"_spawn_yaw_deg"], roll=0.0), False)
        add_tag(u, actor, cfg["owner_tag"])
    for name, value in (("BossDefinition", ctx["definition"]), ("bSpawnOnBeginPlay", cfg["spawn_on_begin_play"]), ("EncounterSeed", cfg["encounter_seed"])):
        ctx["encounter"].set_editor_property(name, value)
    add_tag(u, ctx["light"], cfg["key_light_tag"])
    ctx["support_comp"].modify(True)
    ctx["support_comp"].set_editor_property("bCanEverAffectNavigation", True)
    volume = u.load_object(None, prepared["nav_bounds_actor"]) if prepared["nav_bounds_actor"] else None
    if volume is None:
        volume = ctx["editor"].spawn_actor_from_class(u.NavMeshBoundsVolume, u.Vector(), u.Rotator(), False)
        require(volume is not None, "原生NavBounds工厂创建失败，保留现场")
        volume.set_actor_label(cfg["navigation"]["bounds_label"])
        add_tag(u, volume, cfg["owner_tag"])
    floor = min(prepared["spawns"][role]["location_cm"][2] - prepared[role+"_capsule"]["half_height_cm"] for role in ("player", "boss"))
    low, high = floor-cfg["navigation"]["below_floor_cm"], floor+cfg["air_clearance_cm"]
    nav_center = cfg["navigation"]["center_xy_cm"] + [(low+high)/2]
    nav_extent = cfg["navigation"]["extent_xy_cm"] + [(high-low)/2]
    set_bounds(u, volume, nav_center, nav_extent)
    nav = u.NavigationSystemV1.get_navigation_system(ctx["world"])
    require(nav is not None, "关卡配置后NavigationSystem尚未就绪")
    nav.on_navigation_bounds_updated(volume)
    protect_geometry(u, stage, ctx, before)
    require(set(dirty(u)) - set(before["dirty"]) <= {MAP}, "制作出现P3以外dirty差集，保留现场，不保存")
    return dict(phase="scene_applied_navigation_build_required", prepared=prepared,
                nav_bounds_actor=path_of(volume), nav_center_cm=nav_center, nav_extent_cm=nav_extent,
                saved=False, playable_verified=False)


def request_navigation_build(applied):
    """复用已就绪/在途原生制作，否则本applied仅显式提交一次；调用方保留构建回执。"""
    import unreal as u

    require(os.getpid() == applied["prepared"]["before"]["editor_pid"], "导航制作须在原获准宿主")
    world, _ = host(u, True)
    require(sources() == applied["prepared"]["before"]["sources"], "导航制作源配置已变化")
    volume = u.load_object(None, applied["nav_bounds_actor"])
    require(isinstance(volume, u.NavMeshBoundsVolume) and volume.get_world() == world, "自有NavBounds未就绪")
    observed = readback(applied)
    if observed["phase"] == "scene_fields_and_editor_navigation_verified":
        return dict(phase="navigation_already_ready_no_build", native_readback=observed,
                    saved=False, playable_verified=False)
    if observed["phase"] == "waiting_for_native_navigation":
        applied.setdefault("navigation_build_request", dict(basis="native_build_or_dirty_queue_or_lock", editor_pid=os.getpid()))
        return dict(observed, request=applied["navigation_build_request"])
    require(observed["phase"] == "navigation_not_ready", "导航制作前场景读回未通过")
    require("navigation_build_request" not in applied, "本布局已有原生构建回执；当前仍未就绪，保留失败证据，不重复构建")
    u.SystemLibrary.execute_console_command(world, "RebuildNavigation", None)
    applied["navigation_build_request"] = dict(basis="single_explicit_rebuild_navigation", editor_pid=os.getpid())
    return dict(phase="navigation_build_requested_not_verified", request=applied["navigation_build_request"],
                saved=False, playable_verified=False)


def readback(applied, expected_map_file=None):
    """实际导航投影/连通与场景字段读回；不是PIE、战斗或完整轨迹验收。"""
    import unreal as u
    import restore_bh3_stage_environment as stage

    cfg = read_config()
    ctx = context(u, cfg, True)
    prepared = applied["prepared"]
    before = prepared["before"]
    require(sources() == before["sources"], "读回源码/配置已变化")
    require(receipt(package_file(MAP)) == (expected_map_file if expected_map_file is not None else before["map_file"]),
            "实际地图字节不符，拒绝使用失效前像")
    require(all(receipt(item["path"]) == item for item in before["dependencies"]), "读回依赖已变化")
    protect_geometry(u, stage, ctx, before)
    fields = native_fields(u, ctx)
    require(fields["game_mode"] == cfg["game_mode_class"]
            and fields["definition"] == path_of(ctx["definition"])
            and fields["seed"] == cfg["encounter_seed"]
            and fields["spawn_on_begin_play"] == cfg["spawn_on_begin_play"]
            and fields["support_navigation"], "场景制作字段实际读回不符")
    index = prepared["navigation"]["selected"]["index"]
    require(fields["nav_mask"] == fields["live_nav_mask"] == [i == index for i in range(NAV_AGENT_COUNT)]
            and u.Name(fields["nav_agent"]) == u.Name(fields["live_nav_agent"]) == u.Name(cfg["navigation"]["agent_name"]),
            "关卡/实际World的agent选择读回不符")
    agents = navigation_agents(u, ctx["world"], cfg, prepared["boss_capsule"])
    require(agents["ready"] and agents["global_profiles"] == prepared["navigation"]["global_profiles"],
            "项目Default或KevinBoss原生配置读回不符")
    volume = u.load_object(None, applied["nav_bounds_actor"])
    require(isinstance(volume, u.NavMeshBoundsVolume) and volume.get_world() == ctx["world"], "自有NavBounds不在当前World")
    origin, extent = volume.get_actor_bounds(False, False)
    require(max(abs(a-b) for a, b in zip(xyz(origin), applied["nav_center_cm"])) < 1
            and max(abs(a-b) for a, b in zip(xyz(extent), applied["nav_extent_cm"])) < 1,
            "自有NavBounds原生范围已变化")
    # 该原生谓词也包含 HasDirtyAreasQueued，不能将新布局排队误判为锁定故障。
    # 宿主有限等待；排队／构建／锁定均不签导航就绪。
    if u.NavigationSystemV1.is_navigation_being_built_or_locked(ctx["world"]):
        return dict(phase="waiting_for_native_navigation", reason="原生导航仍在构建、排队或被锁定",
                    saved=False, playable_verified=False)
    navs = [a for a in ctx["editor"].get_all_level_actors() if isinstance(a, u.RecastNavMesh)]
    chosen = [a for a in navs if u.Name(str(nav_data_config(u, a).get_editor_property("Name")))
              == u.Name(cfg["navigation"]["agent_name"])]
    require(len(chosen) <= 1, "实际所选agent的Recast数据不唯一")
    if not chosen:
        return dict(phase="navigation_not_ready", reason="指定agent还没有Recast数据", saved=False, playable_verified=False)
    agent = nav_data_config(u, chosen[0])
    require(agent.get_editor_property("AgentRadius") >= prepared["boss_capsule"]["radius_cm"]
            and agent.get_editor_property("AgentHeight") >= prepared["boss_capsule"]["half_height_cm"]*2,
            "原生导航数据未容纳实际Kevin胶囊")
    projected = {}
    for role in ("player", "boss"):
        point = prepared["spawns"][role]["location_cm"]
        actor = ctx["player_start" if role == "player" else "encounter"]
        require(abs((actor.get_actor_rotation().yaw - cfg[role+"_spawn_yaw_deg"] + 180) % 360 - 180) < .1,
                "实际出生Actor朝向不符：" + role)
        require(math.dist(xyz(actor.get_actor_location()), point) < .1, "实际出生Actor位置不符：" + role)
        movement, capsule = stage.support_capsule_cdo(u, ctx["player_data"].get_editor_property("PawnClass")
                                                     if role == "player" else ctx["boss_class"])
        require(capsule == prepared[role+"_capsule"], "实际胶囊前像已变化：" + role)
        floor_hit = stage.support_sweep(u, ctx["world"], capsule, movement,
                                       [point[0], point[1], point[2]+10], [point[0], point[1], point[2]-20])["hit"]
        require(floor_hit is not None and not floor_hit["initial_penetration"]
                and floor_hit["component"] == path_of(ctx["support_comp"])
                and floor_hit["native_cmc_is_walkable"], "实际/重载出生胶囊缺少原生可走地面：" + role)
        projected[role] = u.NavigationSystemV1.project_point_to_navigation(ctx["world"], u.Vector(*point), chosen[0], None,
                                                                         u.Vector(*cfg["navigation"]["query_extent_cm"]))
        if not isinstance(projected[role], u.Vector):
            return dict(phase="navigation_not_ready", reason="出生点没有真实导航投影：" + role,
                        saved=False, playable_verified=False)
        actual = xyz(projected[role])
        require(math.dist(actual[:2], point[:2]) <= cfg["navigation"]["projection_tolerance_xy_cm"], "导航投影移出出生区：" + role)
        floor = point[2] - prepared[role+"_capsule"]["half_height_cm"]
        require(abs(actual[2]-floor) <= cfg["navigation"]["projection_tolerance_z_cm"], "导航投影落到其它楼层：" + role)
    path = u.NavigationSystemV1.find_path_to_location_synchronously(ctx["world"], projected["boss"], projected["player"], chosen[0], None)
    if path is None or not path.is_valid() or path.is_partial() or len(path.get_editor_property("PathPoints")) < 2:
        return dict(phase="navigation_not_ready", reason="Boss到玩家的真实导航路径不完整",
                    saved=False, playable_verified=False)
    return dict(phase="scene_fields_and_editor_navigation_verified", fields=fields,
                nav_data=path_of(chosen[0]), nav_bounds_actor=applied["nav_bounds_actor"],
                projected={k: xyz(v) for k, v in projected.items()}, path_points=[xyz(p) for p in path.get_editor_property("PathPoints")],
                full_motion_clearance_verified=False, actual_spawn_verified=False,
                actual_cmc_landing_verified=False, combat_verified=False, saved=False)


def save_scene(applied, exact_backup):
    """Root显式提交：仅保存P3；精确备份、依赖、原生读回均须仍有效。"""
    import unreal as u

    before = applied["prepared"]["before"]
    require(os.getpid() == before["editor_pid"], "保存须由原获准制作宿主提交")
    backup = Path(exact_backup).resolve()
    require(backup.is_relative_to(ROOT / "Saved") and backup != package_file(MAP).resolve()
            and receipt(backup)["sha256"] == before["map_file"]["sha256"], "缺少原P3准确独立备份")
    require(not os.path.samefile(backup, package_file(MAP)), "地图备份是活文件的硬链接")
    require(all(receipt(item["path"]) == item for item in before["dependencies"]), "保存前实际依赖已变化")
    observed = readback(applied)
    require(observed["phase"] == "scene_fields_and_editor_navigation_verified",
            "导航未就绪，不保存冒称通过：" + observed.get("reason", observed["phase"]))
    world, _ = host(u, True)
    require(set(dirty(u)) - set(before["dirty"]) <= {MAP}, "保存范围含P3外包，先交Root准确差集")
    require(u.EditorLoadingAndSavingUtils.save_map(world, MAP), "P3精确地图保存失败，保留dirty现场")
    require(MAP not in dirty(u), "P3保存后仍dirty")
    return dict(phase="map_saved_cold_and_runtime_pending", editor_pid=os.getpid(), map_file=receipt(package_file(MAP)),
                backup=receipt(backup), native_readback=observed, saved=True,
                cold_read_verified=False, actual_spawn_verified=False, combat_verified=False)


def cold_read(applied, saved):
    """新获准宿主加载P3后消费原保存回执；不换图或补存，也不签PIE通过。"""
    import unreal as u

    original_dirty = dirty(u)
    require(saved["phase"] == "map_saved_cold_and_runtime_pending" and saved["saved"], "须消费实际P3保存回执")
    require(os.getpid() != saved["editor_pid"], "Cold入口须由新的获准Editor宿主读取，不能同进程冒签")
    require(MAP not in original_dirty, "冷读地图已有未保存改动")
    observed = readback(applied, expected_map_file=saved["map_file"])
    require(dirty(u) == original_dirty, "冷读产生dirty差集，保留现场")
    if observed["phase"] in ("waiting_for_native_navigation", "navigation_not_ready"):
        return observed
    observed.update(phase="saved_scene_cold_read_verified_runtime_pending", saved=True,
                    cold_read_verified=True, map_file=saved["map_file"])
    return observed
