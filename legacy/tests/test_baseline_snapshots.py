"""
Baseline (snapshot) tests: the legacy app must still return exactly the
outputs recorded in tests/snapshots/. If one of these fails, legacy
behaviour changed — which should never happen by accident.
"""
import json

import pytest

from conftest import SAMPLE_FILES, SNAPSHOTS, capture_outputs


@pytest.mark.parametrize("name", SAMPLE_FILES)
def test_outputs_match_snapshot(client, name):
    expected = json.loads((SNAPSHOTS / name.replace(".csv", ".json")).read_text(encoding="utf-8"))
    actual = capture_outputs(client, name)
    for key in expected:
        assert actual[key] == expected[key], f"{name}: '{key}' differs from baseline"
