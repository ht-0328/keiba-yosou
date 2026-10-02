"""展開の予想の結果から、まとまり P の 20列を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import pace_forecast_columns as names


class PaceForecastTableBuilder:
    """元の予測の表（1行 = 1頭。``race_id``・``horse_id`` と ``SOURCE_COLUMNS``）から、対象の出走ごとの P の 20列を作る。

    1頭ずつ当てるモデルは相手が誰かを知らないので、先頭の確率・4コーナーの位置・上がりの速さは、同じレースの馬の中での
    順位と偏差も列にする（まとまり G・M・O と同じ考え）。順位と偏差は、元の予測の表にあるそのレースの全頭で数える。
    例: 4コーナーの位置の予測が 0.20 の馬は、レースの平均 0.50・標準偏差 0.25 なら偏差 −1.2（前にいそう）。
    元の予測が無い出走（予測の無い年・予測していない馬）は全部欠損値。``race_ids``・``horse_ids`` は対象の出走の
    行ごとの鍵で、行の並びと index は ``race_ids`` と同じ。
    """

    def build(self, race_ids: pd.Series, horse_ids: pd.Series, forecasts: pd.DataFrame) -> pd.DataFrame:
        table = self._columns(self._source(forecasts))
        keys = pd.DataFrame({"race_id": race_ids.astype(str).to_numpy(), "horse_id": horse_ids.astype(str).to_numpy()})
        aligned = keys.merge(table, on=names.KEY, how="left")
        return aligned[list(names.PACE_FORECAST_NAMES)].set_axis(race_ids.index).astype("float64")

    def _source(self, forecasts: pd.DataFrame) -> pd.DataFrame:
        """鍵を文字にそろえ、同じ出走の重なりを除いた元の予測。表が空なら、列だけの空の表。"""
        columns = [*names.KEY, *names.SOURCE_COLUMNS]
        if forecasts.empty:
            return pd.DataFrame(columns=columns).astype({column: "float64" for column in names.SOURCE_COLUMNS})
        source = forecasts.reindex(columns=columns)
        source = source.assign(race_id=source["race_id"].astype(str), horse_id=source["horse_id"].astype(str))
        return source.drop_duplicates(names.KEY).reset_index(drop=True)

    def _columns(self, source: pd.DataFrame) -> pd.DataFrame:
        race = source["race_id"]
        leader, corner4, closing = (source[column].astype("float64") for column in (names.LEADER, names.CORNER4, names.CLOSING))
        combined = corner4 + closing
        return pd.DataFrame({
            "race_id": race, "horse_id": source["horse_id"],
            names.LEADER_P: leader, names.LEADER_RANK: self._rank(leader, race, ascending=False),
            names.LEADER_GAP: leader - leader.groupby(race).transform("max"),
            names.FRONT_P: source[names.FRONT], names.MIDDLE_P: source[names.MIDDLE], names.BACK_P: source[names.BACK],
            names.FRONT_RANK: self._rank(source[names.FRONT].astype("float64"), race, ascending=False),
            names.CORNER4_P: corner4, names.CORNER4_RANK: self._rank(corner4, race), names.CORNER4_Z: self._z(corner4, race),
            names.CLOSING_P: closing, names.CLOSING_RANK: self._rank(closing, race), names.CLOSING_Z: self._z(closing, race),
            names.COMBINED: combined, names.COMBINED_RANK: self._rank(combined, race),
            names.HIGH_P: source[names.HIGH], names.SLOW_P: source[names.SLOW],
            names.FIRST_DIFF: source[names.FIRST_MIDDLE],
            names.FIRST_WIDTH: source[names.FIRST_HIGH].astype("float64") - source[names.FIRST_LOW].astype("float64"),
            names.SECOND_DIFF: source[names.SECOND_MIDDLE],
        })

    def _rank(self, values: pd.Series, race: pd.Series, ascending: bool = True) -> pd.Series:
        """レース内の順位（同じ値は同じ順位）。4コーナーの位置と上がりは小さいほど前・速いので小さい順、確率は高い順。"""
        return values.groupby(race).rank(method="min", ascending=ascending)

    def _z(self, values: pd.Series, race: pd.Series) -> pd.Series:
        """レース内の偏差（平均との差 ÷ 標準偏差）。1頭立てや全頭が同じ値なら欠損値。"""
        grouped = values.groupby(race)
        spread = grouped.transform("std").replace(0.0, np.nan)
        return (values - grouped.transform("mean")) / spread
