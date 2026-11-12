"""为两个技能的实际挥刀段添加项目命中窗口；原版命中帧未知。

由独立 Editor 调用 apply(ue, windows, output_dir)。windows 的键必须恰为
Special、ExSpecial，值为 [(start_seconds, end_seconds), ...]。时段由姿态采样
及实拍核对后提供。本工具只保存两个 Montage，命中／伤害仍走既有 GA 和 Combat。
"""
import json
import math
import re
import shutil
from pathlib import Path

ROOT = "/Game/Characters/Player/Pyrios/Animation/Attack/"
NAMES = {"Special": "AM_Pyrios_Attack_Special_01", "ExSpecial": "AM_Pyrios_Attack_ExSpecial_01"}
TRACK = "ProjectHitWindow"


def require(condition, reason):
    if not condition:
        raise RuntimeError("[Pyrios.SkillHitWindow] " + reason)


def events(ue, montage):
    result = {}
    for event in ue.AnimationLibrary.get_animation_notify_events(montage):
        native = event.export_text()
        guid = re.search(r"(?:^|[,\(])Guid=([0-9A-Fa-f]{32})(?:[,\)])", native)
        require(guid is not None, "Notify 缺 Guid")
        result[guid.group(1)] = native
    return result


def apply(ue, windows, output_dir):
    """保存前保留原包、原 Notify；拒绝覆盖已经存在的技能命中窗口。"""
    require(set(windows) == set(NAMES), "必须明确提供两个技能的时段")
    require(not ue.EditorLevelLibrary.get_pie_worlds(True), "PIE 期间不能制作 Montage")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    dirty = set(ue.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    prepared = {}
    for action, name in NAMES.items():
        montage = ue.load_asset(ROOT + name)
        require(isinstance(montage, ue.AnimMontage), "缺 Montage " + name)
        require(montage.get_outermost() not in dirty, "Montage 已有未保存工作 " + name)
        source = ue.load_asset("/Game/Characters/Player/Pyrios/Animation/Avatar_Male_Size03_Pyrois_Ani_Attack_"
                               + ("Special_01" if action == "Special" else "ExSpecial_01"))
        require(isinstance(source, ue.AnimSequence), "缺 Main 动画 " + action)
        previous_end = -1.0
        require(bool(windows[action]), "未配置挥刀段 " + action)
        for start, end in windows[action]:
            require(all(math.isfinite(v) for v in (start, end)) and 0 <= start < end <= source.get_play_length()
                    and start > previous_end, "窗口越界或重叠 " + action)
            previous_end = end
        for event in ue.AnimationLibrary.get_animation_notify_events(montage):
            state = event.get_editor_property("notify_state_class")
            if isinstance(state, ue.GGYGOAnimNotifyState_GameplayEventWindow):
                require("Event.Montage.HitWindowBegin" not in state.get_editor_property("begin_event_tag").export_text(),
                        "已有命中窗，需核对后再改 " + name)
        prepared[action] = (montage, events(ue, montage))

    tags = []
    for name in ("Event.Montage.HitWindowBegin", "Event.Montage.HitWindowEnd"):
        tag = ue.GameplayTag()
        require(tag.import_text('(TagName="' + name + '")'), "Tag 构造失败 " + name)
        tags.append(tag)
    report = {"configuration_source": "项目配置：用户选择按实际挥刀段，原版命中帧未知", "assets": {}}
    for action, (montage, before) in prepared.items():
        name = montage.get_name()
        package_file = Path(ue.Paths.project_content_dir()) / (ROOT.removeprefix("/Game/") + name + ".uasset")
        shutil.copy2(package_file, output / (name + ".before.uasset"))
        ue.AnimationLibrary.add_animation_notify_track(montage, TRACK)
        for start, end in windows[action]:
            state = ue.AnimationLibrary.add_animation_notify_state_event(
                montage, TRACK, start, end - start, ue.GGYGOAnimNotifyState_GameplayEventWindow)
            require(state is not None, "创建命中窗失败 " + action)
            state.set_editor_property("begin_event_tag", tags[0])
            state.set_editor_property("end_event_tag", tags[1])
            state.set_editor_property("notify_state_behavior_flags", 1)
        after = events(ue, montage)
        require(all(after.get(guid) == value for guid, value in before.items()), "原 Notify 被意外改变 " + action)
        require(len(after) == len(before) + len(windows[action]), "新增窗口数量不符 " + action)
        require(ue.EditorAssetLibrary.save_loaded_asset(montage, False), "Montage 保存失败 " + action)
        report["assets"][action] = {"montage": montage.get_path_name(), "windows": windows[action],
                                    "original_notifies_preserved": True, "saved": True}
        (output / "authoring.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
