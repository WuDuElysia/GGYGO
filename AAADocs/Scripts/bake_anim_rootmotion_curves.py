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
import hashlib
import time
from pathlib import Path

import unreal

MODE = "all"

# all 模式每次执行最多处理这么多 clip，然后返回。已完成的 clip 记在 PROGRESS_JSON 里，
# 重复执行同一条命令会接着往下做。分批是因为写曲线会占住游戏线程，
# 一次跑完 119 个会让编辑器长时间无响应，中途中断还会丢掉进度。
# 成功缓存绑定源记录/本脚本/配置/磁盘资产指纹；失败和缺失下次自动重试。
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


PROGRESS_SCHEMA = 2


def source_fingerprint(record):
    payload = {'record': record, 'motion_curves': MOTION_CURVES,
               'scalar_curves': SCALAR_CURVES, 'folder': ANIM_FOLDER,
               'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode('utf-8')).hexdigest()


def asset_fingerprint(asset_path):
    """Hash persisted package bytes, including optional bulk sidecars. Missing is never cached."""
    if not asset_path.startswith('/Game/'):
        raise ValueError('Only /Game animation packages are supported')
    root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())).resolve()
    package = (root / (asset_path[len('/Game/'):] + '.uasset')).resolve()
    if not package.is_relative_to(root):
        raise ValueError('Asset path escapes project content')
    if not package.is_file():
        return None
    digest = hashlib.sha256()
    for suffix in ('.uasset', '.uexp', '.ubulk'):
        part = package.with_suffix(suffix)
        digest.update(suffix.encode())
        if part.is_file():
            with part.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
        else:
            digest.update(b'<absent>')
    return digest.hexdigest()


def cached_success(entry, source_hash, asset_hash):
    return bool(asset_hash and entry.get('status') == 'saved'
                and entry.get('source_fingerprint') == source_hash
                and entry.get('asset_fingerprint') == asset_hash)


def load_progress():
    try:
        with open(PROGRESS_JSON, 'r', encoding='utf-8') as stream:
            data = json.load(stream)
        if data.get('schema') == PROGRESS_SCHEMA and isinstance(data.get('entries'), dict):
            return data
    except (OSError, ValueError):
        pass
    # Legacy clip-name-only completion records cannot prove current asset validity.
    return {'schema': PROGRESS_SCHEMA, 'entries': {}}


def save_progress(progress):
    path = Path(PROGRESS_JSON)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(progress, ensure_ascii=False, indent=1), encoding='utf-8')
    temporary.replace(path)


def save_verified_asset(anim, asset_path):
    if not unreal.EditorAssetLibrary.save_loaded_asset(anim, False):
        raise RuntimeError('save_loaded_asset returned False: ' + asset_path)
    fingerprint = asset_fingerprint(asset_path)
    if fingerprint is None:
        raise RuntimeError('Save returned True but package file is missing: ' + asset_path)
    return fingerprint


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
    entries = progress['entries']
    # Protect live edits; a disk fingerprint does not describe an unsaved editor package.
    dirty = {package.get_name() for package in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    current = {}
    pending = []
    for record in records:
        name = record['name']
        asset_path = ANIM_FOLDER + '/' + name
        source_hash = source_fingerprint(record)
        disk_hash = asset_fingerprint(asset_path)
        current[name] = (source_hash, disk_hash)
        if asset_path in dirty or not cached_success(entries.get(name, {}), source_hash, disk_hash):
            pending.append(record)
    # Failed first items must not starve clips that have never been attempted.
    pending.sort(key=lambda record: entries.get(record['name'], {}).get('last_attempt', 0))
    batch = pending[:BATCH_SIZE]
    for record in batch:
        name = record['name']
        path = ANIM_FOLDER + '/' + name
        entry = {'source_fingerprint': current[name][0], 'last_attempt': time.time_ns()}
        entries[name] = entry
        try:
            if path in dirty:
                raise RuntimeError('Unsaved editor package preserved; save/discard deliberately before retry')
            status, detail = bake_clip(record)
            entry['detail'] = detail
            if status != 'ok':
                entry.update(status='missing', reason=detail.get('reason', status))
            else:
                anim = unreal.load_asset(path)
                entry['asset_fingerprint'] = save_verified_asset(anim, path)
                entry['status'] = 'saved'
        except Exception as exc:
            entry.update(status='failed', reason=str(exc))
            unreal.log_error('[Bake] %s failed, retryable: %s' % (name, exc))
        save_progress(progress)

    done, missing, failed, waiting = [], [], [], []
    for record in records:
        name = record['name']
        entry = entries.get(name, {})
        if cached_success(entry, current[name][0], asset_fingerprint(ANIM_FOLDER + '/' + name)) and ANIM_FOLDER + '/' + name not in dirty:
            done.append(name)
        elif entry.get('status') in ('missing', 'failed'):
            row = {'name': name, 'reason': entry.get('reason', '')}
            (missing if entry['status'] == 'missing' else failed).append(row)
        else:
            waiting.append(name)
    report = {'complete': len(done) == len(records), 'done': done, 'missing': missing,
              'failed': failed, 'pending': waiting, 'attempted_this_run': len(batch),
              'keyTotal': sum(entries[name].get('detail', {}).get('keyTotal', 0) for name in done)}
    Path(REPORT_JSON).parent.mkdir(parents=True, exist_ok=True)
    Path(REPORT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    unreal.log('[Bake] persisted=%d missing=%d failed=%d pending=%d complete=%s; failures/missing retry next run'
               % (len(done), len(missing), len(failed), len(waiting), report['complete']))
    return report


if __name__ == '__main__':
    run()
