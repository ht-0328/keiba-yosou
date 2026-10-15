"""過去の開催の出走馬を、対象のレース × 帯 で数え、予測する馬の帯に突き合わせる。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .tendency_cut import PLACE_PAYBACK, PLACE_RATE, RUNS, WIN_PAYBACK

#: 払戻は 100円あたりの円なので、回収率の分母は 100円 × 出走数。
_STAKE_YEN = 100.0
#: 突き合わせの鍵。
_RACE, _BAND = "race_id", "band"


class EditionStats:
    """1つの切り口について、対象のレースごとに「過去の開催で自分と同じ帯だった馬」の 出走数・複勝率・単勝回収率・複勝回収率 を出す。

    ``past`` は過去の開催の出走馬（``StakesTendencyRepository`` の ``is_target`` が偽の行。列は ``target_race_id``・``finish``・
    ``win_payout``・``place_payout``）。帯は ``ConditionBands`` で付けたものを、過去の側と予測する馬の側の両方に渡す。
    基準との差や縮小推定はせず、そのレースの数字そのものを返す。帯が無い馬・過去にその帯の馬がいないレースは欠損値になる。
    """

    def __init__(self, past: pd.DataFrame) -> None:
        self._race = past["target_race_id"].astype(str).to_numpy()
        self._hit = (pd.to_numeric(past["finish"], errors="coerce").astype("float64") <= 3).to_numpy(dtype="float64")
        self._win = pd.to_numeric(past["win_payout"], errors="coerce").astype("float64").fillna(0.0).to_numpy()
        self._place = pd.to_numeric(past["place_payout"], errors="coerce").astype("float64").fillna(0.0).to_numpy()

    def of(self, past_band: pd.Series, race_id: pd.Series, band: pd.Series) -> pd.DataFrame:
        """``past_band`` は過去の側の帯（``past`` と同じ並び）、``race_id``・``band`` は予測する馬の側。

        返す表の列は ``RUNS``・``PLACE_RATE``・``WIN_PAYBACK``・``PLACE_PAYBACK``、index は ``race_id`` と同じ。
        """
        counted = self._counted(past_band)
        keys = pd.DataFrame({_RACE: race_id.astype(str).to_numpy(), _BAND: band.astype("object").to_numpy()})
        merged = keys.merge(counted, on=[_RACE, _BAND], how="left")
        runs = merged["runs"].to_numpy(dtype="float64")
        missing = np.isnan(runs) | pd.isna(keys[_BAND].to_numpy())
        with np.errstate(invalid="ignore", divide="ignore"):
            table = pd.DataFrame({
                RUNS: runs,
                PLACE_RATE: merged["hits"].to_numpy(dtype="float64") / runs,
                WIN_PAYBACK: merged["win"].to_numpy(dtype="float64") / (_STAKE_YEN * runs),
                PLACE_PAYBACK: merged["place"].to_numpy(dtype="float64") / (_STAKE_YEN * runs),
            }, index=race_id.index)
        table.loc[missing, :] = np.nan
        return table

    def _counted(self, past_band: pd.Series) -> pd.DataFrame:
        """対象のレース × 帯 ごとの 出走数・3着以内の数・単勝と複勝の払戻の合計。帯の無い行は数えない。"""
        frame = pd.DataFrame({_RACE: self._race, _BAND: past_band.astype("object").to_numpy(),
                              "hits": self._hit, "win": self._win, "place": self._place})
        kept = frame[frame[_BAND].notna()]
        grouped = kept.groupby([_RACE, _BAND], sort=False).agg(runs=("hits", "size"), hits=("hits", "sum"),
                                                              win=("win", "sum"), place=("place", "sum"))
        return grouped.reset_index()
