"""1レースの地方の印の買い目を決める流れ: 印の組 → 推奨買目と同じ組の確率（1着・2着・3着の条件つきロジット）と最新のオッズで期待値 →
トリガミを外す → どの組が当たっても払った額より多く戻るように 1レース 5,000円を配り、見込みの回収率で買うか見送るかを決める（中央の ``MarkReturn``）。"""

from __future__ import annotations

from typing import Any

import duckdb
import pandas as pd

from 今週の予想.forecast_columns import HORSE_NO, MARK, PLACE_VALUE
from 今週の予想.race_describer import RaceDescriber
from 今週の予想.torigami_filter import DROPPED, TorigamiFilter

from .forecast_horses import ForecastHorses
from .mark_bets import MarkBets
from .mark_points import MarkPoints
from .mark_ticket_rules import LOCAL_MARK_LABELS, MARK_MIN_HEADS
from .position_coefficients import PositionCoefficients
from .position_model import PROBABILITY, PositionModel
from .race_pools import RacePools
from .recommendation import ORDERED_TICKETS
from .ticket_pricer import TicketPricer
from .ticket_probabilities import TICKET_KEYS, TicketProbabilities

#: ``MarkReturn`` が当日の予想として扱う時点の言葉。
_RACE_DAY = "当日"
_NO_FRAMES = pd.DataFrame({"race_id": pd.Series(dtype="int64"), "horse_no": pd.Series(dtype="int64"), "frame_no": pd.Series(dtype="int64")})


class MarkRecommender:
    """``recommend(rid, forecast, marked)`` は、地方の predict の JSON（モデルごとの 1着・3着以内の確率つき）と、印を付けた全頭の表
    （``MarkRule.assign`` の表。列 ``HORSE_NO``・``MARK``）から、そのレースの印の買い目（``MarkBets``）を返す。
    頭数が線に届かない・◎ が無い・オッズか予想の確率が欠けた馬がいる、なら理由つきの「なし」。"""

    def __init__(self, con: duckdb.DuckDBPyConnection, coefficients: PositionCoefficients, model: PositionModel | None = None) -> None:
        self._con = con
        self._coefficients = coefficients
        self._model = model or PositionModel()

    def recommend(self, rid: str, forecast: dict, marked: pd.DataFrame) -> MarkBets:
        if len(marked) < MARK_MIN_HEADS:
            return MarkBets.none(f"{len(marked)}頭なので印の買い目の対象外（{MARK_MIN_HEADS}頭以上）")
        points = MarkPoints().of(marked)
        if not points:
            return MarkBets.none("◎ が無い")
        horses = ForecastHorses().of(forecast, int(rid), f"{rid[:4]}-{rid[4:6]}-{rid[6:8]}")
        tables = RacePools(self._con).build(rid, horses)
        if tables.horses.empty:
            return MarkBets.none("オッズか予想の確率が欠けた馬がいる")
        combos = self._model.predict(tables, self._coefficients)
        probabilities = TicketProbabilities().of(combos, _NO_FRAMES)
        tickets = self._tickets(rid, points, probabilities, combos)
        # 全頭の印と複勝の期待値も渡す（☆ を相手に入れなかったレースは、買い方の名前から ☆ を除いて見せるため。ShownRuleName）
        shown_horses = marked[[HORSE_NO, MARK, PLACE_VALUE]].to_dict("records")
        returns = RaceDescriber().mark_returns({"timing": _RACE_DAY, "tickets": tickets, "horses": shown_horses}, LOCAL_MARK_LABELS)
        if returns is None:
            return MarkBets.none("オッズのある組が無い")
        return MarkBets(returns[0], tuple(returns[1]))

    def _tickets(self, rid: str, points: list, probabilities: dict[str, pd.DataFrame], combos: pd.DataFrame) -> list[dict[str, Any]]:
        """1点ごとの辞書（``rule``・``label``・``odds``・``value``・``dropped``）。オッズか確率の無い組は落とし、トリガミの組には ``dropped`` を付ける。"""
        pricer = TicketPricer(self._con)
        priced: dict[str, dict[tuple[int, ...], tuple[float, float]]] = {}
        rows = []
        for rule, combo in points:
            ticket = rule.ticket_type.label
            if ticket not in priced:
                table = pricer.priced(ticket, probabilities[ticket], combos, rid)
                keys = list(TICKET_KEYS[ticket])
                priced[ticket] = {tuple(int(value) for value in row[keys]): (float(row["odds"]), float(row[PROBABILITY]))
                                  for _, row in table.iterrows()}
            found = priced[ticket].get(tuple(combo))
            if found is None or not found[0] > 0:
                continue
            odds, probability = found
            joiner = "→" if ticket in ORDERED_TICKETS else "-"
            rows.append({"race_id": int(rid), "rule": rule.label, "label": joiner.join(map(str, combo)), "odds": odds, "value": probability * odds})
        if not rows:
            return []
        table = TorigamiFilter().apply(pd.DataFrame(rows))
        return [{**row, "dropped": bool(dropped)} for row, dropped in zip(rows, table[DROPPED], strict=True)]
