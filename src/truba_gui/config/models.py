from dataclasses import dataclass
from dataclasses import field
from typing import Any

@dataclass
class SSHConfig:
    host: str = ""
    port: int = 22
    username: str = ""
    password: str = ""
    key_path: str = ""
    host_key_policy: str = "accept-new"  # accept-new | strict
    x11_forwarding: bool = False
    dry_run: bool = False  # mock backend
    keepalive_interval_seconds: int = 30  # 0 disables; clamped to 0..3600
    system_settings: dict[str, Any] = field(default_factory=dict)

@dataclass
class AppConfig:
    language: str = "tr"
