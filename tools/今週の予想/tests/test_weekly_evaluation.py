"""FeatureLabels（特徴量の分類と名前）と HorseEvaluator（良い点・悪い点・総合）のテスト。値は架空。"""

from __future__ import annotations

import pandas as pd

from 今週の予想.feature_labels import CATEGORIES, RACE_CONDITION, FeatureLabels
from 今週の予想.horse_evaluator import HorseEvaluator


def test_名前から分類を決める() -> None:
    labels = FeatureLabels()
    assert labels.category("指数_前走_順位") == "能力"
    assert labels.category("騎手×調教師_勝率") == "騎手"
    assert labels.category("調教師×距離_3着内率") == "調教師"
    assert labels.category("父×芝ダ_3着内率") == "血統"
    assert labels.category("対戦レーティング") == "相手関係"
    assert labels.category("展開の予想_先頭の確率") == "展開"
    assert labels.category("オッズから見た3着以内率") == "市場の評価"
    assert labels.category("近5走の平均上がり順位") == "位置取り・末脚"
    assert labels.category("distance_m") == RACE_CONDITION
    assert labels.category("クラス") == RACE_CONDITION
    assert set(map(labels.category, ["坂路_直前4F", "body_weight", "frame_no", "course_wins_before"])) <= set(CATEGORIES)


def test_人が読む名前と値() -> None:
    labels = FeatureLabels()
    assert labels.display_name("指数_前走_順位") == "スピード指数・前走（レース内順位）"
    assert labels.display_name("騎手_1年_3着内率") == "騎手・近1年・3着以内率"
    assert labels.display_value("指数_前走_順位", 2.0) == "2位"
    assert labels.display_value("騎手_3着内率", 0.254) == "25.4%"
    assert labels.display_value("指数_前走", float("nan")) == "なし"


def test_良い点と悪い点を分類ごとに足して出す() -> None:
    horse = pd.Series({"probability": 0.5, "rank": 1, "mark": "◎", "mark_reason": "3着以内に入る確率がレース内1位",
                       "market_top3": 0.4, "place_value": 1.1})
    features = pd.Series({"指数_前走": 90.0, "指数_前走_順位": 1.0, "騎手_3着内率": 0.1, "distance_m": 1600.0})
    contributions = pd.Series({"指数_前走": 0.3, "指数_前走_順位": 0.2, "騎手_3着内率": -0.4, "distance_m": 1.0})
    result = HorseEvaluator().evaluate(horse, features, contributions)
    assert [point["category"] for point in result["good"]] == ["能力"]
    assert [point["category"] for point in result["bad"]] == ["騎手"]
    # 確率 0.5 の馬のロジットが 0.5 上がると、確率はおよそ 0.25 × 0.5 = 12.5 ポイント上がる
    assert result["good"][0]["effect"] == 12.5
    assert result["good"][0]["details"][0]["name"] == "スピード指数・前走"
    # レースの条件は良い点・悪い点に出さない
    assert all(point["category"] != RACE_CONDITION for point in result["categories"])
    assert "10.0ポイント高く" in result["summary"] and "「能力」" in result["summary"] and "→ ◎" in result["summary"]
