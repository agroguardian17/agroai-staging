"""Live diagnostic tail for MQTT ingest failures.


Reads structlog JSON events off the backend's stdout via ``docker compose
logs -f app`` (or plain uvicorn stdout via a pipe) and prints a compact,
color-tagged line for every ``ingest_broker.*`` event plus every
pydantic validation error, so firmware devs can see exactly what the
backend rejected without grepping through raw JSON.


Usage::


    # Inside agro_backend/ with the dev stack up:
    docker compose -f docker-compose.dev.yml logs -f app | python scripts/dev/tail_ingest.py


    # Or against a raw uvicorn stdout pipe:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1 | python scripts/dev/tail_ingest.py


Filters (case-insensitive substrings in the ``event`` field):
* ``ingest_broker.``    - broker lifecycle + drops
* ``app.startup``       - config surface at boot (calibration_mode etc.)
* ``ingest_startup.``   - IngestBroker wiring log lines


Non-JSON stdout lines (paho debug etc.) are passed through untouched.


Zero dependencies beyond stdlib.
"""


from __future__ import annotations

import json
import sys
from typing import Any

COLORS: dict[str, str] = {
    "reset": "\033[0m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "cyan": "\033[36m",
    "magenta": "\033[35m",
}


INTERESTING_PREFIXES: tuple[str, ...] = (
    "ingest_broker.",
    "ingest_startup.",
    "app.startup",
    "app.shutdown",
)




def _colorize(event: str, level: str | None) -> str:
    if event.endswith((".error", "_failed", ".connect_failed", ".unexpected_error")):
        return f"{COLORS['red']}{event}{COLORS['reset']}"
    if "queue_full" in event or "validation_error" in event or "parse_error" in event:
        return f"{COLORS['yellow']}{event}{COLORS['reset']}"
    if event.startswith("app."):
        return f"{COLORS['magenta']}{event}{COLORS['reset']}"
    if level == "warning":
        return f"{COLORS['yellow']}{event}{COLORS['reset']}"
    if level == "error":
        return f"{COLORS['red']}{event}{COLORS['reset']}"
    return f"{COLORS['cyan']}{event}{COLORS['reset']}"




def _format_record(rec: dict[str, Any]) -> str:
    event = str(rec.get("event", ""))
    level = rec.get("level")
    ts = rec.get("timestamp", "")
    # Strip common noise keys so the interesting bits stand out.
    payload = {
        k: v
        for k, v in rec.items()
        if k not in {"event", "level", "timestamp", "logger", "logger_name"}
    }
    payload_str = " ".join(f"{k}={v!r}" for k, v in payload.items())
    return (
        f"{COLORS['dim']}{ts}{COLORS['reset']} "
        f"{_colorize(event, level)} "
        f"{payload_str}"
    )




def _is_interesting(rec: dict[str, Any]) -> bool:
    event = str(rec.get("event", ""))
    if event.startswith(INTERESTING_PREFIXES):
        return True
    # Also surface any error/warning across the app so ingest-adjacent
    # problems (DB timeout, missing plot FK) are visible.
    level = rec.get("level")
    return level in {"warning", "error", "critical"}




def main() -> int:
    for raw in sys.stdin:
        line = raw.rstrip("\n")
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            # Not structured JSON (paho debug, docker prefix, uvicorn header).
            # Pass through so nothing hides from the operator.
            print(line, flush=True)
            continue
        if not isinstance(rec, dict):
            print(line, flush=True)
            continue
        if _is_interesting(rec):
            print(_format_record(rec), flush=True)
    return 0




if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130) from None
