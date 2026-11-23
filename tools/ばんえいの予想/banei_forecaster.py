"""ばんえいの1レースの予想: 出馬表と過去走から、各馬の勝つ確率・世間の見立て・印と、3連単の買い目を出す。"""

from __future__ import annotations

from typing import Any

import duckdb

from ばんえいの予想.banei_feature_builder import BaneiFeatureBuilder
from ばんえいの予想.banei_model import BaneiModel
from ばんえいの予想.banei_runs_repository import BaneiRunsRepository
from ばんえいの予想.trifecta_picker import TrifectaPicker

import pandas as pd

#: 勝つ確率の高い順に付ける印（残りは無印）。
MARKS = ("◎", "○", "▲", "△", "△")


class BaneiForecaster:
    def __init__(self, model: BaneiModel, *, builder: BaneiFeatureBuilder | None = None, picker: TrifectaPicker | None = None) -> None:
        self._model = model
        self._builder = builder or BaneiFeatureBuilder()
        self._picker = picker or TrifectaPicker()

    def forecast(self, con: duckdb.DuckDBPyConnection, rid: str) -> dict[str, Any]:
        """予想の結果（JSON にできる辞書）。``runners`` は勝つ確率の高い順、``picks`` はずれの大きい順。"""
        repository = BaneiRunsRepository(con)
        card = repository.card(rid)
        runs = pd.concat([repository.confirmed(exclude_rid=rid), card], ignore_index=True)
        features = self._builder.build(runs)
        race = self._model.predict(features[features["rid"] == rid]).sort_values("p_win", ascending=False).reset_index(drop=True)
        picks = self._picker.pick(race["umaban"].astype(int).tolist(), race["p_win"].tolist(), race["c_win"].tolist())
        first = race.iloc[0]
        return {
            "rid": rid,
            "race_number": int(first["race_no"]),
            "race_name": str(first["race_name"] or "").strip(),
            "condition": "".join(str(first["cond_name"] or "").split()),
            "post": str(first["post"] or "").strip(),
            "water": None if pd.isna(first["water"]) else float(first["water"]),
            "body_weights": int(race["bw"].notna().sum()),
            "runners": [self._runner(row, rank) for rank, row in enumerate(race.to_dict("records"))],
            "picks": [{"order": list(pick.order), "probability": round(pick.probability, 4), "gap": round(pick.gap, 2), "strong": pick.strong}
                      for pick in picks],
        }

    @staticmethod
    def _runner(row: dict[str, Any], rank: int) -> dict[str, Any]:
        return {"number": int(row["umaban"]), "name": str(row["name"]), "mark": MARKS[rank] if rank < len(MARKS) else "",
                "p_win": round(float(row["p_win"]), 4), "c_win": round(float(row["c_win"]), 4),
                "load": None if pd.isna(row["load"]) else int(row["load"]),
                "body_weight": None if pd.isna(row["bw"]) else int(row["bw"])}
