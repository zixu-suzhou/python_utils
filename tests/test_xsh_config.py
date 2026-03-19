# tests/test_xsh_config.py
import textwrap
import pytest
from pathlib import Path
from xsh_config import load_config, resolve_server, ServerInfo, JumpInfo

SAMPLE_YAML = textwrap.dedent("""\
    jumphosts:
      jmp1:
        host: 10.190.161.169
        user: env1szh
        password: "jumppass"
        port: 22

    servers:
      bench01:
        host: 10.178.235.54
        user: root
        port: 22

      zeekr:
        host: 198.18.36.1
        user: root
        password: "targetpass"
        jump: jmp1
""")


@pytest.fixture
def config_file(tmp_path):
    p = tmp_path / "hosts.yaml"
    p.write_text(SAMPLE_YAML)
    p.chmod(0o600)
    return p


def test_load_config_returns_dict(config_file):
    cfg = load_config(config_file)
    assert "servers" in cfg
    assert "jumphosts" in cfg


def test_resolve_unknown_server_returns_none(config_file):
    cfg = load_config(config_file)
    assert resolve_server("nonexistent", cfg) is None


def test_resolve_direct_server_no_password(config_file):
    cfg = load_config(config_file)
    info = resolve_server("bench01", cfg)
    assert isinstance(info, ServerInfo)
    assert info.host == "10.178.235.54"
    assert info.user == "root"
    assert info.port == 22
    assert info.password is None
    assert info.jump is None


def test_resolve_server_with_jump_and_passwords(config_file):
    cfg = load_config(config_file)
    info = resolve_server("zeekr", cfg)
    assert isinstance(info, ServerInfo)
    assert info.password == "targetpass"
    assert isinstance(info.jump, JumpInfo)
    assert info.jump.host == "10.190.161.169"
    assert info.jump.password == "jumppass"


def test_load_config_missing_file_raises():
    with pytest.raises(SystemExit):
        load_config(Path("/nonexistent/hosts.yaml"))


def test_load_config_bad_yaml_raises(tmp_path):
    p = tmp_path / "hosts.yaml"
    p.write_text("{ bad: yaml: [")
    p.chmod(0o600)
    with pytest.raises(SystemExit):
        load_config(p)


def test_unknown_jump_reference_raises(tmp_path):
    p = tmp_path / "hosts.yaml"
    p.write_text(textwrap.dedent("""\
        servers:
          broken:
            host: 1.2.3.4
            user: root
            jump: doesnotexist
    """))
    p.chmod(0o600)
    cfg = load_config(p)
    with pytest.raises(SystemExit):
        resolve_server("broken", cfg)


def test_bad_permissions_prints_warning(tmp_path, capsys):
    p = tmp_path / "hosts.yaml"
    p.write_text(SAMPLE_YAML)
    p.chmod(0o644)  # world-readable
    load_config(p)  # should not raise, just warn
    captured = capsys.readouterr()
    assert "warning" in captured.err.lower() or "permission" in captured.err.lower()
