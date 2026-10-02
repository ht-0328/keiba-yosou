"""1レースの全頭に印（◎○▲△☆注消）を付ける。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 今週の予想.forecast_columns import (
    DANGER_LINE,
    DANGER_SCORE,
    HORSE_NO,
    IS_DANGER,
    MARK,
    MARK_REASON,
    MARKET_OUT,
    MARKET_TOP3,
    OUT_PROBABILITY,
    PLACE_VALUE,
    POPULARITY,
    PROBABILITY,
    RANK,
    UPDOWN,
    WIN_ODDS,
)

#: 3着以内の確率の順位で付ける印（1位から順）。△は 4〜6位の3頭（利用者の指示「白三角は3点で」）。
RANK_MARKS: tuple[str, ...] = ("◎", "○", "▲", "△", "△", "△")
VALUE_MARK = "☆"
NOTE_MARK = "注"
#: 印の付かなかった馬（買わない馬）と、危険な人気馬の印。利用者の決定（2026-10-03）。
OUT_MARK = "消"
#: 印の並び（画面の凡例と、並べ替えに使う）。
MARK_ORDER: tuple[str, ...] = ("◎", "○", "▲", "△", VALUE_MARK, NOTE_MARK, OUT_MARK)
#: ☆ を付ける複勝の期待値の下限（設計書「買うレースと買い目を決める」07 の 2。研究「回収率100超」で決めた買う線）。
VALUE_LINE = 1.25
#: 人気馬の範囲を広げる頭数（13頭以下は1〜3番人気、14頭以上は1〜5番人気。設計書 07 の 3）。
WIDE_FIELD = 14
_FAVORITES_SMALL = 3
_FAVORITES_WIDE = 5


class MarkRule:
    """1レースの全頭に印を付ける（設計書「買うレースと買い目を決める」07 の 5。印の無い馬は利用者の決定で「消」）。

    - 消（危険な人気馬）: 人気馬の予想で「危険」と判定された馬（07 の 3。前日・当日だけ。今は1番人気だけ。``DangerFinder``）。
      先に消にして、ほかの印の候補から外す。
    - ◎○▲: 消を除いて、3着以内の確率の 1〜3位。△: 同じく 4〜6位の3頭。
    - ☆: 穴馬（人気馬の範囲より下の人気）のうち、印の付いていない馬で、複勝の期待値がいちばん高い馬。
      期待値が ``VALUE_LINE``（1.25）以上のときだけ。オッズの無い時点（木曜）は、期待値が無いので付かない。
    - 注: 印の付いていない馬のうち、上げ下げ（logit(予想) − logit(市場の見立て)）がいちばん大きい馬。上げ下げが正（市場より来ると見る）のときだけ。
      オッズの無い時点（木曜）は、市場の見立てが無いので付かない。
    - 消: ほかの全部の馬（買わない馬）。
    """

    def assign(self, race: pd.DataFrame) -> pd.DataFrame:
        """``race`` は1レースの表（列 ``horse_no``・``probability``。前日・当日は ``win_odds``・``market_top3``・``place_value`` と、
        人気馬には危険の判定の列 ``is_danger`` など）。

        戻り値は ``race`` に列 ``rank``・``popularity``・``updown``・``mark``・``mark_reason`` を足し、3着以内の確率の高い順
        （同じなら馬番の小さい順）に並べた表。``rank`` は全頭の中での順位。
        """
        table = race.copy()
        for column in (WIN_ODDS, MARKET_TOP3, PLACE_VALUE, OUT_PROBABILITY, MARKET_OUT, DANGER_SCORE, DANGER_LINE):
            if column not in table.columns:
                table[column] = np.nan
        table[IS_DANGER] = table[IS_DANGER].fillna(False).astype(bool) if IS_DANGER in table.columns else False
        table = table.sort_values([PROBABILITY, HORSE_NO], ascending=[False, True], na_position="last").reset_index(drop=True)
        table[RANK] = np.arange(1, len(table) + 1)
        table[POPULARITY] = table[WIN_ODDS].rank(method="min")
        table[UPDOWN] = _logit(table[PROBABILITY]) - _logit(table[MARKET_TOP3])
        table[MARK] = OUT_MARK
        table[MARK_REASON] = ""
        dangers = table.index[table[IS_DANGER]]
        for row in dangers:
            table.loc[row, MARK_REASON] = self._danger_reason(table.loc[row])
        self._mark_ranks(table, any_danger=len(dangers) > 0)
        self._mark_value(table)
        self._mark_note(table)
        for row in table.index[(table[MARK] == OUT_MARK) & ~table[IS_DANGER]]:
            table.loc[row, MARK_REASON] = self._out_reason(table.loc[row], any_danger=len(dangers) > 0)
        return table

    def _mark_ranks(self, table: pd.DataFrame, *, any_danger: bool) -> None:
        """危険な人気馬を除いた3着以内の確率の順に ◎○▲△。"""
        candidates = table.index[~table[IS_DANGER]]
        for order, (row, mark) in enumerate(zip(candidates, RANK_MARKS, strict=False), start=1):
            table.loc[row, MARK] = mark
            if any_danger and order != table.loc[row, RANK]:
                table.loc[row, MARK_REASON] = (f"危険な人気馬を除いて、3着以内に入る確率が{order}位"
                                               f"（全頭ではレース内{table.loc[row, RANK]:.0f}位）")
            else:
                table.loc[row, MARK_REASON] = f"3着以内に入る確率がレース内{order}位"

    def _mark_value(self, table: pd.DataFrame) -> None:
        """穴馬で、複勝の期待値がいちばん高い馬に ☆（線以上のときだけ）。"""
        favorites = _favorite_count(len(table))
        free = (table[MARK] == OUT_MARK) & ~table[IS_DANGER] & (table[POPULARITY] > favorites)
        candidates = table[free][PLACE_VALUE].dropna()
        if candidates.empty or candidates.max() < VALUE_LINE:
            return
        row = candidates.idxmax()
        table.loc[row, MARK] = VALUE_MARK
        table.loc[row, MARK_REASON] = (f"穴馬（{table.loc[row, POPULARITY]:.0f}番人気）の中で複勝の期待値がいちばん高く、"
                                       f"{table.loc[row, PLACE_VALUE]:.2f} が線の {VALUE_LINE:.2f} 以上")

    def _mark_note(self, table: pd.DataFrame) -> None:
        """印の無い馬のうち、市場の見立てより来ると見る度合いがいちばん大きい馬に 注（正のときだけ）。"""
        candidates = table[(table[MARK] == OUT_MARK) & ~table[IS_DANGER]][UPDOWN].dropna()
        if candidates.empty or candidates.max() <= 0:
            return
        row = candidates.idxmax()
        table.loc[row, MARK] = NOTE_MARK
        table.loc[row, MARK_REASON] = (f"印の無い馬の中で、市場の見立て（{table.loc[row, MARKET_TOP3]:.1%}）より来ると見る度合いが"
                                       f"いちばん大きい（予想 {table.loc[row, PROBABILITY]:.1%}）")

    def _danger_reason(self, row: pd.Series) -> str:
        """危険な人気馬として消にした理由。"""
        return (f"危険な人気馬（{row[POPULARITY]:.0f}番人気）。人気馬の予想で4着以下になる確率が {row[OUT_PROBABILITY]:.1%} と、"
                f"市場の見立て {row[MARKET_OUT]:.1%} より {row[DANGER_SCORE] * 100:.1f}ポイント高く、"
                f"人気帯の線（{row[DANGER_LINE] * 100:.1f}ポイント）以上")

    def _out_reason(self, row: pd.Series, *, any_danger: bool) -> str:
        """印が付かず消になった理由。"""
        within = f"危険な人気馬を除いて{len(RANK_MARKS)}位まで" if any_danger else f"{len(RANK_MARKS)}位まで"
        reason = f"3着以内に入る確率がレース内{row[RANK]:.0f}位で、◎〜△（{within}）に入らない"
        if pd.notna(row[PLACE_VALUE]):
            reason += f"。複勝の期待値 {row[PLACE_VALUE]:.2f} も☆の条件に当たらない"
        return reason


def _favorite_count(field_size: int) -> int:
    """人気馬とみなす人気の範囲（何番人気まで）。"""
    return _FAVORITES_WIDE if field_size >= WIDE_FIELD else _FAVORITES_SMALL


def _logit(values: pd.Series) -> pd.Series:
    clipped = values.astype(float).clip(1e-6, 1 - 1e-6)
    return np.log(clipped / (1 - clipped))
