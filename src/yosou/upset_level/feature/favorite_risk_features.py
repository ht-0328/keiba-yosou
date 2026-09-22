"""D. 1番人気の危うさ（10個）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import RaceRecords, as_numbers
from yosou.shared.feature.group import WIN_ODDS
from yosou.shared.feature.history import WORSE_THAN_POPULARITY, AsOfLookup, DatedRecords, PopularityRunSummary

#: 特徴量の名前。馬体重の増減は、予測に要る情報の確認にも使うので、外にも見せる。
FAVORITE_PREV_FINISH = "1番人気の前走の着順"
FAVORITE_PREV_POPULARITY = "1番人気の前走の人気"
FAVORITE_PREV_GAP = "1番人気の前走の人気と着順の差"
FAVORITE_RECENT_FINISH = "1番人気の近5走の平均着順"
FAVORITE_WORSE_COUNT = "1番人気の近5走で人気より悪い着順だった回数"
FAVORITE_CAREER_RUNS = "1番人気の通算の出走数"
FAVORITE_JOCKEY_CHANGE = "1番人気の乗り替わり"
FAVORITE_DISTANCE_CHANGE = "1番人気の距離の変更"
FAVORITE_CLASS_CHANGE = "1番人気のクラスの変更"
FAVORITE_WEIGHT_CHANGE = "1番人気の馬体重の増減"
NAMES: tuple[str, ...] = (
    FAVORITE_PREV_FINISH, FAVORITE_PREV_POPULARITY, FAVORITE_PREV_GAP, FAVORITE_RECENT_FINISH, FAVORITE_WORSE_COUNT,
    FAVORITE_CAREER_RUNS, FAVORITE_JOCKEY_CHANGE, FAVORITE_DISTANCE_CHANGE, FAVORITE_CLASS_CHANGE,
    FAVORITE_WEIGHT_CHANGE,
)
#: 途中の計算に使う列の名前（前走の人気と着順の差）。
_PREV_GAP = "prev_gap"
#: 1番人気の1頭ごとの特徴量をそのまま使うもの（レース単位の名前 → 1頭ごとの名前。手本の 09 の B〜E）。
_COPIED: dict[str, str] = {
    FAVORITE_PREV_FINISH: "前走の着順", FAVORITE_PREV_POPULARITY: "前走の人気",
    FAVORITE_RECENT_FINISH: "近5走の平均着順", FAVORITE_CAREER_RUNS: "通算の出走数",
    FAVORITE_JOCKEY_CHANGE: "乗り替わり", FAVORITE_DISTANCE_CHANGE: "距離の変更",
    FAVORITE_CLASS_CHANGE: "クラスの変更", FAVORITE_WEIGHT_CHANGE: "馬体重の増減",
}


class FavoriteRiskFeatures:
    """D. 1番人気の危うさ。その時点の単勝オッズが最小の馬の値を取り出す（設計書 11 の 9）。``RaceFeatureGroup`` を守る。

    「前走の人気と着順の差」と「近5走で人気より悪い着順だった回数」は、人気馬の予想のまとまり J と同じ作り方で、
    その馬の前走までの値から作る（今回の確定人気は使わない）。オッズの無いレース（木曜）は、全部欠損値。
    """

    def build(self, records: RaceRecords) -> pd.DataFrame:
        entries = records.entries
        odds = as_numbers(records.horse_features[WIN_ODDS])
        known = odds.notna()
        favorite_rows = odds[known].groupby(entries.loc[known, "race_id"]).idxmin()
        horse_values = pd.concat([records.horse_features, self._popularity_history(records)], axis=1)
        favorites = horse_values.loc[favorite_rows].set_axis(favorite_rows.index)
        features = pd.DataFrame({name: favorites[source] for name, source in _COPIED.items()})
        return features.assign(**{
            FAVORITE_PREV_GAP: favorites[_PREV_GAP], FAVORITE_WORSE_COUNT: favorites[WORSE_THAN_POPULARITY],
        })[list(NAMES)].reindex(records.race_ids)

    def _popularity_history(self, records: RaceRecords) -> pd.DataFrame:
        """出走の行ごとの、前走の人気と着順の差と、前日までの新しい5走で人気より悪い着順だった回数。"""
        entries = records.entries
        summary = PopularityRunSummary().build(records.records.past_runs)
        dated = DatedRecords(summary, key_column="horse_id", date_column="race_date")
        found = AsOfLookup(entries, "horse_id").latest(dated, days_before=1)
        prev_gap = as_numbers(entries["prev_finish"]) - as_numbers(entries["prev_popularity"])
        return pd.DataFrame({_PREV_GAP: prev_gap, WORSE_THAN_POPULARITY: found[WORSE_THAN_POPULARITY]}, index=entries.index)
