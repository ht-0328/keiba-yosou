"""1着のモデルの作り方（``win_model``）のテスト。値は架空。"""

from __future__ import annotations

import pandas as pd
import pytest

from yosou.shared.dataset import WIN
from yosou.shared.dataset.column_names import POPULARITY
from yosou.shared.feature import PACE_FORECAST_FEATURES, PredictionTiming

from 既存モデルの改善.analysis.walk_forward import WINDOW
from 既存モデルの改善.analysis.win_model import MARKET_WIN, SCORE, WIN_VARIANTS, WinComparison, spec_keyed


def test_win_variants_cover_the_three_timings_with_the_production_columns() -> None:
    assert [spec.timing for spec in WIN_VARIANTS] == [PredictionTiming.DAY_BEFORE, PredictionTiming.THURSDAY, PredictionTiming.RACE_DAY]
    day_before = spec_keyed("win-day_before")
    assert day_before.table == "h2h_ability" and day_before.variant.uses_baseline
    assert "対戦レーティング" in day_before.variant.columns and "単勝オッズ" in day_before.variant.columns
    thursday = spec_keyed("win-thursday")
    assert not thursday.variant.uses_baseline and "単勝オッズ" not in thursday.variant.columns
    assert set(feature.name for feature in PACE_FORECAST_FEATURES) <= set(thursday.variant.columns)
    assert set(thursday.variant.columns) <= set(thursday.catalog.names)
    with pytest.raises(ValueError):
        spec_keyed("win-sunday")


def test_win_comparison_compares_the_model_with_the_market_win_rate() -> None:
    frame = pd.DataFrame({
        WINDOW: ["2023年前半"] * 4 + ["2023年後半"] * 4, WIN: [1, 0, 0, 0] * 2, SCORE: [0.6, 0.2, 0.1, 0.1] * 2,
        MARKET_WIN: [0.4, 0.3, 0.2, 0.1] * 2, POPULARITY: [1, 2, 3, 4] * 2,
    })
    table = WinComparison().by_window(frame)
    assert table[WINDOW].tolist() == ["2023年前半", "2023年後半", "全期間"]
    assert table["小さい"].all()  # モデルの確率のほうが正解に近い
    assert table.loc[2, "行数"] == 8
