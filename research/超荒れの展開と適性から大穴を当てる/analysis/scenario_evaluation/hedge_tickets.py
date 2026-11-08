"""抑えの買い目: 中穴・大穴2頭の組の確率が高いレースで、本線（今の印の 3連複・3連単）に無い 3連複を少ない点数で足す。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

#: 抑えの組み方（名前 → 説明）。
SHAPES: dict[str, str] = {
    "◎−組": "◎ と、確率のいちばん高い中穴・大穴の組の 3連複 1点",
    "組−人気上位3頭": "確率のいちばん高い中穴・大穴の組と、1〜3番人気のそれぞれの 3連複 3点",
}


@dataclass(frozen=True)
class HedgeTickets:
    """``races`` は ``PairProbability.races`` のレースの表に、line 以上の2頭以上の確率のレースだけを残したもの。
    ``favorites`` はレースごとの ◎ の馬番、``popular`` はレースごとの 1〜3番人気の馬番の並び、``main`` は本線の買い目（重なりを除くため）。
    1行 = 1点（race_id・period・shape・combo（3連複の組番。小さい順に2桁ずつ））。本線に同じ組がある点と、同じ馬が2回入る点は買わない。"""

    shape: str

    def build(self, races: pd.DataFrame, favorites: pd.Series, popular: pd.Series, main: pd.DataFrame) -> pd.DataFrame:
        bought = set(zip(main.loc[main["ticket_type"] == "3連複", "race_id"], main.loc[main["ticket_type"] == "3連複", "combo"]))
        rows = []
        for race in races.itertuples(index=False):
            first, second = (int(value) for value in race.pair.split("-"))
            partners = self._partners(race.race_id, favorites, popular)
            for partner in partners:
                horses = {first, second, partner}
                if len(horses) < 3:
                    continue
                combo = "".join(f"{number:02d}" for number in sorted(horses))
                if (race.race_id, combo) in bought:
                    continue
                rows.append({"race_id": race.race_id, "period": race.period, "shape": self.shape, "combo": combo})
        return pd.DataFrame(rows, columns=["race_id", "period", "shape", "combo"])

    def _partners(self, race_id: str, favorites: pd.Series, popular: pd.Series) -> list[int]:
        if self.shape == "◎−組":
            return [int(favorites[race_id])] if race_id in favorites.index else []
        return list(popular.get(race_id, []))
