# modules/search_utils.py
from __future__ import annotations

from typing import List, Optional, Any
import pandas as pd

# ===========================
# Query helpers (DuckDB)
# ===========================

def query_structured(
    db_path: str,
    *,
    start_ts: Optional[str] = None,
    end_ts: Optional[str] = None,
    host_in: Optional[List[str]] = None,
    user_like: Optional[str] = None,
    endpoint_like: Optional[str] = None,
    include_noisy: bool = False,
    limit: int = 1000,
) -> pd.DataFrame:
    import duckdb
    con = duckdb.connect(db_path, read_only=True)
    conds = []
    params: List[Any] = []

    if not include_noisy:
        conds.append("is_noise = FALSE")
    if start_ts:
        conds.append("ts >= TIMESTAMP ?"); params.append(start_ts)
    if end_ts:
        conds.append("ts <= TIMESTAMP ?"); params.append(end_ts)
    if host_in:
        conds.append(f"host IN ({','.join(['?']*len(host_in))})"); params.extend(host_in)
    if user_like:
        conds.append("user_id ILIKE ?"); params.append(f"%{user_like}%")
    if endpoint_like:
        conds.append("endpoint ILIKE ?"); params.append(f"%{endpoint_like}%")

    sql = "SELECT * FROM events"
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY ts DESC LIMIT ?"
    params.append(int(limit))

    df = con.execute(sql, params).df()
    con.close()
    return df


def query_fts(db_path: str, query: str, *, limit: int = 500) -> pd.DataFrame:
    import duckdb
    con = duckdb.connect(db_path, read_only=True)
    sql = """
    WITH hits AS (
      SELECT event_id, score
      FROM match_bm25('events', ?, fields := 'message', k := 1.2, b := 0.75)
      LIMIT ?
    )
    SELECT e.*, h.score
    FROM hits h JOIN events e USING(event_id)
    ORDER BY h.score DESC, e.ts DESC
    """
    try:
        df = con.execute(sql, [query, int(limit)]).df()
    except Exception:
        df = pd.DataFrame()
    con.close()
    return df
