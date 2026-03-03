from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from chat_analyzer_api.main import app


def patch_binary_string_formats(value: Any) -> None:
    if isinstance(value, dict):
        content_media_type = value.get("contentMediaType")
        if (
            value.get("type") == "string"
            and isinstance(content_media_type, str)
            and content_media_type
            and "format" not in value
        ):
            value["format"] = "binary"

        for nested in value.values():
            patch_binary_string_formats(nested)
        return

    if isinstance(value, list):
        for nested in value:
            patch_binary_string_formats(nested)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    target = repo_root / "packages" / "api-contracts" / "openapi" / "openapi.json"
    target.parent.mkdir(parents=True, exist_ok=True)

    schema = app.openapi()
    patch_binary_string_formats(schema)
    target.write_text(json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
