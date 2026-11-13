"""結果のペース・その日のバイアスの傾き（回顧の表2）と、展開の予想（ペースの確率・位置の確率）を出走の表に結ぶ。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

#: ペースの速さの順。
PACE_ORDER = {"スロー": 0, "平均": 1, "ハイ": 2}
#: 予想のペースの区分（ハイかスローの確率がこれ以上なら、その予想とみなす）。
FORECAST_LINE = 0.45
#: 位置の見込みの区分（前・後ろの確率がこれ以上なら、その見込みとみなす）。
PLACE_LINE = 0.5


@dataclass(frozen=True)
class PaceAttachment:
    """``reviews``（race_id・pace・tilt_inner・tilt_front）、``race_forecasts``（race_id・p_slow・p_even・p_high）、
    ``horse_forecasts``（race_id・horse_id・p_leader・p_front・p_middle・p_back）を結び、次の列を足す。

    - ``forecast_pace``: 予想のペースの確率がいちばん大きい区分（予測の無いレースは欠損値）
    - ``forecast_band``: ハイの確率が 0.45 以上なら「ハイ予想」、スローが 0.45 以上なら「スロー予想」、ほかは「平均予想」、予測が無ければ「予測なし」
    - ``pace_vs_forecast``: 結果のペースが予想と同じなら「予想どおり」、速ければ「予想より速い」、遅ければ「予想より遅い」
    - ``expected_place``: 前3分の1（先頭を含む）の確率 0.5 以上で「前の見込み」、後ろ3分の1の確率 0.5 以上で「後ろの見込み」、ほかは「中の見込み」、予測が無ければ「予測なし」
    """

    def add(self, runners: pd.DataFrame, reviews: pd.DataFrame, race_forecasts: pd.DataFrame,
            horse_forecasts: pd.DataFrame) -> pd.DataFrame:
        frame = runners.merge(reviews, on="race_id", how="left").merge(race_forecasts, on="race_id", how="left")
        frame = frame.merge(horse_forecasts, on=["race_id", "horse_id"], how="left")
        shares = frame[["p_slow", "p_even", "p_high"]]
        known = shares.notna().all(axis=1).to_numpy()
        labels = np.array(["スロー", "平均", "ハイ"], dtype=object)
        best = labels[np.nan_to_num(shares.to_numpy(), nan=-1.0).argmax(axis=1)]
        frame["forecast_pace"] = pd.Series(np.where(known, best, None), index=frame.index, dtype="object")
        frame["forecast_band"] = np.select(
            [~known, (frame["p_high"] >= FORECAST_LINE).to_numpy(), (frame["p_slow"] >= FORECAST_LINE).to_numpy()],
            ["予測なし", "ハイ予想", "スロー予想"], default="平均予想")
        frame["pace_vs_forecast"] = self._versus(frame["pace"], frame["forecast_pace"])
        has_place = frame["p_front"].notna().to_numpy()
        frame["expected_place"] = np.select(
            [~has_place, (frame["p_front"] >= PLACE_LINE).to_numpy(), (frame["p_back"] >= PLACE_LINE).to_numpy()],
            ["予測なし", "前の見込み", "後ろの見込み"], default="中の見込み")
        return frame

    @staticmethod
    def _versus(result: pd.Series, forecast: pd.Series) -> pd.Series:
        difference = result.map(PACE_ORDER) - forecast.map(PACE_ORDER)
        known = difference.notna().to_numpy()
        conditions = [known & (difference == 0).to_numpy(), known & (difference > 0).to_numpy(), known]
        values = np.select(conditions, ["予想どおり", "予想より速い", "予想より遅い"], default=None)
        return pd.Series(values, index=result.index, dtype="object")
