"""予測の結果の表に出すオッズの列（単勝オッズ・複勝の最低と最高）を確かめる。"""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from yosou.shared.dataset.column_names import PLACE_ODDS_HIGH, PLACE_ODDS_LOW
from yosou.shared.feature.group import WIN_ODDS
from yosou.shared.workflow.prediction_workflow import PredictionWorkflow


def _workflow() -> PredictionWorkflow:
    """``_shown_odds`` は流れの部品を使わないので、部品を組まずに作る。"""
    return PredictionWorkflow.__new__(PredictionWorkflow)


def _data(features: pd.DataFrame, market: pd.DataFrame | None) -> SimpleNamespace:
    return SimpleNamespace(ids=pd.DataFrame(index=features.index), features=features, market=market)


def test_shown_odds_has_both_place_odds_when_the_market_has_them():
    """複勝の最低と最高の両方が市場の表にあれば、両方を表に出す（複勝オッズから見た3着以内率に要る）。"""
    features = pd.DataFrame({WIN_ODDS: [2.5, 8.0]}, index=[10, 11])
    market = pd.DataFrame({PLACE_ODDS_LOW: [1.2, 2.0], PLACE_ODDS_HIGH: [1.5, 3.1], "field_size": [16, 16]}, index=[10, 11])
    shown = _workflow()._shown_odds(_data(features, market))
    assert list(shown.columns) == [WIN_ODDS, PLACE_ODDS_LOW, PLACE_ODDS_HIGH]
    assert shown[PLACE_ODDS_HIGH].tolist() == [1.5, 3.1]
    assert list(shown.index) == [10, 11]


def test_shown_odds_keeps_only_the_columns_the_market_has():
    """市場の表に最低しか無ければ最低だけ、市場の表が無ければ単勝オッズだけを出す。"""
    features = pd.DataFrame({WIN_ODDS: [2.5]}, index=[3])
    low_only = _workflow()._shown_odds(_data(features, pd.DataFrame({PLACE_ODDS_LOW: [1.2]}, index=[3])))
    assert list(low_only.columns) == [WIN_ODDS, PLACE_ODDS_LOW]
    assert list(_workflow()._shown_odds(_data(features, None)).columns) == [WIN_ODDS]


def test_shown_odds_is_empty_without_win_odds():
    """オッズを使わない時点（木曜）は、オッズの列を出さない。"""
    features = pd.DataFrame({"距離": [1600.0]}, index=[7])
    shown = _workflow()._shown_odds(_data(features, pd.DataFrame({PLACE_ODDS_LOW: [1.2]}, index=[7])))
    assert shown.empty and list(shown.index) == [7]
