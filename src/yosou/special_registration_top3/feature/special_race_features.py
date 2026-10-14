"""Y. 特別競走の印（1個）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import EntryRecords

from .feature_catalog import SPECIAL_RACE


class SpecialRaceFeatures:
    """Y. 特別競走の印。出走の行の競走名（``race_name``）が空でなければ 1、空（平場）なら 0。``FeatureGroup`` を守る。

    学習データを平場も含む全レースで作るので、行が特別競走（登録のあるレース）か平場かをモデルに教える（設計書 09 の Y）。
    登録馬の行では、特別登録の競走名本題から必ず 1 になる。
    """

    def build(self, records: EntryRecords) -> pd.DataFrame:
        entries = records.entries
        names = entries["race_name"].fillna("").astype(str).str.strip()
        return pd.DataFrame({SPECIAL_RACE: (names != "").astype(float)}, index=entries.index)
