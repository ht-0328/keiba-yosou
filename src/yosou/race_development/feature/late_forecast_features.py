"""T. 後半の予想の結果（7個）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import RACE_ID

from .group_forecast import CLOSING_PREDICTION, CORNER4_PREDICTION, SECOND_HALF_QUANTILES, GroupForecast


class LateForecastFeatures:
    """T. 後半の予想（④⑤⑥）の結果から、着順の予想の特徴量を作る（設計書 09 の T）。

    「位置と上がりの予測の和」は、4コーナーで前にいて、速く上がれそうな馬ほど小さい、ゴールでの位置の大まかな目安。
    渡す予測は、そのサンプルを学習に使っていない後半のモデルの予測である（設計書 11 の決まり 11）。
    """

    def horse(self, ids: pd.DataFrame, late: GroupForecast) -> pd.DataFrame:
        """1頭ごとの 7個。``ids`` は学習データ（予測用データ）の ID 列。index は ``ids`` と同じ。"""
        horses, races = late.horse_rows(ids), late.race_rows(ids)
        race = ids[RACE_ID]
        position, closing = horses[CORNER4_PREDICTION], horses[CLOSING_PREDICTION]
        combined = position + closing
        return pd.DataFrame({
            "4コーナーの位置の予測": position,
            "上がりの速さの予測": closing,
            "4コーナーの位置の予測のレース内順位": position.groupby(race).rank(method="min"),
            "上がりの速さの予測のレース内順位": closing.groupby(race).rank(method="min"),
            "位置と上がりの予測の和": combined,
            "位置と上がりの予測の和のレース内順位": combined.groupby(race).rank(method="min"),
            "後半タイムの基準との差の予測": races[SECOND_HALF_QUANTILES[1]],
        }, index=ids.index)
