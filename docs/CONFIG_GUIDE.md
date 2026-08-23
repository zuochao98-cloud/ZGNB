# 配置指南

> 所有配置项均通过 `.env` 文件管理，复制 `.env.example` 后按需修改。

---

## 核心配置

### 数据模式

```ini
DATA_MODE=jnb
```

| 值 | 说明 | 依赖 |
|---|------|------|
| `jnb` | 接入真实行情数据 | 配置 `TUSHARE_TOKEN` + `TUSHARE_API_URL` 数据最全；零配置时默认走 a-stock-data 免费源（v4.1.0 新增） |
| `websearch` | 纯 LLM 对话模式，不走行情接口 | 无需 Tushare 配置 |

---

## 数据层配置（仅 jnb 模式）

### Tushare API

```ini
TUSHARE_TOKEN=你的56位token
TUSHARE_API_URL=https://tt.xiaodefa.cn
TUSHARE_VERIFY_TOKEN_URL=
```

| 变量 | 必填 | 说明 |
|------|------|------|
| `TUSHARE_TOKEN` | 否（jnb 建议） | Tushare Pro 的 56 位 Token，在 https://tushare.pro/user/token 获取 |
| `TUSHARE_API_URL` | 否（jnb 建议） | 中转 API 地址，如 `https://tt.xiaodefa.cn` |
| `TUSHARE_VERIFY_TOKEN_URL` | 否 | 实时行情验证地址，一般不需要 |

**注意**：如果 `DATA_MODE` 不是 `jnb`，这些配置可以为空，程序不会报错；jnb 模式下未配置 Token 时会自动回退 a-stock-data 免费数据源（腾讯/百度/东财/通达信，无需 API Key）。

---

## LLM 配置（可选）

```ini
LLM_API_KEY=你的API密钥
LLM_BASE_URL=https://api.minimaxi.com/v1/chat/completions
LLM_MODEL=MiniMax-M3
```

| 变量 | 必填 | 说明 |
|------|------|------|
| `LLM_API_KEY` | **否** | 未配置时，系统只做意图识别+知识库检索，不生成回答 |
| `LLM_BASE_URL` | 否（有 Key 时填） | OpenAI 兼容格式的 API 地址 |
| `LLM_MODEL` | 否（有 Key 时填） | 模型名称，默认 `MiniMax-M3` |

**支持的 LLM 提供商**：目前支持 OpenAI 兼容格式的 API（MiniMax、OpenRouter、通义千问等）。

---

## 向量知识库配置（可选，默认关闭）

```ini
# KB_ENABLED=true  # 取消注释以启用
# KB_API_URL=http://localhost:8000
```

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `KB_ENABLED` | `false` | 设为 `true` 开启向量知识库检索 |
| `KB_API_URL` | `http://localhost:8000` | 知识库 API 地址（参考 knowledge-base 项目） |

**知识库依赖**：
- Qdrant 向量数据库（localhost:6333）
- Ollama Embedding 模型（localhost:11434）
- FastAPI 知识库服务（localhost:8000）

**未开启知识库时的行为**：
- 意图识别 ✅ 正常
- 角色框架 ✅ 正常（career/life 用本地 prompt 文件）
- LLM 生成 ✅ 正常（配置了 Key 的话）
- 知识库检索 ❌ 跳过（不影响其他功能）

---

## 数据库配置

```ini
DATA_DIR=data
DB_PATH=data/stock_data.db
```

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATA_DIR` | `data` | 数据目录 |
| `DB_PATH` | `data/stock_data.db` | SQLite 数据库路径，支持绝对/相对路径 |

---

## 配置示例

### 最小配置（纯对话，无需任何外部服务）

```ini
DATA_MODE=websearch
```

### 股票分析模式（需 Tushare）

```ini
DATA_MODE=jnb
TUSHARE_TOKEN=ba0930...fa15
TUSHARE_API_URL=https://tt.xiaodefa.cn
```

### 完整模式（股票 + LLM + 知识库）

```ini
DATA_MODE=jnb
TUSHARE_TOKEN=ba0930...fa15
TUSHARE_API_URL=https://tt.xiaodefa.cn
LLM_API_KEY=sk-cp-...ULLC
LLM_BASE_URL=https://api.minimaxi.com/v1/chat/completions
LLM_MODEL=MiniMax-M3
KB_ENABLED=true
KB_API_URL=http://localhost:8000
```
