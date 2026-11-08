"""出走の表に、人気から見た差・集まり方の表で使う切り口の列（帯や区分）を足す。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..tables.race_cuts import distance_band

#: 斤量 ÷ 馬体重 のレースの中の差を5つに分ける名前（全部の出走を小さい順に並べて5等分。同じ値は並びの順で分ける。重い = 体の大きさに対して斤量が重い）。
RATIO_LABELS = ["1 いちばん軽い", "2", "3", "4", "5 いちばん重い"]
STYLES = ("逃げ", "先行", "差し", "追込")


@dataclass(frozen=True)
class RunnerCuts:
    """``RunnerEnrichment`` の表に、次の切り口の列を足す（列名は日本語の見出しのまま）。"""

    def add(self, runners: pd.DataFrame) -> pd.DataFrame:
        frame = runners.copy()
        frame["平均との差"] = pd.cut(frame["carried_vs_mean"], [-20, -2.5, -1.5, -0.5, 0.5, 1.5, 20],
                                 labels=["−3kg以下", "−2kg", "−1kg", "±0", "+1kg", "+2kg以上"])
        frame["トップとの差"] = pd.cut(frame["carried_vs_top"], [-20, -5.5, -3.5, -1.5, -0.5, 0.5],
                                  labels=["−6kg以下", "−4〜−5kg", "−2〜−3kg", "−1kg", "トップ"])
        frame["斤量÷馬体重"] = pd.qcut(frame["carried_ratio_vs_mean"].rank(method="first"), 5, labels=RATIO_LABELS)
        frame["前走との差"] = pd.cut(frame["carried_change"], [-20, -2.5, -0.5, 0.5, 2.5, 20],
                                 labels=["−3kg以上軽く", "−1〜−2kg", "同じ", "+1〜+2kg", "+3kg以上重く"])
        frame["前走との差（3つ）"] = np.select([frame["carried_change"] <= -1, frame["carried_change"] >= 1, frame["carried_change"].notna()],
                                       ["軽くなった", "重くなった", "同じ"], default="前走なし")
        frame["斤量の軽さ"] = np.select([frame["carried_vs_mean"] <= -1, frame["carried_vs_mean"] >= 1], ["軽い（平均−1kg以下）", "重い（平均+1kg以上）"],
                                   default="平均並み")
        frame["減量騎手"] = frame["apprentice"].fillna("不明")
        frame["推定脚質"] = frame["style_before"].where(frame["style_before"].isin(STYLES), "不明")
        frame["推定脚質（前後）"] = frame["推定脚質"].map({"逃げ": "前（逃げ・先行）", "先行": "前（逃げ・先行）", "差し": "後ろ（差し・追込）",
                                                 "追込": "後ろ（差し・追込）"}).fillna("不明")
        frame["距離"] = distance_band(frame["distance_m"])
        frame["馬場"] = np.where(frame["condition"] == "良", "良", "道悪（稍重〜不良）")
        frame["人気"] = pd.cut(frame["popularity"], [0, 1, 3, 5, 9, 18], labels=["1番人気", "2〜3番人気", "4〜5番人気", "6〜9番人気",
                                                                              "10番人気以下"])
        frame["トップハンデか"] = np.where(frame["carried_vs_top"] == 0, "トップ", "トップ以外")
        frame["クラスの替わり"] = frame["class_change"].fillna("不明")
        frame["コースの実績"] = np.where(frame["course_places_before"] > 0, "同じコースで3着以内あり", "なし")
        frame["同じ斤量の実績"] = np.where(frame["same_carried_places"] > 0, "同じ斤量で3着以内あり", "なし")
        frame["重い斤量の実績"] = np.where(frame["heavier_places"] > 0, "今回より重い斤量で3着以内あり", "なし")
        frame["結果のペース"] = frame["pace"].fillna("（不明）")
        frame["予想のペース"] = frame["forecast_band"]
        frame["位置の見込み"] = frame["expected_place"]
        frame["結果の脚質"] = frame["result_style"].fillna("（不明）")
        frame["いつもとの位置の差"] = frame["position_shift"].fillna("（近走なし）")
        frame["枠の側"] = frame["horse_side"]
        frame["その日の内外の傾き"] = pd.cut(frame["tilt_inner"], [-9, -0.1, 0.1, 9], labels=["外が来ている", "平ら", "内が来ている"])
        frame["重量種別"] = frame["weight_type"]
        frame["ハンデ戦か"] = frame["handicap"]
        frame["期間"] = frame["period"]
        return frame
