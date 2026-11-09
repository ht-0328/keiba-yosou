"""人気馬の「4着以下になる確率」の予測から、人気帯ごとの固定の線で危険な人気馬を判定する。"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from yosou.shared.feature.odds import TOP3_RATE

from 今週の予想.danger_picker import MARKED_BANDS

from 印の成績.favorite_danger_judge import COLUMNS
from 印の成績.prediction_file import ODDS_ONLY_OUT, TEST

#: いちばん優先する人気帯（``DangerPicker`` と同じ。この人気帯の馬が線以上なら、その馬だけを消にする）。
_FIRST_BAND = MARKED_BANDS[0]


class FixedLineDangerJudge:
    """人気馬の「4着以下になる確率」の7つの区切りの予測から、テスト期間の危険な人気馬を、人気帯ごとの**固定の線**で判定する。

    ``FavoriteDangerJudge`` は区切りごとに検証期間で線を決め直すが、こちらは渡された線（人気帯 → 危険度の線。今週の予想が使う
    ``danger_thresholds.json`` と同じ形）をどの区切りにも当てる。今週の予想と同じ線で過去のレースの印の成績を数えるのに使う。

    危険度 = 4着以下になる確率 − 市場から見た4着以下の確率（1 − オッズから見た3着以内率。予測にオッズだけのモデルの確率
    ``ODDS_ONLY_OUT`` があれば、それ）。線の無い人気帯は危険と判定しない。消にする馬（``is_danger``）は ``DangerPicker`` と同じ決まりで
    1レース1頭（1番人気が線以上ならその馬、そうでなければ ``bands`` のほかの人気帯で線をいちばん大きく超えた馬）。
    どの人気帯も、危険度が線以上か（``over_line``）は残す。戻り値の形は ``FavoriteDangerJudge.judge`` と同じ（区切りごとの線は、どの区切りも同じ値）。
    """

    def __init__(self, lines: Mapping[str, float], bands: tuple[str, ...] = MARKED_BANDS) -> None:
        self._lines = {band: float(line) for band, line in lines.items() if line is not None and not np.isnan(float(line))}
        self._bands = tuple(bands)

    @property
    def lines(self) -> dict[str, float]:
        """人気帯 → 線（線の無い人気帯は入らない）。"""
        return dict(self._lines)

    def judge(self, predictions: pd.DataFrame, places: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, dict[str, float]]]:
        """``predictions`` は人気馬の予想の全部の行（``PredictionFile.load``）、``places`` は出走の行に着順とオッズから見た3着以内率
        （列 race_id・horse_id・finish・``TOP3_RATE``）を付けた表。戻り値は（テスト期間の判定。列は ``COLUMNS``、区切り → 人気帯 → 線）。"""
        tests = predictions[predictions["period"] == TEST]
        rows = tests.merge(places[["race_id", "horse_id", "finish", TOP3_RATE]], on=["race_id", "horse_id"], how="inner")
        market_out = rows[ODDS_ONLY_OUT] if ODDS_ONLY_OUT in rows.columns else 1 - rows[TOP3_RATE]
        judged = rows.assign(favorite_band=rows["segment"].astype(str), out_probability=rows["probability"], market_out=market_out)
        judged["danger_score"] = judged["out_probability"] - judged["market_out"]
        judged["danger_line"] = judged["favorite_band"].map(self._lines).astype(float)
        with np.errstate(invalid="ignore"):
            judged["over_line"] = (judged["danger_score"] >= judged["danger_line"]).fillna(False).astype(bool)
        judged["is_danger"] = self._picked(judged)
        lines = {fold: dict(self._lines) for fold in sorted(tests["fold"].astype(str).unique())}
        return judged[list(COLUMNS)].reset_index(drop=True), lines

    def _picked(self, judged: pd.DataFrame) -> pd.Series:
        """レースごとに消にする馬を1頭だけ選ぶ（``DangerPicker`` と同じ決まりを、全レースまとめて当てる）。"""
        margin = (judged["danger_score"] - judged["danger_line"]).where(judged["favorite_band"].isin(self._bands))
        over = judged[margin >= 0].assign(margin=margin[margin >= 0])
        first = over[over["favorite_band"] == _FIRST_BAND].drop_duplicates("race_id")
        rest = over[~over["race_id"].isin(first["race_id"])]
        best = rest.sort_values("margin", ascending=False, kind="mergesort").drop_duplicates("race_id")
        chosen = pd.Series(False, index=judged.index)
        chosen[first.index] = True
        chosen[best.index] = True
        return chosen
