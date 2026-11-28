"""道具「公開ルール」の学習の表（``TrainingTable``）のテスト。値は架空。"""

from __future__ import annotations

import pandas as pd

from 公開ルール.training_table import TrainingTable


def _predictions(probabilities: dict[tuple[str, int], float], period: str = "テスト") -> pd.DataFrame:
    return pd.DataFrame([{"race_id": race, "race_date": "2025-10-04", "horse_no": number, "probability": value, "period": period}
                         for (race, number), value in probabilities.items()])


def test_予測とオッズと払戻と事実表をつなぎ_オッズの欠けるレースは外す() -> None:
    win = pd.concat([_predictions({("r1", 1): 0.6, ("r1", 2): 0.4, ("r2", 1): 0.5, ("r2", 2): 0.5}), _predictions({("r3", 1): 1.0}, period="検証")])
    top3 = _predictions({("r1", 1): 0.9, ("r1", 2): 0.8, ("r2", 1): 0.7, ("r2", 2): 0.7})
    win_odds = pd.DataFrame({"race_id": ["r1", "r1", "r2", "r2"], "combo": ["01", "02", "01", "02"], "odds": [1.5, 2.5, 2.0, 2.0]})
    place_odds = pd.DataFrame({"race_id": ["r1", "r1", "r2"], "combo": ["01", "02", "01"], "odds": [1.1, 1.2, 1.1], "odds_high": [1.3, 1.5, 1.4]})
    quinella = pd.DataFrame({"race_id": ["r1", "r2"], "combo": ["0102", "0102"], "odds": [1.8, 1.9]})
    payouts = pd.DataFrame({"race_id": ["r1"], "combo": ["02"], "yen": [250]})
    facts = pd.DataFrame({"race_id": ["r1", "r1"], "horse_no": [1, 2], "distance_m": [1600, 1600]})
    table = TrainingTable(win, top3, win_odds, place_odds, quinella, payouts, facts).build()
    # r2 は 2番の複勝オッズが無いので外す。検証期間の r3 は使わない
    assert list(table["race_id"]) == ["r1", "r1"]
    assert list(table["won"]) == [0, 1]
    assert list(table["quinella_top2"]) == [1.0, 1.0]
    assert list(table["place_odds_high"]) == [1.3, 1.5]
    assert list(table["distance_m"]) == [1600, 1600]
    assert set(table["year"]) == {2025}
