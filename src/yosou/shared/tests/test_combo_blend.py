"""市場とモデルを重みで合わせた組の確率（``combo_value`` の ``ComboBlend`` まわり）のテスト。値は架空。"""

from __future__ import annotations

from itertools import permutations
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ..betting import TicketType
from ..combo_value import (
    FEATURE_COLUMNS,
    HARVILLE,
    HIT,
    MARKET,
    ComboBlend,
    ComboBlendFeatures,
    ComboBlendFitter,
    ComboBlendWeights,
    HorseStrength,
    PoolFolding,
    TrifectaSources,
    join_combo,
    split_combo,
)
from ..combo_value.combo_blend import PROBABILITY, VALUE
from ..combo_value.horse_strength import TOP3_RATIO, WIN_RATIO, WIN_SHARE
from ..repository import ComboBlendWeightsRepository

RACE = "2025010506010101"


def _horses() -> pd.DataFrame:
    """3頭のレース。1着の確率 0.5・0.3・0.2（合計 1）、3着以内の確率はどれも 1.0（3頭なので全頭3着以内）。
    1番だけ市場より強く見ている（1着の比 0.5 ÷ 0.4 = 1.25、3着以内の比 1.0 ÷ 0.8 = 1.25）。"""
    return pd.DataFrame({"race_id": RACE, "horse_no": [1, 2, 3], "win_probability": [0.5, 0.3, 0.2], "market_win": [0.4, 0.3, 0.3],
                         "probability": [1.0, 1.0, 1.0], "market_top3": [0.8, 1.0, 1.0]})


def _trifecta_board() -> pd.DataFrame:
    """3頭の3連単の6組。オッズは全部 6倍（市場の確率はどれも 1/6）。"""
    combos = ["".join(f"{no:02d}" for no in order) for order in permutations((1, 2, 3))]
    return pd.DataFrame({"race_id": RACE, "combo": combos, "odds": 6.0})


def test_馬ごとの見立ては_1着の確率を合計1にそろえ_比は市場の何倍かを出す() -> None:
    strength = HorseStrength().of(_horses()).set_index("horse_no")
    assert strength[WIN_SHARE].sum() == pytest.approx(1.0) and strength.loc[1, WIN_SHARE] == pytest.approx(0.5)
    assert strength.loc[1, WIN_RATIO] == pytest.approx(1.25) and strength.loc[3, WIN_RATIO] == pytest.approx(0.2 / 0.3)
    assert strength.loc[1, TOP3_RATIO] == pytest.approx(1.25) and strength.loc[2, TOP3_RATIO] == pytest.approx(1.0)


def test_3連単の組は_市場の確率とHarvilleの確率を合計1で持つ() -> None:
    sources = TrifectaSources().of(split_combo(_trifecta_board(), 3), HorseStrength().of(_horses()))
    assert sources[MARKET].sum() == pytest.approx(1.0) and sources[MARKET].iloc[0] == pytest.approx(1 / 6)
    first = sources[(sources["h1"] == 1) & (sources["h2"] == 2)][HARVILLE].iloc[0]
    assert first == pytest.approx(0.5 * 0.3 / 0.5 * 0.2 / 0.2)   # 1→2→3 = 0.5 × 0.3/(1−0.5) × 0.2/(1−0.5−0.3) = 0.3
    assert sources[HARVILLE].sum() == pytest.approx(1.0)


def test_3連単から足し合わせて_馬単_馬連_3連複_ワイドの組の確率にする() -> None:
    sources = TrifectaSources().of(split_combo(_trifecta_board(), 3), HorseStrength().of(_horses()))
    folding = PoolFolding()
    exacta = folding.fold(TicketType.EXACTA, sources, [MARKET, HARVILLE]).set_index(["h1", "h2"])
    assert len(exacta) == 6 and exacta.loc[(1, 2), MARKET] == pytest.approx(1 / 6)   # 1→2→3 だけ
    assert exacta.loc[(1, 2), HARVILLE] == pytest.approx(0.3)
    quinella = folding.fold(TicketType.QUINELLA, sources, [MARKET, HARVILLE]).set_index(["h1", "h2"])
    assert len(quinella) == 3 and quinella.loc[(1, 2), MARKET] == pytest.approx(2 / 6)   # 1→2 と 2→1
    trio = folding.fold(TicketType.TRIO, sources, [MARKET])
    assert len(trio) == 1 and trio[MARKET].iloc[0] == pytest.approx(1.0)
    wide = folding.fold(TicketType.WIDE, sources, [MARKET])
    assert len(wide) == 3 and wide[MARKET].sum() == pytest.approx(3.0)   # 3頭なら、どの2頭も必ず3着以内


def test_重みが市場だけなら組の確率はその券種のオッズの逆数をそろえた値になる() -> None:
    strength = HorseStrength().of(_horses())
    sources = TrifectaSources().of(split_combo(_trifecta_board(), 3), strength)
    board = pd.DataFrame({"race_id": RACE, "combo": ["0102", "0103", "0203"], "odds": [2.0, 4.0, 4.0]})
    folded = PoolFolding().fold(TicketType.QUINELLA, sources, [MARKET, HARVILLE])
    features = ComboBlendFeatures().build(TicketType.QUINELLA, board, folded, strength)
    assert list(features.columns[-4:]) == list(FEATURE_COLUMNS)
    blended = ComboBlend().of(TicketType.QUINELLA, features, ComboBlendWeights(1.0, 0.0, 0.0, 0.0)).set_index("combo")
    assert blended.loc["0102", PROBABILITY] == pytest.approx(0.5) and blended.loc["0103", PROBABILITY] == pytest.approx(0.25)
    assert blended.loc["0102", VALUE] == pytest.approx(1.0)   # 0.5 × 2.0
    # 比に重みを掛けると、モデルが強く見た 1番を含む組の確率が上がる
    raised = ComboBlend().of(TicketType.QUINELLA, features, ComboBlendWeights(1.0, 0.0, 0.0, 1.0)).set_index("combo")
    assert raised.loc["0102", PROBABILITY] > 0.5 and raised[PROBABILITY].sum() == pytest.approx(1.0)


def test_重みの推定は_当たりの出方を作った重みに近い値を返す() -> None:
    rng = np.random.default_rng(0)
    races, size, truth = 3000, 6, np.array([0.6, 0.0, 0.0, 0.8])
    rows = []
    for race in range(races):
        own = rng.dirichlet(np.ones(size))
        ratio = rng.normal(0.0, 0.5, size)
        score = truth[0] * np.log(own) + truth[3] * ratio
        chance = np.exp(score - score.max()) / np.exp(score - score.max()).sum()
        winner = rng.choice(size, p=chance)
        rows += [{"race_id": str(race), "log_own": np.log(own[at]), "log_trifecta": 0.0, "log_harville": 0.0, "log_ratio": ratio[at],
                  HIT: at == winner} for at in range(size)]
    weights = ComboBlendFitter().fit(pd.DataFrame(rows))
    assert weights.own == pytest.approx(0.6, abs=0.1) and weights.ratio == pytest.approx(0.8, abs=0.1)


def test_重みはファイルに書いて読み戻せ_無ければ空(tmp_path: Path) -> None:
    repository = ComboBlendWeightsRepository(tmp_path)
    assert repository.load() == {}
    saved = {TicketType.QUINELLA: ComboBlendWeights(0.5, -0.1, 0.7, 0.9)}
    repository.save(saved)
    assert repository.load() == saved


def test_組番と馬番の列を行き来する() -> None:
    board = split_combo(pd.DataFrame({"race_id": RACE, "combo": ["010203", "120304"], "odds": [5.0, 9.0]}), 3)
    assert board[["h1", "h2", "h3"]].values.tolist() == [[1, 2, 3], [12, 3, 4]]
    assert join_combo(board, 3).tolist() == ["010203", "120304"]
