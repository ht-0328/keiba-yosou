"""騎手の成績: 騎手ごとに、その日より前の直近 365日の高知での騎乗数・3着以内率・4コーナーの位置・人気とくらべた来やすさ。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

_KEYS = ["jockey_code", "race_date"]
#: 振り返る日数。その日は含めない（その日のレースの結果を混ぜないため）。
_WINDOW = "365D"
_SUMS = ["rides", "places", "corner4_rel", "expected_places"]


@dataclass(frozen=True)
class JockeyForm:
    """``runs`` は高知の出走の行（``jockey_code``・``race_date``・``popularity``・``placed``・``corner4_rel``）。

    「人気とくらべた来やすさ」は、3着以内の数 ÷ 乗った馬の人気から見込まれる3着以内の数。
    人気ごとの3着以内率は高知の全期間の値を使う（比べる物差しで、騎手ごとの数え方には先の結果を入れない）。
    """

    def add(self, runs: pd.DataFrame) -> pd.DataFrame:
        daily = self._daily(runs)
        window = daily.set_index("race_date").groupby("jockey_code")[_SUMS].rolling(_WINDOW, closed="left").sum().reset_index()
        form = pd.DataFrame({
            "jockey_code": window["jockey_code"], "race_date": window["race_date"],
            "jockey_rides_365": window["rides"],
            "jockey_place_rate_365": window["places"] / window["rides"],
            "jockey_corner4_rel_365": window["corner4_rel"] / window["rides"],
            "jockey_lift_365": window["places"] / window["expected_places"],
        })
        return runs.merge(form, on=_KEYS, how="left")

    def _daily(self, runs: pd.DataFrame) -> pd.DataFrame:
        """騎手 × 開催日の合計（古い順）。"""
        place_rate_by_popularity = runs.groupby("popularity")["placed"].mean()
        rides = pd.DataFrame({
            "jockey_code": runs["jockey_code"], "race_date": runs["race_date"], "rides": 1.0, "places": runs["placed"],
            "corner4_rel": runs["corner4_rel"], "expected_places": runs["popularity"].map(place_rate_by_popularity),
        })
        return rides.groupby(_KEYS)[_SUMS].sum().reset_index().sort_values(_KEYS)
