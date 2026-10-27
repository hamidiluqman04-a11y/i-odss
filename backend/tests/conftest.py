import json
from pathlib import Path

import pytest

from apps.datasets.csv_parser import parse_csv

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SAMPLE_FILES = sorted(p.name for p in FIXTURES.glob("*.csv"))


def load_sample(name):
    """Parse one of the sample CSV files with the new parser."""
    return parse_csv(name, (FIXTURES / name).read_bytes())


def load_legacy_snapshot(name):
    """Outputs the legacy FastAPI app produced for the same sample file."""
    path = FIXTURES / "legacy_snapshots" / name.replace(".csv", ".json")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(params=SAMPLE_FILES)
def sample(request):
    """Runs a test once per sample file: gives (parsed_csv, legacy_snapshot)."""
    return load_sample(request.param), load_legacy_snapshot(request.param)
