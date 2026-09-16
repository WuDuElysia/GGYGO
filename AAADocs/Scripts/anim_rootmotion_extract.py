# -*- coding: utf-8 -*-
"""从 anim/*.fbx 的 Root 节点提取逐帧 root motion，与同名 per-clip JSON 的 muscleClip 标量合并，
输出一份供 UE 侧消费的中间数据文件。

为什么不直接用 JSON 的 rootMotionCurves：
    那 14 条曲线（MotionT/MotionQ/RootT/RootQ）共 33 万个 key 全为 0.0，四元数 w 也没有
    任何一帧接近 ±1，是未填充的占位数据。逐帧 root motion 只能从 FBX 取。

FBX 侧的 Root 节点语义（见 AAADocs/Pyrios_FBX_动画解读.md）：
    Root 是与骨架根 Bone_Root 同级的外部 Null，专门承载 gameplay root motion；
    位移已按 scaleFactorBakedIntoFbx=100 烤成厘米，旋转是度。

轴映射（FBX Y-up/Z-forward → UE Z-up/X-forward）：
    UE.X(前) = FBX.Z    UE.Y(右) = FBX.X    UE.Z(上) = FBX.Y
    UE.Yaw  = FBX.rotY  （FBX 绕 up 轴从 +Z 转向 +X，正好对应 UE 从 +X 转向 +Y）

用法：
    python anim_rootmotion_extract.py <anim目录> <输出json>
"""

import glob
import json
import math
import os
import sys

from fbx_bin_reader import FbxReader
from fbx_anim_extract import build_index, get_curve_arrays, resolve_take_curvenodes

FBXTIME = 46186158000.0
ROOT_NODE = "Root"

# muscleClip 里需要带到 UE 侧的标量（其余如 leftFootStartX 等足部对齐数据 UE 用不上）
MUSCLE_SCALARS = [
    "startTime", "stopTime", "orientationOffsetY", "level", "cycleOffset",
    "averageAngularSpeed", "mirror", "loopTime", "loopBlend",
    "loopBlendOrientation", "loopBlendPositionY", "loopBlendPositionXZ",
    "startAtOrigin", "keepOriginalOrientation", "keepOriginalPositionY",
    "keepOriginalPositionXZ", "heightFromFeet",
]


def unwrap_degrees(values):
    """把 ±180 折叠的角度序列展开成连续累计角，避免曲线插值时从 179 跳到 -179。"""
    if not values:
        return []
    out = [values[0]]
    offset = 0.0
    for prev, cur in zip(values, values[1:]):
        d = cur - prev
        if d > 180.0:
            offset -= 360.0
        elif d < -180.0:
            offset += 360.0
        out.append(cur + offset)
    return out


def resample_channel(times, values, frame_times):
    """把 FBX 曲线按目标帧时间线性重采样。FBX 的 Root 轨道本身就是逐帧烘焙，
    这一步主要负责补齐通道之间 key 数不一致的情况。"""
    if not times or not values:
        return [0.0] * len(frame_times)
    n = min(len(times), len(values))
    ts = [t / FBXTIME for t in times[:n]]
    vs = list(values[:n])
    out = []
    j = 0
    for ft in frame_times:
        while j + 1 < n and ts[j + 1] < ft:
            j += 1
        if ft <= ts[0]:
            out.append(vs[0])
        elif ft >= ts[-1]:
            out.append(vs[-1])
        else:
            t0, t1 = ts[j], ts[min(j + 1, n - 1)]
            v0, v1 = vs[j], vs[min(j + 1, n - 1)]
            a = 0.0 if t1 <= t0 else (ft - t0) / (t1 - t0)
            out.append(v0 + (v1 - v0) * a)
    return out


def read_root_tracks(fbx_path):
    """返回 (frame_times, {'tX':[..], 'tY':[..], 'tZ':[..], 'rX':[..], 'rY':[..], 'rZ':[..]})。
    读不到 Root 节点则返回 (None, None)。"""
    r = FbxReader(fbx_path)
    try:
        idx = build_index(r.parse())
        if not idx["stacks"]:
            return None, None
        # 单动作 FBX 只有一个 take
        stack_id = sorted(idx["stacks"].keys())[0]
        cn = resolve_take_curvenodes(idx, stack_id)
        node = cn.get(ROOT_NODE)
        if not node:
            return None, None

        raw = {}
        for prop, prefix in (("Lcl Translation", "t"), ("Lcl Rotation", "r")):
            for chan in ("X", "Y", "Z"):
                cur_id = node.get(prop, {}).get(chan)
                if cur_id is None:
                    raw[prefix + chan] = ([], [])
                else:
                    raw[prefix + chan] = get_curve_arrays(r.f, idx["curves"][cur_id])

        # 帧时间线取 key 数最多的通道；Root 的六条轨道通常等长且为 60fps 烘焙
        best = max(raw.values(), key=lambda tv: len(tv[0]))
        if not best[0]:
            return None, None
        frame_times = [t / FBXTIME for t in best[0]]
        t0 = frame_times[0]
        frame_times = [t - t0 for t in frame_times]

        tracks = {}
        for k, (times, values) in raw.items():
            shifted = [t / FBXTIME - t0 for t in times]
            tracks[k] = resample_channel(
                [t * FBXTIME for t in shifted], values, frame_times)
        return frame_times, tracks
    finally:
        r.close()


def build_clip_record(name, fbx_path, json_path):
    frame_times, tracks = read_root_tracks(fbx_path)
    if frame_times is None:
        return None, "FBX 中没有带曲线的 Root 节点"

    with open(json_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    clip = meta.get("clip") or {}
    muscle = clip.get("muscleClip") or {}

    # FBX 轴 → UE 轴
    pos_x = tracks["tZ"]          # UE 前
    pos_y = tracks["tX"]          # UE 右
    pos_z = tracks["tY"]          # UE 上
    yaw = unwrap_degrees(tracks["rY"])
    pitch = unwrap_degrees(tracks["rX"])
    roll = unwrap_degrees(tracks["rZ"])

    # 把位置/角度归零到首帧，让曲线表达“从本段起点的累计量”
    def rebase(seq):
        base = seq[0]
        return [v - base for v in seq]

    pos_x, pos_y, pos_z = rebase(pos_x), rebase(pos_y), rebase(pos_z)
    yaw, pitch, roll = rebase(yaw), rebase(pitch), rebase(roll)

    # 派生：累计路程、逐帧速度、水平速度方向
    dist = [0.0]
    for i in range(1, len(frame_times)):
        dist.append(dist[-1] + math.hypot(pos_x[i] - pos_x[i - 1],
                                          pos_y[i] - pos_y[i - 1]))
    speed = [0.0] * len(frame_times)
    dir_x = [0.0] * len(frame_times)
    dir_y = [0.0] * len(frame_times)
    for i in range(1, len(frame_times)):
        dt = frame_times[i] - frame_times[i - 1]
        if dt <= 1e-6:
            continue
        dx = pos_x[i] - pos_x[i - 1]
        dy = pos_y[i] - pos_y[i - 1]
        mag = math.hypot(dx, dy)
        speed[i] = mag / dt
        if mag > 1e-5:
            dir_x[i] = dx / mag
            dir_y[i] = dy / mag
    if len(speed) > 1:
        speed[0] = speed[1]
        dir_x[0], dir_y[0] = dir_x[1], dir_y[1]

    duration = frame_times[-1] if frame_times else 0.0

    # FBX take 比 Unity clip 多带一帧末尾重复帧：位移在前 N-1 个间隔内走完，
    # 末帧与前一帧完全相同。位移曲线保留这个重复值没问题（数值仍然正确），
    # 但差分出的速度/方向会在末帧掉到 0，运行时表现为最后一帧速度突降。
    # 判据用“FBX 时长恰好比 muscleClip 长一帧”，这样只命中导出多出来的那一帧，
    # 不会误伤真正在末尾停下的动画（如 Walk_End）。
    clip_len = float(muscle.get("stopTime", 0.0)) - float(muscle.get("startTime", 0.0))
    frame_dt = 1.0 / float(clip.get("sampleRate") or 60.0)
    trailing_dup = (len(frame_times) >= 3
                    and abs(duration - clip_len - frame_dt) < 1e-4)
    if trailing_dup:
        speed[-1] = speed[-2]
        dir_x[-1], dir_y[-1] = dir_x[-2], dir_y[-2]

    # 交叉校验：JSON 的 averageSpeed（m/s，Unity 轴）与 FBX 位移导出的平均速度（cm/s）
    avg = muscle.get("averageSpeed") or {}
    json_speed_cms = math.sqrt(avg.get("x", 0.0) ** 2 + avg.get("y", 0.0) ** 2
                               + avg.get("z", 0.0) ** 2) * 100.0
    fbx_speed_cms = (math.hypot(pos_x[-1], pos_y[-1]) / duration) if duration > 0 else 0.0
    json_yaw_deg = math.degrees(muscle.get("averageAngularSpeed", 0.0) * duration)

    # 诊断：速度峰值与最大单帧位移跳变，用于发现导出瑕疵造成的假峰值
    peak_speed = max(speed) if speed else 0.0
    peak_frame = speed.index(peak_speed) if speed else 0
    max_step = 0.0
    for i in range(1, len(frame_times)):
        max_step = max(max_step, math.hypot(pos_x[i] - pos_x[i - 1],
                                            pos_y[i] - pos_y[i - 1]))

    record = {
        "name": name,
        "duration": duration,
        "clipLength": clip_len,
        "trailingDuplicateFrame": trailing_dup,
        "frameCount": len(frame_times),
        "sampleRate": clip.get("sampleRate"),
        "times": frame_times,
        "curves": {
            "RootMotion_PosX": pos_x,
            "RootMotion_PosY": pos_y,
            "RootMotion_PosZ": pos_z,
            "RootMotion_Yaw": yaw,
            "RootMotion_Pitch": pitch,
            "RootMotion_Roll": roll,
            "RootMotion_Dist": dist,
            "RootMotion_Speed": speed,
            "RootMotion_DirX": dir_x,
            "RootMotion_DirY": dir_y,
        },
        "scalars": {k: muscle.get(k) for k in MUSCLE_SCALARS if k in muscle},
        "averageSpeed": avg,
        "verify": {
            "jsonAvgSpeedCms": json_speed_cms,
            "fbxAvgSpeedCms": fbx_speed_cms,
            "jsonYawDeg": json_yaw_deg,
            "fbxYawDeg": yaw[-1] if yaw else 0.0,
            "peakSpeedCms": peak_speed,
            "peakSpeedFrame": peak_frame,
            "maxFrameStepCm": max_step,
            "pathLengthCm": dist[-1] if dist else 0.0,
        },
    }
    record["scalars"]["hasMotionFloatCurves"] = clip.get("hasMotionFloatCurves")
    record["scalars"]["wrapMode"] = clip.get("wrapMode")
    return record, None


def main():
    anim_dir = sys.argv[1] if len(sys.argv) > 1 else \
        r"F:\AnimeStudio\Exports\ZZZ\Avatar_Male_Size03_Pyrois_Model\anim"
    out_path = sys.argv[2] if len(sys.argv) > 2 else \
        r"F:\ue_project\GGYGO\Saved\AnimRootMotion\Pyrios_RootMotion.json"

    fbx_files = sorted(glob.glob(os.path.join(anim_dir, "*.fbx")))
    records = []
    skipped = []
    for i, fbx in enumerate(fbx_files, 1):
        name = os.path.splitext(os.path.basename(fbx))[0]
        js = os.path.join(anim_dir, name + ".json")
        if not os.path.exists(js):
            skipped.append((name, "缺少同名 json"))
            continue
        try:
            rec, err = build_clip_record(name, fbx, js)
        except Exception as exc:  # 解析失败不应中断整批
            rec, err = None, "解析异常: %s" % exc
        if rec is None:
            skipped.append((name, err))
            print("[%3d/%d] 跳过 %s —— %s" % (i, len(fbx_files), name, err))
            continue
        records.append(rec)
        v = rec["verify"]
        print("[%3d/%d] %-58s fbxLen=%.3f clipLen=%.3f dup=%d frames=%3d "
              "path=%8.1f peak=%7.1f@%3d step=%6.2f yaw=%7.1f"
              % (i, len(fbx_files), name, rec["duration"], rec["clipLength"],
                 1 if rec["trailingDuplicateFrame"] else 0, rec["frameCount"],
                 v["pathLengthCm"], v["peakSpeedCms"], v["peakSpeedFrame"],
                 v["maxFrameStepCm"], v["fbxYawDeg"]))

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"model": "Avatar_Male_Size03_Pyrois_Model",
                   "clips": records}, f)
    print("\n写出 %d 个 clip -> %s" % (len(records), out_path))

    dup = [r["name"] for r in records if r["trailingDuplicateFrame"]]
    print("末尾重复帧（FBX 比 muscleClip 长恰好一帧）的 clip 数 = %d / %d"
          % (len(dup), len(records)))
    other = [(r["duration"] - r["clipLength"], r["name"]) for r in records
             if not r["trailingDuplicateFrame"]]
    if other:
        print("其余 clip 的 FBX 时长 - clipLength 差值分布:")
        for d, n in sorted(other, reverse=True)[:8]:
            print("   %+.4f  %s" % (d, n))

    print("\n速度峰值最大的 8 个（检查是否有导出瑕疵造成的假峰值）:")
    for r in sorted(records, key=lambda x: -x["verify"]["peakSpeedCms"])[:8]:
        v = r["verify"]
        print("   peak=%8.1f cm/s @frame %3d  maxStep=%6.2f cm  path=%8.1f  %s"
              % (v["peakSpeedCms"], v["peakSpeedFrame"], v["maxFrameStepCm"],
                 v["pathLengthCm"], r["name"]))

    if skipped:
        print("跳过 %d 个:" % len(skipped))
        for n, why in skipped:
            print("   %s —— %s" % (n, why))


if __name__ == "__main__":
    main()
