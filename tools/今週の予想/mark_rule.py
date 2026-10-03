"""1レースの全頭に印（◎○▲△☆注消）を付ける。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 今週の予想.forecast_columns import (
    AXIS,
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
    WIN_PROBABILITY,
    WIN_VALUE,
)

#: ◎ のあとに、3着以内の確率の順で付ける印（○・▲と、△は3頭。利用者の指示「白三角は3点で」）。
TOP_MARK = "◎"
RANK_MARKS: tuple[str, ...] = ("○", "▲", "△", "△", "△")
VALUE_MARK = "☆"
NOTE_MARK = "注"
#: 印の付かなかった馬（買わない馬）と、危険な人気馬の印。利用者の決定。
OUT_MARK = "消"
#: 印の並び（画面の凡例と、並べ替えに使う）。
MARK_ORDER: tuple[str, ...] = (TOP_MARK, "○", "▲", "△", VALUE_MARK, NOTE_MARK, OUT_MARK)
#: ☆ を付ける複勝の期待値の下限（設計書「買うレースと買い目を決める」07 の 2。研究「回収率100超」で決めた買う線）。
VALUE_LINE = 1.25
#: ◎ の候補にする単勝オッズの上限（利用者の決定。設計書 07 の 5）。これより高い大穴は、単勝の期待値が1位でも ◎ にしない
#: （期待値の高い大穴は当たりが少なく成績が運で振れるうえ、3着以内の確率が最下位の馬が ◎ になることがあった）。
TOP_ODDS_LIMIT = 30.0
#: 人気馬の範囲を広げる頭数（13頭以下は1〜3番人気、14頭以上は1〜5番人気。設計書 07 の 3）。
WIDE_FIELD = 14
_FAVORITES_SMALL = 3
_FAVORITES_WIDE = 5
#: 表に無ければ欠損値で足す列。
_OPTIONAL_COLUMNS: tuple[str, ...] = (
    WIN_ODDS, MARKET_TOP3, PLACE_VALUE, WIN_PROBABILITY, WIN_VALUE, OUT_PROBABILITY, MARKET_OUT, DANGER_SCORE, DANGER_LINE,
)


class MarkRule:
    """1レースの全頭に印を付ける（設計書「買うレースと買い目を決める」07 の 5。印の無い馬は利用者の決定で「消」）。

    - 消（危険な人気馬）: 人気馬の予想で「危険」と判定された馬（07 の 3。前日・当日だけ。今は1番人気だけ。``DangerFinder``）。
      先に消にして、ほかの印の候補から外す。
    - ◎: 消を除いた単勝 ``TOP_ODDS_LIMIT``（30倍）以下の馬の中で、単勝の期待値（1着になる確率 × 単勝オッズ）がいちばん高い馬。
      全レースに1頭付ける。30倍以下の馬がいないか、オッズの無い木曜は、1着になる確率が1位の馬。1着の予想が無ければ（前の版のモデル）、
      3着以内の確率が1位の馬。
    - ○▲△: 消と ◎ を除いて、3着以内の確率の 1〜5位（○・▲と、△の3頭）。
    - ☆: 穴馬（人気馬の範囲より下の人気）のうち、印の付いていない馬で、複勝の期待値がいちばん高い馬。
      期待値が ``VALUE_LINE``（1.25）以上のときだけ。オッズの無い時点（木曜）は、期待値が無いので付かない。
    - 注: 印の付いていない馬のうち、上げ下げ（logit(予想) − logit(市場の見立て)）がいちばん大きい馬。上げ下げが正（市場より来ると見る）のときだけ。
      オッズの無い時点（木曜）は、市場の見立てが無いので付かない。
    - 消: ほかの全部の馬（買わない馬）。
    - 軸（列 ``axis``。印ではない）: ◎○▲ のうち3着以内の確率がいちばん高い馬。◎ と同じ馬のことも ○ のこともある（軸と ◎ が同じでも、
      軸を別の馬に替えない）。3連複・3連単の「軸馬」のパターンで軸にする（設計書 08 の 2）。
    レースの期待度（◎ の単勝の期待値の3段階）は、この表の ◎ の単勝の期待値から ``ExpectationLevel`` が決める。
    """

    def assign(self, race: pd.DataFrame) -> pd.DataFrame:
        """``race`` は1レースの表（列 ``horse_no``・``probability``。前日・当日は ``win_odds``・``market_top3``・``place_value`` と、
        1着の予想の ``win_probability``・``win_value``、人気馬には危険の判定の列 ``is_danger`` など）。

        戻り値は ``race`` に列 ``rank``・``popularity``・``updown``・``mark``・``mark_reason``・``axis`` を足し、3着以内の確率の高い順
        （同じなら馬番の小さい順）に並べた表。``rank`` は全頭の中での順位。
        """
        table = race.copy()
        for column in _OPTIONAL_COLUMNS:
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
        self._mark_top_and_ranks(table, any_danger=len(dangers) > 0)
        self._mark_axis(table)
        self._mark_value(table)
        self._mark_note(table)
        for row in table.index[(table[MARK] == OUT_MARK) & ~table[IS_DANGER]]:
            table.loc[row, MARK_REASON] = self._out_reason(table.loc[row], any_danger=len(dangers) > 0)
        return table

    def _mark_top_and_ranks(self, table: pd.DataFrame, *, any_danger: bool) -> None:
        """危険な人気馬を除いて ◎ を決め、残りに3着以内の確率の順で ○▲△。"""
        candidates = list(table.index[~table[IS_DANGER]])
        if not candidates:
            return
        top = self._top_pick(table, candidates)
        rest = [row for row in candidates if row != top]
        excluded = "◎と危険な人気馬" if any_danger else "◎"
        for order, (row, mark) in enumerate(zip(rest, RANK_MARKS, strict=False), start=1):
            table.loc[row, MARK] = mark
            table.loc[row, MARK_REASON] = (f"{excluded}を除いて、3着以内に入る確率が{order}位"
                                           f"（全頭ではレース内{table.loc[row, RANK]:.0f}位）")

    def _mark_axis(self, table: pd.DataFrame) -> None:
        """◎○▲ のうち3着以内の確率がいちばん高い馬を軸にする（表は確率の高い順なので、最初の1頭）。"""
        table[AXIS] = False
        rows = table.index[table[MARK].isin((TOP_MARK, *RANK_MARKS[:2]))]
        if len(rows):
            table.loc[rows[0], AXIS] = True

    def _top_pick(self, table: pd.DataFrame, candidates: list[int]) -> int:
        """◎ の行。単勝 30倍以下の馬の単勝の期待値 → 1着になる確率 → 3着以内の確率 の順に、使える値で決める（同じ値なら3着以内の確率の高いほう）。"""
        priced = table.loc[candidates]
        values = priced[WIN_VALUE][priced[WIN_ODDS] <= TOP_ODDS_LIMIT].dropna()
        if not values.empty:
            row = values.idxmax()
            table.loc[row, MARK] = TOP_MARK
            table.loc[row, MARK_REASON] = (f"単勝 {TOP_ODDS_LIMIT:.0f}倍以下の馬の中で単勝の期待値がレース内1位（1着になる確率 "
                                           f"{table.loc[row, WIN_PROBABILITY]:.1%} × 単勝 {table.loc[row, WIN_ODDS]:.1f}倍 = {values[row]:.2f}）")
            return row
        wins = table.loc[candidates, WIN_PROBABILITY].dropna()
        if not wins.empty:
            row = wins.idxmax()
            table.loc[row, MARK] = TOP_MARK
            why = (f"単勝 {TOP_ODDS_LIMIT:.0f}倍以下の馬がいないので、期待値では選ばない" if table.loc[candidates, WIN_ODDS].notna().any()
                   else "オッズが無いので単勝の期待値は出せない")
            table.loc[row, MARK_REASON] = f"1着になる確率がレース内1位（{wins[row]:.1%}。{why}）"
            return row
        row = candidates[0]
        table.loc[row, MARK] = TOP_MARK
        table.loc[row, MARK_REASON] = f"3着以内に入る確率がレース内{table.loc[row, RANK]:.0f}位（1着の予想が無いので、3着以内の確率で選んだ）"
        return row

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
        within = f"◎と危険な人気馬を除いて{len(RANK_MARKS)}位まで" if any_danger else f"◎を除いて{len(RANK_MARKS)}位まで"
        reason = f"3着以内に入る確率がレース内{row[RANK]:.0f}位で、○〜△（{within}）に入らない"
        if pd.notna(row[WIN_VALUE]) and pd.notna(row[WIN_ODDS]) and row[WIN_ODDS] > TOP_ODDS_LIMIT:
            reason += f"。単勝 {row[WIN_ODDS]:.1f}倍は◎の候補の上限（{TOP_ODDS_LIMIT:.0f}倍）を超える"
        elif pd.notna(row[WIN_VALUE]):
            reason += f"。単勝の期待値 {row[WIN_VALUE]:.2f} も◎ではない"
        if pd.notna(row[PLACE_VALUE]):
            reason += f"。複勝の期待値 {row[PLACE_VALUE]:.2f} も☆の条件に当たらない"
        return reason


def _favorite_count(field_size: int) -> int:
    """人気馬とみなす人気の範囲（何番人気まで）。"""
    return _FAVORITES_WIDE if field_size >= WIDE_FIELD else _FAVORITES_SMALL


def _logit(values: pd.Series) -> pd.Series:
    clipped = values.astype(float).clip(1e-6, 1 - 1e-6)
    return np.log(clipped / (1 - clipped))
