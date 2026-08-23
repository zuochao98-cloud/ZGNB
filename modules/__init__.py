"""
Zettaranc 技术分析模块包
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ─── 全局一次性加载 .env（包首次 import 时执行）───────────────────────────────
# 优先读取环境变量指向的路径，其次查找项目根目录的 .env
_env_path = Path(os.getenv("ZETTARANC_ENV", Path(__file__).parent.parent / ".env"))
load_dotenv(_env_path, override=False)  # 已有的环境变量不被 .env 覆盖（保持测试 fixture 隔离能力）


# ─── 公开 API ────────────────────────────────────────────────────────────────
from .database import get_connection, get_db_path, init_database  # noqa: E402
from .tushare_client import TushareClient  # noqa: E402
from .setup_wizard import run_wizard, check_env_exists, check_data_mode  # noqa: E402

# 随堂测试复盘模块（数据准备层，点评由LLM生成）
from .trade_parser import TradeParser, ParseResult, format_trade_for_review  # noqa: E402
from .trade_manager import TradeManager, trade_manager  # noqa: E402
from .trade_reviewer import TradeReviewer, ReviewContext, create_reviewer  # noqa: E402

__all__ = [
    # 数据库
    "get_connection",
    "get_db_path",
    "init_database",
    # Tushare
    "TushareClient",
    # 初始化向导
    "run_wizard",
    "check_env_exists",
    "check_data_mode",
    # 随堂测试复盘（数据层）
    "TradeParser",
    "ParseResult",
    "format_trade_for_review",
    "TradeManager",
    "trade_manager",
    "TradeReviewer",
    "ReviewContext",
    "create_reviewer",
]


def get_data_mode() -> str:
    """获取当前数据模式：jnb 或 websearch"""
    return os.getenv("DATA_MODE", "websearch")


def get_project_root() -> Path:
    """获取项目根目录（modules/ 的上一级）"""
    return Path(__file__).parent.parent
