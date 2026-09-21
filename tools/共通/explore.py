"""回収率の探索: 指定した条件の中で、単勝か複勝の回収率が閾値（既定 100%）を超える切り口の値を探す。

「東京 芝1600m 良」のように条件を固定し、人気・オッズ帯・枠・前走の着順・逃げ経験 … の切り口を1つずつ
（``pairs`` なら2つの組み合わせも）当てて、出走数が ``min_runs`` 以上で回収率が閾値以上の行を集める。
年ごとの回収率も添える。出走数の少ない行は偶然で超えやすく、たくさんの切り口を試すほど偶然も増えるので、
年ごとに揃っている条件を優先し、別の期間（``--from``/``--to``）でも確かめてから使う。
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any

import duckdb

from . import perf
from .filters import Filters
from .render import Table

#: 探索に使う切り口（既定）。前日までに分かる材料を中心に、利用者が挙げた順に並べる。
DEFAULT_DIMENSIONS: tuple[str, ...] = (
    "venue", "distance", "course-name", "condition", "popularity", "odds", "frame", "number",
    "prev-finish", "prev-style", "winner-style", "course-win", "lead-exp", "best-time-rank", "field-size",
    "best-time-dist-rank", "surface-change", "prev-last3f", "last3f-time",
    "prev-popularity", "prev-margin", "prev-corner4", "prev-last3f-rank", "interval", "distance-change", "class-change",
    "jockey-change", "venue-change", "runs-before", "wins-before", "course-runs", "class", "age", "sex",
    "body-weight", "weight-change", "month", "dm-rank", "tm-rank",
)
DEFAULT_MIN_RUNS = 30
#: 閾値（回収率。1.0 = 100%）。
DEFAULT_THRESHOLD = 1.0
#: どちらの回収率で見るか。
TARGETS: dict[str, str] = {"both": "単勝か複勝", "win": "単勝", "place": "複勝"}
DEFAULT_TARGET = "both"
#: 組み合わせ（2つの切り口）を試すときの切り口の上限。多いと時間がかかる。
MAX_PAIR_DIMENSIONS = 12
DEFAULT_TOP = 100
#: 年ごとの回収率に使う切り口。
_YEAR = "year"
COLUMNS: tuple[str, ...] = ("切り口", "値", *perf.PERF_COLUMNS, "年ごとの回収率（単勝/複勝）")


@dataclass(frozen=True)
class Hit:
    """閾値を超えた1行。"""

    dimension: perf.Dimension
    row: perf.PerfRow
    by_year: dict[Any, perf.PerfRow]

    def score(self, target: str) -> float:
        rates = self.row.rates()
        if target == "win":
            return rates["単勝回収率"]
        if target == "place":
            return rates["複勝回収率"]
        return max(rates["単勝回収率"], rates["複勝回収率"])

    def value_text(self) -> str:
        return " / ".join(str(label) for label in self.row.labels)

    def years_text(self) -> str:
        parts = []
        for year in sorted(self.by_year):
            rates = self.by_year[year].rates()
            parts.append(f"{year} {perf.percent(rates['単勝回収率'])}/{perf.percent(rates['複勝回収率'])}")
        return " · ".join(parts)


def dimensions_from(names: list[str] | tuple[str, ...] | None) -> list[perf.Dimension]:
    """切り口の名前の並びを切り口にする。空なら既定。知らない名前は ``LookupError``。"""
    chosen = [name.strip() for name in (names or DEFAULT_DIMENSIONS) if name and name.strip()]
    return [perf.dimension(name) for name in dict.fromkeys(chosen)]


def passes(row: perf.PerfRow, target: str, threshold: float) -> bool:
    """回収率が閾値以上か。"""
    rates = row.rates()
    if target == "win":
        return rates["単勝回収率"] >= threshold
    if target == "place":
        return rates["複勝回収率"] >= threshold
    return rates["単勝回収率"] >= threshold or rates["複勝回収率"] >= threshold


def _year_rows(con: duckdb.DuckDBPyConnection, dim: perf.Dimension, filters: Filters) -> dict[tuple, dict[Any, perf.PerfRow]]:
    """切り口の値ごとに、年 → 成績。年で分けられない切り口（開催年そのもの）は空。"""
    if any(column.name == "開催年" for column in dim.columns):
        return {}
    crossed = perf.cross(dim, perf.dimension(_YEAR))
    grouped: dict[tuple, dict[Any, perf.PerfRow]] = {}
    for row in perf.perf_rows(con, crossed, filters, min_runs=1):
        grouped.setdefault(row.labels[:-1], {})[row.labels[-1]] = row
    return grouped


def _candidates(dims: list[perf.Dimension], pairs: bool) -> list[perf.Dimension]:
    """試す切り口。``pairs`` なら2つの組み合わせも足す。"""
    if not pairs:
        return list(dims)
    if len(dims) > MAX_PAIR_DIMENSIONS:
        raise ValueError(f"組み合わせを試すときは切り口を {MAX_PAIR_DIMENSIONS} 個までにしてください（今 {len(dims)} 個）")
    out = list(dims)
    for first, second in combinations(dims, 2):
        try:
            out.append(perf.cross(first, second))
        except ValueError:
            continue  # 同じ見出しが重なる組は飛ばす
    return out


def explore(con: duckdb.DuckDBPyConnection, filters: Filters = Filters(), dimension_names: list[str] | None = None, *,
            min_runs: int = DEFAULT_MIN_RUNS, threshold: float = DEFAULT_THRESHOLD, target: str = DEFAULT_TARGET,
            pairs: bool = False, top: int = DEFAULT_TOP) -> Table:
    """条件の中で回収率が閾値を超える切り口の値を集めた表。回収率の高い順。"""
    if target not in TARGETS:
        raise ValueError(f"target は {', '.join(TARGETS)} のどれかです: {target}")
    dims = dimensions_from(dimension_names)
    hits: list[Hit] = []
    checked = 0
    for dim in _candidates(dims, pairs):
        rows = perf.perf_rows(con, dim, filters, min_runs=max(1, int(min_runs)))
        checked += len(rows)
        passing = [row for row in rows if passes(row, target, threshold)]
        if not passing:
            continue
        years = _year_rows(con, dim, filters)
        hits.extend(Hit(dim, row, years.get(row.labels, {})) for row in passing)
    hits.sort(key=lambda hit: (-hit.score(target), -hit.row.runs))
    hits = hits[:max(1, int(top))]
    baseline = perf.summary_row(con, filters)
    table = Table(
        list(COLUMNS), [[hit.dimension.title, hit.value_text(), *hit.row.cells(), hit.years_text()] for hit in hits],
        title=f"回収率 {threshold * 100:.0f}% 以上（{TARGETS[target]}）: {filters.describe()}",
        note=(f"全体の成績: {perf.summary_text(baseline)}。切り口 {len(dims)} 個{'（2つの組み合わせも）' if pairs else ''}・"
              f"出走数 {min_runs} 以上の行 {checked:,} 件のうち {len(hits)} 件。"
              "出走数の少ない行は偶然で超えやすい。年ごとの回収率が揃っている条件を優先し、別の期間でも確かめる。"),
    )
    table.meta = {"hits": len(hits), "checked": checked, "dimensions": [d.name for d in dims], "min_runs": min_runs,
                  "threshold": threshold, "target": target, "pairs": pairs, "filters": filters.describe(),
                  "baseline": perf.summary_dict(baseline)}
    return table


def catalog() -> Table:
    """探索に使える切り口の一覧（既定で使うものに印）。"""
    rows = [[d.name, d.title, "○" if d.name in DEFAULT_DIMENSIONS else "", d.note] for d in perf.DIMENSIONS.values()]
    return Table(["切り口", "表題", "既定", "注意"], rows, title="探索に使える切り口")
