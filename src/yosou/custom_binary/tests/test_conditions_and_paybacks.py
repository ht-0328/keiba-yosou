from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from 共通 import db
from yosou.shared.dataset import TrainingData
from yosou.shared.dataset.column_names import (
    FIELD_SIZE, PLACE_ODDS_LOW, PLACE_PAYOUT, POPULARITY, RACE_DATE, RACE_ID, WIN_ODDS, WIN_PAYOUT,
)
from yosou.shared.feature import FeatureCatalog, PredictionTiming
from yosou.shared.tests import synthetic_season as season

from ..dataset import CustomDataset
from ..evaluation import bootstrap_lower, paybacks, place_probability
from ..feature.registrations import default_registry
from ..row_conditions import RowConditions
from ..settings import ModelSettings, PopularityRange
from .test_settings import BASE, config
from .test_workflow import POPS, settings  # noqa: F401  （フィクスチャ）


def test_conditions_roundtrip_and_mask(tmp_path):
    text = BASE + "conditions:\n  距離: {max: 1400}\n  芝ダ: 芝\n  競馬場: [東京, 中山]\n"
    registry = default_registry()
    loaded = ModelSettings.load(config(tmp_path, text), registry)
    assert loaded.conditions.as_dict() == {"距離": {"max": 1400}, "芝ダ": ["芝"], "競馬場": ["東京", "中山"]}
    assert ModelSettings.from_saved(loaded.as_dict(), registry).as_dict() == loaded.as_dict()
    frame = pd.DataFrame({
        "距離": [1200.0, 1600.0, None, 1400.0], "芝ダ": ["芝", "芝", "芝", "ダート"],
        "競馬場": ["東京", "中山", "東京", "東京"],
    })
    assert loaded.conditions.mask(frame).tolist() == [True, False, False, False]
    assert "距離が1400以下" in loaded.conditions.label()


@pytest.mark.parametrize("conditions,match", [
    ("  未登録の項目: {max: 1}\n", "未登録"),
    ("  距離: 1400\n", "min・max"),
    ("  距離: {max: 1400, low: 1}\n", "min・max"),
    ("  距離: {min: 2000, max: 1400}\n", "minはmax以下"),
    ("  距離: {max: '1400'}\n", "有限な数値"),
    ("  芝ダ: {min: 1}\n", "カテゴリ"),
    ("  芝ダ: []\n", "カテゴリ"),
    ("  馬体重: {max: 440}\n", "使えない"),
])
def test_invalid_conditions(tmp_path, conditions, match):
    text = BASE.replace("当日", "木曜") + "conditions:\n" + conditions
    with pytest.raises(ValueError, match=match):
        ModelSettings.load(config(tmp_path, text), default_registry())


def test_conditions_filter_after_full_field_features(season_db, settings):
    registry = default_registry()
    whole = replace(settings, selected=("斤量とレースの平均との差",), popularity=PopularityRange())
    distances = RowConditions.parse({"距離": {"max": 1600}}, registry, PredictionTiming.RACE_DAY)
    with db.open_db(season_db) as con:
        full = CustomDataset(con, whole, registry).training()
        part = CustomDataset(con, replace(whole, conditions=distances), registry).training()
    assert 0 < len(part) < len(full)
    # 条件の列はモデルに渡さず、レース内の比較は絞る前の全頭の値のまま。
    assert list(part.features.columns) == ["斤量とレースの平均との差"]
    pd.testing.assert_frame_equal(part.features, full.features.loc[part.features.index])


def test_prediction_with_unmatched_condition_is_empty(season_db, settings):
    registry = default_registry()
    nothing = RowConditions.parse({"距離": {"max": 1}}, registry, PredictionTiming.RACE_DAY)
    pops = {int(pair.split(":")[0]): int(pair.split(":")[1]) for pair in POPS}
    with db.open_db(season_db) as con:
        data = CustomDataset(con, replace(settings, conditions=nothing), registry).prediction(season.CARD_RACE_ID, pops)
    assert len(data) == 0


def sample_data(target: str, field_size: int = 16) -> TrainingData:
    """2レース × 2頭。既定では出走頭数16（一部の馬だけ）なので、3着以内の確率のそろえ直しをしない。"""
    ids = pd.DataFrame({RACE_ID: ["a", "a", "b", "b"], RACE_DATE: pd.to_datetime(["2025-01-05"] * 2 + ["2025-01-12"] * 2)})
    evaluation = pd.DataFrame({
        POPULARITY: [1, 2, 1, 2], WIN_ODDS: [2.0, 10.0, 3.0, 5.0], PLACE_ODDS_LOW: [1.1, 2.0, 1.2, 1.5],
        WIN_PAYOUT: [0, 1000, 300, 0], PLACE_PAYOUT: [110, 200, 120, 0], FIELD_SIZE: [field_size] * 4,
    })
    targets = pd.DataFrame({target: [0, 1, 1, 0]})
    return TrainingData(ids, pd.DataFrame(index=ids.index), targets, evaluation, FeatureCatalog(()), target)


def test_paybacks_for_all_top_pick_and_expected_value():
    rows = {row["買い方"]: row for row in paybacks(sample_data("勝利"), np.array([0.3, 0.2, 0.5, 0.1]), "勝利")}
    everyone = rows["対象の全頭（モデルなし）"]
    assert everyone["点数"] == 4 and everyone["単勝回収率"] == pytest.approx(1300 / 400)
    assert everyone["複勝回収率"] == pytest.approx(430 / 400)
    top = rows["各レースで確率1位"]  # a は1頭目、b は3頭目
    assert top["点数"] == 2 and top["単勝回収率"] == pytest.approx(300 / 200)
    value = rows["期待値1.5以上"]  # 期待値は 0.6, 2.0, 1.5, 0.5
    assert value["点数"] == 2 and value["単勝的中率"] == 1.0
    assert rows["期待値2以上"]["点数"] == 1


def test_out_of_top3_model_bets_on_low_probability():
    rows = {row["買い方"]: row for row in paybacks(sample_data("馬券外"), np.array([0.9, 0.2, 0.3, 0.8]), "馬券外")}
    assert rows["各レースで確率1位"]["複勝回収率"] == pytest.approx((200 + 120) / 200)
    assert rows["期待値1.5以上"]["点数"] == 1  # (1-0.2)×2.0 = 1.6 だけ


def test_paybacks_of_empty_data():
    empty = sample_data("勝利").where(pd.Series(False, index=range(4)))
    assert paybacks(empty, np.array([]), "勝利")[0]["点数"] == 0


@pytest.mark.parametrize("extra,match", [
    ("odds_baseline: yes please\n", "trueかfalse"),
    ("odds_baseline: true\n", "前日・当日"),
])
def test_invalid_odds_baseline(tmp_path, extra, match):
    with pytest.raises(ValueError, match=match):
        ModelSettings.load(config(tmp_path, BASE.replace("当日", "木曜") + extra), default_registry())


@pytest.mark.parametrize("target", ["勝利", "馬券内", "馬券外"])
def test_odds_baseline_train_save_and_load(season_db, settings, tmp_path, target):
    from .. import workflow
    from ..model_store import ModelStore

    registry = default_registry()
    settings = replace(settings, target=target, odds_baseline=True)
    with db.open_db(season_db) as con:
        data = CustomDataset(con, settings, registry).training()
    assert data.baseline is not None and len(data.baseline.values) == len(data)
    store = ModelStore(tmp_path / "baseline")
    workflow.fit_and_save(data, settings, registry, store)
    loaded, ensemble = store.load(registry)
    assert loaded.odds_baseline
    test = data.between(settings.period.test_first_day, None)
    probability = ensemble.predict_proba(test)
    assert np.isfinite(probability).all() and ((0 < probability) & (probability < 1)).all()
    with pytest.raises(ValueError, match="基準確率"):
        workflow.fit_and_save(replace(data, baseline=None), settings, registry, ModelStore(tmp_path / "x"))


def test_win_baseline_sums_to_one_within_race():
    from ..odds_baseline import OddsBaseline

    entries = pd.DataFrame({"race_id": ["a"] * 3 + ["b"] * 2, "win_odds": [2.0, 4.0, 8.0, 1.5, 3.0]})
    probability = OddsBaseline("勝利").build(entries).probabilities()
    assert probability.groupby(entries["race_id"]).sum().tolist() == pytest.approx([1.0, 1.0])
    assert probability.iloc[0] > probability.iloc[1] > probability.iloc[2]


def test_place_probability_is_rescaled_only_for_complete_races():
    probability = np.array([0.6, 0.6, 0.3, 0.2])
    # 2頭立て（7頭以下）で全頭そろっているので、合計を2にそろえ直す（上限は1）。
    full = place_probability(sample_data("馬券内", field_size=2), probability, "馬券内")
    assert full.tolist() == pytest.approx([1.0, 1.0, 1.0, 0.8])
    assert place_probability(sample_data("馬券内"), probability, "馬券内").tolist() == pytest.approx(probability)
    assert place_probability(sample_data("馬券外"), probability, "馬券外").tolist() == pytest.approx(1 - probability)


def test_bootstrap_lower_is_below_the_rate_and_needs_two_days():
    days = np.array(["d1", "d1", "d2", "d3", "d3"])
    payouts = np.array([0, 300, 0, 0, 150])
    lower = bootstrap_lower(days, payouts)
    assert lower is not None and lower <= payouts.sum() / (100 * len(payouts))
    assert bootstrap_lower(days[:2], payouts[:2]) is None
