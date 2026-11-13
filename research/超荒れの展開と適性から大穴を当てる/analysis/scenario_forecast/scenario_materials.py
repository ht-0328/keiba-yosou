"""出走の表（``RunnerEnrichment`` の表）から、今のモデルに足す材料（展開・展開の型・その日の馬場の傾向・ハンデ）の列を作る。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

#: 展開の型の列（学ぶときは実際の結果のペース、予想するときは 0・1・2 を入れて3回予測し、予想のペースの確率で混ぜる）。
PACE = "展開の型"
PACE_CODES: dict[str, float] = {"スロー": 0.0, "平均": 1.0, "ハイ": 2.0}
#: 予想のペースの確率の列（混ぜる重みにも使う）。並びは PACE_CODES の 0・1・2 の順。
FORECAST = ("予想_スロー", "予想_平均", "予想_ハイ")
#: 前日と当日で共通の材料（展開・ハンデ）。
COMMON: tuple[str, ...] = (
    PACE, *FORECAST, "位置_先頭", "位置_前", "位置_中", "位置_後ろ", "近5走の位置の平均", "馬番の位置",
    "ハンデ戦か", "トップとの差", "斤量の前走との差", "昇級か", "昇級×斤量の前走との差", "同じ斤量の3着以内", "重い斤量の3着以内",
)
#: 当日だけの材料（その日の先のレースの傾き・馬体重を使う斤量÷馬体重）。
RACE_DAY_ONLY: tuple[str, ...] = ("先のレースの内の傾き", "先のレースの前の傾き", "内の傾き×内寄り", "前の傾き×前寄り", "斤量÷馬体重の差")


@dataclass(frozen=True)
class ScenarioMaterials:
    """``runners`` に展開の予想（``p_*``）・回顧（``pace``）・その日の先のレースの傾き（``prior_inner``・``prior_front``）が
    結ばれている前提で、1行 = 1頭の材料の表（race_id・horse_no と材料の列）を返す。``race_day`` が偽なら当日だけの材料を入れない。"""

    race_day: bool

    def build(self, runners: pd.DataFrame) -> pd.DataFrame:
        frame = runners
        upgrade = (frame["class_change"] == "昇級").astype(float)
        side = (frame["horse_no"] - 1) / (frame["field_size"] - 1).where(frame["field_size"] > 1)
        table = pd.DataFrame({
            "race_id": frame["race_id"].astype(str), "horse_no": frame["horse_no"].astype(float),
            PACE: frame["pace"].map(PACE_CODES).astype(float),
            FORECAST[0]: frame["p_slow"], FORECAST[1]: frame["p_even"], FORECAST[2]: frame["p_high"],
            "位置_先頭": frame["p_leader"], "位置_前": frame["p_front"], "位置_中": frame["p_middle"], "位置_後ろ": frame["p_back"],
            "近5走の位置の平均": frame["expected_position"], "馬番の位置": side,
            "ハンデ戦か": (frame["weight_type"] == "ハンデ").astype(float),
            "トップとの差": frame["carried_vs_top"], "斤量の前走との差": frame["carried_change"], "昇級か": upgrade,
            "昇級×斤量の前走との差": upgrade * frame["carried_change"],
            "同じ斤量の3着以内": frame["same_carried_places"], "重い斤量の3着以内": frame["heavier_places"],
        })
        if self.race_day:
            table["先のレースの内の傾き"] = frame["prior_inner"]
            table["先のレースの前の傾き"] = frame["prior_front"]
            table["内の傾き×内寄り"] = frame["prior_inner"] * (0.5 - side)
            table["前の傾き×前寄り"] = frame["prior_front"] * (0.5 - frame["expected_position"])
            table["斤量÷馬体重の差"] = frame["carried_ratio_vs_mean"]
        return table.astype({column: "float64" for column in table.columns if column != "race_id"})

    @property
    def columns(self) -> tuple[str, ...]:
        return (*COMMON, *RACE_DAY_ONLY) if self.race_day else COMMON

