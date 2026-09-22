"""E. 過去の同条件の荒れ率（8個）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import RaceRecords
from yosou.shared.feature.history import RACES, UPSETS, ConditionUpsetRate
from yosou.shared.repository.race_payout_repository import VOID, YEN

from ..dataset.bet_type import BetType
from ..dataset.upset_level_rule import UpsetLevelRule
from .distance_band import distance_band

#: 条件の鍵（名前 → 列の作り方）。競馬場・芝ダ・距離帯と、クラス。
COURSE_KEY, CLASS_KEY = "course_key", "class_key"


def course_rate_name(bet: BetType) -> str:
    """同じ競馬場・芝ダ・距離帯の、近1年の中荒れ以上の割合の特徴量の名前。"""
    return f"同じ競馬場・芝ダ・距離帯の近1年の中荒れ以上の割合（{bet.label}）"


def class_rate_name(bet: BetType) -> str:
    """同じクラスの、近1年の中荒れ以上の割合の特徴量の名前。"""
    return f"同じクラスの近1年の中荒れ以上の割合（{bet.label}）"


NAMES: tuple[str, ...] = (
    *(course_rate_name(bet) for bet in BetType), *(class_rate_name(bet) for bet in BetType),
)


class ConditionUpsetRateFeatures:
    """E. 過去の同条件の荒れ率。同じ条件のレースが、開催日の前日までの 365日で中荒れ以上だった割合を、券種ごとに数える。
    ``RaceFeatureGroup`` を守る。

    中荒れ以上かどうかは、目的変数と同じ ``UpsetLevelRule`` で決める（線引きを変えれば、ここも一緒に変わる）。
    同じ日の先に終わったレースは数えない（設計書 11 の 7）。
    """

    def __init__(self, rule: UpsetLevelRule) -> None:
        self._rule = rule

    def build(self, records: RaceRecords) -> pd.DataFrame:
        races = self._with_keys(records.races[["race_date", "venue_code", "surface", "distance_m", "class_order"]])
        history = self._with_keys(records.payouts)
        features = {
            **{course_rate_name(bet): self._rate(races, history, COURSE_KEY, bet) for bet in BetType},
            **{class_rate_name(bet): self._rate(races, history, CLASS_KEY, bet) for bet in BetType},
        }
        return pd.DataFrame(features, index=races.index).reindex(records.race_ids)

    def _with_keys(self, table: pd.DataFrame) -> pd.DataFrame:
        """レースの表に、条件の鍵の列を足す。"""
        course = table["venue_code"].astype("str") + "|" + table["surface"].astype("str") + "|" + distance_band(table["distance_m"]).astype("str")
        return table.assign(**{
            COURSE_KEY: course, CLASS_KEY: table["class_order"].astype("str"),
            "race_date": pd.to_datetime(table["race_date"]),
        })

    def _rate(self, races: pd.DataFrame, history: pd.DataFrame, key: str, bet: BetType) -> pd.Series:
        """1つの鍵・1つの券種の荒れ率。"""
        return ConditionUpsetRate(races, key).of(self._days(history, key, bet))

    def _days(self, history: pd.DataFrame, key: str, bet: BetType) -> pd.DataFrame:
        """鍵ごと・開催日ごとの、レース数と中荒れ以上のレース数。払戻の無い（成立しなかった）レースは数えない。"""
        if history.empty:
            return pd.DataFrame(columns=[key, "race_date", RACES, UPSETS])
        yen = pd.to_numeric(history[f"{bet.key}_{YEN}"], errors="coerce")
        counted = yen.notna() & ~history[f"{bet.key}_{VOID}"].fillna(False).astype(bool)
        upset = self._rule.is_upset_or_more(bet, yen) & counted
        counts = pd.DataFrame({key: history[key], "race_date": history["race_date"], RACES: counted, UPSETS: upset})
        return counts.groupby([key, "race_date"], as_index=False)[[RACES, UPSETS]].sum()
