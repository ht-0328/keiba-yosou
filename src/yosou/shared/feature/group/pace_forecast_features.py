"""P. 展開の予想の結果（20個）。"""

from __future__ import annotations

import pandas as pd

from ..entry_records import EntryRecords
from ..pace_forecast import PaceForecastTableBuilder


class PaceForecastFeatures:
    """P. 展開の予想の結果（名前は ``PACE_FORECAST_NAMES``）。``FeatureGroup`` を守る。

    予想「展開から着順を予想」の前半・後半の展開の予想（先頭の確率・先団・中団・後方の確率・ハイとスローの確率・前半と後半の
    タイムの基準との差・4コーナーの位置・上がりの速さ）と、そのレース内の順位・偏差。元の予測は ``records.pace_forecasts``
    （1行 = 1頭。呼ぶ側が、学習データにはそのレースより前だけで学習した展開のモデルの予測を、予測では保存した展開のモデルの
    予測を入れる）。読んでいなければ（空の表）全部欠損値。作り方は ``feature/pace_forecast/`` の部品。
    """

    def build(self, records: EntryRecords) -> pd.DataFrame:
        entries = records.entries
        return PaceForecastTableBuilder().build(entries["race_id"], entries["horse_id"], records.pace_forecasts)
