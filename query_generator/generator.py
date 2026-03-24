"""
Main query generation pipeline.

Usage examples:

  # general_medical — 标准串行
  python -m query_generator.generator \\
      --domain general_medical \\
      --topics topics/general_medical.txt \\
      --bench-db data/benchmark.db \\
      --out-db output/queries.db

  # sports_health — 使用 health 域人设
  python -m query_generator.generator \\
      --domain sports_health \\
      --topics query_generator/topics/sports_health.txt \\
      --bench-db data/benchmark.db \\
      --out-db output/queries.db \\
      --batch 5

  # sports — 12 个运动组合，每个生成 2 批
  python -m query_generator.generator \\
      --domain sports \\
      --topics query_generator/topics/sports.txt \\
      --out-db output/queries.db \\
      --num-groups 2 \\
      --batch 10 \\
      --send-interval 20
"""

import argparse
import asyncio
import datetime
import sqlite3
import sys
from pathlib import Path
from typing import Optional

from tqdm.asyncio import tqdm

from .llm_client import LLMClient
from .output_db import (
    get_stats, init_db,
    insert_queries, insert_sports_queries, insert_red_team_queries,
    is_generated, is_topic_generated,
    upsert_persona,
)
from .persona_reader import get_persona_by_id, get_personas

# ---------------------------------------------------------------------------
# Domain → prompt module mapping
# ---------------------------------------------------------------------------
_DOMAIN_PROMPT_MAP = {
    "general_medical": "query_generator.prompts.general_medical",
    "health":          "query_generator.prompts.health",
    "sports":          "query_generator.prompts.sports",
    "red_team":        "query_generator.prompts.red_team",
    "sports_health":   "query_generator.prompts.sports_health",
}

# 不从 benchmark.db 读取人设的 domain
_NO_PERSONA_DOMAINS: frozenset[str] = frozenset({"sports", "red_team"})

# ---------------------------------------------------------------------------
# [BUG FIX] sports_health 在 benchmark.db 中没有 domain="sports_health" 的人设，
# 需要从其他 domain 借用人设。此映射表定义了加载 persona 时实际使用的 domain 过滤值。
# 如果某个 domain 不在此映射中，则使用自身名称查询。
# ---------------------------------------------------------------------------
_PERSONA_DOMAIN_MAP: dict[str, str | None] = {
    "sports_health": None,  # None = 不按 domain 过滤，使用所有人设
}

# 虚拟 persona，用于 no-persona domain 的任务队列占位
_DUMMY_PERSONA: dict = {"id": 0, "name": "dummy"}

GROUPS_PER_CALL = 1  # LLM 每次固定返回 5 组


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_prompt_module(domain: str):
    import importlib
    module_path = _DOMAIN_PROMPT_MAP.get(domain)
    if module_path is None:
        raise ValueError(
            f"Unknown domain '{domain}'. Supported: {list(_DOMAIN_PROMPT_MAP)}"
        )
    return importlib.import_module(module_path)


def _load_topics(topics_arg: Optional[str], domain: str) -> list[str]:
    if topics_arg is None:
        # 尝试在项目内查找默认 topics 文件
        default_path = Path(__file__).parent / "topics" / f"{domain}.txt"
        if not default_path.exists():
            print(f"❌ --topics 未指定，且默认文件不存在: {default_path}")
            sys.exit(1)
        topics_arg = str(default_path)

    p = Path(topics_arg)
    if p.exists() and p.suffix == ".txt":
        lines = p.read_text(encoding="utf-8").splitlines()
        return [l.strip() for l in lines if l.strip() and not l.startswith("#")]
    return [t.strip() for t in topics_arg.split(",") if t.strip()]


def _build_task_list(
    personas: list[dict],
    topics: list[str],
    n_calls: int,
) -> list[tuple[dict, str]]:
    """
    按顺序展开任务队列：环形取人设，外层按 topic 顺序排列。
    """
    total = len(topics) * n_calls
    tasks = []
    persona_cursor = 0
    n_personas = len(personas)

    for topic in topics:
        for _ in range(n_calls):
            persona = personas[persona_cursor % n_personas]
            tasks.append((persona, topic))
            persona_cursor += 1

    assert len(tasks) == total
    return tasks


# ---------------------------------------------------------------------------
# 断点续跑检查
# ---------------------------------------------------------------------------

def _check_is_generated(
    db_path: str | Path,
    domain: str,
    persona: dict,
    topic: str,
) -> bool:
    if domain in _NO_PERSONA_DOMAINS:
        return is_topic_generated(db_path, domain, topic)
    return is_generated(db_path, domain, persona["id"], topic)


# ---------------------------------------------------------------------------
# 结果写入分发
# ---------------------------------------------------------------------------

def _dispatch_insert(
    db_path: str | Path,
    domain: str,
    persona: dict,
    catalog_topic: str,
    result,
) -> None:
    if domain in ("general_medical", "health", "sports_health"):
        groups = result.get("groups", [])
        if not groups:
            raise ValueError("Empty groups in response")
        upsert_persona(db_path, persona)
        insert_queries(db_path, domain, persona["id"], catalog_topic, groups)

    elif domain == "sports":
        queries = result.get("queries", []) if isinstance(result, dict) else result
        if not queries:
            raise ValueError("Empty queries in sports response")
        insert_sports_queries(db_path, catalog_topic, queries)

    elif domain == "red_team":
        if isinstance(result, list):
            queries = result
        else:
            queries = result.get("queries", result)
        if not queries:
            raise ValueError("Empty queries in red_team response")
        insert_red_team_queries(db_path, catalog_topic, queries)

    else:
        raise ValueError(f"No insert handler for domain '{domain}'")

# ---------------------------------------------------------------------------
# Failure recording
# ---------------------------------------------------------------------------

def _ensure_failed_tasks_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS failed_tasks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            domain      TEXT,
            persona_id  INTEGER,
            topic       TEXT,
            error       TEXT,
            attempts    INTEGER,
            ts          TEXT
        )
    """)


def _record_failure(
    db_path: str | Path,
    domain: str,
    persona_id: int,
    topic: str,
    error: str,
    attempts: int,
) -> None:
    with sqlite3.connect(db_path) as conn:
        _ensure_failed_tasks_table(conn)
        conn.execute(
            "INSERT INTO failed_tasks (domain, persona_id, topic, error, attempts, ts) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                domain,
                persona_id,
                topic,
                error,
                attempts,
                datetime.datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()


def _print_failure_summary(out_db: str | Path) -> None:
    try:
        with sqlite3.connect(out_db) as conn:
            _ensure_failed_tasks_table(conn)
            rows = conn.execute(
                "SELECT persona_id, topic, attempts, error, ts "
                "FROM failed_tasks ORDER BY ts"
            ).fetchall()

        if rows:
            print(f"\n❌ 失败任务汇总 ({len(rows)} 条):")
            print(f"  {'PersonaID':<10} {'Attempts':<9} {'Topic':<25} {'Time':<20} Error")
            print(f"  {'-'*9:<10} {'-'*8:<9} {'-'*24:<25} {'-'*19:<20} -----")
            for pid, topic, attempts, error, ts in rows:
                topic_short = topic[:24]
                error_short = error[:60]
                print(f"  {pid:<10} {attempts:<9} {topic_short:<25} {ts:<20} {error_short}")
        else:
            print("\n✅ 所有任务均成功，无失败记录")

    except Exception:
        pass


# ---------------------------------------------------------------------------
# Single async task
# ---------------------------------------------------------------------------

async def _run_one_task(
    persona: dict,
    topic: str,
    domain: str,
    out_db: str | Path,
    db_lock: asyncio.Lock,
    sem: asyncio.Semaphore,
    pbar: tqdm,
    max_retries: int = 3,
    retry_delay: float = 2.0,
    send_interval: float = 0.0,
) -> None:
    async with sem:
        if send_interval > 0:
            await asyncio.sleep(send_interval)

        if _check_is_generated(out_db, domain, persona, topic):
            tqdm.write(f"  ⏩ [P{persona.get('id', 0):03d}|{topic[:20]}] 已生成，跳过")
            pbar.update(1)
            return

        prompt_mod = _load_prompt_module(domain)
        messages   = prompt_mod.build_messages(persona, topic)
        task_desc  = f"P{persona.get('id', 0):03d}|{topic[:20]}"

        for attempt in range(1, max_retries + 1):
            try:
                client = LLMClient()
                result = await asyncio.to_thread(
                    client.chat_json,
                    messages=messages,
                    temperature=0.85,
                    max_tokens=4096,
                    task_desc=task_desc,
                )

                async with db_lock:
                    _dispatch_insert(out_db, domain, persona, topic, result)
                break

            except Exception as e:
                if attempt < max_retries:
                    tqdm.write(
                        f"  ⚠️  [{task_desc}] attempt {attempt}/{max_retries} failed: {e}"
                        f" — retry in {retry_delay}s"
                    )
                    await asyncio.sleep(retry_delay)
                else:
                    tqdm.write(
                        f"  ❌ [{task_desc}] all {max_retries} attempts failed: {e}"
                    )
                    async with db_lock:
                        _record_failure(
                            db_path=out_db,
                            domain=domain,
                            persona_id=persona.get("id", 0),
                            topic=topic,
                            error=str(e),
                            attempts=max_retries,
                        )

        pbar.update(1)


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

async def run_async(
    domain: str,
    topics: list[str],
    bench_db: str | Path,
    out_db: str | Path,
    num_groups: int,
    batch: int,
    persona_ids: Optional[list[int]] = None,
    max_retries: int = 3,
    retry_delay: float = 2.0,
    send_interval: float = 0.0,
) -> None:
    # 1. 校验 num_groups
    if num_groups % GROUPS_PER_CALL != 0:
        print(f"❌ --num-groups 必须是 {GROUPS_PER_CALL} 的倍数，当前值: {num_groups}")
        sys.exit(1)
    n_calls = num_groups // GROUPS_PER_CALL

    # 2. Init DB
    init_db(out_db)

    # 3. Load personas
    if domain in _NO_PERSONA_DOMAINS:
        personas = [_DUMMY_PERSONA]
        print(f"ℹ️  Domain '{domain}' 不使用 benchmark.db 人设，将直接调用 LLM 生成内联 persona")
    else:
        # [BUG FIX] 使用 _PERSONA_DOMAIN_MAP 解析实际查询 domain
        # sports_health 在 benchmark.db 中没有对应 domain 的人设，
        # 需要不按 domain 过滤（使用所有人设）或映射到其他 domain
        persona_domain = _PERSONA_DOMAIN_MAP.get(domain, domain)
        personas = get_personas(bench_db, domain=persona_domain, persona_ids=persona_ids)
        if not personas:
            print(f"❌ No personas found for domain='{persona_domain}' in {bench_db}")
            print(f"   (原始 domain='{domain}'，persona 查询 domain='{persona_domain}')")
            print(f"   提示：请检查 benchmark.db 中 synthetic_users 表的 domain 字段值")
            sys.exit(1)

    total_calls = len(topics) * n_calls
    print(
        f"👥 人设数: {len(personas)} | "
        f"📚 Topic 数: {len(topics)} | "
        f"🔢 每 Topic 调用次数: {n_calls} (={num_groups} 组) | "
        f"🔁 总调用数: {total_calls} | "
        f"⚡ 并发: {batch} | "
        f"🔄 最大重试: {max_retries}"
        + (f" | ⏱ 提交间隔: {send_interval}s" if send_interval > 0 else "")
    )

    # 4. Upsert personas（仅 persona-based domain）
    if domain not in _NO_PERSONA_DOMAINS:
        for p in personas:
            upsert_persona(out_db, p)

    # 5. 展开任务队列
    tasks = _build_task_list(personas, topics, n_calls)

    # 6. 并发执行
    sem     = asyncio.Semaphore(batch)
    db_lock = asyncio.Lock()

    with tqdm(total=total_calls, desc="Generating", unit="call") as pbar:
        coros = [
            _run_one_task(
                persona=persona,
                topic=topic,
                domain=domain,
                out_db=out_db,
                db_lock=db_lock,
                sem=sem,
                pbar=pbar,
                max_retries=max_retries,
                retry_delay=retry_delay,
                send_interval=send_interval,
            )
            for persona, topic in tasks
        ]
        await asyncio.gather(*coros)

    # 7. Stats
    stats = get_stats(out_db)
    print("\n📊 Output DB stats:")
    for table, count in stats.items():
        print(f"   {table}: {count} rows")
    print(f"\n✅ Done → {out_db}")

    # 8. 失败汇总
    _print_failure_summary(out_db)


def run(
    domain: str,
    topics: list[str],
    bench_db: str | Path,
    out_db: str | Path,
    num_groups: int,
    batch: int,
    persona_ids: Optional[list[int]] = None,
    max_retries: int = 3,
    retry_delay: float = 2.0,
    send_interval: float = 0.0,
) -> None:
    asyncio.run(run_async(
        domain=domain,
        topics=topics,
        bench_db=bench_db,
        out_db=out_db,
        num_groups=num_groups,
        batch=batch,
        persona_ids=persona_ids,
        max_retries=max_retries,
        retry_delay=retry_delay,
        send_interval=send_interval,
    ))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Generate persona-based health queries.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--domain", "-d",
        default="general_medical",
        choices=list(_DOMAIN_PROMPT_MAP),
        help="Query domain (default: general_medical)",
    )
    p.add_argument(
        "--topics", "-t",
        default=None,
        help="Topics: path to .txt file OR comma-separated inline string. "
             "省略时自动读取 topics/{domain}.txt",
    )
    p.add_argument(
        "--bench-db", "-b",
        default="data/benchmark.db",
        help="Path to benchmark.db (default: data/benchmark.db). "
             "sports/red_team domain 不需要此参数。",
    )
    p.add_argument(
        "--out-db", "-o",
        default="output/queries.db",
        help="Path to output queries DB (default: output/queries.db)",
    )
    p.add_argument(
        "--num-groups", "-n",
        type=int,
        default=5,
        help=f"每个 topic 生成的总批次数 (default: 5). "
             f"sports 推荐 2，red_team 推荐 1-3",
    )
    p.add_argument(
        "--batch",
        type=int,
        default=1,
        help="并发请求数上限 (default: 1，即串行)",
    )
    p.add_argument(
        "--persona-id", "-p",
        type=int,
        nargs="+",
        metavar="ID",
        help="只使用指定人设 ID（可多个）。省略则使用全部。sports/red_team 忽略此参数。",
    )
    p.add_argument(
        "--max-retries",
        type=int,
        default=100,
        help="单任务最大重试次数 (default: 100)",
    )
    p.add_argument(
        "--retry-delay",
        type=float,
        default=2.0,
        help="重试间隔秒数 (default: 2.0)",
    )
    p.add_argument(
        "--send-interval",
        type=float,
        default=0.0,
        help="每个并发槽拿到后额外等待的秒数，用于限速（0=不等待）. "
             "health/sports 推荐 20，red_team 可设为 5-10",
    )
    return p


if __name__ == "__main__":
    args = _build_parser().parse_args()

    topics = _load_topics(args.topics, domain=args.domain)

    if not topics:
        print("❌ No topics loaded. Check --topics argument.")
        sys.exit(1)

    run(
        domain=args.domain,
        topics=topics,
        bench_db=args.bench_db,
        out_db=args.out_db,
        num_groups=args.num_groups,
        batch=args.batch,
        persona_ids=args.persona_id,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay,
        send_interval=args.send_interval,
    )
