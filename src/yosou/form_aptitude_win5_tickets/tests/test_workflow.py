"""対象レースの確率の選び方・そろえ方と、WIN5 の日の予測の流れのテスト（今のモデルの代わりを使う）。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from 共通 import db

from yosou.shared.feature import PredictionTiming

from ..formation import BUDGETS, BudgetTiers, DayDecision, FavoriteProduct, FormationSearch, FormationValue, LegOrdering
from ..leg import EDGE, MARKET, SHARE, LegModel, LegModelChooser, LegWinPredictor, RaceWinShare
from ..payout import PayoutEstimator
from ..repository import Win5DayRepository
from ..workflow import Win5PredictionWorkflow
from .fake_prediction import FAVORED_HORSE, FakePrediction
from .win5_sample import FORECAST_CARRY, FORECAST_DAY, JUMP_LEG, NO_ODDS_DAY, UNWEIGHED_LEG, Win5Sample


def _workflow(con, sample: Win5Sample, estimator: PayoutEstimator, ordering: LegOrdering = LegOrdering.BY_EDGE):
    prediction = FakePrediction(sample.odds)
    search = FormationSearch(ordering, FormationValue(estimator))
    return Win5PredictionWorkflow(con, LegWinPredictor(prediction), search, estimator.count), prediction


def test_障害はオッズだけ_馬体重のあるレースは当日_まだのレースは前日(win5_db: Path) -> None:
    with db.open_db(win5_db) as con:
        race_ids = Win5DayRepository(con).read(FORECAST_DAY).race_ids
        models = [LegModelChooser().choose(con, race_id).model for race_id in race_ids]
    expected = [LegModel.RACE_DAY] * 5
    expected[JUMP_LEG - 1] = LegModel.ODDS_ONLY
    expected[UNWEIGHED_LEG - 1] = LegModel.DAY_BEFORE
    assert models == expected


def test_締め切り前のオッズが無いレースは速報の取り込みを案内して止まる(win5_db: Path) -> None:
    with db.open_db(win5_db) as con:
        race_id = Win5DayRepository(con).read(NO_ODDS_DAY).race_ids[0]
        with pytest.raises(LookupError, match="jvstore realtime"):
            LegModelChooser().choose(con, race_id)


def test_障害はオッズから見た勝率をそのまま1着の確率にする(win5_db: Path, win5_sample: Win5Sample) -> None:
    with db.open_db(win5_db) as con:
        race_id = Win5DayRepository(con).read(FORECAST_DAY).race_ids[JUMP_LEG - 1]
        choice = LegModelChooser().choose(con, race_id)
        prediction = LegWinPredictor(FakePrediction(win5_sample.odds)).predict(con, race_id, choice)
    shared = RaceWinShare().of(prediction)
    assert shared[SHARE].sum() == pytest.approx(1.0)
    assert shared[EDGE].tolist() == pytest.approx([1.0] * len(shared))
    odds = win5_sample.odds[(FORECAST_DAY, JUMP_LEG)]
    assert shared["単勝オッズ"].tolist() == [odds[number] for number in sorted(odds)]


def test_そろえた確率は合計1で_上乗せはそろえた確率をオッズから見た勝率で割ったもの() -> None:
    prediction = pd.DataFrame({
        "レースID": "R", "馬番": [1, 2, 3, 4], "馬名": ["A", "B", "C", "D"], "単勝オッズ": [2.0, 4.0, 4.0, None],
        "1着になる確率": [0.30, 0.20, 0.10, 0.05],
    })
    shared = RaceWinShare().of(prediction)
    assert shared["馬番"].tolist() == [1, 2, 3]
    assert shared[SHARE].tolist() == pytest.approx([0.5, 1 / 3, 1 / 6])
    assert shared[MARKET].tolist() == pytest.approx([0.5, 0.25, 0.25])
    assert shared[EDGE].tolist() == pytest.approx([1.0, 4 / 3, 2 / 3])


#: テストの段階の予算（判断用 50点・少なく 30点・多く 100点）。多く買う日の線はテストごとに替える。
TIERS = BudgetTiers(50, 30, 100, 0.0025)


def test_WIN5の日の予測は段階の予算の買い目と予算の候補ごとの表と判断を出す(win5_db: Path, win5_sample: Win5Sample,
                                                           estimator: PayoutEstimator) -> None:
    with db.open_db(win5_db) as con:
        workflow, prediction = _workflow(con, win5_sample, estimator)
        forecast = workflow.run(FORECAST_DAY, TIERS, 1.0)
    timings = [timing for _, timing in prediction.calls]
    assert len(prediction.calls) == 4 and PredictionTiming.DAY_BEFORE in timings
    assert forecast.day.carry == FORECAST_CARRY
    assert [leg.choice.model for leg in forecast.legs][JUMP_LEG - 1] is LegModel.ODDS_ONLY
    assert all(leg.table[SHARE].sum() == pytest.approx(1.0) for leg in forecast.legs)
    assert sorted(forecast.by_budget) == sorted({*BUDGETS, 30, 50, 100})
    assert forecast.judge == forecast.by_budget[50] and forecast.judge.formation.points <= 50
    assert forecast.favorite_product == pytest.approx(FavoriteProduct().of([leg.table for leg in forecast.legs]))
    if forecast.judge.expected_value < 1.0:
        assert forecast.decision is DayDecision.SKIP and forecast.budget == 30
    else:
        expected = DayDecision.BUY_LARGE if forecast.favorite_product >= 0.0025 else DayDecision.BUY_SMALL
        assert forecast.decision is expected and forecast.budget == TIERS.budget_for(expected)
    assert forecast.choice == forecast.by_budget[forecast.budget]
    assert forecast.pool.votes > 0
    first_leg_picks = forecast.choice.formation.legs[0]
    assert first_leg_picks[0] == FAVORED_HORSE


def test_判断は多く_少なく_見送りの3通りになり_買う買い目の予算が変わる(win5_db: Path, win5_sample: Win5Sample,
                                                       estimator: PayoutEstimator) -> None:
    with db.open_db(win5_db) as con:
        workflow, _ = _workflow(con, win5_sample, estimator, LegOrdering.BY_PROBABILITY)
        large = workflow.run(FORECAST_DAY, BudgetTiers(50, 30, 100, 0.0), 0.0)
        small = workflow.run(FORECAST_DAY, BudgetTiers(50, 30, 100, 1.0), 0.0)
        skipped = workflow.run(FORECAST_DAY, BudgetTiers(50, 30, 100, 0.0), 99.0)
    assert large.decision is DayDecision.BUY_LARGE and large.budget == 100 and large.choice.formation.points <= 100
    assert small.decision is DayDecision.BUY_SMALL and small.budget == 30 and small.choice.formation.points <= 30
    assert skipped.decision is DayDecision.SKIP and skipped.budget == 30 and skipped.choice == small.choice
    assert large.judge == small.judge == skipped.judge
    assert large.favorite_product == small.favorite_product == skipped.favorite_product
    assert large.choice.formation.points >= small.choice.formation.points


def test_予測の結果は記録の形にできる(win5_db: Path, win5_sample: Win5Sample, estimator: PayoutEstimator) -> None:
    with db.open_db(win5_db) as con:
        workflow, _ = _workflow(con, win5_sample, estimator, LegOrdering.BY_PROBABILITY)
        forecast = workflow.run(FORECAST_DAY, BudgetTiers(20, 10, 20, 0.0025), 99.0)
    record = forecast.to_dict()
    assert record["開催日"] == FORECAST_DAY.isoformat()
    assert record["判断"] == "見送り" and record["段階"] == "見送り"
    assert record["並べ方"] == "1着の確率の順"
    assert (record["判断用の予算"], record["少なく買う日の予算"], record["多く買う日の予算"], record["多く買う日の線"]) == (20, 10, 20, 0.0025)
    assert record["買う日の線"] == 99.0
    assert record["判断用の点数"] == forecast.judge.formation.points and record["判断用の期待値"] == forecast.judge.expected_value
    assert record["判断用の当たる確率"] == forecast.judge.hit_probability
    assert record["本命の確率の積"] == forecast.favorite_product
    assert record["予算"] == 10 and record["点数"] <= 10 and record["代金"] == record["点数"] * 100
    assert len(record["対象レース"]) == 5
    leg = record["対象レース"][0]
    assert leg["使った確率"] == "当日" and leg["オッズの断面"]
    assert sum(horse["買い目に入れたか"] for horse in leg["馬"]) == len(leg["買い目"])
    assert [entry["予算"] for entry in record["予算の候補"]] == sorted({*BUDGETS, 10, 20})
