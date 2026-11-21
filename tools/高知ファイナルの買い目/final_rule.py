"""予想の付いた1レースの表から、◎ と相手を選び、全券種の買い目を決める。"""

from __future__ import annotations

from itertools import combinations

import pandas as pd

from .final_bets import EXACTA, PLACE, QUINELLA, TRIFECTA, TRIO, WIDE, WIN_BET, FinalBets
from .final_columns import HORSE_NO, PLACE_LOW, POPULARITY_NOW, TOP3, VALUE

#: ◎ を選ぶ人気の帯（そのときの単勝人気）。1番人気は ◎ にしない。
HEAD_FROM = 2
HEAD_TO = 9
#: 相手の頭数。先頭 ``CLOSE`` 頭が ○▲（馬連・馬単・ワイドの相手、3連単の2着）、``WIDE_SET`` 頭までが △（3連単の3着・3連複の3頭目）。
CLOSE = 2
WIDE_SET = 5
#: 複勝・ワイド・3連複を買う線（◎ の 3着以内の確率 × 複勝オッズの低いほう）。
PLACE_LINE = 0.85
#: 買い目を決める最少の頭数。
MIN_HEADS = WIDE_SET + 2


class FinalRule:
    """◎ は ``HEAD_FROM``〜``HEAD_TO`` 番人気の中で割安さ（1着の確率 ÷ オッズが示す確率）がいちばん高い馬。相手は 3着以内の確率の高い順。
    単勝・馬連・馬単・3連単は毎回買う。3連単は ◎ → ○▲ → 相手5頭 と、◎ を1着・1番人気を2着か3着に置いた形（重なる組は1回だけ）。
    複勝・ワイド・3連複は、◎ の複勝の見込みが ``PLACE_LINE`` 以上のレースだけ買う。"""

    def decide(self, scored: pd.DataFrame, announced: str = "") -> FinalBets:
        if len(scored) < MIN_HEADS:
            return FinalBets.none(f"オッズと予想のそろった馬が {len(scored)} 頭（{MIN_HEADS} 頭未満）")
        favorite = int(scored.loc[scored[POPULARITY_NOW].idxmin(), HORSE_NO])
        head_row = self._head(scored)
        head = int(head_row[HORSE_NO])
        ordered = scored[scored[HORSE_NO] != head].sort_values(TOP3, ascending=False)
        partners = tuple(int(no) for no in ordered[HORSE_NO].iloc[:WIDE_SET])
        close = partners[:CLOSE]
        place_value = self._place_value(head_row)
        tickets = {WIN_BET: ((head,),), QUINELLA: tuple(self._pair(head, no) for no in close), EXACTA: tuple((head, no) for no in close),
                   TRIFECTA: self._trifectas(head, close, partners, favorite)}
        if place_value is not None and place_value >= PLACE_LINE:
            tickets[PLACE] = ((head,),)
            tickets[WIDE] = tuple(self._pair(head, no) for no in close)
            tickets[TRIO] = self._trios(head, close, partners)
        return FinalBets(head, partners, favorite, tickets, place_value, PLACE_LINE, announced)

    @staticmethod
    def _head(scored: pd.DataFrame) -> pd.Series:
        """◎ の行。帯に馬がいなければ、1番人気以外でいちばん割安な馬。"""
        band = scored[scored[POPULARITY_NOW].between(HEAD_FROM, HEAD_TO)]
        if band.empty:
            band = scored[scored[POPULARITY_NOW] != scored[POPULARITY_NOW].min()]
        return band.loc[band[VALUE].idxmax()]

    @staticmethod
    def _place_value(head_row: pd.Series) -> float | None:
        low = head_row.get(PLACE_LOW)
        return None if low is None or pd.isna(low) or low <= 0 else round(float(head_row[TOP3] * low), 4)

    @staticmethod
    def _pair(first: int, second: int) -> tuple[int, int]:
        return (first, second) if first < second else (second, first)

    @staticmethod
    def _trifectas(head: int, close: tuple[int, ...], partners: tuple[int, ...], favorite: int) -> tuple[tuple[int, int, int], ...]:
        """◎ → ○▲ → 相手 と、◎ → 1番人気 → 相手・◎ → 相手 → 1番人気。同じ組は1回だけ。"""
        combos = [(head, second, third) for second in close for third in partners if second != third]
        others = [no for no in partners if no != favorite]
        combos += [(head, favorite, no) for no in others] + [(head, no, favorite) for no in others]
        return tuple(dict.fromkeys(combos))

    @staticmethod
    def _trios(head: int, close: tuple[int, ...], partners: tuple[int, ...]) -> tuple[tuple[int, ...], ...]:
        """◎ − ○▲ − 相手（3頭の組。馬番の小さい順）。"""
        pairs = {tuple(sorted(pair)) for pair in combinations(partners, 2) if set(pair) & set(close)}
        return tuple(sorted(tuple(sorted((head, *pair))) for pair in pairs))
