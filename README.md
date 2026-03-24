# Query Generator

基于数字人画像（Persona）的健康查询自动生成模块。从主项目的 HQB 数据库中读取合成用户数据，调用大语言模型（LLM），围绕指定知识目录主题生成结构化的健康查询数据集，并写入独立的输出数据库。

---

## 文件结构

```
query_generator/
├── __init__.py                 # 包标识
├── generator.py                # 主流程 + CLI 入口
├── persona_reader.py           # 从 benchmark.db 读取 persona
├── output_db.py                # 输出数据库建表与读写
├── llm_client.py               # LLM 客户端（含代理 + 指数退避重试）
├── prompts/
│   ├── __init__.py
│   ├── general_medical.py      # general_medical domain 的 prompt 模板
│   ├── health.py               # health domain 的 prompt 模板
│   ├── sports.py               # sports domain 的 prompt 模板
│   └── sports_health.py        # sports_health domain 的 prompt 模板
└── topics/
    ├── general_medical.txt     # general_medical 知识目录
    └── sports_health.txt       # sports_health 知识目录
```

---

## 快速开始

> 项目使用 `uv` 管理环境，所有命令需在**项目根目录**执行。

### 最小化测试（单人设 + 单主题）

```bash
uv run python -m query_generator.generator \
    --domain general_medical \
    --topics "高血压的诊断与分级" \
    --bench-db data/benchmark.db \
    --persona-id 3
```

### 使用主题文件批量生成

```bash
uv run python -m query_generator.generator \
    --domain general_medical \
    --topics query_generator/topics/general_medical.txt \
    --bench-db data/benchmark.db \
    --out-db output/queries.db
```

### sports_health domain

```bash
uv run python -m query_generator.generator \
    --domain sports_health \
    --topics query_generator/topics/sports_health.txt \
    --bench-db data/benchmark.db \
    --out-db output/queries.db \
    --batch 5
```

---

## CLI 参数说明

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

---

## 支持的 Domain

| Domain | 人设来源 | 说明 |
|--------|---------|------|
| `general_medical` | benchmark.db (domain=general_medical) | 泛医疗健康知识 |
| `health` | benchmark.db (domain=health) | 日常健康管理 |
| `sports` | LLM 内联生成 | 运动专项（无需 benchmark.db） |
| `sports_health` | benchmark.db (所有人设) | 运动健康交叉 |
| `red_team` | 无人设 | 红队测试 |

---

## 扩展新 Domain

1. 在 `prompts/` 下新建 prompt 文件，实现 `build_persona_block()` 和 `build_messages()`
2. 在 `output_db.py` 中注册新表 DDL 和 `_DOMAIN_TABLE_MAP`
3. 在 `generator.py` 中注册 `_DOMAIN_PROMPT_MAP`
