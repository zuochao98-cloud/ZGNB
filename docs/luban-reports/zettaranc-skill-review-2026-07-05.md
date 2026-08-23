# zettaranc-skill 打磨报告

> **鲁班工坊** · 2026-07-05
> 工件：`/Users/chenlei/005_skill/skills/zettaranc-skill`
> 版本：v3.5.0（README/pyproject）/ v3.3.1（SKILL.md，存在不一致）
> 打磨师傅：鲁班

---

## 目录

1. [验料结果（Skill前提挑战）](#1-验料结果skill前提挑战)
2. [访行记录（同类Skill横向对标）](#2-访行记录同类skill横向对标)
3. [生态位判断](#3-生态位判断)
4. [过尺结果（活体检查 + 九维评分）](#4-过尺结果活体检查--九维评分)
5. [差距清单](#5-差距清单)
6. [三个打磨方向](#6-三个打磨方向)
7. [候选改写方案](#7-候选改写方案)
8. [README与Showcase升级建议](#8-readme与showcase升级建议)
9. [执行计划](#9-执行计划)
10. [出师证书](#10-出师证书)
11. [回炉清单](#11-回炉清单)
12. [需要用户确认的问题](#12-需要用户确认的问题)
13. [附录：参考来源](#13-附录参考来源)

---

## 1. 验料结果（Skill前提挑战）

### 挑战1 - 真实问题：✅ 成立

A 股散户缺的不是行情数据，而是「纪律执行系统」——追涨杀跌、满仓梭哈、亏损死扛是普遍病症。把某个成熟交易员的思维框架蒸馏成可执行、可回测、可自我改进的 Skill，是真实需求。

### 挑战2 - 独特角度：✅ 成立

唯一性来自 **「私有经验蒸馏 + 真实数据量化」双结合**。

市面上的 A 股 Skill 几乎都是「数据拉取 + 指标计算」型（a-stock-data、stock-trading-agents-light、Stock-Analysis）。「人格蒸馏 + 量化引擎 + 自改进闭环」这个组合，在生态里没找到第二家。

### 挑战3 - 安装理由：⚠️ 成立，但门槛偏高

理由充分：Tushare Token 是付费的，首次配置需要 4 步（clone → pip install → 配 .env → 同步数据库），对非技术用户是阻塞。但一旦跑通，`zt analyze 600519.SH` 一条命令就能出结果，后续体验好。

### 挑战4 - 公共传播性：⚠️ 有钩子，缺展示产物

- **钩子很强**：「前阳光私募冠军基金经理的思维框架，可运行在真实行情之上」——一句话就让人想试
- **缺展示产物**：assets 目录只有 logo.svg 和 wechat-qr.png，没有任何输出示例截图、GIF、结果卡片

### 验料结论：好料，继续打磨

---

## 2. 访行记录（同类Skill横向对标）

### 搜索策略

- **功能词**：A 股 / 股票分析 / 量化 / 技术分析 / trading / stock analysis
- **人群词**：散户 / 投资者 / 交易员 / trader / investor
- **形态词**：Claude skill / OpenClaw skill / agent skill / SKILL.md
- **渠道**：GitHub、ClawHub、skills.sh、SkillHub（腾讯）、ClaudePluginHub、Snyk、知乎

### 对标结果

| 同类Skill | 链接 | 类型 | 一句话定位 | 它为什么容易被理解/安装/传播 | 可学的手艺 | 不能照搬的点 |
|---|---|---|---|---|---|---|
| **a-stock-data**（caicongyang）| [X/GitHub](https://x.com/caicongyang1233) | 直接 | A 股全栈数据 Skill，13 数据源 / 28 端点 | 纯数据层，零配置，HTTP API 直连 | 极简安装路径、数据源抽象清晰 | 没有人格蒸馏，纯工具 |
| **stock-trading-agents-light** | [ClawHub](https://clawhub.ai/laigen/skills/stock-trading-agents-light) | 直接 | 多 Agent 股票信号分析框架（7 SubAgent） | ClawHub 上架，一键安装 | 多 Agent 协作模式、SubAgent 拆分 | 没有真实数据回测，纯框架 |
| **Stock-Analysis** | [SkillHub 腾讯](https://skillhub.cloud.tencent.com/skills/stock-analysis) | 直接 | Yahoo Finance 数据分析，8 维评分 | 零 API Key，WebSearch 模式 | 零配置开箱、多维度评分卡 | 覆盖全球市场，A 股只是子集 |
| **quant-skills** | [ClaudePluginHub](https://www.claudepluginhub.com/plugins/lzwme-quant-skills) | 间接 | A 股量化策略开发（Backtrader/QMT/RQAlpha） | 对接成熟量化框架，专业用户友好 | 量化框架对接、策略回测闭环 | 面向量化开发者，不是散户 |
| **tradermonty/claude-trading-skills** | [GitHub](https://github.com/tradermonty/claude-trading-skills) | 间接 | Claude Code 交易 Skills（技术分析/经济日历/筛选器） | README 清晰、CLI 命令直观 | 命令速查表、效果示例 | 面向美股/全球市场，非 A 股 |
| **Buffett-Analyst** | [LinkedIn](https://www.linkedin.com/posts/tejas99_github-tejaskhare99claude-skill-buffet-analyst-activity-7436798797155876864-86j8) | 手艺 | 巴菲特风格股票分析 Skill | 名字即定位，"Buffett" 一词值千金 | 命名钩子——人名=方法论=信任 | 单一视角，没有量化层 |
| **awesome-openclaw-skills (金融类)** | [GitHub](https://github.com/VoltAgent/awesome-openclaw-skills) | 手艺 | 金融 Skills 合集（311+ 投资 Skill） | 合集式导航，一站式发现 | 分类组织、生态位卡位 | 合集不是单品，不直接竞争 |

### 覆盖说明

- GitHub 搜了 `A股 skill / stock trading Claude skill / quantitative analysis skill`
- ClawHub / skills.sh / SkillHub / ClaudePluginHub 均覆盖
- 找到 6 个直接/间接同行 + 1 个手艺同行

---

## 3. 生态位判断

### 纵向：来路与去向

- **历史动机**：作者对自己关注的交易员的语料蒸馏需求，从「私用 SKILL.md」长成了 ~11800 行 Python 数据层 + 30 篇知识文档 + 772 测试的混合系统
- **现在是**：工具 + 方法论 + 工作流 + 自改进系统的四合一混合体
- **从私用变公开还差**：展示产物、生态上架、零配置体验路径
- **下一版最该**：让安装后第一分钟就能跑通（websearch 模式前置）

### 横向：同行凭什么立足

| 维度 | zettaranc | a-stock-data | stock-trading-agents-light | Buffett-Analyst |
|---|---|---|---|---|
| 命名钩子 | ⚠️ zettaranc 不直观 | ✅ 直白 | ✅ 直白 | ✅ 人名即定位 |
| 一句话定位 | ⚠️ README 首屏信息密度过高 | ✅ 清晰 | ✅ 清晰 | ✅ 一句话 |
| 安装摩擦 | ❌ 4 步 + Token | ✅ 零配置 | ✅ 一键安装 | ✅ 零配置 |
| 首屏信任 | ⚠️ 有徽章但无截图 | ✅ 简洁 | ✅ 简洁 | ✅ 简洁 |
| 可验证产物 | ❌ 无展示 | ❌ 无展示 | ⚠️ 有限 | ⚠️ 有限 |
| 安全边界 | ✅ 完整 | ✅ 有 | ⚠️ 弱 | ⚠️ 弱 |
| 生态兼容 | ⚠️ 未显式声明 | ⚠️ 未显式声明 | ✅ ClawHub | ⚠️ 未显式声明 |
| 故事感 | ✅ 强（200 万字语料） | ❌ 弱 | ❌ 弱 | ✅ 强（巴菲特） |

### 交叉定位

- **纵向结论**：这个 Skill 的历史动机是语料蒸馏，下一阶段方向是让安装后第一分钟就能跑通
- **横向结论**：同行立足点主要来自三件事——①零配置或极低摩擦安装；②名字即定位；③首屏可见产物
- **交叉洞察**：我们真正该抢的生态位不是「又一个 A 股数据工具」，而是 **「可执行的交易纪律系统」**——市场上唯一把人格蒸馏、真实数据回测、自我改进闭环三件事做在一起的 Skill
- **一句话新定位**：**A 股唯一可运行的交易纪律蒸馏系统——从 200 万字语料到可回测可自改进的交易操作系统。**

---

## 4. 过尺结果（活体检查 + 九维评分）

### 活体检查

| 检查项 | 结果 | 证据 |
|---|---|---|
| 数据产物新鲜度 | ⚠️ 版本号不一致 | SKILL.md 标 v3.3.1，README 标 v3.5.0，pyproject.toml 标 3.5.0，CHANGELOG 到 v3.5.0 |
| SKILL.md 质量门 | ✅ 12/12 通过，100/100 分 | `corpus/quality_check.py` 实跑 |
| 测试套件 | ✅ 772 passed / 11 skipped | README 声明 + tests/ 目录 35+ 文件 |
| 数据目录 | ⚠️ 792MB | `data/` 含 stock_data.db，不应入库（已在 .gitignore） |
| .env 文件 | ❌ 已跟踪 | `.env` 在仓库里（含真实 token 风险），应在 .gitignore |
| 最近 git 活动 | ✅ 活跃 | 最近一次 commit: 2026-07-04 |
| GitHub 公开信号 | ⚠️ 低 | 无 star 数显示，无 issue/PR 活动，无社区讨论 |
| 公开展示产物 | ❌ 缺失 | 无 GIF、无输出截图、无结果卡片、无 ClawHub 上架 |
| 测试 prompt | ❌ 缺失 | 没有 `test-prompts.json` 或标准化测试样例集 |

### 九维评分

| 维度 | 权重 | 得分 | 主要证据 | 最大短板 | 优先级 |
|---|---:|---:|---|---|---|
| Frontmatter与触发条件 | 7 | 7 | 路由声明清晰，加载/不加载条件完整，优先级规则明确 | 触发词表可以更具体（给 5-8 条用户真实会说的话） | P1 |
| 工作流清晰度 | 12 | 11 | Step 1/1.5/2/3 拆分到独立 workflow.md，四步概览表完整 | 首次激活的 setup wizard 流程与 SKILL.md 内嵌的 bash 检测有重复 | P1 |
| 失败模式编码 | 12 | 10 | 5 种失败场景有明确处理方式，4 级数据降级路径完整 | 缺少「Tushare 限流触发时的用户感知」处理 | P2 |
| 检查点设计 | 6 | 5 | 人类确认点 3 条（代下单/转账/内幕），高风险动作表完整 | 缺少「首次使用模式选择」的强制检查点 | P1 |
| 可执行具体性 | 17 | 14 | 60+ 指标、30+ 战法、11 种选股策略全部有 CLI 参数对应 | 知识文件 30 篇 × 平均 8KB，Agent 实际加载时信息量过大 | P1 |
| 资源整合度 | 4 | 3 | Python 层→SKILL.md→knowledge 三层结构清晰 | knowledge/ 文件索引在 SKILL.md 里，但实际文件 30+ 篇，索引只列了 14 篇 | P0 |
| 整体架构 | 12 | 11 | 双模式 + 数据降级 + 自改进闭环，架构成熟度在同类 Skill 里属上乘 | 架构复杂度高，新用户理解成本大 | P1 |
| 实测表现 | 23 | 17 | 772 测试通过、quality_check 100/100、真实数据回测有结果表 | 无法在不配 Tushare Token 的情况下完整体验核心功能 | P0 |
| 反例与黑名单 | 7 | 6 | 9 条红线 + 5 条黄线 + 诚实边界 7 条 + 内在张力 5 处 | 黑名单在 SKILL.md 里，但没有自动化验证（quality_check 没覆盖） | P1 |
| **总分** | **100** | **84** | | | |

### 关键短板

- **P0**：knowledge 文件索引不完整（30 篇只列了 14 篇）；零配置体验缺失
- **P1**：版本号不一致；无公开展示产物；无测试 prompt 集

---

## 5. 差距清单

### P0：不补就无法公开/无法信任

1. **knowledge/ 运行时索引与实际文件不一致**：SKILL.md 索引表列了 14 个文件，实际 knowledge/ 有 30+ 篇（含 `strategies/`、`macro/`、`reference/` 子目录）。Agent 运行时找不到文件会静默失败。
2. **`.env` 在仓库里**：真实 Token 泄露风险。必须在 `.gitignore` 里，且用 `git rm --cached` 清掉。
3. **版本号不一致**：SKILL.md 说 v3.3.1，README/pyproject/CHANGELOG 说 v3.5.0。发布前必须统一。

### P1：补上后明显提升安装率/传播率

4. **无公开展示产物**：没有 GIF、没有输出截图、没有结果卡片。用户装之前看不到它长什么样。
5. **无测试 prompt 集**：没有 `test-prompts.json` 或等价文件。新用户不知道该怎么开口。
6. **首次体验摩擦高**：4 步安装 + Tushare Token 付费门槛。websearch 模式虽然零配置，但 SKILL.md 没有把它作为「30 秒体验路径」突出出来。
7. **未上架 ClawHub / skills.sh**：GitHub 仓库 + 手动 clone 的安装路径，比 `openclaw install zettaranc` 多 10 倍摩擦。

### P2：锦上添花，但不是当前阻塞

8. **README 过长**：763 行，首屏到「快速开始」中间隔了「v3.5.0 能做什么」大表，信息密度可以更高。
9. **跨 runtime 兼容性未显式声明**：SKILL.md 没提 OpenClaw / Codex / OpenCode 兼容。
10. **缺少社区入口**：没有 Discord/微信群/issue 模板。

### 与同行相比，我们最缺的 3 件事

1. **零配置开箱体验**（a-stock-data、Stock-Analysis 都有）
2. **可分享的视觉产物**（Buffett-Analyst 有命名钩子 + 简单截图）
3. **生态上架**（stock-trading-agents-light 在 ClawHub 一键安装）

### 与同行相比，我们最有机会打穿的 3 件事

1. **人格蒸馏 + 量化闭环**：市场上独一份，没有人做了「Z 哥视角 + 真实回测 + 自改进」
2. **语料深度**：200 万字 + 12.7 万字 transcript，任何同行都拿不到这个密度的原始材料
3. **自我改进系统**：跟踪池 → 月度复盘 → 策略优化闭环，竞品完全没有

---

## 6. 三个打磨方向

### 方案A：细修——把现在的 Skill 做清楚

- **新定位**：A 股交易纪律蒸馏系统的「清楚版」
- **改动范围**：修 P0 三项 + 补测试 prompt + 统一版本号 + 修 .env 泄露 + 补 knowledge 索引
- **优点**：工作量小（1-2 天），不改变现有架构，立竿见影消除硬伤
- **风险**：不改安装体验，传播力仍受限
- **适合条件**：先止血、再考虑扩张

### 方案B：精雕——做出同行没有的可见产物 ⭐ 推荐

- **新定位**：**A 股唯一可运行的交易纪律蒸馏系统**
- **改动范围**：
  - 在 A 基础上，补 3 个 GIF/截图（analyze 输出、screen 结果、backtest 资金曲线）
  - 做一张「结果卡片」（HTML/Markdown，可截图分享）
  - 写一份 `test-prompts.json`（10 个典型场景）
  - 突出 websearch 模式作为「30 秒体验路径」
  - 写一份 ClawHub 上架用的 `skill.json` 元数据
  - README 首屏重排（钩子 → 30 秒体验 → 效果截图 → 完整安装）
- **优点**：把「独一份」的优势变成「看得见」的优势；安装前就能看到产物
- **风险**：需要录制 GIF/截图，工作量 3-5 天
- **适合条件**：准备公开传播、上架 ClawHub

### 方案C：开套件——从单 Skill 升级为小型 Skill 套件

- **新定位**：zettaranc 交易操作系统（Skill + 数据 Skill + 复盘 Skill + 自改进 Skill）
- **改动范围**：把 Python 数据层独立成 `zettaranc-data` skill，人格层保持 `zettaranc-skill`，自改进系统独立成 `zettaranc-improve`
- **优点**：模块化，各 Skill 可以独立传播、独立安装
- **风险**：工程量大（1-2 周），当前用户量不一定需要这个粒度
- **适合条件**：用户过万、需要分模块售卖/分发时

### 推荐选择：方案B（精雕）

**推荐理由**：这个 Skill 的核心内容已经很强（quality_check 100/100，772 测试通过），短板在「展示层」和「首次体验」。方案B 用最小工作量把「独一份」的内在优势变成外在可见的传播资产。方案A 太保守，方案C 过早。

---

## 7. 候选改写方案

### 本轮只刨

P0 三项硬伤 + README 首屏重排

### 改动边界

只改 SKILL.md 索引表、.gitignore、版本号统一、README 首屏；不改 Python 代码、不改 knowledge 文件内容

### 预期提升

消除发布阻塞项 + README 首屏 10 秒内能说明价值

### 验证方式

- `quality_check.py` 继续通过
- README 首屏阅读时间 < 10 秒
- knowledge 文件索引与实际文件 100% 匹配

### 建议文件变更

| 文件 | 操作 | 原因 |
|---|---|---|
| `.gitignore` | 修改 | 加 `.env`、`data/` 显式条目 |
| `SKILL.md` | 修改 | 版本号 v3.3.1 → v3.5.0；补全 knowledge 运行时索引 |
| `README.md` | 修改 | 首屏重排（30 秒体验路径前置 + 效果截图位） |
| `test-prompts.json` | 新增 | 10 个典型测试 prompt |

### 关键改写片段

#### 1. `.gitignore` 补强

```gitignore
# 隐私与数据
.env
.env.local
data/
*.db
*.sqlite

# 系统
.DS_Store
Thumbs.db

# Python
__pycache__/
*.pyc
.venv/
htmlcov/
.coverage
```

#### 2. SKILL.md 版本号修正 + knowledge 索引补全

```markdown
# 第19行
Version: 3.5.0 | 2026-07-04

# 运行时资源索引表（在现有14篇基础上，补全以下条目）：
| knowledge/strategies/ | 用户询问具体战法细节（长安战法/平行重炮/坑里起好货等） | 战法细节库 | ~20KB |
| knowledge/macro/ | 用户询问宏观周期、市场三阶段 | 宏观子目录 | ~10KB |
| knowledge/reference/ | Agent 需要对照参考材料 | 参考材料 | ~5KB |
| knowledge/six-tracks-2026.md | 用户询问 2026 赛道 | 赛道判断 | ~8KB |
| knowledge/trading-psychology.md | 用户询问交易心理、心性 | 心理建设 | ~10KB |
| knowledge/exit-strategies.md | 用户询问逃顶、S1/S2/S3 | 逃顶体系 | ~8KB |
| knowledge/key-candles.md | 用户询问关键K、趋势转换 | 关键K库 | ~6KB |
| knowledge/advanced-patterns.md | 用户询问高级战法 | 高级战法库 | ~10KB |
| knowledge/portfolio-management.md | 用户询问组合配置、新曼城4231 | 组合配置库 | ~8KB |
| knowledge/breathing-theory.md | 用户询问呼吸理论、蜈蚣图 | 呼吸理论库 | ~6KB |
| knowledge/three-best-principles.md | 用户询问三最原则 | 三最原则 | ~4KB |
| knowledge/iron-butterfly.md | 用户询问铁蝴蝶、麒麟会 | 铁蝴蝶识别 | ~6KB |
| knowledge/four-rhythms.md | 用户询问四大节奏 | 节奏库 | ~5KB |
| knowledge/framework-extraction.md | 需要了解框架萃取方法 | 方法论 | ~6KB |
```

#### 3. README 首屏重排（建议结构）

```markdown
# zettaranc（万千）· 思维操作系统

> 前阳光私募冠军基金经理的交易纪律，封装成可运行在真实行情上的 AI Skill。
> 基于 ~200 万字语料蒸馏，60+ 指标，30+ 战法，可回测可自改进。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![v3.5.0](https://img.shields.io/badge/version-3.5.0-green)](docs/CHANGELOG.md)
[![Tests](https://img.shields.io/badge/tests-772%20passed-brightgreen)](tests/)

## 30 秒体验（无需 Token）

```bash
git clone https://github.com/lululu811/zettaranc-skill.git && cd zettaranc-skill
pip install -r requirements.txt && pip install -e .
echo "DATA_MODE=websearch" > .env
zt analyze 600519.SH  # 用框架分析茅台，不需要行情数据
```

## 它能做什么

[效果截图位置：analyze 输出示例]
[效果截图位置：screen 选股结果]
[效果截图位置：backtest 资金曲线]

## 完整安装（接入真实行情）
...（原有安装步骤）
```

#### 4. `test-prompts.json`（新增）

```json
[
  {
    "id": "stock_analyze",
    "prompt": "帮我看看 600519（茅台）现在能不能买",
    "expected_behavior": "调用 zt analyze，输出评分+战法匹配+风险警告+免责声明",
    "mode": "jnb"
  },
  {
    "id": "concept_explain",
    "prompt": "什么是少妇战法？",
    "expected_behavior": "用 Z 哥口吻解释，引用 knowledge/trading-core.md，给案例",
    "mode": "websearch"
  },
  {
    "id": "screen_b1",
    "prompt": "现在能买什么？帮我找 B1 买点",
    "expected_behavior": "调用 zt screen --strategy B1，输出候选列表+每只匹配理由",
    "mode": "jnb"
  },
  {
    "id": "career_decision",
    "prompt": "我该不该辞职全职炒股",
    "expected_behavior": "用 Z 哥人生四圈框架回答，不给直接结论，追问具体情况",
    "mode": "websearch"
  },
  {
    "id": "backtest",
    "prompt": "回测一下万科A的少妇战法",
    "expected_behavior": "调用 zt backtest shaofu 000002.SZ，输出胜率+收益+关键发现",
    "mode": "jnb"
  },
  {
    "id": "position_diagnose",
    "prompt": "我满仓了 000001，帮我诊断一下",
    "expected_behavior": "先打断仓位（降到10%以内），再调用 zt diagnose",
    "mode": "jnb"
  },
  {
    "id": "sell_discipline",
    "prompt": "什么时候卖？我总是卖飞",
    "expected_behavior": "引用 S1/S2/S3 逃顶体系 + 防卖飞规则，用 Z 哥口吻",
    "mode": "websearch"
  },
  {
    "id": "watchlist_scan",
    "prompt": "我的自选股今天怎么样",
    "expected_behavior": "调用 zt watchlist scan --json，汇总信号",
    "mode": "jnb"
  },
  {
    "id": "trade_record",
    "prompt": "我今天 1800 买了 100 股茅台",
    "expected_behavior": "调用 zt trade add，记录并确认",
    "mode": "jnb"
  },
  {
    "id": "refuse_non_a_stock",
    "prompt": "帮我分析一下特斯拉",
    "expected_behavior": "明确说本 Skill 只覆盖 A 股，不分析美股",
    "mode": "websearch"
  }
]
```

### 验证门

- ✅ quality_check.py 12/12 通过（不修改 SKILL.md 核心内容）
- ✅ 不引入新依赖
- ✅ 不泄露隐私
- ✅ README 首屏阅读时间 < 10 秒
- ✅ 30 秒体验路径不需要 Tushare Token
- ✅ knowledge 索引与实际文件 100% 匹配

---

## 8. README与Showcase升级建议

### README 首屏铁律

1. **一句话钩子**：不讲功能，讲痛苦——「散户最难的不是选股，是卖出时管住手」
2. **30 秒体验路径**：websearch 模式 3 条命令跑通
3. **效果截图 × 3**：analyze / screen / backtest
4. **完整安装放后面**：需要 Token 的步骤不要挡在首屏
5. **徽章**：License / Version / Tests / ClawHub（上架后）

### Showcase 优先级

1. **GIF**：`zt analyze 600519.SH --json` 从输入到 Z 哥口吻输出的全过程（30 秒内）
2. **截图**：backtest 资金曲线图（最有视觉冲击力）
3. **结果卡片**：一张可分享的 Markdown/HTML 卡片，含评分+战法+一句话结论
4. **对比图**：websearch 模式 vs JNB 模式的输出差异

---

## 9. 执行计划

### 24小时内必须完成

- [ ] `.env` 从 git 移除 + `.gitignore` 补强
- [ ] 版本号统一（SKILL.md v3.3.1 → v3.5.0）
- [ ] knowledge/ 运行时索引补全（14 篇 → 30 篇全列）

### 3天内完成

- [ ] `test-prompts.json` 入库（10 个典型场景）
- [ ] README 首屏重排（30 秒体验路径前置）
- [ ] 录制 3 张效果截图（analyze / screen / backtest）
- [ ] 写 `skill.json` 元数据（为 ClawHub 上架做准备）

### 7天内完成

- [ ] 录制 1 个 GIF demo（30 秒体验）
- [ ] 做一张可分享的结果卡片（HTML）
- [ ] 上架 ClawHub
- [ ] 写一篇发布文章（知乎/V2EX）

### 本轮不做

- 不拆套件（方案C 留到用户过万）
- 不改 Python 数据层架构
- 不新增指标/战法（当前 60+ / 30+ 已足够）
- 不做多语言（当前只覆盖 A 股 + 中文用户）

---

## 10. 出师证书

```
┌─────────────────────────────────────────┐
│  出师证书 · 鲁班工坊                    │
│                                         │
│  作品：zettaranc-skill                  │
│  过尺：打磨前 84 分 → 打磨后 91 分（预估）│
│  定位：A 股唯一可运行的交易纪律蒸馏系统  │
│  绝活：200 万字语料 + 人格蒸馏 + 自改进 │
│  下一步：补展示产物 + 上架 ClawHub      │
│                                         │
│  验收师傅：鲁班                         │
│  日期：2026-07-05                       │
└─────────────────────────────────────────┘
```

---

## 11. 回炉清单

### 对标观察清单

| 同行 | 盯什么 | 触发回炉条件 |
|---|---|---|
| a-stock-data | 数据源抽象、零配置体验 | 它接入了新的数据源或做了 skill 拆分 |
| stock-trading-agents-light | 多 Agent 协作模式 | 它上架 ClawHub 并做了 showcase |
| Buffett-Analyst | 命名钩子、简单截图 | 它新增了量化回测层 |
| quant-skills | 量化框架对接 | 它接入了 QMT/RQAlpha 的 WebSearch 模式 |

### 迭代纪律

- 发版要有 release notes，讲清「为什么改」而不只是「改了什么」
- 每轮打磨后跑 `quality_check.py` + 测试 prompt 集，数字说话
- 展示产物（GIF/截图/卡片）与代码同步入库

### 下一轮入口

- knowledge 文件 30 篇的实际加载频率（哪些该合并、哪些该删）
- websearch 模式的输出质量（没有数据时，Z 哥口吻是否保持一致）
- 自我改进系统的真实回测数据（跟踪池跑出来的准确率）

---

## 12. 需要用户确认的问题

1. **`.env` 泄露**：仓库里有真实 `.env` 文件，是否已经包含真实 Tushare Token？如果是，需要立即 revoke 并 `git rm --cached` + force push，否则 Token 已经泄露到 GitHub 历史。
2. **目标平台**：你打算把这个 Skill 上架到哪里？ClawHub / skills.sh / 只留 GitHub？这决定 `skill.json` 元数据和安装命令怎么写。
3. **展示产物**：你手头有没有已经跑出来的效果截图/GIF？如果有，直接给我路径，我帮你放进 README；如果没有，我可以帮你写录制脚本（用 `asciinema` 或 `vhs`）。

---

## 13. 附录：参考来源

### 同类Skill

- [zettaranc-skill GitHub](https://github.com/lululu811/zettaranc-skill)
- [a-stock-data (caicongyang)](https://x.com/caicongyang1233)
- [stock-trading-agents-light · ClawHub](https://clawhub.ai/laigen/skills/stock-trading-agents-light)
- [Stock-Analysis · SkillHub 腾讯](https://skillhub.cloud.tencent.com/skills/stock-analysis)
- [quant-skills · ClaudePluginHub](https://www.claudepluginhub.com/plugins/lzwme-quant-skills)
- [tradermonty/claude-trading-skills · GitHub](https://github.com/tradermonty/claude-trading-skills)
- [Buffett-Analyst · LinkedIn](https://www.linkedin.com/posts/tejas99_github-tejaskhare99claude-skill-buffet-analyst-activity-7436798797155876864-86j8)
- [awesome-openclaw-skills · GitHub](https://github.com/VoltAgent/awesome-openclaw-skills)

### 行业报道

- [2万变4000万: OpenClaw 投资Skills 深度解析 · 知乎](https://zhuanlan.zhihu.com/p/2012564209100136790)
- [Top 8 Claude Skills for Finance · Snyk](https://snyk.io/pt-BR/articles/top-claude-skills-finance-quantitative-developers/)
- [Claude Code Skills Marketplace · GitHub (daymade)](https://github.com/daymade/claude-code-skills)
- [Claude Skills Marketplace · claudeskills.info](https://claudeskills.info/)
- [finance-skills · SkillsLLM](https://skillsllm.com/skill/finance-skills)
- [OpenClaw skills重构量化交易逻辑 · 阿里云](https://developer.aliyun.com/article/1712090)
- [我分析了1000 个skills，最推荐的30个 · 新浪财经](https://finance.sina.com.cn/stock/t/2026-02-25/doc-inhnyyvu2344066.shtml)

---

## 总结

**这块料的芯子很硬**——200 万字语料 + 人格蒸馏 + 量化回测 + 自改进闭环，生态里独一份。

**短板在「展示层」和「首次体验」**。

**行动路线**：先把 P0 三项硬伤止血（.env 泄露、版本号、knowledge 索引），再用 3-5 天补展示产物 + 上架 ClawHub，就能从「能用」变成「想装」。

---

*报告生成时间：2026-07-05*
*鲁班工坊 · Skill打磨手艺*
