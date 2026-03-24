"""
Unified query quality checker.

Reads generated queries from output DB, calls LLM to review quality,
generates a structured report. Automatically adapts review criteria
based on the domain's generation prompt (query type definitions).

Usage:
  # Review general_medical (full)
  python -m query_generator.checker --domain general_medical

  # Review with sampling
  python -m query_generator.checker --domain health --sample 100

  # Specific personas + custom report path
  python -m query_generator.checker --domain sports_health --persona-id 1 3 5 --report output/review_v1.txt

  # Review red_team
  python -m query_generator.checker --domain red_team --sample 50

  # Review sports
  python -m query_generator.checker --domain sports --sample 50
"""

import argparse
import importlib
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

from .llm_client import LLMClient
from .output_db import _DOMAIN_TABLE_MAP, _NO_PERSONA_DOMAINS, _connect

# ---------------------------------------------------------------------------
# Domain → prompt module (mirrors generator.py)
# ---------------------------------------------------------------------------
_DOMAIN_PROMPT_MAP = {
    "general_medical": "query_generator.prompts.general_medical",
    "health":          "query_generator.prompts.health",
    "sports":          "query_generator.prompts.sports",
    "red_team":        "query_generator.prompts.red_team",
    "sports_health":   "query_generator.prompts.sports_health",
}


# ---------------------------------------------------------------------------
# Auto-extract query type info from generation prompt
# ---------------------------------------------------------------------------

def _extract_domain_info(domain: str) -> dict:
    """
    Extract query type definitions and review criteria from a domain's
    generation prompt module. Returns a dict with:
      - type_labels: list of query type labels (e.g. ["通用知识Query", ...])
      - system_prompt: the generation system prompt (for context)
      - has_persona: whether the domain uses personas
    """
    module_path = _DOMAIN_PROMPT_MAP.get(domain)
    if module_path is None:
        raise ValueError(f"Unknown domain: {domain}")

    mod = importlib.import_module(module_path)

    # Extract system prompt
    system_prompt = getattr(mod, "SYSTEM_PROMPT", "")
    if not system_prompt:
        # sports/red_team use different structures
        system_prompt = getattr(mod, "_SYSTEM_PROMPT", "")

    has_persona = domain not in _NO_PERSONA_DOMAINS

    return {
        "system_prompt": system_prompt,
        "has_persona": has_persona,
        "domain": domain,
    }


# ---------------------------------------------------------------------------
# Load queries from DB
# ---------------------------------------------------------------------------

def _load_queries(
    db_path: str | Path,
    domain: str,
    persona_ids: Optional[list[int]] = None,
    sample: Optional[int] = None,
) -> list[dict]:
    """Load queries from the domain table with optional filtering and sampling."""
    table = _DOMAIN_TABLE_MAP.get(domain)
    if table is None:
        raise ValueError(f"Unknown domain: {domain}")

    sql = f"SELECT * FROM {table} WHERE 1=1"
    params: list = []

    if domain not in _NO_PERSONA_DOMAINS and persona_ids:
        placeholders = ",".join("?" * len(persona_ids))
        sql += f" AND persona_id IN ({placeholders})"
        params.extend(persona_ids)

    sql += " ORDER BY id"

    conn = _connect(db_path)
    try:
        rows = conn.execute(sql, params).fetchall()
        queries = [dict(r) for r in rows]
    finally:
        conn.close()

    if sample and sample < len(queries):
        queries = random.sample(queries, sample)

    return queries


# ---------------------------------------------------------------------------
# Build review prompt (adapts to any domain)
# ---------------------------------------------------------------------------

def _build_review_prompt(domain_info: dict, queries_batch: list[dict], domain: str) -> list[dict]:
    """
    Build a review prompt that adapts to the domain.
    Injects the generation prompt's quality criteria so the reviewer
    knows what standards to check against.
    """
    # Format queries for review
    queries_text = ""
    for i, q in enumerate(queries_batch, 1):
        # Adapt field names based on domain
        if domain == "red_team":
            query_text = q.get("query_text", "")
            category = q.get("query_category", "")
            queries_text += f"[{i}] ID={q.get('id')} | 类别={category}\n    {query_text}\n\n"
        elif domain == "sports":
            query_text = q.get("query_text", "")
            query_type = q.get("query_type", "")
            topic = q.get("catalog_topic", "")
            queries_text += f"[{i}] ID={q.get('id')} | 类型={query_type} | 主题={topic}\n    {query_text}\n\n"
        else:
            query_text = q.get("query_text", "")
            type_label = q.get("query_type_label", "")
            topic = q.get("catalog_topic", "")
            persona_id = q.get("persona_id", "?")
            queries_text += (
                f"[{i}] ID={q.get('id')} | persona={persona_id} | "
                f"类型={type_label} | 主题={topic}\n    {query_text}\n\n"
            )

    system_prompt = f"""你是一位严格的健康查询数据集质量审查专家。
你的任务是逐条审查以下由 LLM 生成的 {domain} 域查询，找出有问题的条目。

【审查标准】
1. 语言自然度：是否像真人口语提问，而非机器生成的书面语
2. 类型匹配：查询内容是否符合其标注的类型定义
3. 逻辑一致性：查询是否与人设背景/主题逻辑匹配（如老年人不该问青少年问题）
4. 格式规范：是否包含不该出现的特殊符号（括号解释、英文混杂等）
5. 重复/相似：同一 persona × topic 下是否有高度重复的查询
6. 内容质量：intent 是否合理，data_fields 是否与查询内容匹配

【该 domain 的原始生成约束（供参考）】
{domain_info['system_prompt'][:2000]}

【输出格式（严格 JSON）】
{{
  "total_reviewed": <审查总数>,
  "flagged_count": <有问题的条数>,
  "flagged": [
    {{
      "id": <query ID>,
      "issue_type": "语言不自然/类型不匹配/逻辑矛盾/格式违规/内容重复/质量低下",
      "description": "具体问题说明（1-2句）"
    }}
  ]
}}

只标记确有问题的条目（置信度>80%），正常的不要标记。"""

    user_prompt = f"请审查以下 {len(queries_batch)} 条 {domain} 域查询：\n\n{queries_text}"

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


# ---------------------------------------------------------------------------
# Run review
# ---------------------------------------------------------------------------

def run_check(
    domain: str,
    db_path: str | Path,
    report_path: str | Path,
    persona_ids: Optional[list[int]] = None,
    sample: Optional[int] = None,
    batch_size: int = 30,
) -> None:
    """
    Main review pipeline:
    1. Load queries from DB
    2. Split into batches
    3. LLM reviews each batch
    4. Aggregate and write report
    """
    print(f"📋 Loading {domain} queries from {db_path}...")
    queries = _load_queries(db_path, domain, persona_ids, sample)

    if not queries:
        print(f"❌ No queries found for domain='{domain}' in {db_path}")
        sys.exit(1)

    total = len(queries)
    print(f"   Found {total} queries" + (f" (sampled from larger set)" if sample else ""))

    domain_info = _extract_domain_info(domain)

    # Split into batches
    batches = [queries[i:i+batch_size] for i in range(0, len(queries), batch_size)]
    print(f"   Split into {len(batches)} review batches (batch_size={batch_size})")

    # Review each batch
    client = LLMClient()
    all_flagged = []

    for batch_idx, batch in enumerate(batches, 1):
        print(f"   🔍 Reviewing batch {batch_idx}/{len(batches)} ({len(batch)} queries)...")
        messages = _build_review_prompt(domain_info, batch, domain)

        try:
            result = client.chat_json(
                messages=messages,
                temperature=0.3,
                max_tokens=4096,
                task_desc=f"review-{domain}-batch{batch_idx}",
            )
            flagged = result.get("flagged", [])
            all_flagged.extend(flagged)
            print(f"      → {len(flagged)} issues found")
        except Exception as e:
            print(f"      ⚠️ Batch {batch_idx} review failed: {e}")

    # Build report
    _write_report(
        report_path=report_path,
        domain=domain,
        total=total,
        queries=queries,
        flagged=all_flagged,
    )


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _write_report(
    report_path: str | Path,
    domain: str,
    total: int,
    queries: list[dict],
    flagged: list[dict],
) -> None:
    """Generate structured review report."""
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    ok_count = total - len(flagged)
    ok_pct = ok_count / total * 100 if total > 0 else 0
    flag_pct = len(flagged) / total * 100 if total > 0 else 0

    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"  Query Quality Review Report — {domain}")
    lines.append(f"{'='*60}")
    lines.append("")

    # --- Overall stats ---
    lines.append("【总体比率】")
    lines.append(f"  正常 Query   :  {ok_count:>4d} 条  ({ok_pct:.1f}%)")
    lines.append(f"  标记有问题   :  {len(flagged):>4d} 条  ({flag_pct:.1f}%)")
    lines.append(f"  总计审查     :  {total:>4d} 条")
    lines.append("")

    # --- Distribution by query type ---
    if domain not in _NO_PERSONA_DOMAINS:
        type_counter: dict[str, int] = Counter()
        type_total: dict[str, int] = Counter()
        for q in queries:
            label = q.get("query_type_label", q.get("query_type", "unknown"))
            type_total[label] += 1
        for f in flagged:
            # Match flagged ID back to query
            fid = f.get("id")
            for q in queries:
                if q.get("id") == fid:
                    label = q.get("query_type_label", q.get("query_type", "unknown"))
                    type_counter[label] += 1
                    break

        lines.append("【问题分布 — 按 Query 类型】")
        for label in sorted(type_total.keys()):
            flagged_n = type_counter.get(label, 0)
            total_n = type_total[label]
            pct = flagged_n / total_n * 100 if total_n > 0 else 0
            lines.append(f"  {label:<20s} : {flagged_n} / {total_n} 条有问题  ({pct:.1f}%)")
        lines.append("")

    # --- Distribution by topic/category ---
    if domain == "red_team":
        topic_key = "query_category"
    else:
        topic_key = "catalog_topic"

    topic_counter: dict[str, int] = Counter()
    topic_total: dict[str, int] = Counter()
    for q in queries:
        t = q.get(topic_key, "unknown")
        topic_total[t] += 1
    for f in flagged:
        fid = f.get("id")
        for q in queries:
            if q.get("id") == fid:
                t = q.get(topic_key, "unknown")
                topic_counter[t] += 1
                break

    lines.append(f"【问题分布 — 按{'类别' if domain == 'red_team' else '知识目录主题'}】")
    for topic in sorted(topic_total.keys()):
        flagged_n = topic_counter.get(topic, 0)
        total_n = topic_total[topic]
        pct = flagged_n / total_n * 100 if total_n > 0 else 0
        lines.append(f"  {topic:<30s}  {flagged_n} / {total_n} 条  ({pct:.1f}%)")
    lines.append("")

    # --- Distribution by issue type ---
    issue_type_counter = Counter(f.get("issue_type", "未分类") for f in flagged)
    if issue_type_counter:
        lines.append("【问题分布 — 按问题类型】")
        for itype, count in issue_type_counter.most_common():
            lines.append(f"  {itype:<20s} : {count} 条")
        lines.append("")

    # --- Flagged detail ---
    if flagged:
        lines.append("【有问题 Query 明细】")
        for i, f in enumerate(flagged, 1):
            fid = f.get("id", "?")
            # Find original query
            original = None
            for q in queries:
                if q.get("id") == fid:
                    original = q
                    break

            lines.append(f"  [{i}]")
            lines.append(f"    ID          : {fid}")
            if original:
                if domain not in _NO_PERSONA_DOMAINS:
                    lines.append(f"    persona_id  : {original.get('persona_id', '?')}")
                lines.append(f"    主题        : {original.get(topic_key, '?')}")
                type_label = original.get("query_type_label", original.get("query_type", "?"))
                lines.append(f"    类型        : {type_label}")
                lines.append(f"    Query 文本  : {original.get('query_text', '?')}")
            lines.append(f"    问题类型    : {f.get('issue_type', '?')}")
            lines.append(f"    问题说明    : {f.get('description', '?')}")
            lines.append("")
    else:
        lines.append("【无问题 Query，全部通过审查】")
        lines.append("")

    report_text = "\n".join(lines)

    # Write to file
    report_path.write_text(report_text, encoding="utf-8")
    print(f"\n📊 Report written to {report_path}")
    print(f"   Total: {total} | OK: {ok_count} ({ok_pct:.1f}%) | Flagged: {len(flagged)} ({flag_pct:.1f}%)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Review generated query quality using LLM.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--domain", "-d",
        default="general_medical",
        choices=list(_DOMAIN_PROMPT_MAP),
        help="Domain to review (default: general_medical)",
    )
    p.add_argument(
        "--db", "-b",
        default="output/queries.db",
        help="Path to queries DB (default: output/queries.db)",
    )
    p.add_argument(
        "--report", "-r",
        default=None,
        help="Report output path (default: output/review_{domain}.txt)",
    )
    p.add_argument(
        "--persona-id", "-p",
        type=int,
        nargs="+",
        metavar="ID",
        help="Only review queries from these persona IDs",
    )
    p.add_argument(
        "--sample", "-s",
        type=int,
        default=None,
        help="Random sample N queries instead of reviewing all",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=30,
        help="Queries per LLM review call (default: 30)",
    )
    return p


if __name__ == "__main__":
    args = _build_parser().parse_args()

    report_path = args.report or f"output/review_{args.domain}.txt"

    run_check(
        domain=args.domain,
        db_path=args.db,
        report_path=report_path,
        persona_ids=args.persona_id,
        sample=args.sample,
        batch_size=args.batch_size,
    )
