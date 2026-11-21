"""理論の検証の表: 理論ごと・人気の帯ごとに、当てはまる馬の成績を「同じ人気の馬」と比べた倍率と、単勝・複勝の回収率、期間ごとの倍率を並べる。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from .period_split import PeriodSplit
from .popularity_band import BAND_NAMES
from .same_popularity_rates import PLACE, WIN, SamePopularityRates
from .theory import Theory

#: 帯で絞らない行の名前。
ALL_BANDS = "全"
BASE_COLUMNS: tuple[str, ...] = ("理論", "帯", "頭数", "3着以内率", "3着以内の倍率", "1着の倍率", "単勝回収率", "複勝回収率")
_PERIOD = "_period"


@dataclass(frozen=True)
class TheoryCheckTable:
    """``table``（``FinalRunners`` の表）から、理論 × 帯 の行を作る。

    倍率 = 実際に来た頭数 ÷ 同じ人気の馬と同じ率で来たときの頭数。1 より大きければ人気のわりに来る、小さければ買われすぎ。
    頭数が ``min_runs`` に届かない行は出さず、期間の頭数が ``min_period_runs`` に届かない倍率は空にする（偶然の幅が大きいため）。
    """

    periods: PeriodSplit = PeriodSplit()
    min_runs: int = 60
    min_period_runs: int = 20

    def build(self, table: pd.DataFrame, theories: tuple[Theory, ...], *, title: str) -> Table:
        rates = SamePopularityRates().fit(table)
        labelled = table.assign(**{_PERIOD: self.periods.labels(table["race_date"])})
        period_names = sorted(labelled[_PERIOD].dropna().unique())
        rows = []
        for theory in theories:
            matched = labelled[theory.applies(labelled)]
            rows.extend(self._theory_rows(theory, matched, rates, period_names))
        columns = (*BASE_COLUMNS, *(_period_column(name) for name in period_names))
        note = ("倍率は「同じ人気の馬と同じ率で来たときの頭数」に対する実際の頭数（3着以内・1着）。期間の倍率は3着以内。"
                f"頭数 {self.min_runs} 未満の行は出さない。期間の頭数が {self.min_period_runs} 未満の倍率は空。回収率は 1点 100円。")
        return Table.from_records(rows, columns, title=title, note=note)

    def _theory_rows(self, theory: Theory, matched: pd.DataFrame, rates: SamePopularityRates, period_names: list[str]) -> list[dict]:
        subsets = {ALL_BANDS: matched, **{name: matched[matched["band"] == band] for band, name in BAND_NAMES.items()}}
        return [self._row(theory, band_name, subset, rates, period_names)
                for band_name, subset in subsets.items() if len(subset) >= self.min_runs]

    def _row(self, theory: Theory, band_name: str, subset: pd.DataFrame, rates: SamePopularityRates, period_names: list[str]) -> dict:
        row = {
            "理論": theory.name, "帯": band_name, "頭数": len(subset),
            "3着以内率": _percent(subset[PLACE].mean()),
            "3着以内の倍率": _ratio(subset[PLACE].sum(), rates.expected(subset, PLACE)),
            "1着の倍率": _ratio(subset[WIN].sum(), rates.expected(subset, WIN)),
            "単勝回収率": _percent(subset["win_return"].mean()), "複勝回収率": _percent(subset["place_return"].mean()),
        }
        for name in period_names:
            in_period = subset[subset[_PERIOD] == name]
            enough = len(in_period) >= self.min_period_runs
            row[_period_column(name)] = _ratio(in_period[PLACE].sum(), rates.expected(in_period, PLACE)) if enough else None
        return row


def _period_column(name: str) -> str:
    return f"倍率 {name}"


def _ratio(actual: float, expected: float) -> float | None:
    return round(float(actual) / expected, 2) if expected > 0 else None


def _percent(value: float) -> str:
    return f"{value:.1%}"
