-- 自我改进系统数据库表定义
-- 所有表名以 _self 结尾，与主系统表区分

-- 1. 跟踪池表：管理跟踪的股票
CREATE TABLE IF NOT EXISTS tracking_pool_self (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_code TEXT NOT NULL,                    -- 股票代码
    name TEXT,                                -- 股票名称
    add_date TEXT NOT NULL,                   -- 添加日期
    remove_date TEXT,                         -- 移除日期（NULL表示仍在跟踪）
    status TEXT DEFAULT 'active',             -- 状态：active/paused/removed
    track_reason TEXT,                        -- 跟踪原因（用户添加时的理由）
    strategy_tags TEXT,                       -- 策略标签（B1/B2/B3/长安战法等）
    notes TEXT,                               -- 备注
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(ts_code, add_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_tracking_pool_self_code ON tracking_pool_self(ts_code);
CREATE INDEX IF NOT EXISTS idx_tracking_pool_self_status ON tracking_pool_self(status);
CREATE INDEX IF NOT EXISTS idx_tracking_pool_self_add_date ON tracking_pool_self(add_date);

-- 2. 跟踪记录表：记录每日的行情、指标、信号
CREATE TABLE IF NOT EXISTS tracking_records_self (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_code TEXT NOT NULL,                    -- 股票代码
    trade_date TEXT NOT NULL,                 -- 交易日期
    -- 当日行情
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    vol REAL,                                 -- 成交量
    pct_chg REAL,                             -- 涨跌幅
    amount REAL,                              -- 成交额
    -- 技术指标
    j_value REAL,                             -- J值
    k_value REAL,                             -- K值
    d_value REAL,                             -- D值
    bbi REAL,                                 -- BBI
    macd_dif REAL,                            -- MACD DIF
    macd_dea REAL,                            -- MACD DEA
    macd_hist REAL,                           -- MACD 柱状
    rsi_6 REAL,                               -- RSI
    wr_6 REAL,                                -- WR
    boll_upper REAL,                          -- 布林上轨
    boll_mid REAL,                            -- 布林中轨
    boll_lower REAL,                          -- 布林下轨
    vol_ratio REAL,                           -- 量比
    -- 形态识别
    is_brick_red INTEGER DEFAULT 0,           -- 是否红砖
    is_brick_green INTEGER DEFAULT 0,         -- 是否绿砖
    brick_count INTEGER DEFAULT 0,            -- 砖块计数
    is_n_structure INTEGER DEFAULT 0,         -- 是否N型结构
    is_double_gun INTEGER DEFAULT 0,          -- 是否双枪
    -- 信号
    signal_type TEXT,                         -- 信号类型（BUY/SELL/WATCH/NONE）
    signal_score REAL,                        -- 信号评分
    signal_reason TEXT,                       -- 信号原因
    -- 主力阶段
    stage TEXT,                               -- 主力阶段（吸筹/拉升/派发/回落）
    stage_confidence REAL,                    -- 阶段置信度
    -- 元数据
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(ts_code, trade_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_tracking_records_self_code ON tracking_records_self(ts_code);
CREATE INDEX IF NOT EXISTS idx_tracking_records_self_date ON tracking_records_self(trade_date);
CREATE INDEX IF NOT EXISTS idx_tracking_records_self_signal ON tracking_records_self(signal_type);

-- 3. 月度复盘表：记录每月的复盘结果
CREATE TABLE IF NOT EXISTS monthly_reviews_self (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_month TEXT NOT NULL,               -- 复盘月份（YYYY-MM）
    ts_code TEXT NOT NULL,                    -- 股票代码
    -- 月初状态
    start_price REAL,                         -- 月初价格
    start_j_value REAL,                       -- 月初J值
    start_signal TEXT,                        -- 月初信号
    -- 月末状态
    end_price REAL,                           -- 月末价格
    end_j_value REAL,                         -- 月末J值
    end_signal TEXT,                          -- 月末信号
    -- 月度表现
    monthly_return REAL,                      -- 月度收益率
    max_drawdown REAL,                        -- 最大回撤
    max_gain REAL,                            -- 最大涨幅
    -- 信号表现
    buy_signals_count INTEGER,                -- 买入信号次数
    sell_signals_count INTEGER,               -- 卖出信号次数
    correct_buy_signals INTEGER,              -- 正确买入信号次数
    correct_sell_signals INTEGER,             -- 正确卖出信号次数
    -- 复盘结论
    review_summary TEXT,                      -- 复盘总结
    lessons_learned TEXT,                     -- 经验教训
    strategy_adjustments TEXT,                -- 策略调整建议
    -- 元数据
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(review_month, ts_code)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_monthly_reviews_self_month ON monthly_reviews_self(review_month);
CREATE INDEX IF NOT EXISTS idx_monthly_reviews_self_code ON monthly_reviews_self(ts_code);

-- 4. 策略表现统计表：统计各策略的表现
CREATE TABLE IF NOT EXISTS strategy_performance_self (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_name TEXT NOT NULL,              -- 策略名称（B1/B2/B3/长安战法等）
    review_month TEXT NOT NULL,               -- 统计月份
    -- 信号统计
    total_signals INTEGER,                    -- 总信号数
    correct_signals INTEGER,                  -- 正确信号数
    accuracy_rate REAL,                       -- 准确率
    -- 收益统计
    avg_return REAL,                          -- 平均收益率
    max_return REAL,                          -- 最大收益率
    min_return REAL,                          -- 最小收益率
    win_rate REAL,                            -- 胜率
    -- 风险统计
    avg_drawdown REAL,                        -- 平均回撤
    max_drawdown REAL,                        -- 最大回撤
    sharpe_ratio REAL,                        -- 夏普比率
    -- 复盘结论
    strengths TEXT,                           -- 策略优势
    weaknesses TEXT,                          -- 策略劣势
    adjustments TEXT,                         -- 调整建议
    -- 元数据
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(strategy_name, review_month)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_strategy_performance_self_name ON strategy_performance_self(strategy_name);
CREATE INDEX IF NOT EXISTS idx_strategy_performance_self_month ON strategy_performance_self(review_month);
