"""事実表の過去走（着順・着差・位置取り・末脚・相手の強さ）から、特徴量を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 見る過去走の数。
_RUNS = 5


class PastRunFeatures:
    """事実表（1行 = 1頭の出走）の各行に、その馬の「今回より前の走」だけから作った特徴量を付ける。

    走ごとに先に次の値を作り、近 5走について前走・平均・最良を取る。
    - 相対着順: (着順 − 1) ÷ (頭数 − 1)。0 が1着、1 が最下位
    - 着差: 勝ち馬とのタイム差（秒。勝っていれば負）
    - 序盤の位置: 最初のコーナーの順位 ÷ 頭数（0 に近いほど前）
    - 4角の位置: 4コーナーの順位 ÷ 頭数
    - 末脚: 上がり3F のレース内順位 ÷ 上がりのある頭数（0 に近いほど速い）
    - 先頭: 最初のコーナーで先頭だったか
    - 相手の強さ: そのレースの出走馬の「そのレースの時点の力」（``race_strength``）の上位5頭の平均
    ``race_strength`` は rid → 値。無ければ相手の強さの特徴量は作らない。
    """

    def build(self, facts: pd.DataFrame, race_strength: pd.Series | None = None) -> pd.DataFrame:
        runs = self._per_run(facts, race_strength)
        grouped = runs.groupby("horse_id", sort=False)
        columns = [c for c in ("相対着順", "着差", "序盤の位置", "4角の位置", "末脚", "先頭", "相手の強さ",
                               "ペース", "展開の不利", "末脚と着順のずれ") if c in runs.columns]
        lags = {c: np.column_stack([grouped[c].shift(k).to_numpy(dtype=float) for k in range(1, _RUNS + 1)])
                for c in columns}
        result = pd.DataFrame({"race_id": runs["race_id"], "horse_no": runs["horse_no"]})
        for name, values in lags.items():
            result[f"{name}_前走"] = values[:, 0]
            result[f"{name}_近5走の平均"] = np.nanmean(values, axis=1)
        result["相対着順_近5走の最良"] = np.nanmin(lags["相対着順"], axis=1)
        result["着差_近5走の最良"] = np.nanmin(lags["着差"], axis=1)
        result["先頭率_近5走"] = np.nanmean(lags["先頭"], axis=1)
        result["クラス_前走との差"] = runs["class_order"] - grouped["class_order"].shift(1)
        result["斤量_前走との差"] = runs["carried"] - grouped["carried"].shift(1)
        result["騎手_前走と同じ"] = (runs["jockey_code"] == grouped["jockey_code"].shift(1)).astype(float)
        result["芝ダ替わり"] = (runs["surface"] != grouped["surface"].shift(1)).astype(float)
        result["休み明け_2走目"] = (grouped["interval_days"].shift(1) >= 70).astype(float)
        weights = np.column_stack([grouped["body_weight"].shift(k).to_numpy(dtype=float) for k in range(1, _RUNS + 1)])
        result["体重_近走の平均との差"] = runs["body_weight"].to_numpy(dtype=float) - np.nanmean(weights, axis=1)
        return result

    def _per_run(self, facts: pd.DataFrame, race_strength: pd.Series | None) -> pd.DataFrame:
        runs = facts[facts["ran"]].sort_values(["horse_id", "race_date", "race_id"]).reset_index(drop=True)
        numeric = ["finish", "field_size", "time_diff", "first_corner_rank", "corner4", "last3f_rank",
                   "last3f_count", "class_order", "carried", "interval_days", "body_weight", "first3f"]
        runs[numeric] = runs[numeric].apply(lambda column: pd.to_numeric(column, errors="coerce")).astype(float)
        field = runs["field_size"]
        runs["相対着順"] = (runs["finish"] - 1) / (field - 1).where(field > 1)
        runs["着差"] = runs["time_diff"].clip(-3, 5)
        runs["序盤の位置"] = runs["first_corner_rank"] / field
        runs["4角の位置"] = runs["corner4"] / field
        runs["末脚"] = runs["last3f_rank"] / runs["last3f_count"].where(runs["last3f_count"] > 0)
        runs["先頭"] = (runs["first_corner_rank"] == 1).astype(float).where(runs["first_corner_rank"].notna())
        if race_strength is not None:
            runs["相手の強さ"] = runs["race_id"].map(race_strength)
        runs["ペース"] = runs["race_id"].map(self._race_pace(runs))
        # 展開の不利: スローで後ろにいた（+1）、ハイで前にいた（+1）。どちらでもなければ 0。
        slow_back = (runs["ペース"] < -0.5) & (runs["序盤の位置"] > 0.5)
        fast_front = (runs["ペース"] > 0.5) & (runs["序盤の位置"] < 0.3)
        runs["展開の不利"] = (slow_back | fast_front).astype(float).where(runs["ペース"].notna())
        runs["末脚と着順のずれ"] = runs["相対着順"] - runs["末脚"]
        return runs

    def _race_pace(self, runs: pd.DataFrame) -> pd.Series:
        """レースの前半の速さ: 前3F を、同じ競馬場・芝ダ・距離・馬場状態のそれより前のレースの平均と標準偏差で z にする。

        正ならハイ、負ならスロー。基準は、そのレースより前のレースだけで作る（後のレースを使わない）。
        """
        races = runs.drop_duplicates("race_id")[["race_id", "race_date", "venue_code", "surface", "distance_m",
                                                  "condition", "first3f"]].sort_values("race_date")
        grouped = races.groupby(["venue_code", "surface", "distance_m", "condition"], sort=False)["first3f"]
        count = grouped.cumcount()
        mean = (grouped.cumsum() - races["first3f"]) / count.where(count > 0)
        square = (races["first3f"] ** 2).groupby([races[c] for c in ("venue_code", "surface", "distance_m",
                                                                      "condition")]).cumsum() - races["first3f"] ** 2
        std = np.sqrt((square / count.where(count > 0) - mean ** 2).clip(lower=1e-6))
        pace = -(races["first3f"] - mean) / std
        return pd.Series(pace.where(count >= 20).to_numpy(), index=races["race_id"])
