"""◎ の選び方の候補（結果を見る前に決めた一覧）。全頭の行から、レースごとに ◎ を1頭選び、◎ の1着の確率と単勝の期待値を返す。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from 今週の予想.filter_columns import MEMBERS, member_column
from 今週の予想.forecast_columns import MARK, MARKET_WIN, WIN_PROBABILITY, WIN_VALUE
from 今週の予想.mark_rule import OUT_MARK, TOP_MARK

#: ◎ の行に残す列（期待度の研究の ◎ の行と同じ形）。
KEEP: tuple[str, ...] = ("race_id", "race_date", "year", WIN_PROBABILITY, WIN_VALUE, "win_odds", "popularity", "finish", "win_payout", "place_payout")
#: 今の本番の単勝オッズの上限。
CURRENT_CAP = 30.0


@dataclass(frozen=True)
class TopRule:
    """``key`` は短い名前、``label`` は人が読む決め方、``pick`` は全頭の行（危険な人気馬を除いたもの）から ◎ の行を返す。"""

    key: str
    label: str
    pick: Callable[[pd.DataFrame], pd.DataFrame]

    def tops(self, rows: pd.DataFrame) -> pd.DataFrame:
        """全頭の行（``BacktestMarker.mark`` の戻り値に ``year`` を足したもの）から、レースごとの ◎ の行。危険な人気馬（消）は ◎ にしない。"""
        candidates = rows[rows[MARK] != OUT_MARK]
        return self.pick(candidates)[list(KEEP)].reset_index(drop=True)


def _best(rows: pd.DataFrame, value: pd.Series) -> pd.DataFrame:
    """レースごとに ``value`` が最大の行（値が無い行は選ばない）。"""
    ranked = rows.assign(_value=value).dropna(subset=["_value"])
    return ranked.loc[ranked.groupby("race_id")["_value"].idxmax()]


def _capped(cap: float | None) -> Callable[[pd.DataFrame], pd.DataFrame]:
    def pick(rows: pd.DataFrame) -> pd.DataFrame:
        within = rows if cap is None else rows[rows["win_odds"].astype(float) <= cap]
        return _best(within, within[WIN_VALUE].astype(float))

    return pick


def _shrunk(alpha: float) -> Callable[[pd.DataFrame], pd.DataFrame]:
    """1着の確率をオッズの見立てに ``alpha`` だけ寄せ、寄せた確率と期待値で選ぶ（返す ◎ の確率と期待値も寄せたもの）。"""

    def pick(rows: pd.DataFrame) -> pd.DataFrame:
        within = rows[rows["win_odds"].astype(float) <= CURRENT_CAP].copy()
        probability = (1 - alpha) * within[WIN_PROBABILITY].astype(float) + alpha * within[MARKET_WIN].astype(float)
        within[WIN_PROBABILITY] = probability
        within[WIN_VALUE] = probability * within["win_odds"].astype(float)
        return _best(within, within[WIN_VALUE])

    return pick


def _agreement(rows: pd.DataFrame) -> pd.DataFrame:
    """単勝 30倍以下で、2つのモデルのどちらの確率でも期待値 1 以上の馬がいれば、その中で期待値が1位の馬。いなければ今の決め方。"""
    within = rows[rows["win_odds"].astype(float) <= CURRENT_CAP]
    columns = [member_column(WIN_VALUE, member) for member in MEMBERS if member_column(WIN_VALUE, member) in within.columns]
    agree = np.logical_and.reduce([within[column].astype(float) >= 1.0 for column in columns]) if columns else np.zeros(len(within), bool)
    boosted = within[WIN_VALUE].astype(float) + np.where(agree, 100.0, 0.0)   # 一致した馬を先に選ぶ
    return _best(within, boosted)


def _current(rows: pd.DataFrame) -> pd.DataFrame:
    return rows[rows[MARK] == TOP_MARK]


RULES: tuple[TopRule, ...] = (
    TopRule("今", "今の決め方（単勝 30倍以下で期待値1位）", _current),
    TopRule("上限10", "単勝 10倍以下で期待値1位", _capped(10.0)),
    TopRule("上限20", "単勝 20倍以下で期待値1位", _capped(20.0)),
    TopRule("上限50", "単勝 50倍以下で期待値1位", _capped(50.0)),
    TopRule("上限なし", "全頭で期待値1位", _capped(None)),
    TopRule("寄せ0.25", "確率をオッズの見立てに 25% 寄せて期待値1位（30倍以下）", _shrunk(0.25)),
    TopRule("寄せ0.5", "確率をオッズの見立てに 50% 寄せて期待値1位（30倍以下）", _shrunk(0.5)),
    TopRule("寄せ0.75", "確率をオッズの見立てに 75% 寄せて期待値1位（30倍以下）", _shrunk(0.75)),
    TopRule("2モデル一致", "2つのモデルとも期待値 1 以上の馬を優先して期待値1位（30倍以下）", _agreement),
)
