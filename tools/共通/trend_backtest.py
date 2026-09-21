"""傾向スコアの検証: 終わったレースに同じ採点を当てて、点数の高い馬が本当に来ているかを成績7つで見る。

採点は本番と同じ ``trend.collect`` → ``trend.score``。母集団も当日の馬の累積も「そのレースの開催日より前」だけなので、
結果を先に見ることはない。ただし人気・馬体重・馬場状態は確定後の値を使う（発走前に手で入れた値の代わり）。

言葉:

- 点数の順位: そのレースの中で、点数の高い順に付けた順位。同点はランキングと同じ並び（プラスの多い順 → 馬番の小さい順）。
- 比べる相手: 同じレースの単勝人気の順位。点数の順位別の成績が人気の順位別に近いほど、点数は市場と同じくらい当たっている。
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

import duckdb

from . import perf, trend
from .facts import FACTS_TABLE, ensure_facts
from .filters import Filters
from .render import Table
from .trend_items import FACTORS, Factor

#: 順位の帯（上限, 名前）。上限はその値を含む。
RANK_BANDS: tuple[tuple[int, str], ...] = ((1, "1位"), (2, "2位"), (3, "3位"), (6, "4〜6位"), (10**6, "7位以下"))
#: 点数の帯（上限, 名前）。
SCORE_BANDS: tuple[tuple[int, str], ...] = ((-5, "−5 以下"), (-1, "−4〜−1"), (0, "0"), (4, "+1〜+4"), (9, "+5〜+9"), (10**6, "+10 以上"))
#: 人気の帯（上限, 名前）。
POPULARITY_BANDS: tuple[tuple[int, str], ...] = ((3, "1〜3番人気"), (6, "4〜6番人気"), (10**6, "7番人気以下"))
#: 採点に要る最少の出走頭数。少頭数は順位の意味が薄い。
MIN_FIELD = 5
#: 市場（人気）を使う項目のグループ。``without_market`` で外す。
MARKET_GROUPS: tuple[int, ...] = (8, 9)


def _band(value: int, bands: Sequence[tuple[int, str]]) -> str:
    return next(name for limit, name in bands if value <= limit)


@dataclass
class Tally:
    """帯ごとの成績を数える。"""

    rows: dict[tuple[str, ...], list[int]] = field(default_factory=dict)

    def add(self, key: tuple[str, ...], entry: dict[str, Any]) -> None:
        counts = self.rows.setdefault(key, [0, 0, 0, 0, 0, 0])
        finish = entry["finish"]
        counts[0] += 1
        for index, place in enumerate((1, 2, 3), start=1):
            counts[index] += finish == place
        counts[4] += entry["win_payout"] or 0
        counts[5] += entry["place_payout"] or 0

    def table(self, columns: Sequence[str], order: Sequence[tuple[str, ...]], *, title: str, note: str = "") -> Table:
        rows = [[*key, *perf.PerfRow(key, *self.rows[key]).cells()] for key in order if key in self.rows]
        return Table([*columns, *perf.PERF_COLUMNS], rows, title=title, note=note)


@dataclass
class BacktestResult:
    """検証の結果。"""

    races: int
    skipped: int
    first_date: str | None
    last_date: str | None
    options: trend.Options
    by_score_rank: Tally
    by_popularity_rank: Tally
    by_score_band: Tally
    by_rank_and_popularity: Tally
    seconds: float

    def tables(self) -> list[Table]:
        rank_names = [name for _, name in RANK_BANDS]
        summary = Table(["項目", "値"], [
            ["採点したレース", f"{self.races:,}（{self.first_date}〜{self.last_date}）"],
            ["飛ばしたレース", f"{self.skipped:,}（出走 {MIN_FIELD} 頭未満、または人気の無いレース）"],
            ["判定の線引き", f"出走数 {self.options.min_runs} 以上・良い {self.options.good} 倍以上・悪い {self.options.bad} 倍以下・強さ {self.options.min_z}"
             + (f"・段は {trend.LEVEL_BY_KEY[self.options.scope].title} だけ" if self.options.scope else "")],
            ["かかった時間", f"{self.seconds:.0f} 秒"],
        ], title="傾向スコアの検証")
        return [
            summary,
            self.by_score_rank.table(["点数の順位"], [(name,) for name in rank_names], title="点数の順位別の成績",
                                     note="点数が効いているなら、1位の勝率・複勝率が高く、順位が下がるほど下がる。"),
            self.by_popularity_rank.table(["人気の順位"], [(name,) for name in rank_names], title="比べる相手: 単勝人気の順位別の成績（同じレース）"),
            self.by_score_band.table(["点数"], [(name,) for _, name in SCORE_BANDS], title="点数の帯別の成績"),
            self.by_rank_and_popularity.table(
                ["点数の順位", "人気"], [(rank, pop) for rank in rank_names for _, pop in POPULARITY_BANDS], title="点数の順位 × 人気の帯",
                note="同じ人気の帯の中で、点数の順位が高い馬ほど成績が良ければ、点数は人気に無い情報を足している。"),
        ]


def race_ids(con: duckdb.DuckDBPyConnection, filters: Filters, *, sample: int | None = None) -> list[str]:
    """条件に合う確定レースの rid（古い順）。``sample`` を与えると、その数になるよう等間隔に間引く。"""
    ensure_facts(con)
    where, params = filters.where()
    rids = [rid for (rid,) in con.execute(
        f"SELECT DISTINCT race_id FROM {FACTS_TABLE} WHERE {where} ORDER BY race_id", params).fetchall()]
    if sample and 0 < sample < len(rids):
        step = len(rids) / sample
        rids = [rids[int(index * step)] for index in range(sample)]
    return rids


def without_market(factors: Sequence[Factor] = FACTORS) -> tuple[Factor, ...]:
    """人気を使う項目（穴馬の型・人気馬の型）を外した要因。"""
    return tuple(factor for factor in factors if factor.group not in MARKET_GROUPS)


def run(con: duckdb.DuckDBPyConnection, rids: Iterable[str], options: trend.Options = trend.Options(), *,
        factors: Sequence[Factor] = FACTORS, progress: Callable[[int, int, float], None] | None = None) -> BacktestResult:
    """レースを順に採点して、成績を帯ごとに数える。``progress(済んだ数, 全体, 秒)`` は途中経過の通知。"""
    targets = list(rids)
    tallies = Tally(), Tally(), Tally(), Tally()
    started = time.perf_counter()
    done = skipped = 0
    dates: list[str] = []
    for index, rid in enumerate(targets, start=1):
        report = trend.score(trend.collect(con, rid, factors=factors), options=options, factors=factors)
        runners = [horse for horse in report.horses if horse.entry["popularity"] is not None]
        if len(runners) < MIN_FIELD:
            skipped += 1
        else:
            _tally_race(runners, *tallies)
            dates.append(report.header["日付"])
            done += 1
        if progress:
            progress(index, len(targets), time.perf_counter() - started)
    return BacktestResult(done, skipped, min(dates, default=None), max(dates, default=None), options, *tallies,
                          seconds=time.perf_counter() - started)


def _tally_race(runners: Sequence[trend.HorseScore], by_score_rank: Tally, by_popularity_rank: Tally,
                by_score_band: Tally, by_rank_and_popularity: Tally) -> None:
    """1レースぶんを数える。``runners`` は点数の高い順（ランキングの並び）。"""
    for rank, horse in enumerate(runners, start=1):
        entry = horse.entry
        score_rank, popularity = _band(rank, RANK_BANDS), entry["popularity"]
        by_score_rank.add((score_rank,), entry)
        by_popularity_rank.add((_band(popularity, RANK_BANDS),), entry)
        by_score_band.add((_band(horse.score, SCORE_BANDS),), entry)
        by_rank_and_popularity.add((score_rank, _band(popularity, POPULARITY_BANDS)), entry)
