"""出走の表に列を足す部品を、架空の値で確かめる。"""

from __future__ import annotations

import pandas as pd
import pytest

from WIN5で人気薄の勝ち馬を狙う.analysis.enrichment.model_uplift import ModelUplift
from WIN5で人気薄の勝ち馬を狙う.analysis.enrichment.people_rates import PeopleRates
from WIN5で人気薄の勝ち馬を狙う.analysis.enrichment.race_market_shape import RaceMarketShape
from WIN5で人気薄の勝ち馬を狙う.analysis.enrichment.runner_history import RunnerHistory
from WIN5で人気薄の勝ち馬を狙う.analysis.enrichment.sire_going_rates import SireGoingRates


def _runs() -> pd.DataFrame:
    """1頭の4走（新しい走ほど下）。"""
    return pd.DataFrame({
        "race_id": ["r1", "r2", "r3", "r4"], "race_date": ["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01"],
        "horse_id": ["h"] * 4, "finish": [1.0, 2.0, 9.0, 1.0], "class_order": [3.0, 4.0, 5.0, 4.0],
        "condition": ["良", "重", "良", "良"], "frame_no": [1.0, 2.0, 3.0, 4.0], "jockey_code": ["j1", "j2", "j3", "j1"],
        "blinker": ["なし"] * 4, "interval_days": [None, 31.0, 29.0, 31.0], "style": ["先行", "逃げ", "差し", "先行"],
        "surface": ["芝", "芝", "ダート", "芝"],
    })


def test_過去走の列は今回より前の走だけから作る():
    frame = RunnerHistory().add(_runs()).set_index("race_id")
    assert frame.loc["r3", "prev_class_order"] == 4.0
    assert frame.loc["r4", "prev2_finish"] == 2.0
    assert frame.loc["r4", "best_recent_finish"] == 1.0
    assert frame.loc["r3", "best_placed_class"] == 4.0     # 3走目の時点: 3着以内は1勝・2勝クラス（順 3・4）
    assert pd.isna(frame.loc["r1", "best_placed_class"])
    assert frame.loc["r4", "best_win_class"] == 3.0
    assert frame.loc["r4", "surface_runs_before"] == 2     # 芝は今回より前に2走
    assert frame.loc["r4", "front_places_before"] == 2     # 先行1着・逃げ2着
    assert frame.loc["r4", "back_places_before"] == 0      # 差しの走は9着
    assert frame.loc["r4", "prev_style"] == "差し"


def test_騎手の勝率は前の年の値を使う():
    runners = pd.DataFrame({
        "jockey_code": ["j1", "j1", "j2", "j1"], "prev_jockey": [None, None, None, "j2"], "trainer_code": ["t"] * 4,
        "year": [2023.0, 2023.0, 2023.0, 2024.0], "finish": [1.0, 5.0, 1.0, 3.0],
    })
    frame = PeopleRates().add(runners)
    last = frame.iloc[3]
    assert last["jockey_rate"] == pytest.approx(0.5)
    assert last["prev_jockey_rate"] == pytest.approx(1.0)
    assert last["trainer_rate"] == pytest.approx(2 / 3)
    assert pd.isna(frame.iloc[0]["jockey_rate"])


def test_父の勝率は前の年までで_出走が少なければ欠損値():
    rows = 120
    runners = pd.DataFrame({
        "sire": ["s"] * (rows + 1), "surface": ["芝"] * (rows + 1), "going": ["道悪"] * (rows + 1),
        "year": [2023.0] * rows + [2024.0], "finish": [1.0] * 12 + [5.0] * (rows - 12) + [1.0],
    })
    frame = SireGoingRates().add(runners)
    assert frame.iloc[-1]["sire_going_rate"] == pytest.approx(0.1)
    assert pd.isna(frame.iloc[0]["sire_going_rate"])         # 2023年の行は、それより前の年が無い


def test_オッズから見た勝率と人気薄の合計():
    runners = pd.DataFrame({
        "race_id": ["r"] * 3, "win_odds": [2.0, 4.0, 4.0], "popularity": [1.0, 10.0, 11.0], "carried": [56.0, 54.0, 55.0],
    })
    frame = RaceMarketShape().add(runners)
    assert frame["market"].sum() == pytest.approx(1.0)
    assert frame["market"].iloc[0] == pytest.approx(0.5)
    assert frame["longshot_market"].iloc[0] == pytest.approx(0.5)
    assert frame["favorite_odds"].iloc[0] == 2.0
    assert frame["contenders"].iloc[0] == 3
    assert frame["carried_gap"].iloc[1] == pytest.approx(-1.0)


def test_上乗せは今のモデルの確率をオッズから見た勝率で割る_先の元を優先():
    runners = pd.DataFrame({"race_id": ["r", "r"], "horse_no": [1.0, 2.0], "market": [0.5, 0.5]})
    first = pd.DataFrame({"race_id": ["r"], "horse_no": [1.0], "model": [0.6]})
    second = pd.DataFrame({"race_id": ["r", "r"], "horse_no": [1.0, 2.0], "model": [0.1, 0.4]})
    frame = ModelUplift((first, second)).add(runners)
    assert frame["model"].tolist() == [0.6, 0.4]
    assert frame["uplift"].tolist() == pytest.approx([1.2, 0.8])
    assert frame["model_rank"].tolist() == [1.0, 2.0]
