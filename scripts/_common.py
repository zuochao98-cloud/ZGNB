"""
scripts/ 共享工具模块
v2.10.0 提取：消除 4 个薄壳脚本中重复的 _load_watchlist()
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# 项目根目录（scripts/ 的父目录）
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_watchlist() -> list[str]:
    """
    读取自选股清单，返回 ts_code 列表（如 ['600519.SH', '000001.SZ']）。

    路径优先级：STOCKS_JSON env > data/stocks_final.json
    JSON 格式：[{code, name}, ...]，code 为纯数字（6开头→.SH，其余→.SZ）
    """
    path = os.environ.get("STOCKS_JSON") or str(PROJECT_ROOT / "data" / "stocks_final.json")
    try:
        with open(path) as f:
            items = json.load(f)
    except FileNotFoundError:
        logger.error(f"自选股文件不存在: {path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"自选股文件格式错误: {path} — {e}")
        return []

    result = []
    for item in items:
        code = item["code"]
        # 已有后缀的直接使用，否则按首位判断
        if "." in code:
            result.append(code)
        elif code.startswith("6"):
            result.append(code + ".SH")
        else:
            result.append(code + ".SZ")
    return result
