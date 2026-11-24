"""学習と予測の流れのテスト（年ごとの学習と予測・本番のモデルの学習・1レースの予測）。乱数で作った架空のシーズンだけを使う。"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from yosou.shared.betting import TicketType
from yosou.shared.setting import HyperparameterSettings

from .. import DEFAULT_BANDS, DEFAULT_VALUE_LINE, YOSOU_NAME, HighPayoutPredictor, HighPayoutRule, PayoutBand, PredictionStore
from ..evaluation import AVERAGE, MARKET, SCALED_MARKET
from ..repository import ComboTableRepository, TicketModelRepository
from ..workflow import PREDICTION_COLUMNS, WalkForwardWorkflow, YearSamples
from . import synthetic_race as race
from . import synthetic_season
from .conftest import FIRST_TEST_YEAR

WIDE, TRIFECTA, TRIO = TicketType.WIDE, TicketType.TRIFECTA, TicketType.TRIO
#: 架空のシーズンの1レースの組の数（7頭）。ワイドは 7C2、3連単は 7P3。
WIDE_COMBOS, TRIFECTA_COMBOS = 21, 210


def _one_race(season: SimpleNamespace) -> tuple[pd.DataFrame, dict[TicketType, pd.DataFrame]]:
    """架空のシーズンの最後の年の、最初のレースの馬ごとの表と5券種の板。"""
    horses = season.horses[synthetic_season.YEARS[-1]]
    one = horses[horses["race_id"] == horses["race_id"].iloc[0]]
    return one, synthetic_season.boards_of(one)


def test_道具から呼ぶ名前がパッケージの入口にある() -> None:
    assert YOSOU_NAME == "高配当の組が当たるかを予想" and DEFAULT_VALUE_LINE == 1.05
    assert isinstance(DEFAULT_BANDS[TicketType.TRIO], PayoutBand)
    assert all(callable(each) for each in (HighPayoutPredictor.load, HighPayoutRule, PredictionStore))


def test_年ごとの学習は_2年前までで学び_1年前で止めて_その年の全部の組を予測する(season: SimpleNamespace, walked: SimpleNamespace) -> None:
    results = walked.results[TRIFECTA]
    assert [result.year for result in results] == [2023, 2024] and not any(result.was_skipped for result in results)
    table_2024 = season.tables.load(TRIFECTA, 2024)
    assert results[1].predicted_row_count == len(table_2024) == synthetic_season.RACES_PER_YEAR * TRIFECTA_COMBOS   # 間引かない
    assert results[0].train_row_count < results[1].train_row_count          # 2024年は学ぶ年が1年多い
    assert all(count >= 1 for count in results[1].tree_counts.values()) and set(results[1].tree_counts) == {"LightGBM", "CatBoost"}


def test_年ごとの予測は_道具と約束した列を持つ(season: SimpleNamespace, walked: SimpleNamespace) -> None:
    predictions = walked.store.load(WIDE)
    wanted = ["race_id", "race_date", "ticket_type", "combo", "odds", "payout", "hit", "probability",
              "probability_lightgbm", "probability_catboost", "market_probability"]
    assert set(wanted) <= set(predictions.columns) and {"h1", "h2"} <= set(predictions.columns)
    assert sorted(predictions["race_date"].dt.year.unique()) == [2023, 2024] and set(predictions["ticket_type"]) == {"ワイド"}
    assert predictions["probability"].between(0.0, 1.0).all()
    average = (predictions["probability_lightgbm"] + predictions["probability_catboost"]) / 2
    assert np.allclose(predictions["probability"], average)
    table = season.tables.load(WIDE, 2024)
    of_2024 = predictions[predictions["race_date"].dt.year == 2024]
    assert np.allclose(of_2024["market_probability"], np.exp(table["log_q"].astype(float)))
    assert of_2024["hit"].sum() == table["hit"].sum() == synthetic_season.RACES_PER_YEAR * 3   # ワイドは1レース3組当たる


def test_モデルは市場の確率を出発点にするので_予測は市場の確率と強く連動する(walked: SimpleNamespace) -> None:
    predictions = walked.store.load(TRIFECTA)
    correlation = np.corrcoef(np.log(predictions["probability"]), np.log(predictions["market_probability"]))[0, 1]
    assert correlation > 0.9


def test_予測のある年は飛ばし_作り直しを頼めば学び直す(season: SimpleNamespace, walked: SimpleNamespace,
                                 fast_settings: HyperparameterSettings, samples: YearSamples) -> None:
    again = WalkForwardWorkflow(season.tables, walked.store, fast_settings, samples).run(WIDE, FIRST_TEST_YEAR)
    assert [result.was_skipped for result in again] == [True, True]
    forced = WalkForwardWorkflow(season.tables, walked.store, fast_settings, samples, overwrite=True).run(WIDE, 2024)
    assert [(result.year, result.was_skipped) for result in forced] == [(2024, False)]


def test_学ぶ年と止める年の無い年は予測しない(season: SimpleNamespace, walked: SimpleNamespace,
                             fast_settings: HyperparameterSettings, samples: YearSamples) -> None:
    results = WalkForwardWorkflow(season.tables, walked.store, fast_settings, samples).run(WIDE, 2021)
    assert [result.year for result in results] == [2023, 2024]   # 2021年と2022年は、前の年の表が足りない


def test_表が足りなければ誤り(tmp_path: Path, fast_settings: HyperparameterSettings) -> None:
    workflow = WalkForwardWorkflow(ComboTableRepository(tmp_path), PredictionStore(tmp_path / "predictions"), fast_settings)
    with pytest.raises(ValueError, match="表が足りません"):
        workflow.run(TRIO, 2023)


def test_本番のモデルは_最後の1年で止めて_券種ごとに保存する(trained_models: SimpleNamespace) -> None:
    result = trained_models.results[TRIFECTA]
    last_year = synthetic_season.YEARS[-1]
    assert result.valid_last_day.year == last_year and result.train_last_day < result.valid_last_day
    assert (pd.Timestamp(result.valid_last_day) - pd.Timestamp(result.train_last_day)).days >= 365
    assert result.train_row_count > result.valid_row_count > 0
    assert set(result.losses) == {"LightGBM", "CatBoost", AVERAGE, MARKET, SCALED_MARKET}
    assert all(0.0 < loss < 1.0 for loss in result.losses.values())
    repository = TicketModelRepository(trained_models.folder)
    assert repository.has(TRIFECTA) and repository.has(WIDE) and not repository.has(TRIO)
    assert result.folder == trained_models.folder / "trifecta" / "race_day"
    assert sorted(path.name for path in result.folder.iterdir()) == ["catboost.cbm", "lightgbm.joblib", "settings.json"]


def test_1レースの予測は_モデルのある券種の対象の組に確率と期待値を付ける(season: SimpleNamespace, trained_models: SimpleNamespace) -> None:
    predictor = HighPayoutPredictor.load(trained_models.folder, race.WIDE_OPEN_BANDS)
    assert predictor.ticket_types == (WIDE, TRIFECTA)
    horses, boards = _one_race(season)
    combos = predictor.predict(horses, boards)
    assert list(combos.columns) == list(PREDICTION_COLUMNS) == ["race_id", "ticket_type", "combo", "horses", "odds", "probability", "value"]
    assert combos["ticket_type"].value_counts().to_dict() == {"3連単": TRIFECTA_COMBOS, "ワイド": WIDE_COMBOS}
    assert combos["probability"].between(0.0, 1.0).all() and np.allclose(combos["value"], combos["probability"] * combos["odds"])
    first = combos.iloc[0]
    assert first["horses"] == (int(first["combo"][:2]), int(first["combo"][2:4])) and first["ticket_type"] == "ワイド"
    picks = HighPayoutRule(race.WIDE_OPEN_BANDS, DEFAULT_VALUE_LINE).pick(combos)
    assert list(picks.columns) == list(combos.columns) and len(picks) <= len(combos)
    assert ((picks["value"] >= DEFAULT_VALUE_LINE) & (picks["odds"] >= 2.0)).all()


def test_1レースの予測は_保存し直したモデルでも学習のときと同じ確率を出す(season: SimpleNamespace, trained_models: SimpleNamespace) -> None:
    horses, boards = _one_race(season)
    first = HighPayoutPredictor.load(trained_models.folder, race.WIDE_OPEN_BANDS).predict(horses, boards)
    again = HighPayoutPredictor.load(trained_models.folder, race.WIDE_OPEN_BANDS).predict(horses, boards)
    assert np.allclose(first["probability"], again["probability"])


def test_板が足りない券種は_誤りにせず行を出さない(season: SimpleNamespace, trained_models: SimpleNamespace) -> None:
    predictor = HighPayoutPredictor.load(trained_models.folder, race.WIDE_OPEN_BANDS)
    horses, boards = _one_race(season)
    without_trio = {ticket_type: board for ticket_type, board in boards.items() if ticket_type is not TRIO}
    assert set(predictor.predict(horses, without_trio)["ticket_type"]) == {"ワイド"}       # 3連単の材料は3連複の板が要る
    without_trifecta = {ticket_type: board for ticket_type, board in boards.items() if ticket_type is not TRIFECTA}
    empty = predictor.predict(horses, without_trifecta)                                    # 3連単の板が無いと、どの券種も作れない
    assert empty.empty and list(empty.columns) == list(PREDICTION_COLUMNS)


def test_既定の帯なら_学ぶ下限より下のオッズの組は出さない(season: SimpleNamespace, trained_models: SimpleNamespace) -> None:
    horses, boards = _one_race(season)
    combos = HighPayoutPredictor.load(trained_models.folder).predict(horses, boards)
    wide, trifecta = combos[combos["ticket_type"] == "ワイド"], combos[combos["ticket_type"] == "3連単"]
    assert wide["odds"].between(3.0, 300.0, inclusive="left").all() and len(wide) < WIDE_COMBOS
    assert trifecta["odds"].between(100.0, 10_000.0, inclusive="left").all()


def test_モデルの無いフォルダからは_何も扱わない入口ができる(tmp_path: Path, season: SimpleNamespace) -> None:
    predictor = HighPayoutPredictor.load(tmp_path)
    horses, boards = _one_race(season)
    assert predictor.ticket_types == () and predictor.predict(horses, boards).empty
