# tests/test_xsh.py
import pytest
from unittest.mock import patch, MagicMock
from xsh import parse_xsh_args, _exec_ssh, _build_proxy_command
from xsh_config import ServerInfo, JumpInfo


def test_simple_server_name():
    flags, server, remote_cmd = parse_xsh_args(["bench01"])
    assert flags == []
    assert server == "bench01"
    assert remote_cmd == []


def test_flags_before_server():
    flags, server, remote_cmd = parse_xsh_args(["-v", "-o", "StrictHostKeyChecking=no", "zeekr"])
    assert flags == ["-v", "-o", "StrictHostKeyChecking=no"]
    assert server == "zeekr"
    assert remote_cmd == []


def test_remote_command():
    flags, server, remote_cmd = parse_xsh_args(["bench01", "ls", "/tmp"])
    assert flags == []
    assert server == "bench01"
    assert remote_cmd == ["ls", "/tmp"]


def test_flags_and_remote_command():
    flags, server, remote_cmd = parse_xsh_args(["-v", "zeekr", "echo hello"])
    assert flags == ["-v"]
    assert server == "zeekr"
    assert remote_cmd == ["echo hello"]


def test_no_args_raises():
    with pytest.raises(SystemExit):
        parse_xsh_args([])


def _make_direct_server(password=None, port=22):
    return ServerInfo(host="10.0.0.1", user="root", password=password, port=port)


def _make_jump_server(target_password=None, jump_password=None):
    jump = JumpInfo(host="10.0.0.2", user="jumper", password=jump_password, port=22)
    return ServerInfo(host="10.0.0.1", user="root", password=target_password, jump=jump)


def test_build_proxy_command_no_jump_password():
    jump = JumpInfo(host="10.0.0.2", user="jumper")
    result = _build_proxy_command(jump, jump_tmp=None)
    assert result == "ssh -W %h:%p jumper@10.0.0.2"


def test_build_proxy_command_with_jump_password():
    jump = JumpInfo(host="10.0.0.2", user="jumper", password="pw")
    result = _build_proxy_command(jump, jump_tmp="/tmp/xsh_abc")
    assert "sshpass -f /tmp/xsh_abc" in result
    assert "ssh -W %h:%p" in result


def test_exec_ssh_no_password_calls_execvp():
    info = _make_direct_server()
    with patch("os.execvp") as mock_exec:
        _exec_ssh(info, [], [])
        mock_exec.assert_called_once()
        cmd = mock_exec.call_args[0][1]
        assert cmd[0] == "ssh"
        assert "root@10.0.0.1" in cmd


def test_exec_ssh_with_password_calls_subprocess(tmp_path):
    info = _make_direct_server(password="secret")
    with patch("subprocess.run") as mock_run, \
         patch("sys.exit") as mock_exit, \
         patch("xsh._check_sshpass"):
        mock_run.return_value = MagicMock(returncode=0)
        _exec_ssh(info, [], [])
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "sshpass" in cmd[0]
        assert "ssh" in cmd
        mock_exit.assert_called_with(0)


def test_exec_ssh_jump_both_passwords_calls_subprocess():
    info = _make_jump_server(target_password="tpass", jump_password="jpass")
    with patch("subprocess.run") as mock_run, \
         patch("sys.exit") as mock_exit, \
         patch("xsh._check_sshpass"):
        mock_run.return_value = MagicMock(returncode=0)
        _exec_ssh(info, [], [])
        cmd = mock_run.call_args[0][0]
        proxy_idx = cmd.index("-o") + 1
        assert "sshpass" in cmd[proxy_idx]   # jump password in ProxyCommand
        assert "sshpass" in cmd[0]           # target password via outer sshpass
