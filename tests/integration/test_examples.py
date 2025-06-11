import importlib
import sys
from pathlib import Path

import pytest
from starlette.testclient import TestClient

# ── 1.  Ensure the repo root is on sys.path *if* we can see the examples dir
ROOT = Path(__file__).resolve().parent.parent.parent  # project root
EXAMPLES_DIR = ROOT / "examples"
if EXAMPLES_DIR.exists() and str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))  # keeps import order deterministic


EXAMPLES = [
    "examples.simple_example",
    "examples.list_example",
    "examples.disabled_example",
    "examples.literal_enum_example",
    "examples.submit_validation_example",
    "examples.complex_example",
]


@pytest.mark.integration  # keeps separation from fast unit suite
@pytest.mark.parametrize("module_path", EXAMPLES, ids=lambda p: p.split(".")[-1])
def test_example_boots_and_serves_root(module_path):
    """Import the demo, wrap the FastHTML app in TestClient, hit GET /."""
    mod = importlib.import_module(module_path)

    # All demos expose `app, rt = fh.fast_app(...)`
    client = TestClient(mod.app)

    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
