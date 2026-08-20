from __future__ import annotations

import os
import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class DemoLoginConfig:
    username: str
    password: str

    @property
    def enabled(self) -> bool:
        return bool(self.username and self.password)


def load_demo_login_config() -> DemoLoginConfig:
    """Shared demo login from env. Disabled when user or password is unset."""
    return DemoLoginConfig(
        username=os.environ.get("DEMO_LOGIN_USER", "").strip(),
        password=os.environ.get("DEMO_LOGIN_PASSWORD", "").strip(),
    )


def verify_demo_login(username: str, password: str, cfg: DemoLoginConfig) -> bool:
    if not cfg.enabled:
        return True
    user_ok = secrets.compare_digest(username.strip(), cfg.username)
    pass_ok = secrets.compare_digest(password, cfg.password)
    return user_ok and pass_ok
