"""@file test_minimal_multiplayer_status.py @brief 回归 Windows 双端状态文件读写冲突。"""
import json
import multiprocessing
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from minimal_multiplayer_status import append_status, read_status


def writer(filename):
    for index in range(200):
        append_status(Path(filename), dict(index=index, payload="中文" * 2100))


class StatusTests(unittest.TestCase):
    def test_open_reader_does_not_block_publication(self):
        with tempfile.TemporaryDirectory() as folder:
            filename = Path(folder) / "state.jsonl"
            append_status(filename, dict(index=0))
            with filename.open("rb") as reader:
                append_status(filename, dict(index=1))
                self.assertIn(b'"index": 1', reader.read())
            self.assertEqual(read_status(filename), dict(index=1))

    def test_partial_last_line_is_not_a_status(self):
        with tempfile.TemporaryDirectory() as folder:
            filename = Path(folder) / "state.jsonl"
            filename.write_bytes(b'{"index": 0}\n{"index":')
            self.assertEqual(read_status(filename), dict(index=0))
            filename.write_bytes(b'{"index":')
            self.assertIsNone(read_status(filename))

    def test_separate_process_read_while_appending_large_unicode_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            filename = Path(folder) / "state.jsonl"
            append_status(filename, dict(index=-1))
            process = multiprocessing.Process(target=writer, args=(str(filename),))
            process.start()
            previous = -1
            deadline = time.monotonic() + 20
            while process.is_alive() and time.monotonic() < deadline:
                state = read_status(filename)
                self.assertGreaterEqual(state["index"], previous)
                previous = state["index"]
            process.join(5)
            self.assertEqual(process.exitcode, 0)
            self.assertEqual(read_status(filename)["index"], 199)
            rows = [json.loads(row) for row in filename.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([row["index"] for row in rows], list(range(-1, 200)))


if __name__ == "__main__":
    unittest.main()
