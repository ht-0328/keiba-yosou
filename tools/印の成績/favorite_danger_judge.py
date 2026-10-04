"""7つの区切りの人気馬の予想から、テスト期間の危険な人気馬を判定する。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.favorites_out_of_top3.danger import DangerThreshold
from yosou.shared.feature.odds import TOP3_RATE

from 今週の予想.danger_picker import MARKED_BANDS, DangerPicker

from 印の成績.prediction_file import TEST, VALID

#: 結果の列（今週の予想の ``forecast_columns`` の危険の列と同じ名前）と、印に使うかによらず危険度が線以上か（``over_line``）。
COLUMNS: tuple[str, ...] = (
    "race_id", "horse_id", "favorite_band", "out_probability", "market_out", "danger_score", "danger_line", "is_danger",
    "over_line",
)


class FavoriteDangerJudge:
    """人気馬の予想（4着以下になる確率）の7つの区切りの予測から、テスト期間の危険な人気馬を判定する（今週の予想と同じ決め方）。

    危険度 = 4着以下になる確率 − 市場から見た4着以下の確率（1 − オッズから見た3着以内率）。線は区切りごと・人気帯ごとに、
    その区切りの検証期間で ``DangerThreshold.choose_for``（本番の学習と同じ選び方）で決め直す。テスト期間の結果は線に使わない。
    消にする馬（``is_danger``）は、今週の予想と同じ ``DangerPicker`` が1レース1頭だけ選ぶ。``bands`` は消にできる人気帯
    （既定は今週の予想と同じ ``MARKED_BANDS``）。どの人気帯も、危険度が線以上か（``over_line``）は残す（人気帯ごとの成績の表に使う）。
    """

    def __init__(self, bands: tuple[str, ...] = MARKED_BANDS) -> None:
        self._picker = DangerPicker(tuple(bands))

    def judge(self, predictions: pd.DataFrame, places: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, dict[str, float]]]:
        """``predictions`` は人気馬の予想の全部の行（``PredictionFile.load``）、``places`` は出走の行に着順とオッズから見た3着以内率
        （列 race_id・horse_id・finish・``TOP3_RATE``）を付けた表。

        戻り値は（テスト期間の人気馬の判定。列は ``COLUMNS``、区切り → 人気帯 → 線）。
        """
        rows = predictions.merge(places[["race_id", "horse_id", "finish", TOP3_RATE]], on=["race_id", "horse_id"], how="inner")
        rows = rows.assign(market_out=1 - rows[TOP3_RATE], lost=(~(rows["finish"] <= 3)).astype(float))
        rows["danger_score"] = rows["probability"] - rows["market_out"]
        parts, lines = [], {}
        for (fold, band), group in rows.groupby(["fold", "segment"], sort=True):
            valid = group[group["period"] == VALID]
            line = (DangerThreshold().choose_for(band, valid["danger_score"], valid["lost"], valid["market_out"]) if len(valid)
                    else np.nan)
            lines.setdefault(fold, {})[band] = line
            test = group[group["period"] == TEST]
            over = (test["danger_score"] >= line) if not np.isnan(line) else False
            parts.append(test.assign(favorite_band=band, out_probability=test["probability"], danger_line=line, over_line=over))
        if not parts:
            return pd.DataFrame(columns=list(COLUMNS)), lines
        judged = pd.concat(parts, ignore_index=True)
        judged["is_danger"] = self._picked(judged)
        return judged[list(COLUMNS)], lines

    def _picked(self, judged: pd.DataFrame) -> pd.Series:
        """レースごとに、消にする危険な人気馬を1頭だけ選ぶ（``DangerPicker``）。"""
        picked = [self._picker.pick(race["favorite_band"], race["danger_score"], race["danger_line"])
                  for _, race in judged.groupby("race_id", sort=False)]
        return pd.concat(picked).reindex(judged.index, fill_value=False).astype(bool)
