from __future__ import annotations

import re

from apps.api.services.featherless_client import FeatherlessClient


def main() -> None:
    with FeatherlessClient() as c:
        models = c.list_models()

    # Prefer instruct/chat style models for this benchmark.
    instruct = [m for m in models if re.search(r"(instruct|chat)", m, flags=re.IGNORECASE)]
    print(f"total_models={len(models)}")
    print(f"instruct_like={len(instruct)}")

    for m in instruct[:60]:
        print(m)


if __name__ == "__main__":
    main()

