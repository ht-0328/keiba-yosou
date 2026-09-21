"""事象の検索: 「人気馬が負けた」「穴馬が勝った」に当てはまる出走を、1行 = 1頭で並べる。

研究の出発点は「事象が起きたレースを集めて1件ずつ見る」こと。ここでは、

- 対象（分母）: 出走した馬のうち、人気・オッズの条件に合うもの（例: 1番人気）
- 事象（分子）: そのうち着順の条件に合うもの（例: 4着以下 = 馬券外。競走中止・失格も含む）

を数え、事象の行に「勝ち馬」「1番人気」の列を添えて返す。閾値はすべて引数で変えられる。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import duckdb

from . import perf
from .facts import FACTS_TABLE, ensure_facts
from .filters import Filters, Range
from .render import Table

#: 事象の種類。
KINDS: dict[str, str] = {"lost": "人気馬が負けた", "longshot": "穴馬が勝った"}
#: 規則として読む項目（絞り込みの同名の項目は使わない）。
RULE_FIELDS: tuple[str, ...] = ("pop", "odds", "finish")
MAX_LIMIT = 1000

#: 一覧に出す列（事実表の列名か付随列, 見出し）。
EVENT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("race_date", "日付"), ("venue", "場"), ("race_no", "R"), ("race_name", "レース名"), ("class_name", "クラス"),
    ("course", "コース"), ("distance_m", "距離"), ("condition", "馬場"), ("field_size", "頭数"),
    ("horse_no", "馬番"), ("horse_name", "馬名"), ("popularity", "人気"), ("win_odds", "単勝"), ("finish", "着順"),
    ("abnormal_name", "異常"), ("jockey", "騎手"), ("corner4", "4角"), ("last3f", "上がり"), ("win_payout", "単勝払戻"),
    ("winner", "勝ち馬"), ("winner_pop", "勝ち馬人気"), ("winner_odds", "勝ち馬単勝"),
    ("fav_name", "1番人気"), ("fav_finish", "1番人気の着順"), ("race_id", "rid"), ("horse_id", "hid"),
)


@dataclass(frozen=True)
class EventRule:
    """事象の規則。``pop``・``odds`` が対象、``finish`` が事象。"""

    kind: str
    pop: Range | None
    odds: Range | None
    finish: Range

    def describe(self) -> str:
        """人が読む形。例: ``1番人気が4着以下``。"""
        subject = " かつ ".join(part for part in (
            f"{self.pop.text()}番人気" if self.pop else "", f"単勝{self.odds.text()}倍" if self.odds else "",
        ) if part) or "全馬"
        return f"{subject}が{_finish_text(self.finish)}"

    def subject_sql(self) -> tuple[str, list[Any]]:
        """対象（分母）の条件。"""
        clauses, params = [], []
        for column, value in (("popularity", self.pop), ("win_odds", self.odds)):
            if value is not None:
                clause, args = value.sql(column)
                clauses.append(clause)
                params.extend(args)
        return " AND ".join(clauses) or "TRUE", params

    def event_sql(self) -> tuple[str, list[Any]]:
        """事象（分子）の条件。上限が無ければ、着順の付かない行（競走中止・失格）も事象に入れる。"""
        if self.finish.high is None:
            return "(finish IS NULL OR finish >= ?)", [self.finish.low]
        return self.finish.sql("finish")


#: 既定の規則。
LOST_DEFAULT = EventRule("lost", Range(1, 1), None, Range(4, None))
LONGSHOT_DEFAULT = EventRule("longshot", None, Range(10, None), Range(1, 1))
DEFAULTS: dict[str, EventRule] = {"lost": LOST_DEFAULT, "longshot": LONGSHOT_DEFAULT}


def _finish_text(finish: Range) -> str:
    if finish.low == finish.high:
        return f"{int(finish.low)}着"
    if finish.high is None:
        return f"{int(finish.low)}着以下（中止・失格を含む）"
    return f"{int(finish.low or 1)}〜{int(finish.high)}着"


def rule_from(kind: str, pop: str | None = None, odds: str | None = None, finish: str | None = None) -> EventRule:
    """文字列（CLI・URL）から規則を作る。省略した項目は種類ごとの既定。"""
    if kind not in DEFAULTS:
        raise ValueError(f"事象の種類は {', '.join(KINDS)} のどれかです: {kind}")
    base = DEFAULTS[kind]
    chosen_pop = Range.parse(pop) if pop else base.pop
    chosen_odds = Range.parse(odds) if odds else base.odds
    if kind == "longshot" and (pop or odds):
        chosen_pop = Range.parse(pop) if pop else None
        chosen_odds = Range.parse(odds) if odds else None
    return EventRule(kind, chosen_pop, chosen_odds, Range.parse(finish) if finish else base.finish)


def search_events(con: duckdb.DuckDBPyConnection, rule: EventRule, filters: Filters, *, limit: int = 200,
                  offset: int = 0) -> Table:
    """事象の一覧。``meta`` に対象数・事象数・率。"""
    ensure_facts(con)
    where, where_params = filters.where()
    subject, subject_params = rule.subject_sql()
    event, event_params = rule.event_sql()
    limit = max(1, min(int(limit), MAX_LIMIT))
    offset = max(0, int(offset))
    # DuckDB の ? は SQL 文中に現れた順に束縛される。対象（base）を先に書き、事象の条件をその後に置く。
    base = f"subject AS (SELECT * FROM {FACTS_TABLE} WHERE ran AND {where} AND {subject})"
    base_params = [*where_params, *subject_params]
    population, events, *aggregates = con.execute(
        f"WITH {base} SELECT count(*), count(*) FILTER (WHERE {event}), {perf.AGGREGATES_SQL} FROM subject",
        [*base_params, *event_params],
    ).fetchone()
    subject_perf = perf.perf_row_from(("対象",), aggregates)
    select = ", ".join(column for column, _ in EVENT_COLUMNS)
    cursor = con.execute(
        f"""
        WITH {base}, race_extra AS (
            SELECT race_id,
                   max(CASE WHEN finish = 1 THEN horse_name END) AS winner,
                   max(CASE WHEN finish = 1 THEN popularity END) AS winner_pop,
                   max(CASE WHEN finish = 1 THEN win_odds END) AS winner_odds,
                   max(CASE WHEN popularity = 1 THEN horse_name END) AS fav_name,
                   max(CASE WHEN popularity = 1 THEN finish END) AS fav_finish
            FROM {FACTS_TABLE} WHERE ran GROUP BY race_id
        )
        SELECT {select} FROM subject JOIN race_extra USING (race_id)
        WHERE {event}
        ORDER BY race_date DESC, race_id DESC, popularity NULLS LAST
        LIMIT ? OFFSET ?
        """, [*base_params, *event_params, limit, offset],
    )
    rows = [list(row) for row in cursor.fetchall()]
    rate = events / population if population else 0.0
    shown = f"{offset + 1}〜{offset + len(rows)} 件" if rows else "該当なし"
    table = Table(
        [title for _, title in EVENT_COLUMNS], rows,
        title=f"{KINDS[rule.kind]}: {rule.describe()}（{filters.describe()}）",
        note=(f"対象 {population:,} 頭のうち {events:,} 頭（{rate * 100:.1f}%）。{shown}を表示。"
              f"対象の成績: {perf.summary_text(subject_perf)}"),
    )
    table.meta = {"kind": rule.kind, "rule": rule.describe(), "population": population, "events": events,
                  "rate": round(rate, 4), "offset": offset, "limit": limit, "filters": filters.describe(),
                  "summary": perf.summary_dict(subject_perf)}
    return table
