"""血統（父・父の父・母父）ごとの、産駒の成績。

**「産駒の成績」とは、その血統を持つ馬たちが走った成績のこと。** 種牡馬自身が現役だったころの成績ではない。

条件ごとの成績（成績7つ。``perf`` を参照）に加えて、**2つの差**を出す。
差が大きいところが「この血統が得意な条件」で、予想の材料や、予想AI の特徴量を決めるのに使う。

| 差 | 意味 | 使いどころ |
|---|---|---|
| 血統の全体との差 | その条件の複勝率 − その血統の全体の複勝率 | その血統の中で、得意な条件・苦手な条件 |
| 条件の平均との差 | その条件の複勝率 − その条件の全馬の複勝率 | ほかの血統と比べて、その条件で強いか |

**条件どうしを比べるときは「条件の平均との差」を見る。** 複勝率は頭数で変わる（頭数が少ないほど高く出る）ので、
「血統の全体との差」だけで見ると、頭数の少ない障害レースがいつも得意に見える。

    from 共通 import pedigree
    rows = pedigree.split_rows(con, pedigree.role("父"), pedigree.split("競馬場"), Filters())
    table = pedigree.split_table(rows, "父", pedigree.split("競馬場"), Filters())
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from . import perf
from .filters import Filters
from .render import Table

#: 血統の立場（CLI と画面で指名する名前 → ``perf`` の切り口の名前）。
ROLES: dict[str, str] = {"父": "sire", "父の父": "grandsire", "母父": "damsire"}
#: 条件の切り口（CLI と画面で指名する名前 → ``perf`` の切り口の名前）。
SPLITS: dict[str, str] = {
    "競馬場": "venue", "芝ダ": "surface", "馬場状態": "going", "距離帯": "distance-band",
    "コース": "course-name", "コース単位": "course",
}
#: 差を見る成績の列（この列で「得意・不得意」を測る）。
EDGE_KEY = "複勝率"
#: 差の列の見出し。
PEDIGREE_EDGE_COLUMN = "血統の全体との差"
BASELINE_EDGE_COLUMN = "条件の平均との差"
#: 血統ごとの成績を見るのに要る、その血統の産駒の出走数。これ未満は率が極端になりやすい。
DEFAULT_MIN_RUNS = 50
#: 条件ごとに分けたあと、1行として残すのに要る出走数。
DEFAULT_MIN_SPLIT_RUNS = 20
#: 並べ方（指名する名前 → 何で並べるか）。
SORT_KEYS: tuple[str, ...] = (EDGE_KEY, PEDIGREE_EDGE_COLUMN, BASELINE_EDGE_COLUMN)
DEFAULT_SORT_KEY = EDGE_KEY


@dataclass(frozen=True)
class PedigreeRow:
    """血統 × 条件 の1行。

    ``overall`` はその血統の全体の成績、``baseline`` はその条件の全馬の成績。どちらも差を出すのに使う。
    """

    name: str
    split_labels: tuple[str, ...]
    row: perf.PerfRow
    overall: perf.PerfRow
    baseline: perf.PerfRow

    @property
    def rate(self) -> float:
        """その条件での複勝率。"""
        return self.row.rates()[EDGE_KEY]

    @property
    def pedigree_edge(self) -> float:
        """その条件の複勝率 − その血統の全体の複勝率。プラスなら、その血統の中では得意な条件。"""
        return self.rate - self.overall.rates()[EDGE_KEY]

    @property
    def baseline_edge(self) -> float:
        """その条件の複勝率 − その条件の全馬の複勝率。プラスなら、ほかの血統より強い。"""
        return self.rate - self.baseline.rates()[EDGE_KEY]

    def sort_value(self, key: str) -> float:
        """``SORT_KEYS`` の名前で並べるときの値。"""
        values = {EDGE_KEY: self.rate, PEDIGREE_EDGE_COLUMN: self.pedigree_edge,
                  BASELINE_EDGE_COLUMN: self.baseline_edge}
        return values[key]

    def cells(self) -> list[str]:
        """表のセル（血統・条件の値・成績7つ・2つの差）。"""
        return [self.name, *self.split_labels, *self.row.cells(),
                _signed_percent(self.pedigree_edge), _signed_percent(self.baseline_edge)]


def _signed_percent(value: float) -> str:
    """差を ``+3.2%`` の形にする。"""
    return f"{value * 100:+.1f}%"


def role(name: str) -> perf.Dimension:
    """血統の立場（父・父の父・母父）の切り口。知らない名前は選べるものを添えて落とす。"""
    return _dimension_of(name, ROLES, "血統の立場")


def split(name: str) -> perf.Dimension:
    """条件の切り口（競馬場・芝ダ・馬場状態・距離帯・コース・コース単位）。"""
    return _dimension_of(name, SPLITS, "条件")


def _dimension_of(name: str, catalog: dict[str, str], label: str) -> perf.Dimension:
    try:
        return perf.dimension(catalog[name])
    except KeyError:
        raise LookupError(f"知らない{label}です: {name}\n選べるもの: {', '.join(catalog)}") from None


def overall_rows(con: duckdb.DuckDBPyConnection, role_dim: perf.Dimension, filters: Filters,
                 min_runs: int = DEFAULT_MIN_RUNS) -> dict[str, perf.PerfRow]:
    """血統ごとの、条件で分けない全体の成績（血統の名前 → 成績）。"""
    rows = perf.perf_rows(con, role_dim, filters, min_runs=min_runs)
    return {str(row.labels[0]): row for row in rows}


def baseline_rows(con: duckdb.DuckDBPyConnection, split_dim: perf.Dimension,
                  filters: Filters) -> dict[tuple[str, ...], perf.PerfRow]:
    """条件ごとの、全馬の成績（条件の値 → 成績）。血統の強さを比べる基準にする。"""
    rows = perf.perf_rows(con, split_dim, filters)
    return {tuple(str(label) for label in row.labels): row for row in rows}


def split_rows(con: duckdb.DuckDBPyConnection, role_dim: perf.Dimension, split_dim: perf.Dimension,
               filters: Filters = Filters(), *, min_runs: int = DEFAULT_MIN_RUNS,
               min_split_runs: int = DEFAULT_MIN_SPLIT_RUNS, name: str | None = None) -> list[PedigreeRow]:
    """血統 × 条件 ごとの成績。``name`` を渡すと、その血統（部分一致）だけにする。

    出走の少ない血統（``min_runs`` 未満）と、出走の少ない条件（``min_split_runs`` 未満）は落とす。
    """
    overall = overall_rows(con, role_dim, filters, min_runs)
    baseline = baseline_rows(con, split_dim, filters)
    rows = perf.perf_rows(con, perf.cross(role_dim, split_dim), filters, min_runs=min_split_runs)
    wanted = _wanted_names(overall, name)
    return [_pedigree_row(row, overall, baseline) for row in rows if str(row.labels[0]) in wanted]


def _pedigree_row(row: perf.PerfRow, overall: dict[str, perf.PerfRow],
                  baseline: dict[tuple[str, ...], perf.PerfRow]) -> PedigreeRow:
    name = str(row.labels[0])
    split_labels = tuple(str(label) for label in row.labels[1:])
    return PedigreeRow(name, split_labels, row, overall[name], baseline[split_labels])


def _wanted_names(overall: dict[str, perf.PerfRow], name: str | None) -> set[str]:
    """出す血統の名前。``name`` があれば部分一致で絞る。1つも無ければ、名前を添えて落とす。"""
    if name is None:
        return set(overall)
    matched = {found for found in overall if name in found}
    if not matched:
        raise LookupError(f"その血統の産駒が、条件に合う出走の中にいません（出走が少ない血統も落としています）: {name}")
    return matched


def sorted_rows(rows: list[PedigreeRow], *, sort_key: str = DEFAULT_SORT_KEY,
                top: int | None = None) -> list[PedigreeRow]:
    """``sort_key``（``SORT_KEYS`` のどれか）の大きい順に並べ、上位だけ返す。"""
    if sort_key not in SORT_KEYS:
        raise ValueError(f"並べ方は {', '.join(SORT_KEYS)} のどれかです: {sort_key}")
    ordered = sorted(rows, key=lambda row: -row.sort_value(sort_key))
    return ordered[:top] if top else ordered


def split_table(rows: list[PedigreeRow], role_name: str, split_dim: perf.Dimension, filters: Filters,
                cover: perf.Coverage | None = None) -> Table:
    """血統 × 条件 の表。列は 血統 | 条件の値 | 成績7つ | 2つの差。"""
    title = f"{role_name}の産駒の成績（{split_dim.title}別） — {filters.describe()}"
    columns = [role_name, *split_dim.column_names, *perf.PERF_COLUMNS,
               PEDIGREE_EDGE_COLUMN, BASELINE_EDGE_COLUMN]
    note = (f"{PEDIGREE_EDGE_COLUMN} = その条件の{EDGE_KEY} − その血統の全体の{EDGE_KEY}（その血統の中で得意な条件）。"
            f"{BASELINE_EDGE_COLUMN} = その条件の{EDGE_KEY} − その条件の全馬の{EDGE_KEY}（ほかの血統と比べて強いか）。"
            f"条件どうしを比べるときは{BASELINE_EDGE_COLUMN}を見る（複勝率は頭数で変わるため）。")
    table = Table(columns, [row.cells() for row in rows],
                  title=title + (f"（{cover.text()}）" if cover else ""), note=note)
    table.meta = {"role": role_name, "split": split_dim.name, "filters": filters.describe(), "rows": len(rows)}
    return table


def overall_table(overall: dict[str, perf.PerfRow], role_name: str, filters: Filters) -> Table:
    """血統ごとの、条件で分けない全体の成績。"""
    rows = sorted(overall.values(), key=lambda row: -row.rates()[EDGE_KEY])
    return Table([role_name, *perf.PERF_COLUMNS], [[*row.labels, *row.cells()] for row in rows],
                 title=f"{role_name}の産駒の成績（全体） — {filters.describe()}")


def catalog() -> Table:
    """選べる血統の立場・条件・並べ方の一覧。"""
    roles = [["血統の立場", name, perf.dimension(key).title] for name, key in ROLES.items()]
    splits = [["条件", name, perf.dimension(key).title] for name, key in SPLITS.items()]
    sorts = [["並べ方", name, ""] for name in SORT_KEYS]
    return Table(["種類", "指定する名前", "中身"], [*roles, *splits, *sorts], title="血統成績で選べるもの")
