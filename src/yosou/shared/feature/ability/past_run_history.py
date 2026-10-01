"""過去走（着順・着差・位置取り・末脚・相手の強さ・ペース）から、列を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .ability_columns import PER_RUN_VALUES

#: 見る過去走の数。
_RUNS = 5
#: 休み明けとみなす前走からの日数。
_LAYOFF_DAYS = 70
#: 数にそろえる列。
_NUMERIC = ["finish", "field_size", "time_diff", "first_corner_rank", "corner4", "last3f_rank", "last3f_count",
            "class_order", "carried", "interval_days", "body_weight"]


class PastRunHistory:
    """出走の各行に、その馬の「今回より前の走」だけから作った列を付ける。

    走ごとに先に次の値を作り、近 5走について前走・平均・最良を取る。
    - 相対着順: (着順 − 1) ÷ (頭数 − 1)。0 が1着、1 が最下位
    - 着差: 勝ち馬とのタイム差（秒。−3〜5 に丸める）
    - 序盤の位置: 最初のコーナーの順位 ÷ 頭数（0 に近いほど前）。4角の位置: 4コーナーの順位 ÷ 頭数
    - 末脚: 上がり3F のレース内順位 ÷ 上がりのある頭数（0 に近いほど速い）
    - 先頭: 最初のコーナーで先頭だったか。相手の強さ: そのレースの強さ（``RaceStrength``）
    - ペース: そのレースの前半の速さ（``RacePace``）。展開の不利: スローで後ろにいた・ハイで前にいた
    - 末脚と着順のずれ: 相対着順 − 末脚（末脚のわりに着順が悪いと正）
    ``runs`` は出走した馬の行。列は race_id・horse_id と ``PAST_RUN_COLUMNS``（ability_columns.py）。
    """

    def build(self, runs: pd.DataFrame, strength: pd.Series, pace: pd.Series) -> pd.DataFrame:
        per_run = self._per_run(runs, strength, pace)
        grouped = per_run.groupby("horse_id", sort=False)
        lags = {name: np.column_stack([grouped[name].shift(k).to_numpy(dtype=float) for k in range(1, _RUNS + 1)])
                for name in PER_RUN_VALUES}
        result = pd.DataFrame({"race_id": per_run["race_id"], "horse_id": per_run["horse_id"]})
        for name, values in lags.items():
            result[f"{name}_前走"] = values[:, 0]
            result[f"{name}_近5走の平均"] = self._nan_mean(values)
        result["相対着順_近5走の最良"] = self._nan_min(lags["相対着順"])
        result["着差_近5走の最良"] = self._nan_min(lags["着差"])
        result["先頭率_近5走"] = self._nan_mean(lags["先頭"])
        result["クラス_前走との差"] = per_run["class_order"] - grouped["class_order"].shift(1)
        result["斤量_前走との差"] = per_run["carried"] - grouped["carried"].shift(1)
        result["騎手_前走と同じ"] = (per_run["jockey_code"] == grouped["jockey_code"].shift(1)).astype(float)
        result["芝ダ替わり"] = (per_run["surface"] != grouped["surface"].shift(1)).astype(float)
        result["休み明け_2走目"] = (grouped["interval_days"].shift(1) >= _LAYOFF_DAYS).astype(float)
        weights = np.column_stack([grouped["body_weight"].shift(k).to_numpy(dtype=float) for k in range(1, _RUNS + 1)])
        result["体重_近走の平均との差"] = per_run["body_weight"].to_numpy(dtype=float) - self._nan_mean(weights)
        return result

    def _per_run(self, runs: pd.DataFrame, strength: pd.Series, pace: pd.Series) -> pd.DataFrame:
        per_run = runs.sort_values(["horse_id", "race_date", "race_id"]).reset_index(drop=True)
        per_run[_NUMERIC] = per_run[_NUMERIC].apply(lambda column: pd.to_numeric(column, errors="coerce")).astype(float)
        field = per_run["field_size"]
        per_run["相対着順"] = (per_run["finish"] - 1) / (field - 1).where(field > 1)
        per_run["着差"] = per_run["time_diff"].astype(float).clip(-3, 5)
        per_run["序盤の位置"] = per_run["first_corner_rank"] / field
        per_run["4角の位置"] = per_run["corner4"] / field
        per_run["末脚"] = per_run["last3f_rank"] / per_run["last3f_count"].where(per_run["last3f_count"] > 0)
        per_run["先頭"] = (per_run["first_corner_rank"] == 1).astype(float).where(per_run["first_corner_rank"].notna())
        per_run["相手の強さ"] = per_run["race_id"].map(strength)
        per_run["ペース"] = per_run["race_id"].map(pace)
        # 展開の不利: スローで後ろにいた（+1）、ハイで前にいた（+1）。どちらでもなければ 0。
        slow_back = (per_run["ペース"] < -0.5) & (per_run["序盤の位置"] > 0.5)
        fast_front = (per_run["ペース"] > 0.5) & (per_run["序盤の位置"] < 0.3)
        per_run["展開の不利"] = (slow_back | fast_front).astype(float).where(per_run["ペース"].notna())
        per_run["末脚と着順のずれ"] = per_run["相対着順"] - per_run["末脚"]
        return per_run

    def _nan_mean(self, values: np.ndarray) -> np.ndarray:
        """行ごとの欠損値を除いた平均。全部欠損値の行は欠損値（警告を出さない）。"""
        counts = np.isfinite(values).sum(axis=1)
        return np.where(counts > 0, np.nansum(values, axis=1) / np.maximum(counts, 1), np.nan)

    def _nan_min(self, values: np.ndarray) -> np.ndarray:
        """行ごとの欠損値を除いた最小。全部欠損値の行は欠損値。"""
        filled = np.where(np.isfinite(values), values, np.inf)
        smallest = filled.min(axis=1)
        return np.where(np.isfinite(smallest), smallest, np.nan)
