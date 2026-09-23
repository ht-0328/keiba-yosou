"""C. 出走馬の実績のばらつき（10個）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import RaceRecords, as_numbers

#: 特徴量の名前。
MARGIN_GAP = "近5走の平均着差の1位と2位の差"
FINISH_STD = "近5走の平均着順の標準偏差"
FINISH_MEDIAN = "近5走の平均着順の中央値"
PREV_PLACED_SHARE = "前走3着以内だった馬の割合"
NO_PREV_SHARE = "前走が無い馬の割合"
PROMOTED_COUNT = "昇級馬の数"
JOCKEY_CHANGE_COUNT = "乗り替わりの馬の数"
JOCKEY_RATE_MAX = "騎手の近1年の3着以内の割合の最大"
LEAD_CANDIDATES = "逃げそうな馬の数"
TIMED_SHARE = "持ち時計の順位が付く馬の割合"
NAMES: tuple[str, ...] = (
    MARGIN_GAP, FINISH_STD, FINISH_MEDIAN, PREV_PLACED_SHARE, NO_PREV_SHARE, PROMOTED_COUNT,
    JOCKEY_CHANGE_COUNT, JOCKEY_RATE_MAX, LEAD_CANDIDATES, TIMED_SHARE,
)
#: 集約する1頭ごとの特徴量の名前（手本の 09 の C〜G）。
_MARGIN, _FINISH, _PREV_FINISH = "近5走の平均着差", "近5走の平均着順", "前走の着順"
_RUN_COUNT, _CLASS_CHANGE, _JOCKEY_CHANGE = "近5走の数", "クラスの変更", "乗り替わり"
_JOCKEY_RATE, _LEAD, _BEST_TIME_RANK = "騎手の近1年の3着以内の割合", "逃げそうな馬の数", "持ち時計のレース内順位（コース単位）"
#: 3着以内、昇級、乗り替わりの値。
_LAST_PLACE = 3
_PROMOTED, _CHANGED = "昇級", "乗り替わり"


class FieldStrengthSpreadFeatures:
    """C. 出走馬の実績のばらつき。1頭ごとの近走・前走・騎手の特徴量を、全出走馬で集約する。``RaceFeatureGroup`` を守る。"""

    def build(self, records: RaceRecords) -> pd.DataFrame:
        race = records.entries["race_id"]
        features = records.horse_features
        margin = as_numbers(features[_MARGIN])
        finish = as_numbers(features[_FINISH])
        by_race = finish.groupby(race)
        return pd.DataFrame({
            MARGIN_GAP: self._gap_of_best_two(race, margin),
            FINISH_STD: by_race.std(),
            FINISH_MEDIAN: by_race.median(),
            PREV_PLACED_SHARE: as_numbers(features[_PREV_FINISH]).le(_LAST_PLACE).groupby(race).mean(),
            NO_PREV_SHARE: as_numbers(features[_RUN_COUNT]).fillna(0).eq(0).groupby(race).mean(),
            PROMOTED_COUNT: features[_CLASS_CHANGE].eq(_PROMOTED).groupby(race).sum().astype("float64"),
            JOCKEY_CHANGE_COUNT: features[_JOCKEY_CHANGE].eq(_CHANGED).groupby(race).sum().astype("float64"),
            JOCKEY_RATE_MAX: as_numbers(features[_JOCKEY_RATE]).groupby(race).max(),
            LEAD_CANDIDATES: as_numbers(features[_LEAD]).groupby(race).first(),
            TIMED_SHARE: as_numbers(features[_BEST_TIME_RANK]).notna().groupby(race).mean(),
        }).reindex(records.race_ids)

    def _gap_of_best_two(self, race: pd.Series, margin: pd.Series) -> pd.Series:
        """近5走の平均着差の、小さい順の1位と2位の差。値のある馬が2頭に満たなければ欠損値。"""
        known = margin.notna()
        ordered = pd.DataFrame({"race": race[known], "margin": margin[known]}).sort_values(["race", "margin"], kind="stable")
        ordered["rank"] = ordered.groupby("race").cumcount() + 1
        by_rank = ordered[ordered["rank"] <= 2].pivot(index="race", columns="rank", values="margin")
        if 2 not in by_rank.columns:
            return pd.Series(dtype="float64")
        return by_rank[2] - by_rank[1]
