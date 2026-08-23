"""大盘状态获取。"""

from datetime import datetime

from ..database import get_db_connection
from .models import MarketStatus


def get_market_status() -> MarketStatus:
    """
    获取大盘状态（简化版，用主要指数代替）
    """
    today = datetime.now().strftime("%Y%m%d")

    # 获取沪深300成分股简单评估
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ts_code FROM stock_basic
        WHERE market IN ('主板')
        LIMIT 100
    """)
    stocks = [row["ts_code"] for row in cursor.fetchall()]

    rise_count = 0
    total_count = 0

    for ts_code in stocks[:20]:
        cursor.execute(
            """
            SELECT pct_chg FROM daily_kline
            WHERE ts_code = ?
            ORDER BY trade_date DESC
            LIMIT 1
        """,
            (ts_code,),
        )
        row = cursor.fetchone()
        if row:
            total_count += 1
            if row["pct_chg"] > 0:
                rise_count += 1

    conn.close()

    # 计算涨跌家数比
    if total_count > 0:
        rise_ratio = rise_count / total_count
    else:
        rise_ratio = 0.5

    # 大盘状态判断
    if rise_ratio >= 0.6:
        direction = "LONG"
        strength = 75
        reasons = ["上涨家数占优", "市场活跃"]
    elif rise_ratio <= 0.4:
        direction = "SHORT"
        strength = 25
        reasons = ["下跌家数较多", "注意风险"]
    else:
        direction = "NEUTRAL"
        strength = 50
        reasons = ["多空均衡", "观望为主"]

    return MarketStatus(
        trade_date=today, is_trading=True, market_direction=direction, market_strength=strength, reasons=reasons
    )
