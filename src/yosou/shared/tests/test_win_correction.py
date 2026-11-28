"""1着の確率の直し（``yosou.shared.win_correction``）のテスト。値は架空。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ..win_correction import FACT_COLUMNS, FEATURES, QuinellaTop2, WinCorrectionFeatures, WinCorrectionModel


def test_馬連から見た2着以内率は逆数を合計1にそろえて組に入る馬ごとに足す() -> None:
    board = pd.DataFrame({"race_id": ["r"] * 4, "combo": ["0102", "0103", "0203", "0104"], "odds": [2.0, 4.0, 4.0, None]})
    rates = QuinellaTop2().of(board).set_index("horse_no")["quinella_top2"]
    # オッズの無い 1-4 は使わない。逆数 0.5・0.25・0.25 → 1番 0.75・2番 0.75・3番 0.5
    assert rates.to_dict() == pytest.approx({1: 0.75, 2: 0.75, 3: 0.5})


def _horses(n_races: int = 1, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for race in range(n_races):
        p = rng.dirichlet(np.ones(6))
        odds = 0.8 / p
        for number in range(6):
            rows.append({"race_id": f"r{race}", "horse_no": number + 1, "win_probability": p[number] * 2, "probability": min(3 * p[number], 0.95),
                         "win_odds": odds[number], "place_odds_low": max(1.0, odds[number] / 3), "place_odds_high": max(1.2, odds[number] / 2),
                         "quinella_top2": 2 * p[number], **{column: 1.0 for column in FACT_COLUMNS}})
    return pd.DataFrame(rows)


def test_材料は出発点と決まった列で_確率はレースで合計1にそろえてから使う() -> None:
    horses = _horses()
    frame = WinCorrectionFeatures().frame(horses)
    assert list(frame.columns) == ["base", *FEATURES]
    p = horses["win_probability"] / horses["win_probability"].sum()
    assert np.allclose(frame["base"], np.log(p / (1 - p)))
    # 1着の確率をオッズから見た勝率と同じにしてあるので、ずれは 0
    assert np.allclose(frame["p_vs_win"], 0.0)
    assert list(frame["popularity"]) == list(horses["win_odds"].rank(method="first"))


def test_事実表の列が無ければ欠損値_最高オッズが無ければ広がりは0() -> None:
    horses = _horses().drop(columns=list(FACT_COLUMNS)).assign(place_odds_high=None)
    frame = WinCorrectionFeatures().frame(horses)
    assert frame[list(FACT_COLUMNS)].isna().all().all()
    assert (frame["place_spread"] == 0).all()


def test_モデルは学んで日本語の置き場所に保存して読み直せ_確率はレースで合計1(tmp_path: Path) -> None:
    horses = _horses(n_races=40)
    frame = WinCorrectionFeatures().frame(horses)
    won = (horses.groupby("race_id")["win_probability"].transform("max") == horses["win_probability"]).astype(int)
    model = WinCorrectionModel.fit(frame, won, seeds=(0, 1), rounds=5)
    folder = tmp_path / "公開ルール" / "models"
    assert len(model.save(folder)) == 2
    loaded = WinCorrectionModel.load(folder)
    probabilities = loaded.probabilities(frame, horses["race_id"])
    assert np.allclose(probabilities, model.probabilities(frame, horses["race_id"]))
    assert np.allclose(probabilities.groupby(horses["race_id"]).sum(), 1.0)
    assert WinCorrectionModel.load(tmp_path / "無い") is None
