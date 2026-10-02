"""出走の行（1行 = 1頭）から、1行 = 1レースの「決着の表」を作る。"""

from __future__ import annotations

import pandas as pd

#: 決着の表の列と意味。切り口（``outcome_dimension``）はこの列から値を作る。
RACE_COLUMNS: dict[str, str] = {
    "race_id": "rid", "race_date": "開催日", "year": "開催年", "venue": "競馬場", "race_no": "レース番号", "field_size": "出走頭数",
    "pop_1st": "1着馬の単勝人気", "pop_2nd": "2着馬の単勝人気", "pop_3rd": "3着馬の単勝人気",
    "odds_1st": "1着馬の単勝オッズ", "odds_2nd": "2着馬の単勝オッズ",
    "fav1_finish": "1番人気の着順（馬券外・着順なしは 99）", "fav2_finish": "2番人気の着順（同上）", "fav3_finish": "3番人気の着順（同上）",
    "n_under10": "単勝 10倍以下の頭数", "n_under30": "単勝 30倍以下の頭数",
    "age_min": "出走馬の最も若い馬齢", "age_max": "出走馬の最も高い馬齢",
}
#: 3着以内に入らなかった（または着順の付かない）人気馬の着順に入れる値。
OUT_OF_MONEY = 99
#: 3着以内として見る頭数。同着で4頭以上いるときは、着順 → 人気の順で先の3頭だけ。
_TOP = 3
_RACE_ATTRIBUTES = ("race_date", "year", "venue", "race_no", "field_size")
_FAVOURITES = (1, 2, 3)
_ODDS_LINES = {"n_under10": 10.0, "n_under30": 30.0}


class RaceTable:
    """出走の行から決着の表を作る。

    - 1〜3着の人気・オッズ: 着順 → 人気 の順に並べた先頭の3頭（同着は人気の上の馬を先にする）。
    - 1〜3番人気の着順: 3着以内に入らなければ ``OUT_OF_MONEY``。同じ人気が2頭いれば（まれ）良いほうの着順。
    - 単勝 10倍以下・30倍以下の頭数: 出走した馬のうちオッズがその値以下の数。
    """

    def build(self, runners: pd.DataFrame) -> pd.DataFrame:
        if runners.empty:
            return pd.DataFrame(columns=list(RACE_COLUMNS)).set_index("race_id")
        by_race = runners.groupby("race_id", sort=True)
        races = by_race[list(_RACE_ATTRIBUTES)].first()
        races = races.join(self._placed(runners)).join(self._favourites(runners)).join(self._odds_counts(by_race))
        races["age_min"] = by_race["age"].min()
        races["age_max"] = by_race["age"].max()
        return races[[name for name in RACE_COLUMNS if name != "race_id"]]

    @staticmethod
    def _placed(runners: pd.DataFrame) -> pd.DataFrame:
        """1〜3着の人気とオッズ（``pop_1st`` … ``odds_2nd``）。"""
        placed = runners[runners["finish"].le(_TOP)].sort_values(["race_id", "finish", "popularity"])
        placed = placed.assign(rank=placed.groupby("race_id").cumcount() + 1)
        placed = placed[placed["rank"].le(_TOP)]
        pops = placed.pivot(index="race_id", columns="rank", values="popularity")
        odds = placed.pivot(index="race_id", columns="rank", values="win_odds")
        return pd.DataFrame({
            "pop_1st": pops.get(1), "pop_2nd": pops.get(2), "pop_3rd": pops.get(3),
            "odds_1st": odds.get(1), "odds_2nd": odds.get(2),
        })

    @staticmethod
    def _favourites(runners: pd.DataFrame) -> pd.DataFrame:
        """1〜3番人気の着順（``fav1_finish`` …）。3着以内に入らなければ ``OUT_OF_MONEY``。"""
        favourites = runners[runners["popularity"].isin(_FAVOURITES)]
        finish = favourites["finish"].where(favourites["finish"].le(_TOP), OUT_OF_MONEY).fillna(OUT_OF_MONEY)
        best = favourites.assign(finish=finish).pivot_table(index="race_id", columns="popularity", values="finish", aggfunc="min")
        return pd.DataFrame({f"fav{pop}_finish": best.get(pop) for pop in _FAVOURITES})

    @staticmethod
    def _odds_counts(by_race) -> pd.DataFrame:
        """単勝オッズが線以下の頭数。"""
        return pd.DataFrame({name: by_race["win_odds"].agg(lambda odds, line=line: int(odds.le(line).sum()))
                             for name, line in _ODDS_LINES.items()})
