r"""
Re-generates the baseline snapshot files.

Run this ONLY if you deliberately want to record new legacy behaviour:
    .venv\Scripts\python legacy\tests\make_snapshots.py
"""
import json

from conftest import SAMPLE_FILES, SNAPSHOTS, capture_outputs, main
from fastapi.testclient import TestClient

client = TestClient(main.app)
SNAPSHOTS.mkdir(exist_ok=True)
for name in SAMPLE_FILES:
    data = capture_outputs(client, name)
    path = SNAPSHOTS / name.replace(".csv", ".json")
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", path.name)
