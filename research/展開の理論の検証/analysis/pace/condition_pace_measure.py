"""馬場状態を基準の鍵に入れて、レースの速さを測る。"""

from __future__ import annotations

import pandas as pd

from yosou.race_development.feature.history.pace_baseline import MEAN, STD, PaceBaseline


class ConditionPaceMeasure:
    """``time_column`` のタイムを、同じ競馬場・コース・距離・**馬場状態**・クラスの基準と比べた z（速いほどプラス）。

    基準の作り方は ``PaceBaseline`` と同じ（開催日の前日までの3年。30 レースに満たなければクラスをまとめる）。
    馬場状態を鍵に入れるため、トラックコードに馬場状態を連結してから渡す（``PaceBaseline`` の鍵は競馬場・トラックコード・
    距離・クラスで固定のため）。馬場状態ごとの基準が作れないレース（不良のように少ない馬場）は、馬場状態を分けない基準で補う。
    例: 東京ダ1600 の不良は、東京ダ1600 の不良どうしで比べる。重いダートは時計が速いので、良と混ぜるとハイに寄る。
    """

    def __init__(self, time_column: str) -> None:
        self._time_column = time_column
        self._baseline = PaceBaseline(time_column, "基準")

    def z(self, races: pd.DataFrame) -> pd.Series:
        keyed = races.assign(track_code=races["track_code"].astype(str) + "|" + races["condition"].astype(str))
        return self._z(keyed).fillna(self._z(races))

    def _z(self, races: pd.DataFrame) -> pd.Series:
        attached = self._baseline.attach(races)
        mean = pd.to_numeric(attached[self._baseline.column(MEAN)], errors="coerce")
        std = pd.to_numeric(attached[self._baseline.column(STD)], errors="coerce")
        return (mean - pd.to_numeric(races[self._time_column], errors="coerce")) / std
