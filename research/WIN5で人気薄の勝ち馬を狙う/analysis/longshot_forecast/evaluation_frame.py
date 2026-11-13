"""確かめの表の元: 人気薄（10番人気以下）の行に、オッズから見た勝率・今のモデルのそろえた確率・作り方ごとの確率を並べる。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .longshot_variant import LONGSHOT_FROM

#: 表の列の名前。
MARKET, CURRENT = "人気の順（オッズから見た勝率）", "今のモデル"


@dataclass(frozen=True)
class EvaluationFrame:
    """``current`` は今のモデルの区切りごとの予測（``PredictionFile.load`` の表のテスト期間）、``predictions`` は 作り方の名前 → その予測の表。
    返す表は1行 = 人気薄1頭で、列は race_id・race_date・year・won・popularity・``MARKET``・``CURRENT``・作り方の名前。
    今のモデルの予測と、全部の作り方の予測がそろった行だけ（同じ馬で比べるため）。"""

    def build(self, current: pd.DataFrame, predictions: dict[str, pd.DataFrame]) -> pd.DataFrame:
        share = current.assign(horse_no=current["horse_no"].astype(int))
        share[CURRENT] = share["probability"] / share.groupby("race_id")["probability"].transform("sum")
        frame = share[["race_id", "horse_no", CURRENT]]
        for index, (name, predicted) in enumerate(predictions.items()):
            frame = frame.merge(self._renamed(predicted, name, index == 0), on=["race_id", "horse_no"], how="inner")
        frame = frame.loc[frame["popularity"] >= LONGSHOT_FROM]
        return frame.assign(year=frame["race_date"].dt.year, won=frame["won"].astype(int)).reset_index(drop=True)

    @staticmethod
    def _renamed(predicted: pd.DataFrame, name: str, with_facts: bool) -> pd.DataFrame:
        columns = {"レースID": "race_id", "馬番": "horse_no", "確率": name}
        facts = {"開催日": "race_date", "人気": "popularity", "1着": "won", "オッズから見た勝率": MARKET} if with_facts else {}
        picked = predicted[[*columns, *facts]].rename(columns={**columns, **facts})
        return picked.astype({"race_id": str, "horse_no": int})
