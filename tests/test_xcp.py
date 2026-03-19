# tests/test_xcp.py
import pytest
from unittest.mock import patch, MagicMock
from xcp import is_remote_token, parse_xcp_args, _exec_scp
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
