from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.config import get_settings
from apps.api.services.orchestrator import run_orchestrated
from apps.api.services.run_store import load_passport


def main() -> None:
    settings = get_settings()
    run_id = "latest"
    model = settings.default_model

    # Full suite by default; a9_mode="auto" picks strict only if enforcement is proven.
    run_orchestrated(model=model, only_classes=None, a9_mode="auto", run_id=run_id)
    passport = load_passport(run_id)
    if passport is None:
        raise SystemExit("failed to load generated passport")

    # Also write a convenience pointer.
    out_path = Path("reports/passports/passport.latest.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(passport.model_dump(), indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
