"""ばんえいの1レースの予想: 出馬表と過去走から、各馬の勝つ確率・3着以内の確率・世間の見立て・印と、3連単の買い目を出す。"""

from __future__ import annotations

import re
from typing import Any

import duckdb
import pandas as pd

from ばんえいの予想.banei_feature_builder import BaneiFeatureBuilder
from ばんえいの予想.banei_mark_rule import BaneiMarkRule
from ばんえいの予想.banei_model import BaneiModel
from ばんえいの予想.banei_odds_repository import BaneiOddsRepository
from ばんえいの予想.banei_runs_repository import BaneiRunsRepository
from ばんえいの予想.order_probabilities import OrderProbabilities
from ばんえいの予想.trifecta_picker import TrifectaPicker

#: 競走条件名称の中の区切り（空白が2つ以上続く所。後ろに賞金の条件などが続く）。
_CONDITION_BREAK = re.compile(r"[ 　]{2,}")


class BaneiForecaster:
    def __init__(self, model: BaneiModel, *, builder: BaneiFeatureBuilder | None = None, picker: TrifectaPicker | None = None,
                 marks: BaneiMarkRule | None = None) -> None:
        self._model = model
        self._builder = builder or BaneiFeatureBuilder()
        self._picker = picker or TrifectaPicker()
        self._marks = marks or BaneiMarkRule()

    def forecast(self, con: duckdb.DuckDBPyConnection, rid: str) -> dict[str, Any]:
        """予想の結果（JSON にできる辞書）。``runners`` は勝つ確率の高い順、``picks`` はずれの大きい順。
        単勝・複勝のオッズと期待値は、表に見せるためだけに添える（印と買い目には使わない）。"""
        repository = BaneiRunsRepository(con)
        card = repository.card(rid)
        runs = pd.concat([repository.confirmed(exclude_rid=rid), card], ignore_index=True)
        features = self._builder.build(runs)
        race = self._model.predict(features[features["rid"] == rid]).sort_values("p_win", ascending=False).reset_index(drop=True)
        model, crowd = race["p_win"].tolist(), race["c_win"].tolist()
        race["p_top3"] = OrderProbabilities(model).top3()
        marks = self._marks.assign(model, crowd)
        odds = BaneiOddsRepository(con).read(rid)
        picks = self._picker.pick(race["umaban"].astype(int).tolist(), model, crowd)
        first = race.iloc[0]
        return {
            "rid": rid,
            "race_number": int(first["race_no"]),
            "race_name": str(first["race_name"] or "").strip(),
            "condition": self._condition(first["cond_name"]),
            "post": str(first["post"] or "").strip(),
            "water": None if pd.isna(first["water"]) else float(first["water"]),
            "body_weights": int(race["bw"].notna().sum()),
            "runners": [self._runner(row, marks[index], odds.get(int(row["umaban"]), (None, None)))
                        for index, row in enumerate(race.to_dict("records"))],
            "picks": [{"order": list(pick.order), "probability": round(pick.probability, 4), "gap": round(pick.gap, 2), "strong": pick.strong}
                      for pick in picks],
        }

    @staticmethod
    def _condition(text: object) -> str:
        """競走条件名称からクラスの部分だけ（例 ``Ｃ２－６``・``２歳Ｄ－８``）。後ろの賞金の条件は落とす。"""
        head = _CONDITION_BREAK.split(str(text or "").strip(" 　"))[0]
        return "".join(head.split())

    @staticmethod
    def _runner(row: dict[str, Any], mark: tuple[str, str], odds: tuple[float | None, float | None]) -> dict[str, Any]:
        win_odds, place_odds = odds
        return {"number": int(row["umaban"]), "name": str(row["name"]), "mark": mark[0], "mark_reason": mark[1],
                "p_win": round(float(row["p_win"]), 4), "p_top3": round(float(row["p_top3"]), 4), "c_win": round(float(row["c_win"]), 4),
                "win_odds": win_odds, "place_odds": place_odds,
                "win_value": None if win_odds is None else round(float(row["p_win"]) * win_odds, 3),
                "place_value": None if place_odds is None else round(float(row["p_top3"]) * place_odds, 3),
                "load": None if pd.isna(row["load"]) else int(row["load"]),
                "body_weight": None if pd.isna(row["bw"]) else int(row["bw"])}
