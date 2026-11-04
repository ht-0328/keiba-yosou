"""理論の検証の表: 理論ごと・帯ごと・期間ごとに、当てはまる馬の成績と「同じ人気の馬全体」「同じオッズの馬全体」の成績を並べ、残すかを判定する。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from 共通.render import Table

from .odds_baseline import OddsBaseline
from .popularity_band import BAND_NAMES
from .popularity_baseline import PLACE_RATE, PLACE_RETURN, WIN_RETURN, PopularityBaseline
from .theory import FAVORITE_FAILS, LONGSHOT_FAILS, Theory

COLUMNS: tuple[str, ...] = ("種類", "理論", "帯", "期間", "頭数", "1年あたり", "複勝率", "同じ人気の複勝率", "差（人気）",
                            "同じオッズの複勝率", "差（オッズ）", "複勝回収率", "同じオッズの複勝回収率", "単勝回収率", "同じオッズの単勝回収率",
                            "判定", "意味")
#: 残す候補の線: 1年あたりの頭数と、同じオッズの馬全体との複勝率の差（ポイント）。向きは理論の種類で決まる。
MIN_RUNS_PER_YEAR = 100
MIN_GAP_POINTS = 1.5
KEEP, WRONG_WAY, TOO_FEW, WEAK = "残す候補", "向きが違う", "頭数不足", "差が小さい"
#: 「来ない・崩れる」の理論は、差が負（複勝率が同じオッズより低い）なら当たり。
_NEGATIVE_KINDS = (FAVORITE_FAILS, LONGSHOT_FAILS)


@dataclass(frozen=True)
class TheoryCheckTable:
    """``table``（帯・事情つきの出走の行）を ``split`` の前後の2つの期間に分け、理論 × 帯 × 期間 の行を作る。判定は2つの期間をまとめて1つ。

    判定は「同じオッズの馬全体」との差で行う。人気の順位は同じでもオッズが違えば市場の見立ては違うので、
    オッズとの差が残る事情だけが、市場（オッズ）で分かること以上の手がかりである。
    """

    split: date

    def build(self, table: pd.DataFrame, theories: tuple[Theory, ...], *, title: str) -> Table:
        periods = self._periods(table)
        by_popularity = {label: PopularityBaseline().fit(rows) for label, rows in periods.items()}
        by_odds = {label: OddsBaseline().fit(rows) for label, rows in periods.items()}
        rows = []
        for theory in theories:
            rows.extend(self._theory_rows(theory, periods, by_popularity, by_odds))
        note = ("同じ人気の〜 / 同じオッズの〜 は、当てはまる馬と同じ人気（単勝オッズの帯）の馬全体の成績を内訳で重み付けした平均。差 = 複勝率 − それ（ポイント）。"
                f"判定は「{KEEP}」= 2つの期間とも 差（オッズ）の向きが理論どおりで {MIN_GAP_POINTS}pt 以上、1年あたり {MIN_RUNS_PER_YEAR} 頭以上。回収率は 1点 100円。")
        return Table.from_records(rows, COLUMNS, title=title, note=note)

    def _periods(self, table: pd.DataFrame) -> dict[str, pd.DataFrame]:
        day = pd.to_datetime(table["race_date"])
        before = table[day < pd.Timestamp(self.split)]
        after = table[day >= pd.Timestamp(self.split)]
        return {self._label(before): before, self._label(after): after}

    def _label(self, rows: pd.DataFrame) -> str:
        if rows.empty:
            return "（空）"
        years = pd.to_datetime(rows["race_date"]).dt.year
        return f"{years.min()}〜{years.max()}"

    def _theory_rows(self, theory: Theory, periods: dict[str, pd.DataFrame],
                     by_popularity: dict[str, PopularityBaseline], by_odds: dict[str, OddsBaseline]) -> list[dict]:
        rows = []
        for band in theory.bands:
            cells = [self._cells(theory, band, label, rows_in, by_popularity[label], by_odds[label]) for label, rows_in in periods.items()]
            verdict = self._verdict(theory, cells)
            rows.extend({**cell, "判定": verdict} for cell in cells)
        return rows

    def _cells(self, theory: Theory, band: str, label: str, rows: pd.DataFrame,
               by_popularity: PopularityBaseline, by_odds: OddsBaseline) -> dict:
        in_band = rows[rows["band"] == band]
        subset = in_band[theory.applies(in_band)]
        empty = subset.empty
        actual = _EMPTY if empty else by_popularity.actual(subset)
        popularity = _EMPTY if empty else by_popularity.expected(subset)
        odds = _EMPTY if empty else by_odds.expected(subset)
        years = max(pd.to_datetime(rows["race_date"]).dt.year.nunique(), 1) if len(rows) else 1
        gap_popularity = (actual[PLACE_RATE] - popularity[PLACE_RATE]) * 100
        gap_odds = (actual[PLACE_RATE] - odds[PLACE_RATE]) * 100
        return {
            "種類": theory.kind, "理論": theory.name, "帯": BAND_NAMES[band], "期間": label, "頭数": len(subset),
            "1年あたり": round(len(subset) / years), "複勝率": _pct(actual[PLACE_RATE]),
            "同じ人気の複勝率": _pct(popularity[PLACE_RATE]), "差（人気）": _points(gap_popularity),
            "同じオッズの複勝率": _pct(odds[PLACE_RATE]), "差（オッズ）": _points(gap_odds),
            "複勝回収率": _pct(actual[PLACE_RETURN]), "同じオッズの複勝回収率": _pct(odds[PLACE_RETURN]),
            "単勝回収率": _pct(actual[WIN_RETURN]), "同じオッズの単勝回収率": _pct(odds[WIN_RETURN]),
            "意味": theory.meaning, "_gap": gap_odds, "_per_year": len(subset) / years,
        }

    def _verdict(self, theory: Theory, cells: list[dict]) -> str:
        sign = -1.0 if theory.kind in _NEGATIVE_KINDS else 1.0
        gaps = [cell["_gap"] * sign for cell in cells]
        if any(cell["_per_year"] < MIN_RUNS_PER_YEAR for cell in cells):
            return TOO_FEW
        if any(gap != gap or gap <= 0 for gap in gaps):
            return WRONG_WAY
        if any(gap < MIN_GAP_POINTS for gap in gaps):
            return WEAK
        return KEEP


_EMPTY = {PLACE_RATE: float("nan"), PLACE_RETURN: float("nan"), WIN_RETURN: float("nan")}


def _pct(value: float) -> str:
    return "—" if value != value else f"{value:.1%}"


def _points(value: float) -> float | str:
    return "—" if value != value else round(value, 1)
