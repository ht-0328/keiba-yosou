"""1頭の予想の理由（良い点・悪い点・総合）を、人が読む形にする。"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from 今週の予想.feature_labels import CATEGORIES, RACE_CONDITION, FeatureLabels
from 今週の予想.forecast_columns import (
    DANGER_SCORE,
    FAVORITE_BAND,
    IS_DANGER,
    MARK,
    MARK_REASON,
    MARKET_TOP3,
    PLACE_VALUE,
    PROBABILITY,
    RANK,
)

#: 良い点・悪い点に出す分類の数（それぞれ）。
POINTS_SHOWN = 3
#: 分類の中で、根拠として並べる特徴量の数。
DETAILS_SHOWN = 2
#: 良い点・悪い点に出す、ロジットの上げ下げの下限。これより小さい分類は、効いていないとみなして出さない。
#: 確率の動き（ポイント）で線を引くと、確率の低い馬はどの分類も線に届かないので、ロジットで引く。
MIN_EFFECT_LOGIT = 0.05
#: 印ごとの役割（設計書「買うレースと買い目を決める」07 の 5）。
MARK_ROLES: dict[str, str] = {
    "◎": "軸（安心な馬。ワイド・3連複の軸）", "○": "相手", "▲": "相手", "△": "相手（3連複の3列目）",
    "☆": "美味しい穴馬（複勝で買う候補）", "注": "表示だけ（ワイドの相手の候補）", "消": "買わない（危険な人気馬もここ）",
}


class HorseEvaluator:
    """1頭の、特徴量ごとの寄与（ロジットの上げ下げ）を分類ごとに足して、良い点・悪い点・総合の文にする。

    寄与は、確率の動き（ポイント）に直して見せる。確率 p の馬のロジットが x 動くと、確率はおよそ p(1−p)・x 動く。
    「レースの条件」（距離・頭数など全馬に同じ値のもの）は、馬どうしの比べにならないので、良い点・悪い点に出さない。
    前日・当日のモデルは市場の見立て（オッズから見た3着以内率）を出発点にしているので、寄与は「市場の見立てからの上げ下げ」になる。
    """

    def __init__(self, labels: FeatureLabels | None = None) -> None:
        self._labels = labels or FeatureLabels()

    def evaluate(self, horse: pd.Series, features: pd.Series, contributions: pd.Series) -> dict[str, Any]:
        """``horse`` は印を付けた表の1行、``features`` はその馬の特徴量の値、``contributions`` はその馬の寄与。

        戻り値は ``good``（良い点）・``bad``（悪い点）・``categories``（分類ごとの動き。画面のグラフ用）・``summary``（総合の文）・``role``（印の役割）。
        """
        scale = _slope(horse[PROBABILITY])
        points = self._category_points(features, contributions, scale)
        good = [point for point in points if point["logit"] >= MIN_EFFECT_LOGIT][:POINTS_SHOWN]
        bad = sorted((point for point in points if point["logit"] <= -MIN_EFFECT_LOGIT), key=lambda p: p["logit"])[:POINTS_SHOWN]
        return {
            "good": good, "bad": bad,
            "categories": [{"category": point["category"], "effect": point["effect"], "logit": point["logit"]} for point in points],
            "summary": self._summary(horse, good, bad), "role": MARK_ROLES.get(horse[MARK], ""),
        }

    def _category_points(self, features: pd.Series, contributions: pd.Series, scale: float) -> list[dict[str, Any]]:
        """分類ごとの上げ下げ（``logit``）と確率の動き（``effect``。ポイント）と根拠の特徴量。上げ下げの大きい順（正の大きい順）。"""
        logits = contributions.astype(float).rename("logit")
        frame = logits.to_frame().assign(category=[self._labels.category(name) for name in logits.index])
        frame = frame[frame["category"] != RACE_CONDITION]
        points = []
        for category in CATEGORIES:
            members = frame[frame["category"] == category]["logit"]
            if members.empty:
                continue
            total = float(members.sum())
            same_side = members[members > 0] if total >= 0 else members[members < 0]
            top = same_side.abs().sort_values(ascending=False).index[:DETAILS_SHOWN]
            details = [{"name": self._labels.display_name(name), "value": self._labels.display_value(name, _plain(features.get(name))),
                        "effect": round(float(members[name]) * scale * 100, 2)} for name in top]
            points.append({"category": category, "logit": round(total, 3), "effect": round(total * scale * 100, 2), "details": details})
        return sorted(points, key=lambda point: point["logit"], reverse=True)

    def _summary(self, horse: pd.Series, good: list[dict[str, Any]], bad: list[dict[str, Any]]) -> str:
        """総合の文: 確率と順位 → 市場の見立てとの差 → 効いた分類 → 印とその理由。"""
        parts = [f"3着以内に入る確率は {horse[PROBABILITY]:.1%}（レース内{horse[RANK]:.0f}位）。"]
        market = horse.get(MARKET_TOP3)
        if market is not None and pd.notna(market):
            difference = (horse[PROBABILITY] - market) * 100
            side = "高く" if difference >= 0 else "低く"
            parts.append(f"市場の見立て（オッズから見た3着以内率）{market:.1%} より {abs(difference):.1f}ポイント{side}見ている。")
        value = horse.get(PLACE_VALUE)
        if value is not None and pd.notna(value):
            parts.append(f"複勝の期待値は {value:.2f}。")
        if good:
            parts.append("押し上げたのは" + "・".join(f"「{point['category']}」" for point in good) + "。")
        if bad:
            parts.append("割り引いたのは" + "・".join(f"「{point['category']}」" for point in bad) + "。")
        score = horse.get(DANGER_SCORE)
        if score is not None and pd.notna(score) and not bool(horse.get(IS_DANGER)):
            parts.append(f"人気馬の予想の危険度は {score * 100:+.1f}ポイント（{horse[FAVORITE_BAND]}。"
                         "危険の判定を印に使うのは1番人気だけなので、参考）。")
        parts.append(f"→ {horse[MARK]}（{MARK_ROLES.get(horse[MARK], '')}）: {horse[MARK_REASON]}。")
        return "".join(parts)


def _slope(probability: float) -> float:
    """ロジットが 1 動いたときの確率の動き（p(1−p)）。"""
    p = min(max(float(probability), 1e-6), 1 - 1e-6)
    return p * (1 - p)


def _plain(value: Any) -> Any:
    """numpy の数を Python の数にする（表示と JSON のため）。"""
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value
