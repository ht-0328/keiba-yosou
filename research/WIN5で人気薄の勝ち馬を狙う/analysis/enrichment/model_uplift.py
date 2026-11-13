"""今のモデルの1着の確率と、オッズから見た勝率との比（上乗せ）・レースの中での順位の列を足す。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ModelUplift:
    """出走の表（``market`` の列が要る）に ``model``（そろえた1着の確率）・``model_rank``（レースの中での順位）・
    ``uplift``（model ÷ market）を足す。``predictions`` は1行 = 1頭で列 race_id・horse_no・model。
    同じ馬が複数の元にあれば、先に並べた元を使う。予測の無いレースは欠損値。"""

    predictions: tuple[pd.DataFrame, ...]

    def add(self, runners: pd.DataFrame) -> pd.DataFrame:
        merged = pd.concat(self.predictions, ignore_index=True).drop_duplicates(["race_id", "horse_no"], keep="first")
        frame = runners.merge(merged, on=["race_id", "horse_no"], how="left")
        frame["model_rank"] = frame.groupby("race_id")["model"].rank(ascending=False, method="min")
        frame["uplift"] = frame["model"] / frame["market"]
        return frame
