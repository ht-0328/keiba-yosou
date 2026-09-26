"""前半と後半の予想（①〜⑥）の、年ごとの当たり具合。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from ..dataset import label_names as names
from ..feature import (
    BACK_PROBABILITY,
    CLOSING_PREDICTION,
    CORNER4_PREDICTION,
    EVEN_PROBABILITY,
    FIRST_HALF_QUANTILES,
    FRONT_PROBABILITY,
    HIGH_PROBABILITY,
    LEADER_PROBABILITY,
    MIDDLE_PROBABILITY,
    SECOND_HALF_QUANTILES,
    SLOW_PROBABILITY,
)
from .race_metrics import RaceMetrics
from .stage_baselines import StageBaselines

#: 出力の列。
KIND, METRIC, YEAR, VALUE = "予想", "指標", "年", "値"
#: 比べる基準にする近走の特徴量（設計書 16 の 3）。
RECENT_CORNER4 = "近5走の平均4コーナー位置"
RECENT_CLOSING = "近5走の上がりの速さの平均"
#: 基準の割合の表の鍵の列（一時的に足す）。
_PREVIOUS_ZONE, _CANDIDATES = "_previous_zone", "_candidates"
#: 1行の形（予想・指標・年・値）。
Row = tuple[str, str, str, float]


class StageYearMetrics:
    """①〜⑥ の、年ごとの当たり具合と、モデルによらない基準（設計書 16 の 2・3・7 の表4）を、縦長の表で出す。

    ``horses`` は1行 = 1頭（列 ``年``・``race_id`` と、目的変数・予測・基準に使う特徴量）、``races`` は1行 = 1レース。
    予測は、どれも学習に使っていない予測（その年より前だけで学習したモデルの予測）である。割合の基準は、その年より前の年の
    行だけで数えるので、``horses``・``races`` には、確かめる年より前の年の行も入れておく。
    """

    def __init__(self) -> None:
        self._metrics = RaceMetrics()
        self._baselines = StageBaselines()

    def table(self, horses: pd.DataFrame, races: pd.DataFrame, years: Sequence[int]) -> pd.DataFrame:
        """列は ``予想``・``指標``・``年``・``値``。``years`` の年だけを出す。"""
        horses = horses.assign(**{_PREVIOUS_ZONE: self._baselines.previous_zone(horses)})
        races = races.assign(**{_CANDIDATES: self._baselines.candidate_bucket(races)})
        rows: list[Row] = []
        for year in (str(year) for year in years):
            rows += self._horse_rows(year, horses[horses[YEAR] == year], horses[horses[YEAR] < year])
            rows += self._race_rows(year, races[races[YEAR] == year], races[races[YEAR] < year])
        return pd.DataFrame(rows, columns=[KIND, METRIC, YEAR, VALUE])

    def _horse_rows(self, year: str, horses: pd.DataFrame, before: pd.DataFrame) -> list[Row]:
        return [
            *self._leader_rows(year, horses[horses[names.LEADER].notna()]),
            *self._zone_rows(year, horses[horses[names.EARLY_ZONE].notna()], before[before[names.EARLY_ZONE].notna()]),
            *self._regression_rows("④ 4コーナーの位置", year, horses, before, (names.CORNER4_POSITION, CORNER4_PREDICTION, RECENT_CORNER4)),
            *self._regression_rows("⑤ 上がりの速さ", year, horses, before, (names.CLOSING_SPEED, CLOSING_PREDICTION, RECENT_CLOSING)),
        ]

    def _leader_rows(self, year: str, leader: pd.DataFrame) -> list[Row]:
        metrics, answer, race = self._metrics, leader[names.LEADER], leader["race_id"]
        uniform = 1.0 / race.groupby(race).transform("size")
        return [
            ("① 先頭の馬", "レースごとのログ損失", year, metrics.race_log_loss(leader[LEADER_PROBABILITY], answer)),
            ("① 先頭の馬", "同（基準: 全馬に同じ確率）", year, metrics.race_log_loss(uniform, answer)),
            ("① 先頭の馬", "同（基準: 先頭率をそろえただけ）", year,
             metrics.race_log_loss(self._baselines.leader_by_rate(leader), answer)),
            ("① 先頭の馬", "同（基準: 推定脚質が逃げの馬に等分）", year,
             metrics.race_log_loss(self._baselines.leader_by_style(leader), answer)),
            ("① 先頭の馬", "確率1位が先頭だった割合", year, metrics.top_hit_rate(leader[LEADER_PROBABILITY], race, answer)),
        ]

    def _zone_rows(self, year: str, zone: pd.DataFrame, before: pd.DataFrame) -> list[Row]:
        labels = zone[names.EARLY_ZONE].to_numpy()
        predicted = zone[[FRONT_PROBABILITY, MIDDLE_PROBABILITY, BACK_PROBABILITY]].to_numpy()
        return self._class_rows("② 序盤の位置", year, labels, predicted, [
            ("前年までの割合", self._baselines.prior(before, names.EARLY_ZONE, len(zone))),
            ("前走の区分からの割合", self._baselines.by_key(before, zone, _PREVIOUS_ZONE, names.EARLY_ZONE)),
        ])

    def _race_rows(self, year: str, races: pd.DataFrame, before: pd.DataFrame) -> list[Row]:
        pace, pace_before = races[races[names.PACE_CLASS].notna()], before[before[names.PACE_CLASS].notna()]
        labels = pace[names.PACE_CLASS].to_numpy()
        predicted = pace[[SLOW_PROBABILITY, EVEN_PROBABILITY, HIGH_PROBABILITY]].to_numpy()
        return [
            *self._class_rows("③ 前半のペース", year, labels, predicted, [
                ("前年までの割合", self._baselines.prior(pace_before, names.PACE_CLASS, len(pace))),
                ("逃げそうな馬の数からの割合", self._baselines.by_key(pace_before, pace, _CANDIDATES, names.PACE_CLASS)),
            ]),
            *self._interval_rows("③ 前半タイム", year, races, names.FIRST_HALF_DIFF, FIRST_HALF_QUANTILES),
            *self._interval_rows("⑥ 後半タイム", year, races, names.SECOND_HALF_DIFF, SECOND_HALF_QUANTILES),
        ]

    def _class_rows(self, kind: str, year: str, labels: np.ndarray, predicted: np.ndarray,
                    baselines: list[tuple[str, np.ndarray]]) -> list[Row]:
        loss = self._metrics.multiclass_log_loss
        return [
            (kind, "多クラスのログ損失", year, loss(predicted, labels)),
            *[(kind, f"同（基準: {name}）", year, loss(values, labels)) for name, values in baselines],
            (kind, "正解率", year, float((predicted.argmax(axis=1) == labels).mean())),
        ]

    def _regression_rows(self, kind: str, year: str, horses: pd.DataFrame, before: pd.DataFrame,
                         columns: tuple[str, str, str]) -> list[Row]:
        """``columns`` は（目的変数、予測、近走の平均）。近走の平均が無い馬は、その年より前の年の平均で埋める。"""
        label, predicted, recent = columns
        usable = horses[horses[label].notna()]
        actual = usable[label]
        baseline = usable[recent].fillna(before[label].mean())
        return [
            (kind, "MAE", year, float((usable[predicted] - actual).abs().mean())),
            (kind, "MAE（基準: 近走の平均）", year, float((baseline - actual).abs().mean())),
            (kind, "レース内の順位相関", year, self._metrics.rank_correlation(usable[predicted], actual, usable["race_id"])),
        ]

    def _interval_rows(self, kind: str, year: str, races: pd.DataFrame, label: str,
                       quantiles: tuple[str, str, str]) -> list[Row]:
        usable = races[races[label].notna()]
        actual = usable[label].to_numpy()
        low, middle, high = (pd.to_numeric(usable[column], errors="coerce").to_numpy(dtype=float) for column in quantiles)
        predicted = ~np.isnan(middle)
        inside = ((actual >= low) & (actual <= high))[predicted]
        return [
            (kind, "MAE（秒）", year, float(np.abs(middle - actual).mean())),
            (kind, "MAE（基準: 基準のタイムだけ）", year, float(np.abs(actual).mean())),
            (kind, "80% の幅に入った割合", year, float(inside.mean()) if predicted.any() else float("nan")),
        ]
