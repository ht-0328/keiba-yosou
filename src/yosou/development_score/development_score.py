"""確率と表 G から、馬ごとの展開スコア D を出す。"""

from __future__ import annotations

import pandas as pd

from . import names
from .advantage_table import AdvantageTable, cell
from .style_probabilities import StyleProbabilities

#: 出力の列の並び。
COLUMNS: tuple[str, ...] = ("race_id", "horse_id", *names.STYLES, *names.PACES, *names.CONTRIBUTIONS, names.SCORE)


class DevelopmentScore:
    """展開スコア D = Σ_ペース P(ペース) × Σ_脚質 P(その馬がその脚質の位置を取る) × G(脚質, ペース, 競馬場と芝ダ)（設計書 05 の 2）。

    ``forecasts`` は元の予測の表（``race_id``・``horse_id`` と ``pace_forecast.SOURCE_COLUMNS``）、``courses`` は 1行 = 1レースの
    競馬場コードと芝ダ（``race_id``・``競馬場コード``・``芝ダ``）。脚質ごとの内訳（その脚質の確率 × ペースで平均した G）も出す。
    例: 東京・芝でハイ 0.45・平均 0.38・スロー 0.17、逃げ 0.31・先行 0.41・差し 0.21・追込 0.07 の馬は、設計書 05 の例の G なら +0.020。
    ``courses`` に無いレースの馬は欠損値。
    """

    def __init__(self) -> None:
        self._probabilities = StyleProbabilities()

    def of(self, forecasts: pd.DataFrame, courses: pd.DataFrame, table: AdvantageTable) -> pd.DataFrame:
        """列は ``COLUMNS``。行の並びと index は ``forecasts`` と同じ。"""
        probabilities = self._probabilities.of(forecasts)
        course = forecasts[["race_id"]].astype(str).merge(
            courses[["race_id", names.VENUE_CODE, names.SURFACE]].astype(str), on="race_id", how="left").set_axis(forecasts.index)
        gaps = table.cells_for(course[names.VENUE_CODE], course[names.SURFACE])
        known = course[names.VENUE_CODE].notna()
        contributions = pd.DataFrame({
            names.contribution(style): probabilities[style] * sum(
                probabilities[pace] * gaps[cell(style, pace)] for pace in names.PACES)
            for style in names.STYLES
        })
        score = contributions.sum(axis=1, skipna=False).where(known)
        result = pd.concat([forecasts[["race_id", "horse_id"]], probabilities, contributions.where(known), score.rename(names.SCORE)], axis=1)
        return result[list(COLUMNS)]
