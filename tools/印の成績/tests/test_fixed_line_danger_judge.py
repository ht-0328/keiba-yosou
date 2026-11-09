"""FixedLineDangerJudge（人気帯ごとの固定の線で危険な人気馬を判定する）のテスト。値は架空。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from yosou.shared.feature.odds import TOP3_RATE

from 印の成績.favorite_danger_judge import COLUMNS, FavoriteDangerJudge
from 印の成績.fixed_line_danger_judge import FixedLineDangerJudge


def _predictions(rows: list[tuple[str, str, str, float]]) -> pd.DataFrame:
    """（レース, 馬, 人気帯, 4着以下の確率）の行。全部テスト期間・同じ区切り。"""
    return pd.DataFrame([{"race_id": race, "race_date": pd.Timestamp("2025-01-05"), "horse_id": horse, "horse_no": 1, "probability": p,
                          "fold": "2025年前半", "period": "テスト", "segment": band} for race, horse, band, p in rows])


def _places(rows: list[tuple[str, str, int, float]]) -> pd.DataFrame:
    """（レース, 馬, 着順, オッズから見た3着以内率）の行。"""
    return pd.DataFrame([{"race_id": race, "horse_id": horse, "finish": finish, TOP3_RATE: rate} for race, horse, finish, rate in rows])


def test_固定の線で危険度を判定し_消は1レース1頭で1番人気を優先する() -> None:
    predictions = _predictions([("R1", "a", "1番人気", 0.52), ("R1", "b", "2〜3番人気", 0.70), ("R1", "c", "2〜3番人気", 0.40),
                                ("R2", "d", "1番人気", 0.30), ("R2", "e", "2〜3番人気", 0.60), ("R2", "f", "4〜5番人気", 0.80)])
    places = _places([("R1", "a", 1, 0.60), ("R1", "b", 4, 0.50), ("R1", "c", 2, 0.50),
                      ("R2", "d", 1, 0.70), ("R2", "e", 5, 0.50), ("R2", "f", 6, 0.30)])
    dangers, lines = FixedLineDangerJudge({"1番人気": 0.10, "2〜3番人気": 0.05}).judge(predictions, places)
    assert list(dangers.columns) == list(COLUMNS)
    judged = dangers.set_index("horse_id")
    # 危険度 = 4着以下の確率 − (1 − オッズから見た3着以内率)。a は 0.52 − 0.40 = 0.12 で1番人気の線以上 → R1 は a だけが消
    assert judged.loc["a", "danger_score"] == pytest.approx(0.12) and judged.loc["a", "danger_line"] == 0.10
    assert judged.loc["a", "is_danger"] and not judged.loc["b", "is_danger"]   # b（0.20 ≥ 0.05）は線以上だが、1番人気を優先
    assert judged.loc["b", "over_line"] and not judged.loc["c", "over_line"]
    # R2 は1番人気 d（0.30 − 0.30 = 0）が線未満。e（0.10）は線以上、f は 4〜5番人気の線が無いので判定しない → e が消
    assert not judged.loc["d", "is_danger"] and judged.loc["e", "is_danger"] and not judged.loc["f", "is_danger"]
    assert np.isnan(judged.loc["f", "danger_line"]) and not judged.loc["f", "over_line"]
    assert lines == {"2025年前半": {"1番人気": 0.10, "2〜3番人気": 0.05}}


def test_線をいちばん大きく超えた馬を消にし_消にできる人気帯を絞れる() -> None:
    predictions = _predictions([("R", "a", "1番人気", 0.30), ("R", "b", "2〜3番人気", 0.62), ("R", "c", "4〜5番人気", 0.80)])
    places = _places([("R", "a", 1, 0.70), ("R", "b", 4, 0.50), ("R", "c", 6, 0.30)])
    # b は 0.12 − 0.05 = 0.07、c は 0.10 − 0.02 = 0.08 だけ線を超える → c
    dangers, _ = FixedLineDangerJudge({"1番人気": 0.10, "2〜3番人気": 0.05, "4〜5番人気": 0.02}).judge(predictions, places)
    assert dangers.set_index("horse_id")["is_danger"].to_dict() == {"a": False, "b": False, "c": True}
    narrowed, _ = FixedLineDangerJudge({"1番人気": 0.10, "2〜3番人気": 0.05, "4〜5番人気": 0.02}, bands=("1番人気", "2〜3番人気")).judge(predictions, places)
    assert narrowed.set_index("horse_id")["is_danger"].to_dict() == {"a": False, "b": True, "c": False}
    assert narrowed.set_index("horse_id")["over_line"].to_dict() == {"a": False, "b": True, "c": True}   # 線以上かは人気帯を絞っても残す


def test_区切りごとの線と同じ値を渡せば_同じ消になる() -> None:
    """検証期間で決めた線をそのまま固定の線にすると、``FavoriteDangerJudge`` と同じ判定になる。"""
    rows = [("R1", "a", "1番人気", 0.55), ("R1", "b", "2〜3番人気", 0.45), ("R2", "c", "1番人気", 0.35), ("R2", "d", "2〜3番人気", 0.70)]
    tests = _predictions(rows)
    valid = pd.concat([_predictions([(f"V{i}", f"v{i}", "1番人気", 0.30 + i * 0.01) for i in range(40)]).assign(period="検証"),
                       _predictions([(f"W{i}", f"w{i}", "2〜3番人気", 0.40 + i * 0.01) for i in range(40)]).assign(period="検証")])
    predictions = pd.concat([tests, valid], ignore_index=True)
    places = pd.concat([_places([("R1", "a", 4, 0.60), ("R1", "b", 2, 0.50), ("R2", "c", 1, 0.70), ("R2", "d", 5, 0.50)]),
                        _places([(f"V{i}", f"v{i}", 4 if i % 2 else 1, 0.70) for i in range(40)]),
                        _places([(f"W{i}", f"w{i}", 4 if i % 3 else 1, 0.50) for i in range(40)])], ignore_index=True)
    by_fold, lines = FavoriteDangerJudge().judge(predictions, places)
    fixed, _ = FixedLineDangerJudge(lines["2025年前半"]).judge(predictions, places)
    assert by_fold.set_index("horse_id")["is_danger"].to_dict() == fixed.set_index("horse_id")["is_danger"].to_dict()
