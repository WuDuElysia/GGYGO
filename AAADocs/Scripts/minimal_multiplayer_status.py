"""@file minimal_multiplayer_status.py @brief 双端进度采用单写者追加，读者只消费完整 JSON 行。"""
import json


def append_status(filename, state):
    # Windows 上替换文件会与另一端的普通读句柄冲突；追加不需要删除共享权限。
    with filename.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(state, ensure_ascii=False, allow_nan=False) + "\n")


def read_status(filename):
    with filename.open("rb") as stream:
        cursor = stream.seek(0, 2)
        tail = b""
        while cursor:
            start = max(0, cursor - 4096)
            stream.seek(start)
            tail = stream.read(cursor - start) + tail
            cursor = start
            # 第一个片段可能从行中间开始，至少两条行边界才能取得最后完整行。
            if tail.count(b"\n") >= 2:
                break
    lines = tail.split(b"\n")
    return json.loads(lines[-2]) if len(lines) >= 2 else None
