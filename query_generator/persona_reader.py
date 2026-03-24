"""
Reads persona/synthetic_users data from the main HQB benchmark database.
Only extracts persona-relevant fields; no dependency on main project code.
"""

import json
import sqlite3
from pathlib import Path
from typing import Optional

# Scalar fields to pull from synthetic_users
_SCALAR_FIELDS = [
    "id", "name", "gender", "age", "height_cm", "weight_kg", "bmi",
    "health_goal", "health_conditions", "fitness_level", "sleep_pattern",
    "device_type", "domain", "occupation", "physiological_stage",
    "sport_mastery", "sport_goal",  # sports-domain only (NULL otherwise)
]
# Fields stored as JSON strings in the DB
_JSON_FIELDS = [
    "personality_tags",       # list[str], always present
    "preferred_sports",       # list[str], sports domain only
    "core_health_concerns",   # list[str], health domain only
]


def _parse_row(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a plain dict, decoding JSON blob fields."""
    d = dict(row)
    for field in _JSON_FIELDS:
        val = d.get(field)
        if isinstance(val, str):
            try:
                d[field] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                pass  # keep raw string if malformed
    return d


def get_personas(
    db_path: str | Path,
    domain: Optional[str] = None,
    persona_ids: Optional[list[int]] = None,
) -> list[dict]:
    """
    Load persona records from the main benchmark database.

    Args:
        db_path:     Path to data/benchmark.db
        domain:      Filter by domain, e.g. "general_medical" / "sports" / "health"
        persona_ids: If set, only fetch these specific user IDs.

    Returns:
        List of persona dicts with all profile fields.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"Benchmark DB not found: {db_path}")

    fields_sql = ", ".join(_SCALAR_FIELDS + _JSON_FIELDS)
    sql = f"SELECT {fields_sql} FROM synthetic_users WHERE 1=1"
    params: list = []

    if domain:
        sql += " AND domain = ?"
        params.append(domain)

    if persona_ids:
        placeholders = ",".join("?" * len(persona_ids))
        sql += f" AND id IN ({placeholders})"
        params.extend(persona_ids)

    sql += " ORDER BY id"

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
        return [_parse_row(r) for r in rows]
    finally:
        conn.close()


def get_persona_by_id(db_path: str | Path, persona_id: int) -> Optional[dict]:
    """Fetch a single persona by ID. Returns None if not found."""
    results = get_personas(db_path, persona_ids=[persona_id])
    return results[0] if results else None
