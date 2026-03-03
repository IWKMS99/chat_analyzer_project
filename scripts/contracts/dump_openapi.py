from __future__ import annotations

import json
from pathlib import Path

from chat_analyzer_api.main import app


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    target = repo_root / "packages" / "api-contracts" / "openapi" / "openapi.json"
    target.parent.mkdir(parents=True, exist_ok=True)

    schema = app.openapi()
    target.write_text(json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
