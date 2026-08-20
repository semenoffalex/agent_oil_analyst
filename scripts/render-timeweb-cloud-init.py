#!/usr/bin/env python3
"""Render docker/cloud-init.yaml with secrets from .env (never commit output)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docker" / "cloud-init.yaml"
DEFAULT_OUT = ROOT / ".scratch" / "timeweb-cloud-init.rendered.yaml"

PLACEHOLDERS = (
    "REPLACE_DEEPSEEK_API_KEY",
    "REPLACE_OPENROUTER_API_KEY",
    "REPLACE_DEMO_LOGIN_USER",
    "REPLACE_DEMO_LOGIN_PASSWORD",
)

ENV_MAP = {
    "REPLACE_DEEPSEEK_API_KEY": "DEEPSEEK_API_KEY",
    "REPLACE_OPENROUTER_API_KEY": "OPENROUTER_API_KEY",
    "REPLACE_DEMO_LOGIN_USER": "DEMO_LOGIN_USER",
    "REPLACE_DEMO_LOGIN_PASSWORD": "DEMO_LOGIN_PASSWORD",
}


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    env = load_env(ROOT / ".env")
    text = TEMPLATE.read_text(encoding="utf-8")

    missing = [name for name in PLACEHOLDERS if not env.get(ENV_MAP[name], "").strip()]
    if missing:
        print("Missing values in .env:", ", ".join(ENV_MAP[m] for m in missing), file=sys.stderr)
        return 1

    for placeholder, key in ENV_MAP.items():
        text = text.replace(placeholder, env[key])

    if re.search(r"REPLACE_[A-Z0-9_]+", text):
        print("Unresolved REPLACE_* placeholders remain in output", file=sys.stderr)
        return 1

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
