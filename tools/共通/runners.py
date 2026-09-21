"""出走の検索: 事実表を絞り込みで検索して、1行 = 1頭の出走の一覧を返す。

画面の「出走（検索）」と ``tools/出走検索/runners.py`` の両方がここを使う。
"""

from __future__ import annotations

import duckdb

from . import perf
from .facts import FACTS_TABLE, ensure_facts
from .filters import Filters
from .render import Table

#: 一覧に出す列（事実表の列名, 見出し）。
RUNNER_COLUMNS: tuple[tuple[str, str], ...] = (
    ("race_date", "日付"), ("venue", "場"), ("race_no", "R"), ("race_name", "レース名"), ("class_name", "クラス"),
    ("course", "コース"), ("distance_m", "距離"), ("condition", "馬場"), ("field_size", "頭数"),
    ("frame_no", "枠"), ("horse_no", "馬番"), ("horse_name", "馬名"), ("sex", "性"), ("age", "齢"), ("jockey", "騎手"),
    ("popularity", "人気"), ("win_odds", "単勝"), ("finish", "着順"), ("abnormal_name", "異常"),
    ("corner4", "4角"), ("last3f", "上がり"), ("dm_rank", "タイム型"), ("tm_rank", "対戦型"),
    ("race_id", "rid"), ("horse_id", "hid"),
)
#: 並べ替えの選択肢と ORDER BY。
SORTS: dict[str, str] = {
    "date": "race_date DESC, race_id DESC, popularity NULLS LAST",
    "odds": "win_odds DESC NULLS LAST, race_date DESC",
    "finish": "finish NULLS LAST, race_date DESC",
    "pop": "popularity NULLS LAST, race_date DESC",
}
DEFAULT_SORT = "date"
#: 1度に返す行数の上限。
MAX_LIMIT = 1000


def search_runners(con: duckdb.DuckDBPyConnection, filters: Filters, *, limit: int = 200, offset: int = 0,
                   sort: str = DEFAULT_SORT) -> Table:
    """条件に合う出走（取消・除外を除く）。``meta["total"]`` に総件数。"""
    if sort not in SORTS:
        raise ValueError(f"並べ替えは {', '.join(SORTS)} のどれかです: {sort}")
    ensure_facts(con)
    where, params = filters.where()
    limit = max(1, min(int(limit), MAX_LIMIT))
    offset = max(0, int(offset))
    total = con.execute(f"SELECT count(*) FROM {FACTS_TABLE} WHERE ran AND {where}", params).fetchone()[0]
    select = ", ".join(column for column, _ in RUNNER_COLUMNS)
    cursor = con.execute(
        f"SELECT {select} FROM {FACTS_TABLE} WHERE ran AND {where} ORDER BY {SORTS[sort]} LIMIT ? OFFSET ?",
        [*params, limit, offset],
    )
    rows = [list(row) for row in cursor.fetchall()]
    shown = f"{offset + 1}〜{offset + len(rows)} 件" if rows else "該当なし"
    summary = perf.summary_row(con, filters)
    table = Table([title for _, title in RUNNER_COLUMNS], rows, title=f"出走の検索: {filters.describe()}",
                  note=f"全 {total:,} 件のうち {shown}。この条件の成績: {perf.summary_text(summary)}")
    table.meta = {"total": total, "offset": offset, "limit": limit, "sort": sort, "filters": filters.describe(),
                  "summary": perf.summary_dict(summary)}
    return table
