# tests/test_xcp.py
import pytest
from unittest.mock import patch, MagicMock
from xcp import is_remote_token, parse_xcp_args, _exec_scp, _extract_positional
from xsh_config import ServerInfo, JumpInfo


# --- is_remote_token ---

def test_server_colon_path_is_remote():
    assert is_remote_token("bench01:/tmp/foo") is True

def test_server_colon_empty_path_is_remote():
    assert is_remote_token("bench01:") is True

def test_dotslash_prefix_is_local():
    assert is_remote_token("./log:data") is False

def test_absolute_path_is_local():
    assert is_remote_token("/tmp/file:backup") is False

def test_plain_local_file_is_local():
    assert is_remote_token("myfile.txt") is False

def test_relative_subdir_colon_is_local():
    assert is_remote_token("subdir/file:foo") is False


# --- parse_xcp_args ---

def test_parse_upload():
    flags, local, remotes = parse_xcp_args(["file.txt", "bench01:/tmp/"])
    assert flags == []
    assert local == ["file.txt"]
    assert remotes == [("bench01", "/tmp/", "bench01:/tmp/")]

def test_parse_recursive_flag():
    flags, local, remotes = parse_xcp_args(["-r", "dir/", "zeekr:/dest/"])
    assert "-r" in flags
    assert local == ["dir/"]

def test_parse_download():
    flags, local, remotes = parse_xcp_args(["zeekr:/data/file.txt", "./"])
    assert remotes == [("zeekr", "/data/file.txt", "zeekr:/data/file.txt")]
    assert local == ["./"]

def test_parse_no_remote_gives_empty_remotes():
    flags, local, remotes = parse_xcp_args(["file1.txt", "file2.txt"])
    assert remotes == []
    assert local == ["file1.txt", "file2.txt"]


# --- _exec_scp command building ---

def _direct_server(password=None):
    return ServerInfo(host="10.0.0.1", user="root", password=password, port=22)


def _jump_server(target_pw=None, jump_pw=None):
    jump = JumpInfo(host="10.0.0.2", user="jumper", password=jump_pw)
    return ServerInfo(host="10.0.0.1", user="root", password=target_pw, jump=jump)


def test_exec_scp_no_password_calls_execvp():
    server_map = {"bench01": _direct_server()}
    with patch("os.execvp") as mock_exec:
        _exec_scp(server_map, [], ["file.txt", "bench01:/tmp/"])
        mock_exec.assert_called_once()
        cmd = mock_exec.call_args[0][1]
        assert "scp" in cmd
        assert "root@10.0.0.1:/tmp/" in cmd


def test_exec_scp_with_password_uses_sshpass():
    server_map = {"zeekr": _direct_server(password="secret")}
    with patch("subprocess.run") as mock_run, \
         patch("sys.exit"), \
         patch("xcp._check_sshpass"):
        mock_run.return_value = MagicMock(returncode=0)
        _exec_scp(server_map, ["-r"], ["dir/", "zeekr:/dest/"])
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "sshpass"
        assert "scp" in cmd
        assert "root@10.0.0.1:/dest/" in cmd
        assert "-r" in cmd


def test_exec_scp_jump_both_passwords():
    server_map = {"zeekr": _jump_server(target_pw="tp", jump_pw="jp")}
    with patch("subprocess.run") as mock_run, \
         patch("sys.exit"), \
         patch("xcp._check_sshpass"):
        mock_run.return_value = MagicMock(returncode=0)
        _exec_scp(server_map, [], ["file.txt", "zeekr:/tmp/"])
        cmd = mock_run.call_args[0][0]
        proxy_val = cmd[cmd.index("-o") + 1]
        assert "sshpass" in proxy_val
        assert "sshpass" in cmd[0]


# --- _extract_positional ---

def test_extract_positional_preserves_order_download():
    # remote token comes first, local last — order must be preserved
    result = _extract_positional(["zeekr:/data/file.txt", "./"])
    assert result == ["zeekr:/data/file.txt", "./"]

def test_extract_positional_preserves_order_upload():
    result = _extract_positional(["file.txt", "bench01:/tmp/"])
    assert result == ["file.txt", "bench01:/tmp/"]

def test_extract_positional_skips_flags_and_their_values():
    # -P consumes its value; -r is a boolean flag
    result = _extract_positional(["-r", "-P", "2222", "zeekr:/src/", "./dst/"])
    assert result == ["zeekr:/src/", "./dst/"]

def test_extract_positional_flag_only():
    result = _extract_positional(["-r", "-v"])
    assert result == []

def test_extract_positional_flag_between_positionals():
    # Flags interspersed between positional args must not affect positional order
    result = _extract_positional(["file.txt", "-P", "2222", "bench01:/tmp/"])
    assert result == ["file.txt", "bench01:/tmp/"]


# --- download ordering in _exec_scp ---

def test_exec_scp_download_order_preserved():
    """Remote token first → stays first in scp cmd (download, not upload)."""
    server_map = {"zeekr": _direct_server()}
    with patch("os.execvp") as mock_exec:
        _exec_scp(server_map, [], ["zeekr:/data/file.txt", "./"])
        cmd = mock_exec.call_args[0][1]
        remote_idx = cmd.index("root@10.0.0.1:/data/file.txt")
        local_idx = cmd.index("./")
        assert remote_idx < local_idx, "remote source must precede local dest for a download"


def test_exec_scp_recursive_download():
    """xcp -r zeekr:/data/dir ./ — recursive flag forwarded and order correct."""
    server_map = {"zeekr": _direct_server(password="pw")}
    with patch("subprocess.run") as mock_run, \
         patch("sys.exit"), \
         patch("xcp._check_sshpass"):
        mock_run.return_value = MagicMock(returncode=0)
        _exec_scp(server_map, ["-r"], ["zeekr:/data/dir", "./"])
        cmd = mock_run.call_args[0][0]
        assert "-r" in cmd
        remote_idx = cmd.index("root@10.0.0.1:/data/dir")
        local_idx = cmd.index("./")
        assert remote_idx < local_idx, "remote source must precede local dest for a recursive download"
