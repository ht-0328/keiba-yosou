"""地方の裏の当たる確率: 印の全頭の表（``MarkedTable``）から1行 = 1レースの材料と答え（裏が当たったか）を作り、中央と同じモデル（``ReverseExactaModel``。
LightGBM と CatBoost の平均）を、年を入れ替えて（または前の年だけで）学び、学びに使わなかった年のレースの確率を出す。

裏は「1着が ○▲☆（☆ は複勝の期待値 1.25 以上だけ）のどれかで、◎ が2着か3着」。材料と答えは中央の研究「裏目を買うかの予想」と同じ部品（``race_rows``）で作る。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss, roc_auc_score

from 今週の予想.reverse_exacta_features import ReverseExactaFeatures
from 今週の予想.reverse_exacta_model import ReverseExactaModel

from 裏目を買うかの予想.fit import race_rows

from .mark_table_builder import FORWARD

#: 学ぶときのスレッドの数（発走前の通知と並べて動かしても通知を遅らせないように、全部は使わない）。
THREADS = 6
#: 確率の列。
REVERSE_PROBABILITY = "reverse_probability"


@dataclass(frozen=True)
class ReverseProbabilities:
    """``of(marked, protocol)`` は ``race_id``（整数）・``year``・``y``（裏が当たったか）・``REVERSE_PROBABILITY`` の表。
    ``quality(table)`` は年ごとの当たり具合（ログ損失・AUC・予想の平均・実際の割合）。"""

    def of(self, marked: pd.DataFrame, protocol: str) -> pd.DataFrame:
        rows = race_rows(marked)
        rows["year"] = pd.to_datetime(rows["day"]).dt.year
        rows["race_id"] = rows["race_id"].astype("int64")
        features = ReverseExactaFeatures().frame(rows["features"].tolist())
        years = sorted(rows["year"].unique())
        parts = []
        for year in years:
            learn = (rows["year"] < year) if protocol == FORWARD else (rows["year"] != year)
            if not learn.any():
                continue
            model = ReverseExactaModel.fit(features[learn.to_numpy()], rows.loc[learn, "y"], THREADS)
            check = (rows["year"] == year).to_numpy()
            parts.append(rows.loc[check, ["race_id", "year", "y"]].assign(**{REVERSE_PROBABILITY: model.predict(features[check])}))
            print(f"{year}年: 裏の確率を出しました（{check.sum():,} レース）", flush=True)
        return pd.concat(parts, ignore_index=True)

    @staticmethod
    def quality(table: pd.DataFrame) -> list[dict]:
        records = []
        for year, part in table.groupby("year"):
            probability = np.clip(part[REVERSE_PROBABILITY].to_numpy(), 1e-4, 1 - 1e-4)
            records.append({"年": f"{year}年", "レース": len(part), "裏が当たった割合": f"{part['y'].mean():.1%}", "予想の平均": f"{probability.mean():.3f}",
                            "ログ損失": f"{log_loss(part['y'], probability):.4f}", "AUC": f"{roc_auc_score(part['y'], probability):.3f}"})
        return records
