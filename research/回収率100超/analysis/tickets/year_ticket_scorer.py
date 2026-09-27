"""1つの券種の1年ぶんの全部の買い目に、確率・期待値・払戻を付ける。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .combo_probability import ComboProbability
from .odds_band_calibrator import OddsBandCalibrator
from .race_win_table import RaceWinTable
from .ticket_kind import TicketKind

#: 残す買い目の期待値の下限。検証で動かす線（1.0〜1.5）の、いちばん低い値。
KEEP_FROM = 1.0


@dataclass(frozen=True)
class YearScore:
    """1年ぶんの結果。

    - ``candidates``: 期待値が ``KEEP_FROM`` 以上の買い目（rid・flat・odds・price・probability・ev・payout）。
    - ``all_rows``: 全部の買い目（rid・flat・odds・price・probability・ev・payout）。印の買い目を引くのと、
      荒れそうかを計算するのに使う。``keep_all`` が偽なら空（3連単は1年で数百万行あり、使わないため）。
    - ``raw``: 確率を直す前の値（odds・raw_probability・hit）。次の年の較正に足す。
    """

    candidates: pd.DataFrame
    all_rows: pd.DataFrame
    raw: pd.DataFrame


class YearTicketScorer:
    """買い目ごとに、確率（較正のあと）・期待値・払戻を付ける。

    手順:
    1. レースごとに、勝率から全部の買い目の確率の表を作り、オッズの行に当てる（``ComboProbability``）。
    2. 払戻の表と突き合わせ、当たった買い目に払戻を付ける（当たらなければ 0）。
    3. 前の年までの実績で、オッズの帯ごとに確率を直す（``OddsBandCalibrator``）。
    4. 期待値 = 直した確率 × 受け取る額の見込み。ワイドは最低オッズ × 帯ごとの倍率、ほかはオッズそのもの。
    """

    def __init__(self, kind: TicketKind, probability: ComboProbability, wins: RaceWinTable) -> None:
        self._kind = kind
        self._probability = probability
        self._wins = wins

    def score(self, odds: pd.DataFrame, payouts: pd.DataFrame, calibrator: OddsBandCalibrator,
              price: pd.Series, keep_all: bool = True) -> YearScore:
        """``price`` は受け取る額の見込み（``odds`` と同じ行の並び）。"""
        horses = [f"h{index + 1}" for index in range(self._kind.horses)]
        rows = odds.assign(flat=self._kind.flat_index(odds[horses].to_numpy()), price=price.to_numpy())
        rows = rows.sort_values("rid", kind="stable").reset_index(drop=True)
        rows["raw_probability"] = self._raw_probability(rows)
        rows = rows[rows["raw_probability"].notna()].reset_index(drop=True)
        rows = rows.merge(self._payout_by_flat(payouts, horses), on=["rid", "flat"], how="left")
        rows["payout"] = rows["payout"].fillna(0.0)
        rows["probability"] = rows["raw_probability"] * calibrator.factors(rows["odds"].to_numpy())
        rows["ev"] = rows["probability"] * rows["price"]
        kept = ["rid", "flat", "odds", "price", "probability", "ev", "payout"]
        raw = pd.DataFrame({"odds": rows["odds"], "raw_probability": rows["raw_probability"],
                            "hit": (rows["payout"] > 0).astype(float)})
        all_rows = rows[kept] if keep_all else rows.loc[[], kept]
        return YearScore(rows.loc[rows["ev"] >= KEEP_FROM, kept].reset_index(drop=True), all_rows, raw)

    def _raw_probability(self, rows: pd.DataFrame) -> np.ndarray:
        """レースごとに確率の表を作り、各行の買い目の確率を引く。予測の無いレースは NaN。"""
        rid = rows["rid"].to_numpy()
        flat = rows["flat"].to_numpy()
        starts = np.flatnonzero(np.r_[True, rid[1:] != rid[:-1]])
        ends = np.r_[starts[1:], len(rid)]
        result = np.full(len(rid), np.nan)
        for begin, end in zip(starts, ends, strict=True):
            result[begin:end] = self._race_probability(int(rid[begin]), flat[begin:end])
        return result

    def _race_probability(self, rid: int, flat: np.ndarray) -> np.ndarray:
        wins = self._wins.get(rid)
        if wins is None:
            return np.full(len(flat), np.nan)
        return self._probability.table(self._kind, wins)[flat]

    def _payout_by_flat(self, payouts: pd.DataFrame, horses: list[str]) -> pd.DataFrame:
        """払戻の表を、rid・flat・payout の形にする。同じ買い目が2行あれば大きい方。"""
        table = payouts.assign(flat=self._kind.flat_index(payouts[horses].to_numpy()))
        return table.groupby(["rid", "flat"], as_index=False)["payout"].max()
