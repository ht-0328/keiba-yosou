"""判定の決め方・方針の読み方・掛け金と成績のまとめ。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from yosou.shared.dataset.column_names import PLACE_PAYOUT, WIN_PAYOUT
from yosou.shared.feature import PredictionTiming

from ..dataset import IN_THE_MONEY, OUT_OF_THE_MONEY, WIN
from ..decision import DECISION, FADE, PLACE_ONLY, WIN_AND_PLACE, BuyDecision
from ..evaluation import DecisionSummary, StakePlan
from ..setting import BuyOrFadeSettings
from ..similarity import SCORE_COLUMNS


def _scores(win: list[float], in_the_money: list[float], out: list[float]) -> pd.DataFrame:
    return pd.DataFrame({SCORE_COLUMNS[WIN]: win, SCORE_COLUMNS[IN_THE_MONEY]: in_the_money,
                         SCORE_COLUMNS[OUT_OF_THE_MONEY]: out})


def test_decision_compares_the_scores():
    scores = _scores(win=[10, 70, 40, 50], in_the_money=[40, 50, 50, 50], out=[80, 20, 30, 50])
    assert BuyDecision(0, 0).decide(scores).tolist() == [FADE, WIN_AND_PLACE, PLACE_ONLY, PLACE_ONLY]
    # 同点（4行目）は消さず、単勝も足さない。線を上げると、はっきり近い馬だけになる
    assert BuyDecision(45, 25).decide(scores).tolist() == [PLACE_ONLY, PLACE_ONLY, PLACE_ONLY, PLACE_ONLY]


def test_default_settings_load_and_overrides_apply(tmp_path: Path):
    defaults = BuyOrFadeSettings.load()
    assert defaults.timing is PredictionTiming.RACE_DAY and defaults.k == 10 and defaults.fade_margin == 5.0
    # オッズなしで予想する（単勝オッズから見た評価 K は使わない。前走の人気などの人気の履歴 J は使う）
    assert defaults.group_weights["K"] == 0.0 and defaults.group_weights["J"] == 1.0
    override = tmp_path / "mine.toml"
    override.write_text('[similarity]\nk = 20\n[features]\ntiming = "前日"\n', encoding="utf-8")
    mine = BuyOrFadeSettings.load(override)
    assert mine.k == 20 and mine.timing is PredictionTiming.DAY_BEFORE and mine.min_unit_rows == defaults.min_unit_rows
    assert BuyOrFadeSettings.from_dict(mine.to_dict()) == mine


def test_settings_reject_unknown_names_and_thursday(tmp_path: Path):
    typo = tmp_path / "typo.toml"
    typo.write_text("[similarity]\nkk = 3\n", encoding="utf-8")
    with pytest.raises(ValueError, match="知らない設定の名前"):
        BuyOrFadeSettings.load(typo)
    thursday = tmp_path / "thursday.toml"
    thursday.write_text('[features]\ntiming = "木曜"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="前日 か 当日"):
        BuyOrFadeSettings.load(thursday)


def test_stake_plan_and_summary():
    plan = StakePlan(win_and_place_win=100, win_and_place_place=200, place_only_place=300)
    rows = pd.DataFrame({
        DECISION: [FADE, WIN_AND_PLACE, PLACE_ONLY, WIN_AND_PLACE],
        WIN: [1, 1, 0, 0], IN_THE_MONEY: [1, 1, 1, 0], OUT_OF_THE_MONEY: [0, 0, 0, 1],
        WIN_PAYOUT: [150, 200, 0, 0], PLACE_PAYOUT: [110, 120, 130, 0],
    })
    assert plan.invested(rows[DECISION]).tolist() == [0, 300, 300, 300]
    # 単勝 100円 × 2.0倍 + 複勝 200円 × 1.2倍 = 440円。複勝 300円 × 1.3倍 = 390円
    assert plan.returned(rows[DECISION], rows[[WIN_PAYOUT, PLACE_PAYOUT]]).tolist() == [0, 440, 390, 0]
    summary = DecisionSummary(plan).summarize(rows)
    assert summary["消した数"] == 1 and summary["消した馬の馬券外率"] == "0.0%"
    assert summary["単勝も買った馬の勝率"] == "50.0%" and summary["全体の勝率"] == "50.0%"
    assert summary["買い分けの投資"] == "900円" and summary["買い分けの回収率"] == "92.2%"
