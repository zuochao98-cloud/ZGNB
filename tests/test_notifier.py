"""
Z哥量化推送模块测试
"""

from unittest.mock import patch, MagicMock
from modules.notifier import escape_applescript_string, notify_macos, notify_feishu, notify_all


def test_escape_applescript():
    assert escape_applescript_string('hello "world"') == 'hello \\"world\\"'
    assert escape_applescript_string("it's ok") == "it\\'s ok"
    assert escape_applescript_string("back\\slash") == "back\\\\slash"


@patch("subprocess.run")
def test_notify_macos(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    res = notify_macos("测试标题", "测试内容")
    assert res is True
    mock_run.assert_called_once()

    # M4: 已收窄为 OSError/FileNotFoundError/CalledProcessError 等
    mock_run.side_effect = FileNotFoundError("AppleScript error")
    assert notify_macos("测试", "内容") is False


@patch("requests.post")
def test_notify_feishu(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    res = notify_feishu("https://fake-webhook.url", "标题", "消息")
    assert res is True
    mock_post.assert_called_once()

    # M4: 已收窄为 requests.RequestException/ConnectionError/TimeoutError
    mock_post.side_effect = ConnectionError("network error")
    assert notify_feishu("https://fake-webhook.url", "标题", "消息") is False


@patch("modules.notifier.notify_macos")
@patch("modules.notifier.notify_feishu")
@patch("os.uname")
def test_notify_all_mac(mock_uname, mock_feishu, mock_macos):
    # 模拟在 macOS (Darwin) 环境下
    mock_uname.return_value = MagicMock(sysname="Darwin")
    mock_macos.return_value = True
    mock_feishu.return_value = True

    res = notify_all("测试标题", "测试内容", webhook_url="https://fake-webhook.url")
    assert res["macos"] is True
    assert res["feishu"] is True
    mock_macos.assert_called_once()
    mock_feishu.assert_called_once()


@patch("modules.notifier.notify_macos")
@patch("modules.notifier.notify_feishu")
@patch("os.uname")
def test_notify_all_linux(mock_uname, mock_feishu, mock_macos):
    # 模拟在 Linux 环境下 (不触发 macOS 通知)
    mock_uname.return_value = MagicMock(sysname="Linux")
    mock_macos.return_value = True
    mock_feishu.return_value = True

    res = notify_all("测试标题", "测试内容", webhook_url="https://fake-webhook.url")
    assert res["macos"] is False
    assert res["feishu"] is True
    mock_macos.assert_not_called()
    mock_feishu.assert_called_once()
