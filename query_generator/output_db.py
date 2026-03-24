"""
Manages the query generator's own SQLite database.

Schema:
- personas                  : mirror of persona fields used for generation
- queries_general_medical   : generated queries for general_medical domain
- queries_health            : generated queries for health domain
- queries_sports            : generated queries for sports domain (inline personas)
- queries_red_team          : generated queries for red_team domain
- queries_sports_health     : generated queries for sports_health domain
"""

import json
import sqlite3
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

_CREATE_PERSONAS = """
CREATE TABLE IF NOT EXISTS personas (
    id                   INTEGER PRIMARY KEY,  -- same as synthetic_users.id
    name                 TEXT,
    gender               TEXT,
    age                  INTEGER,
    height_cm            REAL,
    weight_kg            REAL,
    bmi                  REAL,
    health_goal          TEXT,
    health_conditions    TEXT,
    fitness_level        TEXT,
    sleep_pattern        TEXT,
    device_type          TEXT,
    domain               TEXT,
    occupation           TEXT,
    physiological_stage  TEXT,
    personality_tags     TEXT,  -- JSON array
    preferred_sports     TEXT,  -- JSON array  (sports domain)
    sport_mastery        TEXT,  -- (sports domain)
    sport_goal           TEXT,  -- (sports domain)
    core_health_concerns TEXT,  -- JSON array  (health domain)
    created_at           DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_QUERIES_GENERAL_MEDICAL = """
CREATE TABLE IF NOT EXISTS queries_general_medical (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_id          INTEGER NOT NULL REFERENCES personas(id),
    catalog_topic       TEXT NOT NULL,       -- knowledge catalog item that prompted this batch
    group_index         INTEGER NOT NULL,    -- 1-5, which of the 5 groups in one LLM call
    query_type          INTEGER NOT NULL,    -- 1=通用知识 2=个性化数据 3=隐性个性化
    query_type_label    TEXT NOT NULL,       -- human-readable label
    query_text          TEXT NOT NULL,       -- the actual query (Chinese)
    intent              TEXT,               -- why this persona would ask this
    data_fields         TEXT,               -- JSON array of health data fields touched
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_gm_persona    ON queries_general_medical(persona_id);
CREATE INDEX IF NOT EXISTS idx_gm_topic      ON queries_general_medical(catalog_topic);
CREATE INDEX IF NOT EXISTS idx_gm_type       ON queries_general_medical(query_type);
"""

_CREATE_QUERIES_SPORTS_HEALTH = """
CREATE TABLE IF NOT EXISTS queries_sports_health (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_id       INTEGER NOT NULL REFERENCES personas(id),
    catalog_topic    TEXT    NOT NULL,
    group_index      INTEGER NOT NULL,
    query_type       INTEGER NOT NULL,   -- 1=专业知识 / 2=用户数据查询 / 3=知识计算
    query_type_label TEXT    NOT NULL,
    query_text       TEXT    NOT NULL,
    intent           TEXT,
    data_fields      TEXT,               -- JSON 数组
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_qsh_persona   ON queries_sports_health(persona_id);
CREATE INDEX IF NOT EXISTS idx_qsh_topic     ON queries_sports_health(catalog_topic);
CREATE INDEX IF NOT EXISTS idx_qsh_type      ON queries_sports_health(query_type);
"""

# ---------------------------------------------------------------------------
# health domain 表
# ---------------------------------------------------------------------------

_CREATE_QUERIES_HEALTH = """
CREATE TABLE IF NOT EXISTS queries_health (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_id          INTEGER NOT NULL REFERENCES personas(id),
    catalog_topic       TEXT NOT NULL,
    topic_count         INTEGER NOT NULL DEFAULT 1,  -- number of sub-domains in catalog_topic
    group_index         INTEGER NOT NULL,
    query_type          INTEGER NOT NULL,    -- 1=通用知识 2=个性化数据 3=隐性个性化
    query_type_label    TEXT NOT NULL,
    query_text          TEXT NOT NULL,
    intent              TEXT,
    data_fields         TEXT,               -- JSON array
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_health_persona ON queries_health(persona_id);
CREATE INDEX IF NOT EXISTS idx_health_topic   ON queries_health(catalog_topic);
CREATE INDEX IF NOT EXISTS idx_health_type    ON queries_health(query_type);
CREATE INDEX IF NOT EXISTS idx_health_tcount  ON queries_health(topic_count);
"""

# ---------------------------------------------------------------------------
# sports domain 表
# ---------------------------------------------------------------------------

_CREATE_QUERIES_SPORTS = """
CREATE TABLE IF NOT EXISTS queries_sports (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    catalog_topic        TEXT NOT NULL,    -- sport combo, e.g. "冲浪_赛艇"
    query_index          INTEGER NOT NULL, -- 1-15 within one LLM call
    query_type           TEXT NOT NULL,    -- "通用知识"/"个性化数据"/"隐性个性化"
    query_text           TEXT NOT NULL,
    intent               TEXT,
    personal_data_needed TEXT,             -- JSON array
    scenario             TEXT,
    -- inline persona fields (LLM-generated, not from benchmark.db)
    persona_gender       TEXT,
    persona_age          INTEGER,
    persona_bmi          REAL,
    persona_sports       TEXT,             -- JSON array
    persona_level        TEXT,
    persona_frequency    TEXT,
    persona_goals        TEXT,             -- JSON array
    persona_background   TEXT,
    created_at           DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sports_topic  ON queries_sports(catalog_topic);
CREATE INDEX IF NOT EXISTS idx_sports_type   ON queries_sports(query_type);
"""

# ---------------------------------------------------------------------------
# red_team domain 表
# ---------------------------------------------------------------------------

_CREATE_QUERIES_RED_TEAM = """
CREATE TABLE IF NOT EXISTS queries_red_team (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    query_category  TEXT NOT NULL,   -- prompt_injection / persona_induction / function_inquiry / active_clarification
    query_text      TEXT NOT NULL,
    extra_fields    TEXT,            -- JSON blob: all category-specific fields besides query
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_rt_category ON queries_red_team(query_category);
"""

# ---------------------------------------------------------------------------
# Domain → table name mapping
# ---------------------------------------------------------------------------

_DOMAIN_TABLE_MAP: dict[str, str] = {
    "general_medical": "queries_general_medical",
    "health":          "queries_health",
    "sports":          "queries_sports",
    "red_team":        "queries_red_team",
    "sports_health":   "queries_sports_health",
}

# 不使用 personas 表 FK 的 domain
_NO_PERSONA_DOMAINS: set[str] = {"sports", "red_team"}


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def _connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

def init_db(db_path: str | Path) -> None:
    """Create all tables if they do not already exist."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = _connect(db_path)
    with conn:
        conn.executescript(_CREATE_PERSONAS)
        conn.executescript(_CREATE_QUERIES_GENERAL_MEDICAL)
        conn.executescript(_CREATE_QUERIES_HEALTH)
        conn.executescript(_CREATE_QUERIES_SPORTS)
        conn.executescript(_CREATE_QUERIES_RED_TEAM)
        conn.executescript(_CREATE_QUERIES_SPORTS_HEALTH)
    conn.close()
    print(f"✅ Output DB ready: {db_path}")


# ---------------------------------------------------------------------------
# Persona upsert
# ---------------------------------------------------------------------------

def upsert_persona(db_path: str | Path, persona: dict) -> None:
    """
    Insert or replace a persona record (keyed by id).
    List fields are serialised to JSON strings.
    """
    _JSON_LIST_FIELDS = {"personality_tags", "preferred_sports", "core_health_concerns"}

    row = {}
    for k, v in persona.items():
        if k in _JSON_LIST_FIELDS and isinstance(v, list):
            row[k] = json.dumps(v, ensure_ascii=False)
        else:
            row[k] = v

    columns = ", ".join(row.keys())
    placeholders = ", ".join("?" * len(row))
    sql = f"INSERT OR REPLACE INTO personas ({columns}) VALUES ({placeholders})"

    conn = _connect(db_path)
    with conn:
        conn.execute(sql, list(row.values()))
    conn.close()


# ---------------------------------------------------------------------------
# Query insertion — general_medical / health / sports_health
# ---------------------------------------------------------------------------

def insert_queries(
    db_path: str | Path,
    domain: str,
    persona_id: int,
    catalog_topic: str,
    groups: list[dict],
) -> None:
    """
    Save a list of query groups (as returned by the LLM) to the domain table.
    Supports: general_medical, health, sports_health.
    For sports / red_team use insert_sports_queries / insert_red_team_queries.
    """
    table = _DOMAIN_TABLE_MAP.get(domain)
    if table is None:
        raise ValueError(f"Unknown domain '{domain}'. Supported: {list(_DOMAIN_TABLE_MAP)}")
    if domain in _NO_PERSONA_DOMAINS:
        raise ValueError(
            f"Domain '{domain}' does not use insert_queries(). "
            f"Use insert_sports_queries() or insert_red_team_queries() instead."
        )

    is_health = (domain == "health")
    topic_count = len(catalog_topic.split("_")) if is_health else None

    if is_health:
        sql = f"""
        INSERT INTO {table}
            (persona_id, catalog_topic, topic_count, group_index, query_type,
             query_type_label, query_text, intent, data_fields)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
    else:
        sql = f"""
        INSERT INTO {table}
            (persona_id, catalog_topic, group_index, query_type,
             query_type_label, query_text, intent, data_fields)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

    rows = []
    for group in groups:
        g_idx = group["group_index"]
        for q in group["queries"]:
            data_fields = q.get("data_fields", [])
            if isinstance(data_fields, list):
                data_fields = json.dumps(data_fields, ensure_ascii=False)
            if is_health:
                rows.append((
                    persona_id, catalog_topic, topic_count, g_idx,
                    q["type"], q["type_label"], q["query_text"],
                    q.get("intent", ""), data_fields,
                ))
            else:
                rows.append((
                    persona_id, catalog_topic, g_idx,
                    q["type"], q["type_label"], q["query_text"],
                    q.get("intent", ""), data_fields,
                ))

    conn = _connect(db_path)
    with conn:
        conn.executemany(sql, rows)
    conn.close()


# ---------------------------------------------------------------------------
# Query insertion — sports
# ---------------------------------------------------------------------------

def insert_sports_queries(
    db_path: str | Path,
    catalog_topic: str,
    queries: list[dict],
) -> None:
    """Save sports queries to queries_sports table."""
    sql = """
    INSERT INTO queries_sports
        (catalog_topic, query_index, query_type, query_text, intent,
         personal_data_needed, scenario,
         persona_gender, persona_age, persona_bmi, persona_sports,
         persona_level, persona_frequency, persona_goals, persona_background)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    rows = []
    for idx, q in enumerate(queries, 1):
        p = q.get("persona") or {}
        persona_sports = p.get("sports", [])
        persona_goals  = p.get("goals", [])
        rows.append((
            catalog_topic,
            idx,
            q.get("type", ""),
            q.get("query", ""),
            q.get("intent", ""),
            json.dumps(q.get("personal_data_needed") or [], ensure_ascii=False),
            q.get("scenario", ""),
            p.get("gender", ""),
            p.get("age"),
            p.get("bmi"),
            json.dumps(persona_sports if isinstance(persona_sports, list) else [], ensure_ascii=False),
            p.get("level", ""),
            p.get("frequency", ""),
            json.dumps(persona_goals if isinstance(persona_goals, list) else [], ensure_ascii=False),
            p.get("background", ""),
        ))

    conn = _connect(db_path)
    with conn:
        conn.executemany(sql, rows)
    conn.close()


# ---------------------------------------------------------------------------
# Query insertion — red_team
# ---------------------------------------------------------------------------

def insert_red_team_queries(
    db_path: str | Path,
    query_category: str,
    queries: list[dict],
) -> None:
    """Save red_team queries to queries_red_team table."""
    sql = """
    INSERT INTO queries_red_team (query_category, query_text, extra_fields)
    VALUES (?, ?, ?)
    """
    rows = []
    for q in queries:
        query_text   = q.get("query", "")
        extra_fields = {k: v for k, v in q.items() if k != "query"}
        rows.append((
            query_category,
            query_text,
            json.dumps(extra_fields, ensure_ascii=False),
        ))

    conn = _connect(db_path)
    with conn:
        conn.executemany(sql, rows)
    conn.close()


# ---------------------------------------------------------------------------
# Read-back helpers
# ---------------------------------------------------------------------------

def get_queries(
    db_path: str | Path,
    domain: str,
    persona_id: Optional[int] = None,
    catalog_topic: Optional[str] = None,
) -> list[dict]:
    """Fetch generated queries with optional filters."""
    table = _DOMAIN_TABLE_MAP[domain]
    sql = f"SELECT * FROM {table} WHERE 1=1"
    params: list = []

    if domain not in _NO_PERSONA_DOMAINS and persona_id is not None:
        sql += " AND persona_id = ?"
        params.append(persona_id)

    topic_col = "query_category" if domain == "red_team" else "catalog_topic"
    if catalog_topic:
        sql += f" AND {topic_col} = ?"
        params.append(catalog_topic)

    order_col = "query_category, id" if domain == "red_team" else "catalog_topic, id"
    sql += f" ORDER BY {order_col}"

    conn = _connect(db_path)
    try:
        rows = conn.execute(sql, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            for json_field in ("data_fields", "personal_data_needed", "extra_fields",
                               "persona_sports", "persona_goals"):
                if d.get(json_field):
                    try:
                        d[json_field] = json.loads(d[json_field])
                    except (json.JSONDecodeError, TypeError):
                        pass
            result.append(d)
        return result
    finally:
        conn.close()


def get_stats(db_path: str | Path) -> dict:
    """Return row counts for all tables."""
    conn = _connect(db_path)
    try:
        stats = {}
        all_tables = ["personas"] + list(_DOMAIN_TABLE_MAP.values())
        for table in all_tables:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                stats[table] = count
            except sqlite3.OperationalError:
                stats[table] = 0
        return stats
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 断点续跑辅助
# ---------------------------------------------------------------------------

def is_generated(
    db_path: str | Path,
    domain: str,
    persona_id: int,
    catalog_topic: str,
) -> bool:
    """Return True if this persona × topic combination already has rows."""
    table = _DOMAIN_TABLE_MAP.get(domain)
    if table is None:
        return False
    try:
        conn = _connect(db_path)
        try:
            (count,) = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE persona_id=? AND catalog_topic=?",
                (persona_id, catalog_topic),
            ).fetchone()
            return count > 0
        finally:
            conn.close()
    except sqlite3.OperationalError:
        return False


def is_topic_generated(
    db_path: str | Path,
    domain: str,
    catalog_topic: str,
) -> bool:
    """For no-persona domains: Return True if this topic already has rows."""
    table = _DOMAIN_TABLE_MAP.get(domain)
    if table is None:
        return False
    topic_col = "query_category" if domain == "red_team" else "catalog_topic"
    try:
        conn = _connect(db_path)
        try:
            (count,) = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {topic_col}=?",
                (catalog_topic,),
            ).fetchone()
            return count > 0
        finally:
            conn.close()
    except sqlite3.OperationalError:
        return False
