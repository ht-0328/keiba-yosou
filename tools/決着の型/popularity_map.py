"""レースごとの「人気 → 馬番」の対応。人気で決める買い目を馬番の組にするのに使う。"""

from __future__ import annotations

import pandas as pd


class PopularityMap:
    """出走の行から、rid → （単勝人気 → 馬番の並び）を作る。同じ人気が2頭いれば（まれ）両方並ぶ。人気の無い馬は入れない。"""

    def __init__(self, runners: pd.DataFrame) -> None:
        self._by_race: dict[str, dict[int, list[int]]] = {}
        with_popularity = runners.dropna(subset=["popularity", "horse_no"])
        for race_id, popularity, horse_no in zip(with_popularity["race_id"], with_popularity["popularity"], with_popularity["horse_no"]):
            self._by_race.setdefault(race_id, {}).setdefault(int(popularity), []).append(int(horse_no))

    def of(self, race_id: str) -> dict[int, list[int]]:
        """そのレースの 人気 → 馬番。レースが無ければ空。"""
        return self._by_race.get(race_id, {})

    def race_ids(self) -> list[str]:
        return list(self._by_race)
