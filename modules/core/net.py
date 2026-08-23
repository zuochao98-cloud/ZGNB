"""
网络相关公共函数
"""

import os


def disable_proxy() -> None:
    """
    禁用 HTTP/HTTPS 代理

    用于避免 Tushare 等数据源的连接问题。
    """
    os.environ["HTTP_PROXY"] = ""
    os.environ["HTTPS_PROXY"] = ""


__all__ = ["disable_proxy"]
