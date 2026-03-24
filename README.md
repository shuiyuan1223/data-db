# Query Generator

基于数字人画像（Persona）的健康查询自动生成模块。从主项目的 HQB 数据库中读取合成用户数据，调用大语言模型（LLM），围绕指定知识目录主题生成结构化的健康查询数据集，并写入独立的输出数据库。

---

## 文件结构

```
query_generator/
├── __init__.py                 # 包标识
├── generator.py                # 主流程 + CLI 入口
├── checker.py                  # 统一质量审查 + 报告生成
├── persona_reader.py           # 从 benchmark.db 读取 persona
├── output_db.py                # 输出数据库建表与读写
├── llm_client.py               # LLM 客户端（含代理 + 指数退避重试）
├── prompts/
│   ├── __init__.py
│   ├── general_medical.py      # general_medical domain prompt
│   ├── health.py               # health domain prompt
│   ├── sports.py               # sports domain prompt (内联 persona)
│   ├── sports_health.py        # sports_health domain prompt
│   └── red_team.py             # red_team domain prompt (4 类攻击)
└── topics/
    ├── general_medical.txt     # general_medical 知识目录
    └── sports_health.txt       # sports_health 知识目录
```

---

## 快速开始

> 项目使用 `uv` 管理环境，所有命令需在**项目根目录**执行。

### 生成 Query

```bash
# 最小化测试（单人设 + 单主题）
uv run python -m query_generator.generator \
    --domain general_medical \
    --topics "高血压的诊断与分级" \
    --bench-db data/benchmark.db \
    --persona-id 3

# 批量生成
uv run python -m query_generator.generator \
    --domain general_medical \
    --topics query_generator/topics/general_medical.txt \
    --bench-db data/benchmark.db \
    --out-db output/queries.db

# sports_health（使用所有域人设）
uv run python -m query_generator.generator \
    --domain sports_health \
    --topics query_generator/topics/sports_health.txt \
    --bench-db data/benchmark.db \
    --out-db output/queries.db --batch 5

# sports（LLM 自行生成内联 persona，不需要 benchmark.db）
uv run python -m query_generator.generator \
    --domain sports --topics query_generator/topics/sports.txt \
    --out-db output/queries.db --num-groups 2 --batch 10 --send-interval 20

# red_team（4 类红队测试）
uv run python -m query_generator.generator \
    --domain red_team --topics query_generator/topics/red_team.txt \
    --out-db output/queries.db --num-groups 3 --batch 4
```

### 质量审查

```bash
# 全量审查
uv run python -m query_generator.checker --domain general_medical

# 抽样 100 条
uv run python -m query_generator.checker --domain health --sample 100

# 指定人设 + 自定义报告路径
uv run python -m query_generator.checker \
    --domain general_medical \
    --persona-id 1 3 5 \
    --report output/review_v1.txt

# 审查 sports
uv run python -m query_generator.checker --domain sports --sample 50

# 审查 red_team
uv run python -m query_generator.checker --domain red_team
```

---

## Generator CLI 参数

| 参数 | 短参 | 默认值 | 说明 |
|------|------|--------|------|
| `--domain` | `-d` | `general_medical` | 生成的 query domain |
| `--topics` | `-t` | 自动查找 `topics/{domain}.txt` | 知识目录主题，支持 .txt 文件或逗号分隔字符串 |
| `--bench-db` | `-b` | `data/benchmark.db` | 主项目 HQB 数据库路径 |
| `--out-db` | `-o` | `output/queries.db` | 输出数据库路径 |
| `--num-groups` | `-n` | `5` | 每个 topic 生成的总批次数 |
| `--batch` | | `1` | 并发请求数上限 |
| `--persona-id` | `-p` | 全部 | 指定人设 ID |
| `--max-retries` | | `100` | 单任务最大重试次数 |
| `--send-interval` | | `0` | 限速间隔秒数 |

## Checker CLI 参数

| 参数 | 短参 | 默认值 | 说明 |
|------|------|--------|------|
| `--domain` | `-d` | `general_medical` | 审查的 domain |
| `--db` | `-b` | `output/queries.db` | queries DB 路径 |
| `--report` | `-r` | `output/review_{domain}.txt` | 报告输出路径 |
| `--persona-id` | `-p` | 全部 | 只审查指定人设 |
| `--sample` | `-s` | 全部 | 随机抽样 N 条 |
| `--batch-size` | | `30` | 每次 LLM 审查的条数 |

---

## Checker 工作原理

Checker 是**体系化的统一审查系统**，无需为每个 domain 单独写 review prompt：

1. **自动读取生成 prompt**：从对应 domain 的 `prompts/*.py` 中提取 SYSTEM_PROMPT 和 query 类型定义
2. **构建审查 prompt**：将生成约束注入审查 prompt，让 LLM reviewer 知道原始质量标准
3. **分批审查**：按 batch_size 分批调用 LLM，避免 token 超限
4. **聚合报告**：按 query 类型、主题、问题类型三个维度统计，输出明细

**报告结构：**
```
【总体比率】     正常/有问题 百分比
【按 Query 类型】 各类型问题分布
【按知识主题】   各主题问题分布
【按问题类型】   语言不自然/类型不匹配/逻辑矛盾/...
【明细】         每条问题 Query 的 ID、文本、问题说明
```

**新增 domain 自动适配**：只要在 `_DOMAIN_PROMPT_MAP` 中注册了 prompt 模块，checker 就能自动审查该 domain，无需额外代码。

---

## 支持的 Domain

| Domain | 人设来源 | 说明 |
|--------|---------|------|
| `general_medical` | benchmark.db (domain=general_medical) | 泛医疗健康知识 |
| `health` | benchmark.db (domain=health) | 日常健康管理 |
| `sports` | LLM 内联生成 | 运动专项（无需 benchmark.db） |
| `sports_health` | benchmark.db (所有人设) | 运动健康交叉 |
| `red_team` | 无人设 | 红队安全测试（4 类） |

---

## 扩展新 Domain

1. 在 `prompts/` 下新建 prompt 文件，实现 `build_persona_block()` 和 `build_messages()`
2. 在 `output_db.py` 中注册新表 DDL 和 `_DOMAIN_TABLE_MAP`
3. 在 `generator.py` 中注册 `_DOMAIN_PROMPT_MAP`
4. Checker 自动适配，无需额外修改
