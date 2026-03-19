#!/usr/bin/env python3
"""Shared config loading for xsh and xcp."""

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


@dataclass
class JumpInfo:
    host: str
    user: str
    password: Optional[str] = None
    port: int = 22


@dataclass
class ServerInfo:
    host: str
    user: str
    password: Optional[str] = None
    port: int = 22
    jump: Optional[JumpInfo] = None


DEFAULT_CONFIG = Path.home() / ".config" / "xsh" / "hosts.yaml"


def load_config(config_path: Path = DEFAULT_CONFIG) -> Dict[str, Any]:
    """Load and parse hosts.yaml. Exits with error message on failure."""
    if not config_path.exists():
        print(
            f"xsh: config file not found: {config_path}\n"
            f"Create it at {config_path} — see the design doc for an example.",
            file=sys.stderr,
        )
        sys.exit(1)

    mode = config_path.stat().st_mode & 0o777
    if mode & 0o044:  # group-readable or world-readable
        print(
            f"xsh warning: {config_path} has permissions {oct(mode)} — "
            "recommend chmod 600 to protect passwords.",
            file=sys.stderr,
        )

    try:
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        print(f"xsh: YAML parse error in {config_path}:\n{e}", file=sys.stderr)
        sys.exit(1)


def resolve_server(name: str, config: Dict[str, Any]) -> Optional[ServerInfo]:
    """Return ServerInfo for name, or None if not found. Exits on config errors."""
    servers = config.get("servers") or {}
    if name not in servers:
        return None

    raw = servers[name]
    jump = None

    if "jump" in raw:
        jump_name = raw["jump"]
        jumphosts = config.get("jumphosts") or {}
        if jump_name not in jumphosts:
            print(
                f"xsh: server '{name}' references unknown jumphost '{jump_name}'",
                file=sys.stderr,
            )
            sys.exit(1)
        j = jumphosts[jump_name]
        jump = JumpInfo(
            host=j["host"],
            user=j["user"],
            password=j.get("password"),
            port=int(j.get("port", 22)),
        )

    return ServerInfo(
        host=raw["host"],
        user=raw["user"],
        password=raw.get("password"),
        port=int(raw.get("port", 22)),
        jump=jump,
    )
