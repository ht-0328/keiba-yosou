"""形 × 期間ごとの成績の表。"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from 共通.bootstrap_interval import BootstrapInterval
from 共通.perf import percent
from 共通.render import Table

from .member_races import MemberRaces
from .payout_table import PAYOUT
from .period import Period
from .row_spec import RowSpec
from .ticket_settlement import HIT, POINTS

#: 1点の額（円）。
POINT_YEN = 100
#: 払戻の実額を出さない表（docs に貼る）の列と、実額つきの表の列。
_HEAD = ["形", "券種", "期間", "買ったレース", "点数", "1レースの点数", "1レースの金額"]
_YEN = ["投資", "払戻"]
_TAIL = ["回収率", "回収率の90%の幅", "的中レース", "的中率", "集計金額を満たした的中の割合"]


class PeriodTable:
    """精算の表から、行（``RowSpec``: 形か合計）× 期間ごとの成績の表を作る。

    数えるのは、買ったレース（1点以上あるレース）・点数・1レースの点数と金額・投資・払戻・回収率（払戻 ÷ 投資）・
    90% の幅（開催日を単位にしたブートストラップ）・的中レース・的中率・集計金額を満たした的中の割合（的中のうち、1レースの払戻が
    サイトの集計金額以上だったもの。サイトが載せている当たりがどれだけ選ばれたものかを見る）。
    ``with_yen`` を偽にすると投資・払戻の実額の列を省く（docs 向け）。
    """

    def __init__(self, specs: Sequence[RowSpec], periods: Sequence[Period], with_yen: bool = True) -> None:
        self._specs = list(specs)
        self._periods = list(periods)
        self._with_yen = with_yen
        self._members = MemberRaces()
        self._interval = BootstrapInterval()

    @property
    def headers(self) -> list[str]:
        return [*_HEAD, *(_YEN if self._with_yen else []), *_TAIL]

    def table(self, settled: pd.DataFrame, title: str, note: str = "") -> Table:
        rows = []
        years = pd.to_datetime(settled["race_date"]).dt.year
        for spec in self._specs:
            races = self._members.of(settled, spec)
            race_years = pd.to_datetime(races["race_date"]).dt.year if not races.empty else pd.Series(dtype=int)
            for period in self._periods:
                chosen = races[period.contains(race_years)] if not races.empty else races
                if chosen.empty and not period.contains(years).any():
                    continue
                rows.append(self.row(spec, period.label, chosen))
        return Table(self.headers, rows, title=title, note=note)

    def row(self, spec: RowSpec, period_label: str, races: pd.DataFrame) -> list[str]:
        """1行の値。``races`` は ``MemberRaces.of`` の戻り値をその期間に絞ったもの。"""
        if races.empty:
            return [spec.label, spec.ticket, period_label, "0", "0", "—", "—", *(["0円", "0円"] if self._with_yen else []), "—", "—", "0", "—", "—"]
        count = len(races)
        points = int(races[POINTS].sum())
        stake = float(points * POINT_YEN)
        payout = float(races[PAYOUT].sum())
        low, high = self._interval.of(races["race_date"], races[POINTS].astype(float) * POINT_YEN, races[PAYOUT].astype(float))
        hits = int(races[HIT].sum())
        yen_cells = [f"{stake:,.0f}円", f"{payout:,.0f}円"] if self._with_yen else []
        return [spec.label, spec.ticket, period_label, f"{count:,}", f"{points:,}", f"{points / count:.1f}", f"{points / count * POINT_YEN:,.0f}円",
                *yen_cells, percent(payout / stake), f"{percent(low)}〜{percent(high)}", f"{hits:,}", percent(hits / count),
                self._floor_share(spec, races)]

    @staticmethod
    def _floor_share(spec: RowSpec, races: pd.DataFrame) -> str:
        """的中のうち、1レースの払戻が集計金額以上だったものの割合（集計金額ごと）。合計の行や的中が無ければ —。"""
        hits = races[races[HIT]]
        if not spec.floors or hits.empty:
            return "—"
        parts = []
        for floor in spec.floors:
            floors = hits[POINTS].astype(int).map(floor.of)
            parts.append(f"{percent(float((hits[PAYOUT] >= floors).mean()))}（{floor.label}）")
        return " ／ ".join(parts)
