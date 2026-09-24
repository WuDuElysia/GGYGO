"""Bind the existing Pyrios material instances to its skeletal mesh defaults."""
import runpy
from pathlib import Path

builder = runpy.run_path(str(Path(__file__).with_name("build_pyrios_materials.py")),
                         run_name="pyrios_material_library")
builder["bind_editor_preview_materials"]()
