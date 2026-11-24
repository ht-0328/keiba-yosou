"""印を付けた1レースの表とオッズの板から、高配当の買い目を作る。"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType

from 今週の予想.filter_columns import AGREEMENT, POOL_BACKED
from 今週の予想.forecast_columns import (
    DANGER_SCORE,
    HORSE_NO,
    IS_DANGER,
    MARK,
    MARKET_TOP3,
    MARKET_WIN,
    PLACE_ODDS_HIGH,
    PLACE_ODDS_LOW,
    PLACE_VALUE,
    POPULARITY,
    PROBABILITY,
    RANK,
    UNRATED,
    UPDOWN,
    WIN_ODDS,
    WIN_PROBABILITY,
    WIN_VALUE,
    WIN_VALUE_BAND,
)
from 今週の予想.mark_tickets import COLUMNS, RULE, VALUE
from 今週の予想.ticket_rules import HIGH_PAYOUT_LABELS, HIGH_PAYOUT_MAX_POINTS, HIGH_PAYOUT_TICKET_TYPES, HIGH_PAYOUT_VALUE_LINE

#: 予想に渡す馬ごとの表の列（予想のパッケージとの約束。印を付けた表に無い列は欠損値で渡す）。
HORSE_COLUMNS: tuple[str, ...] = (
    "race_id", HORSE_NO, PROBABILITY, WIN_PROBABILITY, MARKET_WIN, MARKET_TOP3, WIN_ODDS, PLACE_ODDS_LOW, PLACE_ODDS_HIGH, POPULARITY, RANK,
    IS_DANGER, DANGER_SCORE, MARK, UPDOWN, WIN_VALUE, PLACE_VALUE,
)
#: レースから写す列（無ければ欠損値）と、旗の列（無ければ偽）。
_RACE_COLUMNS: tuple[str, ...] = ("race_id", "race_date", "fold", WIN_VALUE_BAND)
_RACE_FLAGS: tuple[str, ...] = (AGREEMENT, POOL_BACKED)
#: 予想の結果（組の表）の列。券種の名前・組の馬番の並び。
_TICKET_TYPE, _HORSES = "ticket_type", "horses"


class HighPayoutPicker:
    """印を付けた1レースの表（``MarkRule.assign`` の戻り値に ``race_id`` などを足したもの）と、締め切り前の5券種の板
    （券種 → 列 ``race_id``・``combo``・``odds``）から、高配当の買い目（1行 = 1点。列は ``MarkTickets`` の ``COLUMNS``）を作る。

    組の確率は予想「高配当の組が当たるかを予想」（``predictor``。``HighPayoutPredictor``）が出し、買う組は買い目の決まり
    （``rule``。``HighPayoutRule``。オッズが高配当の線以上・上限未満で、確率 × オッズが期待値の線以上。上限の点数があれば確率の高い順）が選ぶ。
    買い方の名前は ``HIGH_PAYOUT_LABELS``（例 ``ワイド（高配当）``）、1点の単位は 1.0、期待値は 確率 × オッズ。
    対象の券種（``ticket_types``）でない券種の組と、評価できない馬（列 ``unrated`` が真）を含む組は落とす。
    当日の予想の表には複勝オッズ（最高）の列が無いので、``pick`` に渡した馬番ごとの複勝オッズ（``place_odds``。列 ``horse_no``・
    ``place_odds_high``）で埋める（予想は複勝オッズの最低と最高の両方を材料に学んでいるので、欠けたままだと学んだときと違う材料になる）。
    学習済みモデルが無いとき（``load`` に渡した置き場所が無いか、どの券種のモデルも置いていない）は ``ready`` が偽で、買い目は 0点。
    モデルの無い券種・板の足りない券種は、予想が組を返さないので 0点（誤りにしない）。
    ``value_line``・``max_points`` は ``rule`` を作ったときの期待値の線と上限の点数（結果の JSON と文に書くために持つ。選ぶのは ``rule``）。

    例: 板にワイド 3-9 が 24.5倍、予想の確率が 0.05 なら、期待値は 1.225 で、高配当の線（10倍）以上なので ``ワイド（高配当）`` の ``0309`` を1点。
    """

    def __init__(self, predictor: Any | None, rule: Any | None, high_lines: Mapping[TicketType, float] | None = None,
                 ticket_types: tuple[TicketType, ...] = HIGH_PAYOUT_TICKET_TYPES, value_line: float = HIGH_PAYOUT_VALUE_LINE,
                 max_points: int | None = HIGH_PAYOUT_MAX_POINTS) -> None:
        self._predictor = predictor
        self._rule = rule
        self._high_lines = dict(high_lines or {})
        self._ticket_types = tuple(ticket_types)
        self._value_line = value_line
        self._max_points = max_points

    @classmethod
    def load(cls, models: Path | None) -> HighPayoutPicker:
        """``models``（学習済みモデルの置き場所。``<置き場所>/<券種の英名>/race_day/``）を読んで作る。置き場所が無いか、どの券種のモデルも
        置いていなければ、買い目を作らない部品を返す。期待値の線と上限の点数は ``ticket_rules.py`` の ``HIGH_PAYOUT_VALUE_LINE``・
        ``HIGH_PAYOUT_MAX_POINTS``、帯は予想のパッケージの既定。
        予想のパッケージは、置き場所があるときだけ読み込む（学習の部品まで読み込んで重いので）。"""
        if models is None or not Path(models).is_dir():
            return cls(None, None)
        from yosou.high_payout_combos import DEFAULT_BANDS, HighPayoutPredictor, HighPayoutRule

        predictor = HighPayoutPredictor.load(Path(models))
        if not predictor.ticket_types:
            return cls(None, None)
        rule = HighPayoutRule(DEFAULT_BANDS, HIGH_PAYOUT_VALUE_LINE, HIGH_PAYOUT_MAX_POINTS)
        high_lines = {ticket_type: float(band.high_line) for ticket_type, band in DEFAULT_BANDS.items()}
        return cls(predictor, rule, high_lines)

    @property
    def ready(self) -> bool:
        """買い目を作れるか（学習済みモデルを読めたか）。"""
        return self._predictor is not None and self._rule is not None

    def needed(self) -> tuple[TicketType, ...]:
        """読むオッズの板の券種。対象の券種を絞っても、ほかの券種の板を予想の材料に使うので、5券種の全部。作れないときは読まない。"""
        return tuple(HIGH_PAYOUT_LABELS) if self.ready else ()

    def conditions(self) -> dict[str, Any]:
        """買い目の決まり（予想の結果の JSON に残して、文を作るときに使う）。``high_lines`` は 券種の名前 → 高配当の線（倍）。"""
        lines = {ticket_type.label: self._high_lines[ticket_type] for ticket_type in self._ticket_types if ticket_type in self._high_lines}
        return {"ready": self.ready, "value_line": self._value_line, "max_points": self._max_points, "high_lines": lines}

    def pick(self, marked: pd.DataFrame, boards: dict[TicketType, pd.DataFrame], place_odds: pd.DataFrame | None = None) -> pd.DataFrame:
        empty = pd.DataFrame(columns=list(COLUMNS))
        if not self.ready or marked.empty:
            return empty
        combos = self._predictor.predict(self._horses(marked, place_odds), boards)
        if combos is None or combos.empty:
            return empty
        picks = self._rule.pick(combos)
        label_of = {ticket_type.label: HIGH_PAYOUT_LABELS[ticket_type] for ticket_type in self._ticket_types}
        picks = picks[picks[_TICKET_TYPE].isin(label_of)]
        picks = picks[~self._has_unrated(picks, marked)]
        if picks.empty:
            return empty
        return picks.assign(**self._race_values(marked), **{RULE: picks[_TICKET_TYPE].map(label_of), "combo": picks["combo"].astype(str),
                                                           "stake_units": 1.0, VALUE: picks["value"].astype(float)})[list(COLUMNS)].reset_index(drop=True)

    @staticmethod
    def _horses(marked: pd.DataFrame, place_odds: pd.DataFrame | None = None) -> pd.DataFrame:
        """予想に渡す馬ごとの表（``HORSE_COLUMNS``。印を付けた表に無い列は欠損値）。複勝オッズ（最高）の無い馬は、``place_odds`` の値で埋める。"""
        horses = marked.reindex(columns=list(HORSE_COLUMNS))
        horses = horses.assign(race_id=horses["race_id"].astype(str), **{HORSE_NO: horses[HORSE_NO].astype(int)}).reset_index(drop=True)
        if place_odds is None or place_odds.empty:
            return horses
        highest = place_odds.dropna(subset=[HORSE_NO]).drop_duplicates(HORSE_NO).set_index(HORSE_NO)[PLACE_ODDS_HIGH].astype(float)
        known = pd.to_numeric(horses[PLACE_ODDS_HIGH], errors="coerce")
        return horses.assign(**{PLACE_ODDS_HIGH: known.fillna(horses[HORSE_NO].map(highest))})

    @staticmethod
    def _has_unrated(picks: pd.DataFrame, marked: pd.DataFrame) -> pd.Series:
        """評価できない馬を含む組か（真偽）。列 ``unrated`` が無ければ（前の形の表）全部偽。"""
        if UNRATED not in marked.columns:
            return pd.Series(False, index=picks.index)
        unrated = set(marked.loc[marked[UNRATED].fillna(False).astype(bool), HORSE_NO].astype(int))
        return picks[_HORSES].map(lambda horses: any(int(horse) in unrated for horse in horses)).astype(bool)

    @staticmethod
    def _race_values(marked: pd.DataFrame) -> dict[str, Any]:
        """買い目に写すレースの列の値（1レースなので先頭の行から）。"""
        first = marked.iloc[0]
        values = {column: first.get(column, np.nan) for column in _RACE_COLUMNS}
        flags = {flag: bool(first.get(flag)) if pd.notna(first.get(flag)) else False for flag in _RACE_FLAGS}
        return {**values, **flags}
