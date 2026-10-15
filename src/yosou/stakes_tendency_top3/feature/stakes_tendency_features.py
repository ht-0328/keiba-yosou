"""K. 重賞の傾向（51個）を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.feature import EntryRecords

from 共通.stakes import GRADE_NAMES, RUNNER_COLUMNS

from .condition_bands import ConditionBands
from .edition_stats import EditionStats
from .tendency_cut import CUTS, EDITIONS, FAV1_PLACE_RATE, FAV123_PLACE_RATE, STATS

#: 出走の行と、対象の馬の行（前走のレースの鍵）を突き合わせる鍵。
_KEY = ["race_id", "horse_id"]
#: 過去の開催の出走馬の表の列（空の表を作るときに使う）。
_PAST_COLUMNS = ("target_race_id", "race_id", "prev_key", *(name for name, _ in RUNNER_COLUMNS))


class StakesTendencyFeatures:
    """K. 重賞の傾向（設計書 09 の K）。``FeatureGroup`` を守る。

    ``records.stakes_tendency``（対象の重賞ごとの、それより前の開催の出走馬。``StakesTendencyRepository`` が読む）から、
    予測する馬ごとに「そのレースの過去の開催で、自分と同じ条件（帯）だった馬」の 出走数・複勝率・単勝回収率・複勝回収率 を
    切り口ごとに数える（12個の切り口 × 4 = 48個）。これに、レース単位の3個（過去の開催の数、1番人気と1〜3番人気の複勝率）を足す。
    基準との差ではなく、そのレースの数字そのもの。帯が決まらない馬（木曜の枠など）や、過去にその帯の馬がいないレースは欠損値。
    重賞でないレースの行は全部欠損値になる（過去の開催が無い重賞は、過去開催の数だけ 0）。
    """

    def __init__(self) -> None:
        self._bands = ConditionBands()

    def build(self, records: EntryRecords) -> pd.DataFrame:
        entries = records.entries
        runners = records.stakes_tendency if len(records.stakes_tendency) else pd.DataFrame(columns=[*_PAST_COLUMNS, "is_target", "horse_id"])
        past = runners[~runners["is_target"].astype(bool)]
        stats = EditionStats(past)
        own = self._entry_bands(entries, runners[runners["is_target"].astype(bool)])
        theirs = self._past_bands(past)
        columns = [self._race_level(entries, past)]
        for cut in CUTS:
            table = stats.of(theirs[cut.key], entries["race_id"], own[cut.key])
            columns.append(table.rename(columns={stat: cut.feature_name(stat) for stat in STATS}))
        return pd.concat(columns, axis=1)

    def _entry_bands(self, entries: pd.DataFrame, targets: pd.DataFrame) -> pd.DataFrame:
        """予測する馬の側の帯（列 = 切り口の鍵）。前走のレースの鍵だけは、対象の馬の行から突き合わせて引く。"""
        bands = self._bands
        return pd.DataFrame({
            "prev_race": bands.prev_race(self._prev_keys(entries, targets)),
            "prev_finish": bands.prev_finish(entries["prev_finish"]),
            "prev_popularity": bands.prev_popularity(entries["prev_popularity"]),
            "frame": bands.frame(entries["frame_no"]),
            "odds": bands.odds(entries["win_odds"]),
            "popularity": bands.popularity_of_odds(entries["win_odds"], entries["race_id"]),
            "style": bands.style(entries["style_before"]),
            "interval": bands.interval(entries["interval_days"]),
            "affiliation": bands.affiliation(entries["affiliation"]),
            "experience": bands.experience(entries["same_race_places_before"]),
            "age": bands.age(entries["age"]),
            "sex": bands.sex(entries["sex"]),
        }, index=entries.index)

    def _past_bands(self, past: pd.DataFrame) -> pd.DataFrame:
        """過去の開催の出走馬の側の帯（列 = 切り口の鍵）。脚質・人気・オッズは、その開催の確定値で分ける。"""
        bands = self._bands
        return pd.DataFrame({
            "prev_race": bands.prev_race(past["prev_key"]),
            "prev_finish": bands.prev_finish(past["prev_finish"]),
            "prev_popularity": bands.prev_popularity(past["prev_popularity"]),
            "frame": bands.frame(past["frame_no"]),
            "odds": bands.odds(past["win_odds"]),
            "popularity": bands.popularity(past["popularity"]),
            "style": bands.style(past["style"]),
            "interval": bands.interval(past["interval_days"]),
            "affiliation": bands.affiliation(past["affiliation"]),
            "experience": bands.experience(past["same_race_places_before"]),
            "age": bands.age(past["age"]),
            "sex": bands.sex(past["sex"]),
        }, index=past.index)

    def _prev_keys(self, entries: pd.DataFrame, targets: pd.DataFrame) -> pd.Series:
        """出走の行ごとの前走のレースの鍵。対象の馬の行に無ければ欠損値（「前走なし」になる）。"""
        keys = entries[_KEY].astype(str)
        found = targets[[*_KEY, "prev_key"]].astype({column: str for column in _KEY}).drop_duplicates(_KEY)
        merged = keys.merge(found, on=_KEY, how="left")
        return pd.Series(merged["prev_key"].to_numpy(), index=entries.index, dtype="object")

    def _race_level(self, entries: pd.DataFrame, past: pd.DataFrame) -> pd.DataFrame:
        """レース単位の3個。過去の開催の数は、重賞なら過去が無くても 0、重賞でなければ欠損値。"""
        race_id = entries["race_id"].astype(str)
        is_stakes = entries["grade_code"].isin(GRADE_NAMES).to_numpy()
        target = past["target_race_id"].astype(str)
        hit = pd.to_numeric(past["finish"], errors="coerce").astype("float64") <= 3
        popularity = pd.to_numeric(past["popularity"], errors="coerce").astype("float64")
        editions = past.groupby(target)["race_id"].nunique() if len(past) else pd.Series(dtype="float64")
        fav1 = hit[popularity == 1].groupby(target[popularity == 1]).mean() if len(past) else pd.Series(dtype="float64")
        fav123 = hit[popularity <= 3].groupby(target[popularity <= 3]).mean() if len(past) else pd.Series(dtype="float64")
        counted = race_id.map(editions).astype("float64").fillna(0.0)
        return pd.DataFrame({
            EDITIONS: np.where(is_stakes, counted, np.nan),
            FAV1_PLACE_RATE: race_id.map(fav1).astype("float64").to_numpy(),
            FAV123_PLACE_RATE: race_id.map(fav123).astype("float64").to_numpy(),
        }, index=entries.index)
