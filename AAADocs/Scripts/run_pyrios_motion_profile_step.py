"""UE commandlet entry: execute exactly one frozen Pyrios Profile author step.

This coordinator utility never builds curves, saves assets itself, batches steps,
changes formal MovementSet wiring, or retries a failed/occupied report.
"""
import hashlib
from pathlib import Path
import runpy
import sys

AUTHOR = Path("F:/ue_project/GGYGO/AAADocs/Scripts/create_pyrios_walk_motion_profiles.py")
AUTHOR_SHA256 = "098c9eaeba204f47df5c24ca9ba3b044b6f73d2072d0430dedf8158938aea424"
ENTRY = {
    "RunLoop": "create_run_loop",
    "StartStop": "create_start_stop",
    "WalkStop": "create_walk_stop",
    "RunStop": "create_run_stop",
    "TurnBack": "create_turn_back",
}

if len(sys.argv) != 2 or sys.argv[1] not in ENTRY:
    raise RuntimeError("[GGYGO.ProfileCommandlet] Required one explicit fixed Profile step.")
if hashlib.sha256(AUTHOR.read_bytes()).hexdigest() != AUTHOR_SHA256:
    raise RuntimeError("[GGYGO.ProfileCommandlet] Frozen native-author orchestration script changed.")
api = runpy.run_path(str(AUTHOR))
result = api[ENTRY[sys.argv[1]]]()
if result["status"] != "passed":
    raise RuntimeError("[GGYGO.ProfileCommandlet] Step did not produce a passed native receipt.")
