from __future__ import annotations

import json
from pathlib import Path


EXAMPLE_PATH = Path("examples/example_chat.json")


def main() -> None:
    payload = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise SystemExit("example_chat.json must be a JSON object")

    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        raise SystemExit("example_chat.json must include non-empty messages list")

    first = messages[0]
    if not isinstance(first, dict):
        raise SystemExit("messages[0] must be an object")

    required_keys = {"type", "date", "from", "text"}
    missing = sorted(required_keys - set(first.keys()))
    if missing:
        raise SystemExit(f"messages[0] is missing keys: {', '.join(missing)}")


if __name__ == "__main__":
    main()
