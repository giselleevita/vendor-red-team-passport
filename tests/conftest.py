import sys
from pathlib import Path

# Allow running `pytest` without editable install by ensuring repo root is on sys.path.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

