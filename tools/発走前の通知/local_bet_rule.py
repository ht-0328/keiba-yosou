"""地方の1レースで実際に買う買い目: 推奨買目（道具「地方の推奨買目」。単勝・複勝・枠連・ワイド・馬単・3連単）に、
全頭の予想の ◎ の単勝（期待値 1.00 以上）と複勝（期待値 1.25 以上）を足す。"""

from __future__ import annotations

import pandas as pd

from 今週の予想.forecast_columns import HORSE_NO, MARK, PLACE_VALUE, PROBABILITY, WIN_ODDS, WIN_PROBABILITY, WIN_VALUE
from 今週の予想.mark_rule import TOP_MARK
from 今週の予想.ticket_rules import PLACE_VALUE_LINE

from 地方の推奨買目.recommendation import Recommendation
from 地方の推奨買目.recommendation_set import RecommendationSet

#: 単勝を買う ◎ の単勝の期待値の線（全頭の予想の買い方。当日の時点だけ）。
WIN_VALUE_LINE = 1.00


class LocalBetRule:
    """当日の時点だけ買う。前日の時点（馬体重が届く前。オッズだけ）は買わない。
    同じ券種・同じ組は1度だけ数える。推奨買目の理由（11頭未満 など）は、点があっても添える。"""

    def pick(self, table: pd.DataFrame, race_day: bool, recommended: RecommendationSet) -> RecommendationSet:
        if not race_day:
            return RecommendationSet((), "馬体重が届く前の前日の時点では買わない")
        own, reasons = self._own(table)
        merged = recommended.merged(own)
        if merged.none:
            return RecommendationSet((), "。".join(reason for reason in (recommended.reason, *reasons) if reason))
        return merged

    def _own(self, table: pd.DataFrame) -> tuple[list[Recommendation], list[str]]:
        """全頭の予想の ◎ の単勝と、複勝の期待値が線以上の馬の複勝。買わない理由も返す。"""
        rows: list[Recommendation] = []
        reasons: list[str] = []
        top = table[table[MARK] == TOP_MARK]
        if top.empty:
            reasons.append("◎ が無い")
        elif top.iloc[0][WIN_VALUE] < WIN_VALUE_LINE:
            reasons.append(f"◎ の単勝の期待値 {top.iloc[0][WIN_VALUE]:.2f} は {WIN_VALUE_LINE:.2f} 未満")
        else:
            rows.append(self._win(top.iloc[0]))
        places = table[table[PLACE_VALUE] >= PLACE_VALUE_LINE]
        rows += [self._place(row) for _, row in places.iterrows()]
        if places.empty:
            reasons.append(f"複勝の期待値 {PLACE_VALUE_LINE:.2f} 以上の馬はいない")
        return rows, reasons

    @staticmethod
    def _win(row: pd.Series) -> Recommendation:
        return Recommendation("単勝", (int(row[HORSE_NO]),), float(row[WIN_ODDS]), float(row[WIN_PROBABILITY]), float(row[WIN_VALUE]))

    @staticmethod
    def _place(row: pd.Series) -> Recommendation:
        """複勝のオッズは predict に無いので、期待値 ÷ 3着以内の確率（見込みの倍率）にする。"""
        probability = float(row[PROBABILITY])
        value = float(row[PLACE_VALUE])
        return Recommendation("複勝", (int(row[HORSE_NO]),), value / probability if probability > 0 else 0.0, probability, value)
