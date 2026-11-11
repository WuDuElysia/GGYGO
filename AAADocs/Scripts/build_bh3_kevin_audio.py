"""@file build_bh3_kevin_audio.py
@brief Kevin SoundWave/SoundCue/衰减资产的精确新增准备与只读核验，由 Root 的标准 Editor 窗调用。

prepare 仅准备明确目标，返回未保存对象；不保存、不写 Montage/GA/Tag 配置。
SoundCueFactoryNew 生成原生可编辑图；多播放组交 Animation 同点放置多个 Notify。
最终命中 GameplayCue 由 FX 唯一制作，本工具只交其实际 SoundCue 输入。
原 GA 持有持续声 Actor/组件，声音作者不增加运行时管理器或按 Tag 清理后继。
"""

import math
from pathlib import Path
from types import ModuleType


_PLAN_PATH = Path(__file__).with_name("plan_bh3_kevin_audio.py")
# 在制作窗只读取已冻结 helper，不因加载它额外写 __pycache__ 或改全局 Python 设置。
PLAN = ModuleType("kevin_audio_plan")
PLAN.__file__ = str(_PLAN_PATH)
exec(compile(_PLAN_PATH.read_text(encoding="utf-8"), str(_PLAN_PATH), "exec"), PLAN.__dict__)


def planned_targets(config_path=PLAN.CONFIG):
    """返回实际新增写集；Root 可选显式子集，依赖必须先存在或包含在同一准备调用。"""
    config = PLAN.read_json(config_path)
    return ([row["target"] for row in config["soundwaves"] if not row["existing"]]
            + [row["target"] for row in config["attenuations"]]
            + [row["target"] for row in config["sound_cues"]])


def dirty_packages(ue):
    return {package.get_path_name() for package in
            list(ue.EditorLoadingAndSavingUtils.get_dirty_content_packages())
            + list(ue.EditorLoadingAndSavingUtils.get_dirty_map_packages())}


def object_path(package):
    return package + "." + package.rsplit("/", 1)[1]


def original_object(ue, package, asset):
    PLAN.require(asset is not None and asset.get_path_name() == object_path(package)
                 and ue.find_object(None, object_path(package)) == asset,
                 "原资产对象被替换：" + package)


def wave_snapshot(ue, asset, row):
    PLAN.require(isinstance(asset, ue.SoundWave), "依赖不是 SoundWave：" + row["target"])
    original_object(ue, row["target"], asset)
    import_data = ue.find_object(asset, "AssetImportData")
    PLAN.require(isinstance(import_data, ue.AssetImportData), "SoundWave 缺少实际导入来源")
    filenames = list(import_data.extract_filenames())
    PLAN.require(len(filenames) == 1 and Path(filenames[0]).resolve() == Path(row["source"]["path"]).resolve(),
                 "SoundWave 实际导入来源不符：" + row["target"])
    data = ue.AssetRegistryHelpers.create_asset_data(asset)
    rate = ue.AssetRegistryHelpers.get_tag_value(data, "ImportedSampleRate")
    PLAN.require(isinstance(rate, str) and rate, "缺少公开 ImportedSampleRate 读回")
    actual = {"duration": float(asset.get_editor_property("duration")),
              "sample_rate": int(rate),
              "channels": int(asset.get_editor_property("num_channels")),
              "looping": bool(asset.get_editor_property("looping")),
              "volume": float(asset.get_editor_property("volume")),
              "pitch": float(asset.get_editor_property("pitch"))}
    PLAN.require(math.isfinite(actual["duration"])
                 and abs(actual["duration"] - row["duration_seconds"]) <= max(1e-5, 1 / row["sample_rate"])
                 and actual["sample_rate"] == row["sample_rate"] and actual["channels"] == row["channels"]
                 and actual["looping"] is False and actual["volume"] == 1.0 and actual["pitch"] == 1.0,
                 "SW Native 属性与来源不符：" + row["target"])
    return actual


def sound_cue_players(ue, asset, row):
    """读取公开播放树，并核对 Cue 自有节点库存；不访问受保护的 AllNodes。"""
    PLAN.require(isinstance(asset, ue.SoundCue), "目标不是 SoundCue：" + row["target"])
    original_object(ue, row["target"], asset)
    root = asset.get_editor_property("first_node")
    count = len(row["wave_targets"])
    PLAN.require(count > 0, "SoundCue 缺少明确播放源")
    if count == 1:
        PLAN.require(isinstance(root, ue.SoundNodeWavePlayer), "单声 Cue 必须由 WavePlayer 直接作为根")
        players = [root]
        reachable = [root]
    else:
        PLAN.require(isinstance(root, ue.SoundNodeRandom), "多源 Cue 必须由 Random 直接连接 WavePlayer")
        players = list(root.get_editor_property("child_nodes"))
        PLAN.require(len(players) == count and all(isinstance(node, ue.SoundNodeWavePlayer) for node in players),
                     "Random 子节点为空、数量不符或包含未配置的中间节点")
        reachable = [root] + players
    PLAN.require(all(not list(player.get_editor_property("child_nodes")) for player in players),
                 "WavePlayer 不能再连接其它节点")
    PLAN.require(all(node.get_outer() == asset and ue.find_object(None, node.get_path_name()) == node
                     for node in reachable), "播放树节点并非原 Cue 自有对象")
    references = []
    for player in players:
        sound = player.get_editor_property("sound_wave")
        PLAN.require(sound is not None, "WavePlayer 的实际资源未加载")
        references.append(sound.get_path_name())
    PLAN.require(references == [object_path(target) for target in row["wave_targets"]],
                 "播放树的实际 Wave 引用或输入次序不符")
    # 原生工厂将 SoundNode 的 Outer 设为 Cue；公开库存与可达树求等，保留孤立/额外节点检查。
    owned = [node for node in ue.ObjectIterator(ue.SoundNode) if node.get_outer() == asset]
    owned_paths = sorted(node.get_path_name() for node in owned)
    PLAN.require(len(owned) == len(reachable)
                 and set(owned_paths) == {node.get_path_name() for node in reachable},
                 "Cue 自有节点库存与播放树不一致，存在孤立、额外或重复引用节点")
    return root, players, owned_paths


def sound_cue_snapshot(ue, asset, row):
    root, players, owned_paths = sound_cue_players(ue, asset, row)
    expected = {object_path(target): loop for target, loop in zip(row["wave_targets"], row["wave_looping"])}
    actual = {}
    for player in players:
        sound = player.get_editor_property("sound_wave")
        PLAN.require(sound is not None, "WavePlayer 的实际资源未加载")
        actual[sound.get_path_name()] = bool(player.get_editor_property("looping"))
    PLAN.require(actual == expected and len(players) == len(expected), "SoundCue 播放源或循环不符")
    if len(players) > 1:
        weights = list(root.get_editor_property("weights"))
        PLAN.require(len(weights) == len(row["weights"])
                     and all(math.isclose(a, b, rel_tol=1e-6) for a, b in zip(weights, row["weights"]))
                     and bool(root.get_editor_property("randomize_without_replacement"))
                     == row["project_random_without_replacement"], "SoundCue 随机配置不符")
    PLAN.require(math.isclose(asset.get_editor_property("volume_multiplier"), row["project_volume"], rel_tol=1e-6)
                 and math.isclose(asset.get_editor_property("pitch_multiplier"), row["project_pitch"], rel_tol=1e-6),
                 "SoundCue 项目音量/音高不符")
    attenuation = asset.get_editor_property("attenuation_settings")
    PLAN.require(asset.get_editor_property("override_attenuation") is False and attenuation is not None
                 and attenuation.get_path_name() == object_path(row["attenuation_target"]), "SoundCue 空间衰减引用不符")
    return {"root": root.get_class().get_name(), "waves": actual,
            "graph": {"root_object": root.get_path_name(), "owned_nodes": owned_paths,
                      "player_order": [player.get_path_name() for player in players]},
            "project_volume": row["project_volume"], "project_pitch": row["project_pitch"],
            "attenuation": attenuation.get_path_name()}


def attenuation_snapshot(ue, asset, row):
    PLAN.require(isinstance(asset, ue.SoundAttenuation), "目标不是 SoundAttenuation")
    original_object(ue, row["target"], asset)
    settings = asset.get_editor_property("attenuation")
    PLAN.require(settings.get_editor_property("attenuate") is True
                 and settings.get_editor_property("spatialize") == row["spatialize"]
                 and settings.get_editor_property("distance_algorithm") == getattr(ue.AttenuationDistanceModel, row["distance_model"])
                 and settings.get_editor_property("attenuation_shape") == getattr(ue.AttenuationShape, row["shape"])
                 and settings.get_editor_property("attenuation_shape_extents").x == row["radius_cm"]
                 and settings.get_editor_property("falloff_distance") == row["falloff_cm"], "项目空间衰减参数不符")
    return {"spatialize": row["spatialize"], "radius_cm": row["radius_cm"], "falloff_cm": row["falloff_cm"]}


def selected_rows(config, targets, include_existing=False):
    wanted = set(targets)
    PLAN.require(targets and len(targets) == len(wanted), "需要非空、不重复的实际目标集合")
    PLAN.require(all(target.startswith(PLAN.WAVE_ROOT + "/") and ".." not in target.split("/")
                     and "\\" not in target for target in wanted), "写集/回读目标越出 Kevin Audio 范围")
    available = {row["target"]: (kind, row) for kind, key in
                 (("wave", "soundwaves"), ("attenuation", "attenuations"), ("sound_cue", "sound_cues"))
                 for row in config[key] if include_existing or kind != "wave" or not row["existing"]}
    PLAN.require(wanted <= set(available), "目标超出 Kevin Audio 实际制作配置")
    return [(target, kind, row) for target, (kind, row) in available.items() if target in wanted]


def prepare(expected_targets, allowed_dirty_packages=(), config_path=PLAN.CONFIG):
    """在 Root 已保护的标准 Editor 中准备明确目标，依赖可由同窗前序准备提供；返回后由 Root 精确保存。"""
    import unreal as ue

    PLAN.require(Path(ue.Paths.project_dir()).resolve() == PLAN.PROJECT.resolve(), "UE 工程不是 GGYGO")
    config = PLAN.read_json(config_path)
    selected = selected_rows(config, list(expected_targets))
    before_dirty = dirty_packages(ue)
    PLAN.require(before_dirty == set(allowed_dirty_packages), "当前 dirty 与 Root 明确交入集合不符")
    frozen = [PLAN.identity(config_path), PLAN.identity(__file__), PLAN.identity(_PLAN_PATH)]
    wave_rows = {row["target"]: row for row in config["soundwaves"]}
    attenuation_rows = {row["target"]: row for row in config["attenuations"]}
    dependency_waves = set()
    for target, kind, row in selected:
        PLAN.require(all(value is None for value in PLAN.package_files(target).values())
                     and ue.find_object(None, object_path(target)) is None
                     and not ue.EditorAssetLibrary.does_asset_exist(target), "新增目标已存在：" + target)
        if kind == "wave":
            dependency_waves.add(target)
        elif kind == "sound_cue":
            dependency_waves.update(row["wave_targets"])
    for target in dependency_waves:
        row = wave_rows[target]
        if row["existing"]:
            PLAN.require(PLAN.package_files(target) == row["package_before"], "现有 SW 包前像改变：" + target)
            frozen.extend(value for value in row["package_before"].values() if value is not None)
        else:
            PLAN.require(PLAN.identity(row["source"]["path"]) == row["source"], "新 SW 原 WAV 身份改变")
            frozen.append(row["source"])

    objects, snapshots = {}, {}

    def load(package):
        asset = objects.get(package)
        if asset is None:
            asset = ue.load_asset(package)
        PLAN.require(asset is not None, "缺少同窗准备或已保存依赖：" + package)
        original_object(ue, package, asset)
        return asset

    tools = ue.AssetToolsHelpers.get_asset_tools()
    for target, kind, row in selected:
        name, directory = target.rsplit("/", 1)[1], target.rsplit("/", 1)[0]
        if kind == "attenuation":
            asset = tools.create_asset(name, directory, ue.SoundAttenuation, ue.SoundAttenuationFactory())
            original_object(ue, target, asset)
            settings = ue.SoundAttenuationSettings()
            for field, value in (("attenuate", True), ("spatialize", row["spatialize"]),
                                 ("distance_algorithm", getattr(ue.AttenuationDistanceModel, row["distance_model"])),
                                 ("attenuation_shape", getattr(ue.AttenuationShape, row["shape"])),
                                 ("attenuation_shape_extents", ue.Vector(row["radius_cm"], 0.0, 0.0)),
                                 ("falloff_distance", row["falloff_cm"])):
                settings.set_editor_property(field, value)
            asset.set_editor_property("attenuation", settings)
            snapshots[target] = attenuation_snapshot(ue, asset, row)
        elif kind == "wave":
            factory = ue.SoundFactory()
            for field in ("auto_create_cue", "include_attenuation_node", "include_looping_node", "include_modulator_node"):
                factory.set_editor_property(field, False)
            task = ue.AssetImportTask()
            for field, value in (("filename", row["source"]["path"]), ("destination_path", directory),
                                 ("destination_name", name), ("automated", True), ("replace_existing", False),
                                 ("save", False), ("factory", factory)):
                task.set_editor_property(field, value)
            tools.import_asset_tasks([task])
            PLAN.require(list(task.get_editor_property("imported_object_paths")) == [object_path(target)],
                         "声音导入未返回唯一准确目标：" + target)
            asset = load(target)
            for field, value in (("looping", False), ("volume", 1.0), ("pitch", 1.0)):
                asset.set_editor_property(field, value)
                original_object(ue, target, asset)
            snapshots[target] = wave_snapshot(ue, asset, row)
        elif kind == "sound_cue":
            waves = [load(package) for package in row["wave_targets"]]
            for wave, package in zip(waves, row["wave_targets"]):
                wave_snapshot(ue, wave, wave_rows[package])
            factory = ue.SoundCueFactoryNew()
            factory.set_editor_property("initial_sound_waves", waves)
            asset = tools.create_asset(name, directory, ue.SoundCue, factory)
            root, players, _ = sound_cue_players(ue, asset, row)
            loops = {object_path(package): looping for package, looping in zip(row["wave_targets"], row["wave_looping"])}
            PLAN.require(len(players) == len(loops), "原生工厂未生成完整播放图")
            for player in players:
                wave = player.get_editor_property("sound_wave")
                PLAN.require(wave is not None and wave.get_path_name() in loops, "原生播放节点资源不符")
                player.set_editor_property("looping", loops[wave.get_path_name()])
                original_object(ue, target, asset)
            if len(waves) > 1:
                PLAN.require(isinstance(root, ue.SoundNodeRandom), "原生工厂未生成随机节点")
                root.set_editor_property("weights", row["weights"])
                root.set_editor_property("randomize_without_replacement", row["project_random_without_replacement"])
            attenuation = load(row["attenuation_target"])
            attenuation_snapshot(ue, attenuation, attenuation_rows[row["attenuation_target"]])
            asset.set_editor_property("attenuation_settings", attenuation)
            asset.set_editor_property("override_attenuation", False)
            asset.set_editor_property("volume_multiplier", row["project_volume"])
            asset.set_editor_property("pitch_multiplier", row["project_pitch"])
            snapshots[target] = sound_cue_snapshot(ue, asset, row)
        objects[target] = asset
        PLAN.require(dirty_packages(ue) <= before_dirty | set(expected_targets), "制作回调触及范围外 dirty 包")
        PLAN.require(all(value is None for value in PLAN.package_files(target).values()), "准备步骤意外保存目标")
    for original in frozen:
        PLAN.require(PLAN.identity(original["path"]) == original, "准备期间冻结输入改变：" + original["path"])
    PLAN.require(before_dirty <= dirty_packages(ue), "准备期间原 dirty 包被保存或清除")
    PLAN.require(all(value is None for target in objects for value in PLAN.package_files(target).values()),
                 "后续制作回调意外保存了前序目标")
    return {"preparation_complete": True, "errors": [],
            "prepared_targets": list(objects), "objects": {target: asset.get_path_name() for target, asset in objects.items()},
            "native_snapshots": snapshots, "dirty_before": sorted(before_dirty), "dirty_after": sorted(dirty_packages(ue)),
            "saved": [], "runtime_verified": False, "original_timing_verified": False}


def readback(expected_targets, config_path=PLAN.CONFIG):
    """只读实际 Native 对象；不导入、不修改、不保存，独立 Cold 由 Root 安排。"""
    import unreal as ue

    PLAN.require(Path(ue.Paths.project_dir()).resolve() == PLAN.PROJECT.resolve(), "UE 工程不是 GGYGO")
    config = PLAN.read_json(config_path)
    selected = selected_rows(config, list(expected_targets), include_existing=True)
    before = dirty_packages(ue)
    snapshots = {}
    for target, kind, row in selected:
        asset = ue.load_asset(target)
        PLAN.require(asset is not None, "回读目标缺失：" + target)
        checker = {"wave": wave_snapshot, "attenuation": attenuation_snapshot, "sound_cue": sound_cue_snapshot}[kind]
        snapshots[target] = checker(ue, asset, row)
    PLAN.require(dirty_packages(ue) == before, "只读加载引发 dirty 差异")
    return {"readback_complete": True, "errors": [], "native_snapshots": snapshots,
            "saved": [], "runtime_verified": False,
            "original_timing_verified": False}
