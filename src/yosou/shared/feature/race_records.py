"""レース単位の特徴量を作る元の記録の入れ物。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .entry_records import EntryRecords


@dataclass(frozen=True)
class RaceRecords:
    """レース単位の特徴量（荒れ具合の設計書 09 の A〜E）を作る元の記録。

    - ``records``: 1頭ごとの記録。``records.entries`` は、対象のレースの出走馬の行（1行 = 1頭）。
    - ``horse_features``: ``records.entries`` の行ごとの、1頭ごとの特徴量（共通の ``FeatureBuilder`` の出力。
      index は ``records.entries`` と同じ）。レース単位のまとまりは、これを集約して作る。
    - ``race_results``: レースごとの結果（1行 = 1レース。対象のレースと、その前のレース）。荒れ具合の予想では払戻
      （過去の荒れ率の材料）、展開から着順を予想する予想では前半・後半タイムとその基準。
    """

    records: EntryRecords
    horse_features: pd.DataFrame
    race_results: pd.DataFrame

    @property
    def entries(self) -> pd.DataFrame:
        """対象のレースの出走馬の行（1行 = 1頭）。"""
        return self.records.entries

    @property
    def race_ids(self) -> pd.Index:
        """対象のレースの ID（出走の行に出てきた順）。レース単位の表の index になる。"""
        return pd.Index(self.entries["race_id"].drop_duplicates())

    @property
    def races(self) -> pd.DataFrame:
        """レースごとに1行にした出走の行（各レースの最初の馬の行。index はレースID）。レースの条件を読むのに使う。"""
        return self.entries.drop_duplicates("race_id").set_index("race_id", drop=False)
