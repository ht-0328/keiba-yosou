"""終わった出走ごとに、3つの不利（出遅れ・展開が向かなかった・バイアスと逆）とその程度を出す。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.development_score import AdvantageTable
from yosou.development_score import names as score_names
from yosou.development_score.advantage_table import cell
from yosou.shared.feature import as_numbers
from yosou.track_bias import Positions
from yosou.track_bias import names as bias_names

from . import names
from .early_positions import EarlyPositions
from .handicap_lines import (
    BIAS_LINE,
    BIAS_STEP,
    LATE_START_LINE,
    LATE_START_STEP,
    PACE_LINE,
    PACE_STEP,
    REVIEW_DEGREE,
    HandicapLines,
)
from .result_style import ResultStyle

#: 出力の列。
COLUMNS: tuple[str, ...] = (
    names.RACE_ID, names.RACE_DATE, names.HORSE_ID, names.LATE_START_GAP, names.RESULT_SCORE, names.RESULT_BIAS,
    names.LATE_START_DEGREE, names.PACE_DEGREE, names.BIAS_DEGREE, names.HANDICAPS, names.DEGREE, names.NEXT_RUN,
)


class RunHandicaps:
    """``prepared``（``AdvantageRuns`` の表。表 G の材料と結果のペース・市場から見た3着以内率を持つ出走の表）の行ごとに、

    - 出遅れの量 = 実際の序盤の位置 − 見込みの序盤の位置（近5走の平均）
    - 結果の展開スコア = 表 G［結果の脚質（その走の位置）, 結果のペース］
    - 結果のバイアス = 使う内の傾き × 内らしさ + 使う前の傾き × 結果の前らしさ（4コーナーの位置から）

    を出し、線（``handicap_lines``）で程度（0〜3）に分ける。4着以下の走だけ不利と数える。``table`` は表 G、``used`` はレースごとの
    使う傾き（``race_id`` を index にした ``USED_INNER``・``USED_FRONT``。終わった日の全レースから）。
    不利の種類は程度が 1 以上のものを「・」でつなぎ、程度は3つの最大、次走の扱いは程度が中以上なら「見直す」。
    """

    def __init__(self) -> None:
        self._early = EarlyPositions()
        self._style = ResultStyle()
        self._positions = Positions()
        self._lines = HandicapLines()

    def of(self, prepared: pd.DataFrame, table: AdvantageTable, used: pd.DataFrame) -> pd.DataFrame:
        """列は ``COLUMNS``。行の並びと index は ``prepared`` と同じ。"""
        finish = as_numbers(prepared["finish"])
        early = self._early.of(prepared)
        gap = early["actual"] - early["expected"]
        score = self._result_score(prepared, table)
        bias = self._result_bias(prepared, used)
        degrees = pd.DataFrame({
            names.LATE_START_DEGREE: self._lines.degree(gap, finish, LATE_START_LINE, LATE_START_STEP),
            names.PACE_DEGREE: self._lines.degree(score, finish, PACE_LINE, PACE_STEP),
            names.BIAS_DEGREE: self._lines.degree(bias, finish, BIAS_LINE, BIAS_STEP),
        }, index=prepared.index)
        worst = degrees.max(axis=1)
        kinds = pd.Series([self._kinds(row) for row in degrees.to_numpy()], index=prepared.index, dtype="object")
        return pd.DataFrame({
            names.RACE_ID: prepared["race_id"].astype(str), names.RACE_DATE: prepared["race_date"], names.HORSE_ID: prepared["horse_id"].astype(str),
            names.LATE_START_GAP: gap, names.RESULT_SCORE: score, names.RESULT_BIAS: bias, **{column: degrees[column] for column in degrees},
            names.HANDICAPS: kinds, names.DEGREE: worst, names.NEXT_RUN: np.where(worst >= REVIEW_DEGREE, names.REVIEW, names.NONE),
        }, index=prepared.index)

    def _result_score(self, prepared: pd.DataFrame, table: AdvantageTable) -> pd.Series:
        """表 G を結果の脚質と結果のペースで引く。どちらかが無ければ欠損値。"""
        style, pace = self._style.of(prepared), prepared[score_names.PACE]
        cells = table.cells_for(prepared[score_names.VENUE_CODE], prepared[score_names.SURFACE])
        which = pd.Series([cell(s, p) if isinstance(s, str) and isinstance(p, str) else None for s, p in zip(style, pace)], index=prepared.index)
        values = np.full(len(prepared), np.nan)
        for name in cells.columns:
            rows = (which == name).to_numpy()
            values[rows] = cells[name].to_numpy()[rows]
        return pd.Series(values, index=prepared.index)

    def _result_bias(self, prepared: pd.DataFrame, used: pd.DataFrame) -> pd.Series:
        """使う傾きからいつもの傾き（同じ馬場の全期間の平均）を引いた分を、馬番の位置と結果の4コーナーの位置に掛ける（``BiasCorrection`` と同じ式）。"""
        race_ids = prepared["race_id"].astype(str)
        usual = used.reindex(columns=[bias_names.COURSE_INNER, bias_names.COURSE_FRONT]).fillna(0.0)
        inner_slope = race_ids.map(used[bias_names.USED_INNER] - usual[bias_names.COURSE_INNER]).astype("float64")
        front_slope = race_ids.map(used[bias_names.USED_FRONT] - usual[bias_names.COURSE_FRONT]).astype("float64")
        inner = inner_slope * self._positions.innerness(prepared["horse_no"], prepared["field_size"])
        front = front_slope * self._positions.frontness_of_rank(prepared["corner4"], prepared["field_size"])
        return inner + front

    def _kinds(self, degrees: np.ndarray) -> str:
        return "・".join(kind for kind, degree in zip(names.HANDICAP_KINDS, degrees) if degree >= 1)
