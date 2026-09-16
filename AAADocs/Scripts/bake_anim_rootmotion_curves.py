# -*- coding: utf-8 -*-
"""
bake_anim_rootmotion_curves.py —— 把 anim_rootmotion_extract.py 产出的中间数据写成
AnimSequence 上的真实 FloatCurve。

在 UE 编辑器 Python 命令行执行：
  exec(open(r"F:/ue_project/GGYGO/AAADocs/Scripts/bake_anim_rootmotion_curves.py", encoding="utf-8").read())

MODE 控制行为：
  "probe" —— 只处理 PROBE_CLIPS 里的动画，写入后立刻回读校验并打印，不保存包。
  "all"   —— 处理中间数据里的全部 clip 并保存。

数据来源分工（为什么不直接读 anim_settings.json）：
  JSON 的 rootMotionCurves（MotionT/MotionQ/RootT/RootQ）全部 key 值为 0，是占位数据；
  逐帧 root motion 来自各动作 FBX 的外部 Root 节点，muscleClip 标量来自 per-clip JSON。
  两者由 anim_rootmotion_extract.py 合并成 SOURCE_JSON。

写入的曲线：
  RootMotion_PosX/PosY/PosZ  以本段首帧为 0 基准的累计位移，UE 轴（X 前、Y 右、Z 上），厘米
  RootMotion_Yaw/Pitch/Roll  以本段首帧为 0 基准的累计角度，度；已解 ±180 折叠，可直接差分
  RootMotion_Dist            累计水平路程，厘米，单调不减
  RootMotion_Speed           逐帧水平速度，厘米/秒
  RootMotion_DirX/DirY       水平速度方向的单位分量，UE 轴
  Cfg_*                      muscleClip 的 per-clip 常量，写成两个 key 的常量曲线，
                             这样运行时 GetCurveValue 能直接取到，不必读资产元数据

恒定曲线只写首尾两个 key。恒定值在任何插值模式下都不会过冲，所以这个压缩不改变采样结果；
而逐帧变化的曲线一律写满每一帧，不做抽稀，避免三次插值在抽稀点之间产生过冲。
"""

import json
import os

import unreal

MODE = "all"

# all 模式每次执行最多处理这么多 clip，然后返回。已完成的 clip 记在 PROGRESS_JSON 里，
# 重复执行同一条命令会接着往下做。分批是因为写曲线会占住游戏线程，
# 一次跑完 119 个会让编辑器长时间无响应，中途中断还会丢掉进度。
# 想整批重来时删掉 PROGRESS_JSON，否则已完成的 clip 会被跳过。
BATCH_SIZE = 15

SOURCE_JSON = r"F:/ue_project/GGYGO/Saved/AnimRootMotion/Pyrios_RootMotion.json"
ANIM_FOLDER = "/Game/Characters/Player/Pyrios/Animation"
REPORT_JSON = r"F:/ue_project/GGYGO/Saved/AnimRootMotion/BakeReport.json"
PROGRESS_JSON = r"F:/ue_project/GGYGO/Saved/AnimRootMotion/BakeProgress.json"

PROBE_CLIPS = [
    "Avatar_Male_Size03_Pyrois_Ani_TurnBack",   # 唯一同时带 180° yaw 和往复位移的动作
    "Avatar_Male_Size03_Pyrois_Ani_Run_Loop",   # 循环动画，校验速度量级
    "Avatar_Male_Size03_Pyrois_Ani_Idle_Loop",  # 全静止，校验常量曲线压缩
]

MOTION_CURVES = [
    "RootMotion_PosX", "RootMotion_PosY", "RootMotion_PosZ",
    "RootMotion_Yaw", "RootMotion_Pitch", "RootMotion_Roll",
    "RootMotion_Dist", "RootMotion_Speed",
    "RootMotion_DirX", "RootMotion_DirY",
]

# muscleClip 标量 -> 常量曲线名。布尔按 0/1 写入。
SCALAR_CURVES = [
    ("Cfg_CycleOffset", "cycleOffset"),
    ("Cfg_OrientationOffsetY", "orientationOffsetY"),
    ("Cfg_Level", "level"),
    ("Cfg_LoopTime", "loopTime"),
    ("Cfg_LoopBlend", "loopBlend"),
    ("Cfg_LoopBlendOrientation", "loopBlendOrientation"),
    ("Cfg_LoopBlendPositionY", "loopBlendPositionY"),
    ("Cfg_LoopBlendPositionXZ", "loopBlendPositionXZ"),
    ("Cfg_Mirror", "mirror"),
    ("Cfg_StartAtOrigin", "startAtOrigin"),
    ("Cfg_KeepOriginalOrientation", "keepOriginalOrientation"),
    ("Cfg_KeepOriginalPositionY", "keepOriginalPositionY"),
    ("Cfg_KeepOriginalPositionXZ", "keepOriginalPositionXZ"),
    ("Cfg_HeightFromFeet", "heightFromFeet"),
]

FLOAT_TYPE = unreal.RawCurveTrackTypes.RCT_FLOAT


# ---------------------------------------------------------------- 曲线读写封装

def curve_exists(anim, name):
    try:
        return bool(unreal.AnimationLibrary.does_curve_exist(
            anim, unreal.Name(name), FLOAT_TYPE))
    except Exception:
        return False


def remove_curve(anim, name):
    try:
        unreal.AnimationLibrary.remove_curve(anim, unreal.Name(name), False)
        return True
    except Exception:
        return False


def add_curve(anim, name):
    """新建一条空的 FloatCurve。已存在则先删掉，避免旧 key 与新 key 混在一起。"""
    if curve_exists(anim, name):
        remove_curve(anim, name)
    unreal.AnimationLibrary.add_curve(anim, unreal.Name(name), FLOAT_TYPE, False)


def write_float_keys(anim, name, times, values):
    """批量写入 key。优先用批量 API；不可用时退回逐 key，逐 key 在整批上会很慢但能跑通。"""
    batch = getattr(unreal.AnimationLibrary, "add_float_curve_keys", None)
    if callable(batch):
        batch(anim, unreal.Name(name), [float(t) for t in times],
              [float(v) for v in values])
        return len(times)
    single = getattr(unreal.AnimationLibrary, "add_float_curve_key", None)
    if callable(single):
        for t, v in zip(times, values):
            single(anim, unreal.Name(name), float(t), float(v))
        return len(times)
    raise RuntimeError("AnimationLibrary 上找不到写入 float 曲线 key 的 API")


def read_float_at(anim, name, time):
    try:
        return float(unreal.AnimationLibrary.get_float_value_at_time(
            anim, unreal.Name(name), float(time)))
    except Exception:
        return None


def compress_constant(times, values):
    """恒定序列压成首尾两个 key，其余原样返回。"""
    if len(values) > 2 and (max(values) - min(values)) < 1e-6:
        return [times[0], times[-1]], [values[0], values[0]]
    return times, values


# ---------------------------------------------------------------- 时间轴对齐

def resample(src_times, src_values, dst_times):
    """把源曲线线性重采样到目标帧时间。仅在 UE 资产帧数与 FBX 帧数不一致时用到。"""
    if not src_times:
        return [0.0] * len(dst_times)
    out = []
    j = 0
    n = len(src_times)
    for t in dst_times:
        while j + 1 < n and src_times[j + 1] < t:
            j += 1
        if t <= src_times[0]:
            out.append(src_values[0])
        elif t >= src_times[-1]:
            out.append(src_values[-1])
        else:
            t0, t1 = src_times[j], src_times[min(j + 1, n - 1)]
            v0, v1 = src_values[j], src_values[min(j + 1, n - 1)]
            a = 0.0 if t1 <= t0 else (t - t0) / (t1 - t0)
            out.append(v0 + (v1 - v0) * a)
    return out


def sampled_key_count(anim):
    for getter in ("get_number_of_sampled_keys", "get_number_of_keys"):
        fn = getattr(anim, getter, None)
        if callable(fn):
            try:
                return int(fn())
            except Exception:
                pass
    try:
        return int(unreal.AnimationLibrary.get_num_frames(anim)) + 1
    except Exception:
        return 0


def sequence_length(anim):
    try:
        return float(anim.get_editor_property("sequence_length"))
    except Exception:
        try:
            return float(unreal.AnimationLibrary.get_sequence_length(anim))
        except Exception:
            return 0.0


# ---------------------------------------------------------------- 单个 clip

def scalar_value(scalars, key):
    v = scalars.get(key)
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if v is None:
        return 0.0
    return float(v)


def bake_clip(record):
    """返回 (状态字符串, 详情 dict)。"""
    name = record["name"]
    asset_path = "%s/%s" % (ANIM_FOLDER, name)
    anim = unreal.load_asset(asset_path)
    if anim is None or not isinstance(anim, unreal.AnimSequence):
        return "missing", {"name": name, "reason": "资产不存在或不是 AnimSequence"}

    src_times = record["times"]
    ue_keys = sampled_key_count(anim)
    ue_len = sequence_length(anim)

    # UE 资产的帧数与 FBX 提取的帧数一致时逐帧一对一写入；否则按 UE 帧重采样。
    if ue_keys == len(src_times):
        dst_times = src_times
        resampled = False
    else:
        step = ue_len / (ue_keys - 1) if ue_keys > 1 else 0.0
        dst_times = [i * step for i in range(ue_keys)]
        resampled = True

    ctrl = None
    try:
        ctrl = anim.get_controller()
        ctrl.open_bracket("BakeRootMotionCurves", False)
    except Exception:
        ctrl = None

    written = {}
    try:
        for curve_name in MOTION_CURVES:
            values = record["curves"].get(curve_name)
            if values is None:
                continue
            if resampled:
                values = resample(src_times, values, dst_times)
            t, v = compress_constant(dst_times, values)
            add_curve(anim, curve_name)
            written[curve_name] = write_float_keys(anim, curve_name, t, v)

        scalars = record.get("scalars") or {}
        avg = record.get("averageSpeed") or {}
        derived = {
            # muscleClip 的 [startTime, stopTime] 才是规范化后的循环长度，
            # 通常比 FBX take 少一帧（循环动画末帧等于首帧，不该重复计入）。
            "Cfg_ClipLength": float(scalars.get("stopTime", 0.0))
                              - float(scalars.get("startTime", 0.0)),
            # averageSpeed 是 Unity 单位 m/s，乘 100 换成 cm/s
            "Cfg_AvgSpeed": 100.0 * (avg.get("x", 0.0) ** 2 + avg.get("y", 0.0) ** 2
                                     + avg.get("z", 0.0) ** 2) ** 0.5,
            # averageAngularSpeed 是弧度/秒且无符号，转身方向只在 RootMotion_Yaw 里
            "Cfg_AvgAngularSpeed": 57.2957795
                                   * float(scalars.get("averageAngularSpeed", 0.0)),
        }
        span = [dst_times[0], dst_times[-1]] if dst_times else [0.0, 0.0]
        for curve_name, value in derived.items():
            add_curve(anim, curve_name)
            written[curve_name] = write_float_keys(
                anim, curve_name, span, [value, value])
        for curve_name, key in SCALAR_CURVES:
            value = scalar_value(scalars, key)
            add_curve(anim, curve_name)
            written[curve_name] = write_float_keys(
                anim, curve_name, span, [value, value])
    finally:
        if ctrl is not None:
            try:
                ctrl.close_bracket(False)
            except Exception:
                pass

    anim.modify()
    return "ok", {
        "name": name,
        "ueKeys": ue_keys,
        "srcKeys": len(src_times),
        "ueLength": ue_len,
        "resampled": resampled,
        "curveCount": len(written),
        "keyTotal": sum(written.values()),
    }


# ---------------------------------------------------------------- 回读校验

def verify_clip(record):
    name = record["name"]
    anim = unreal.load_asset("%s/%s" % (ANIM_FOLDER, name))
    if anim is None:
        return
    unreal.log("-" * 78)
    unreal.log("[Verify] %s  len=%.4f keys=%d"
               % (name, sequence_length(anim), sampled_key_count(anim)))
    times = record["times"]
    end = times[-1] if times else 0.0
    for curve_name in MOTION_CURVES:
        src = record["curves"].get(curve_name)
        if src is None:
            continue
        mid = len(src) // 2
        got_mid = read_float_at(anim, curve_name, times[mid])
        got_end = read_float_at(anim, curve_name, end)
        unreal.log("  %-18s src mid=%10.3f end=%10.3f | asset mid=%10.3f end=%10.3f"
                   % (curve_name, src[mid], src[-1],
                      -999.0 if got_mid is None else got_mid,
                      -999.0 if got_end is None else got_end))
    for curve_name in ["Cfg_ClipLength", "Cfg_LoopTime", "Cfg_AvgSpeed",
                       "Cfg_AvgAngularSpeed", "Cfg_CycleOffset"]:
        unreal.log("  %-18s asset=%s"
                   % (curve_name, read_float_at(anim, curve_name, end)))


# ---------------------------------------------------------------- 入口

def load_records():
    if not os.path.exists(SOURCE_JSON):
        raise RuntimeError("找不到中间数据 %s，先在命令行跑 anim_rootmotion_extract.py"
                           % SOURCE_JSON)
    with open(SOURCE_JSON, "r", encoding="utf-8") as f:
        return json.load(f)["clips"]


def load_progress():
    if not os.path.exists(PROGRESS_JSON):
        return {"done": [], "missing": [], "failed": []}
    try:
        with open(PROGRESS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k in ("done", "missing", "failed"):
            data.setdefault(k, [])
        return data
    except Exception:
        return {"done": [], "missing": [], "failed": []}


def save_progress(progress):
    os.makedirs(os.path.dirname(PROGRESS_JSON), exist_ok=True)
    with open(PROGRESS_JSON, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=1)


def run():
    records = load_records()
    if MODE == "probe":
        wanted = set(PROBE_CLIPS)
        records = [r for r in records if r["name"] in wanted]
        unreal.log("[Bake] probe 模式，%d 个 clip，不保存资产" % len(records))
    else:
        unreal.log("[Bake] all 模式，%d 个 clip" % len(records))

    if MODE == "probe":
        ok, missing, failed = [], [], []
        for rec in records:
            status, detail = bake_clip(rec)
            if status == "ok":
                ok.append(detail)
                unreal.log("[Bake] %s 曲线=%d key=%d resampled=%s"
                           % (detail["name"], detail["curveCount"],
                              detail["keyTotal"], detail["resampled"]))
            else:
                missing.append(detail)
                unreal.log_warning("[Bake] 跳过 %s: %s"
                                   % (detail["name"], detail.get("reason")))
        for rec in records:
            verify_clip(rec)
        unreal.log("[Bake] probe 完成：成功 %d，缺资产 %d，失败 %d（未保存）"
                   % (len(ok), len(missing), len(failed)))
        return

    progress = load_progress()
    handled = set(progress["done"]) | {d["name"] for d in progress["missing"]} \
        | {d["name"] for d in progress["failed"]}
    pending = [r for r in records if r["name"] not in handled]
    batch = pending[:BATCH_SIZE]

    unreal.log("[Bake] 总计 %d，已处理 %d，本批 %d，剩余 %d"
               % (len(records), len(handled), len(batch),
                  len(pending) - len(batch)))

    for rec in batch:
        name = rec["name"]
        try:
            status, detail = bake_clip(rec)
        except Exception as exc:
            progress["failed"].append({"name": name, "reason": str(exc)})
            save_progress(progress)
            unreal.log_error("[Bake] %s 失败: %s" % (name, exc))
            continue

        if status != "ok":
            progress["missing"].append(detail)
            save_progress(progress)
            unreal.log_warning("[Bake] 跳过 %s: %s" % (name, detail.get("reason")))
            continue

        # 逐个保存并记录进度，这样中途被打断也不会重做已完成的部分
        anim = unreal.load_asset("%s/%s" % (ANIM_FOLDER, name))
        try:
            unreal.EditorAssetLibrary.save_loaded_asset(anim, False)
        except Exception as exc:
            progress["failed"].append({"name": name, "reason": "保存失败: %s" % exc})
            save_progress(progress)
            unreal.log_error("[Bake] 保存 %s 失败: %s" % (name, exc))
            continue

        progress["done"].append(name)
        progress.setdefault("detail", {})[name] = detail
        save_progress(progress)
        unreal.log("[Bake] ok %-58s 曲线=%d key=%d resampled=%s"
                   % (name, detail["curveCount"], detail["keyTotal"],
                      detail["resampled"]))

    remaining = len(pending) - len(batch)
    if remaining > 0:
        unreal.log("[Bake] 本批结束，还剩 %d 个。再执行同一条命令继续。" % remaining)
        return

    detail_map = progress.get("detail") or {}
    report = {
        "done": progress["done"],
        "missing": progress["missing"],
        "failed": progress["failed"],
        "keyTotal": sum(d.get("keyTotal", 0) for d in detail_map.values()),
        "resampled": [n for n, d in detail_map.items() if d.get("resampled")],
    }
    try:
        os.makedirs(os.path.dirname(REPORT_JSON), exist_ok=True)
        with open(REPORT_JSON, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
    except Exception as exc:
        unreal.log_warning("[Bake] 写报告失败: %s" % exc)

    unreal.log("[Bake] 全部完成：成功 %d，缺资产 %d，失败 %d，key 总量 %d"
               % (len(progress["done"]), len(progress["missing"]),
                  len(progress["failed"]), report["keyTotal"]))
    if report["resampled"]:
        unreal.log_warning("[Bake] 需要重采样（UE 帧数与 FBX 不一致）的 clip: %s"
                           % ", ".join(report["resampled"]))
    for d in progress["missing"]:
        unreal.log_warning("  缺资产: %s" % d["name"])
    for d in progress["failed"]:
        unreal.log_error("  失败: %s —— %s" % (d["name"], d.get("reason")))


run()
