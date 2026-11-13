"""道具「印の成績」の ``--win5``（過去の WIN5 での買い方の確かめ）のテスト。値は架空。DB は合成DB だけを使う。"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from 共通 import db
from 合成DB import synth

from yosou.form_aptitude_win5_tickets.formation import Formation, FormationChoice
from yosou.form_aptitude_win5_tickets.leg import RaceWinShare
from yosou.form_aptitude_win5_tickets.payout import PayoutEstimator
from yosou.form_aptitude_win5_tickets.repository import Win5HistoryRepository, Win5LegRunnerHistoryRepository
from yosou.form_aptitude_win5_tickets.repository.win5_columns import (
    CARRY,
    HORSE_NO,
    JUMP,
    LEG,
    POST_TIME,
    RACE_DATE,
    RACE_ID,
    SATURDAY,
    WIN_ODDS,
)
from yosou.form_aptitude_win5_tickets.settlement import HIT, PAYOUT, STAKE, STRATEGY, Win5Outcome, Win5Settlement
from yosou.form_aptitude_win5_tickets.tests.win5_sample import FORECAST_DAY, Win5Sample
from yosou.shared.feature import PredictionTiming
from yosou.shared.workflow import WIN_PROBABILITY

from 印の成績.mark_stats import build_parser, main
from 印の成績.win5_adoption_judge import ADOPTED, BY_CHANCE, NOT_REACHED, Win5AdoptionJudge
from 印の成績.win5_backtest_day import Win5BacktestDay
from 印の成績.win5_backtest_days import NO_FOLD, NO_PREDICTION, ODDS_ONLY, Win5BacktestDays
from 印の成績.win5_bet_columns import BUDGET, EXPECTED_VALUE, KIND, LARGE_DAY, OURS, TIERED
from 印の成績.win5_day_bets import RULE, RULE_CARRY, STRATEGIES, Win5DayBets, popularity_label
from 印の成績.win5_fold_predictions import Win5FoldPredictions
from 印の成績.win5_leg_timing import Win5LegTiming
from 印の成績.win5_periods import CONFIRM, EXPLORE, Win5Periods
from 印の成績.win5_record_bets import RECORDED, Win5RecordBets
from 印の成績.win5_stats import REPORT_NAME, SETTLED_NAME, Win5Stats
from 印の成績.win5_strategy_choice import Win5StrategyChoice
from 印の成績.win5_strategy_summary import DAYS, HIT_RATE, LOW, RECOVERY
from 印の成績.win5_tier_report import ADOPTED_MARK, Win5TierReport
from 印の成績.win5_tier_signal import Win5TierSignal
from 印の成績.win5_tier_strategy import ADOPTED_TIER, TIER_BUDGETS, TIER_CANDIDATES, TIER_JUDGE, Win5TierStrategy

NOTHING = (frozenset(),) * 5


def test_期間は2019年からを探索と確認に分ける() -> None:
    periods = Win5Periods()
    assert periods.label_of("2018-12-23") is None
    assert periods.label_of("2019-01-06") == EXPLORE and periods.label_of("2024-12-28") == EXPLORE
    assert periods.label_of("2025-01-05") == CONFIRM


def test_1レース目の発走から60分以上あとのレースは前日の予測にする() -> None:
    timings = Win5LegTiming().of(["1440", "1515", "1539", "1540", "1625"])
    day, before = PredictionTiming.RACE_DAY, PredictionTiming.DAY_BEFORE
    assert timings == (day, day, day, before, before)
    assert Win5LegTiming().of(["1440", None, "", "1500", "1530"]) == (day, before, before, day, day)


def _summary(rows: list[tuple[str, int, float, float]]) -> pd.DataFrame:
    return pd.DataFrame([{STRATEGY: label, DAYS: days, RECOVERY: recovery, HIT_RATE: hit} for label, days, recovery, hit in rows])


def test_買い方は30日以上の中から回収率で選び_同じなら的中率で選ぶ() -> None:
    summary = _summary([("大当たり", 5, 9.0, 0.2), ("A", 40, 1.3, 0.01), ("B", 40, 1.3, 0.02), ("C", 30, 1.1, 0.5)])
    assert Win5StrategyChoice().choose(summary) == "B"
    assert Win5StrategyChoice().best(_summary([("少ない", 29, 2.0, 0.1)])) is None


def test_探索期間で100パーセントを超える買い方が無ければ選べる買い方なし() -> None:
    summary = _summary([("A", 40, 0.9, 0.01), ("B", 50, 1.0, 0.02)])
    assert Win5StrategyChoice().choose(summary) is None
    assert Win5StrategyChoice().best(summary) == "B"


def _judge_row(recovery: float, low: float = 0.5) -> pd.Series:
    return pd.Series({RECOVERY: recovery, LOW: low})


def test_採用の基準は回収率と幅の下の端と比べる相手で決める() -> None:
    judge = Win5AdoptionJudge()
    assert judge.judge(_judge_row(1.5, 1.1), _judge_row(0.7), _judge_row(0.8))[0] == ADOPTED
    assert judge.judge(_judge_row(1.5, 0.6), _judge_row(0.7), _judge_row(0.8))[0] == BY_CHANCE
    assert judge.judge(_judge_row(1.5, 1.1), _judge_row(1.6), _judge_row(0.8))[0] == NOT_REACHED
    verdict, reason = judge.judge(_judge_row(0.8, 0.3), _judge_row(0.7), _judge_row(0.6))
    assert verdict == NOT_REACHED and "100% を超えない" in reason


def _runner_rows(race_date: str, legs: list[tuple[bool, str]], field: int = 6) -> list[dict[str, object]]:
    rows = []
    for leg, (jump, post) in enumerate(legs, start=1):
        race_id = f"{race_date.replace('-', '')}0501010{leg}"
        for number in range(1, field + 1):
            rows.append({RACE_DATE: race_date, LEG: leg, RACE_ID: race_id, JUMP: jump, POST_TIME: post, HORSE_NO: number,
                         WIN_ODDS: float(number * 2)})
    return rows


def _predictions(race_ids: list[str], *, field: int = 6) -> pd.DataFrame:
    rows = [{"race_id": race_id, "race_date": "2024-05-26", "horse_no": number, "probability": 0.1 * (field + 1 - number),
             "fold": "2024年前半"} for race_id in race_ids for number in range(1, field + 1)]
    return pd.DataFrame(rows)


def test_日ごとの確率の表は時点を選び_障害はオッズで代え_予測の無い日は除く() -> None:
    legs = [(False, "1430"), (False, "1505"), (True, "1530"), (False, "1600"), (False, "1625")]
    runners = pd.DataFrame(_runner_rows("2024-05-26", legs) + _runner_rows("2024-06-02", legs) + _runner_rows("2023-01-08", legs))
    history = pd.DataFrame([{RACE_DATE: day, SATURDAY: False, CARRY: 0} for day in ("2023-01-08", "2024-05-26", "2024-06-02")])
    flat = [f"202405260501010{leg}" for leg in (1, 2, 4, 5)]
    race_day = _predictions(flat[:2])
    day_before = _predictions(flat[2:])
    folds = pd.DataFrame([{"fold": "2024年前半", "start": "2024-01-06", "end": "2024-06-30"}])
    days, skipped = Win5BacktestDays().of(history, runners, Win5FoldPredictions(race_day, day_before, folds))
    assert [day.race_date for day in days] == ["2024-05-26"]
    day = days[0]
    assert day.sources == (PredictionTiming.RACE_DAY.label, PredictionTiming.RACE_DAY.label, ODDS_ONLY,
                           PredictionTiming.DAY_BEFORE.label, PredictionTiming.DAY_BEFORE.label)
    assert all(math.isclose(leg["そろえた1着の確率"].sum(), 1.0) for leg in day.legs)
    jump = day.legs[2]
    assert np.allclose(jump["そろえた1着の確率"], jump["オッズから見た勝率"])
    assert skipped.set_index("開催日")["理由"].to_dict() == {"2023-01-08": NO_FOLD, "2024-06-02": NO_PREDICTION}


def _leg(race_id: str, odds: list[float], probability: list[float]) -> pd.DataFrame:
    table = pd.DataFrame({RACE_ID: race_id, HORSE_NO: list(range(1, len(odds) + 1)), WIN_ODDS: odds, WIN_PROBABILITY: probability})
    return RaceWinShare().of(table)


def test_1日の買い方と比べる相手は同じ精算で数え_線に届いた買い方だけ買う() -> None:
    legs = tuple(_leg(f"R{leg}", [8.0, 2.0, 4.0, 15.0, 30.0, 6.0], [0.10, 0.30, 0.20, 0.05, 0.15, 0.20]) for leg in range(5))
    day = Win5BacktestDay("2024-05-26", "2024年前半", False, 1_000_000, legs, ("当日",) * 5)
    history = pd.DataFrame({RACE_DATE: ["2024-05-19"], SATURDAY: [False], "発売票数": [4_000_000]})
    estimator = PayoutEstimator((1.0, 0.5), 0.0, 1.0, 0.5, 100)
    outcome = Win5Outcome("2024-05-26", (((2, 2, 3, 6, 5), 50_000),), False, NOTHING, 4_000_000, 1_000_000)
    rows = pd.DataFrame(Win5DayBets(history).settle(day, estimator, outcome))
    by_label = rows.set_index(STRATEGY)
    popularity = [2, 3, 6, 1, 4, 5]
    rule_sets = [Formation(tuple(tuple(popularity[3:6] if leg == hole else popularity[:2]) for leg in range(5))) for hole in range(5)]
    rule_payout = sum(Win5Settlement().settle(formation, outcome).payout for formation in rule_sets)
    assert by_label.loc[RULE, STAKE] == 24_000 and by_label.loc[RULE, PAYOUT] == rule_payout
    assert by_label.loc[RULE_CARRY, STAKE] == 24_000
    assert by_label.loc[popularity_label(20), STAKE] <= 2_000
    ours = rows.loc[rows[KIND] == OURS]
    assert set(ours[STRATEGY]) <= {strategy.label for strategy in STRATEGIES}
    assert (ours[EXPECTED_VALUE] >= ours[STRATEGY].str.extract(r"線([\d.]+)")[0].astype(float)).all()
    tiers = rows.loc[rows[KIND] == TIERED]
    judge_bought = bool((ours[STRATEGY] == TIER_JUDGE.label).any())
    assert (len(tiers) == len(TIER_CANDIDATES)) == judge_bought
    if judge_bought:
        assert (tiers[STAKE] <= tiers[BUDGET] * 100).all()
        assert (tiers[EXPECTED_VALUE] == float(ours.loc[ours[STRATEGY] == TIER_JUDGE.label, EXPECTED_VALUE].iloc[0])).all()
        adopted = tiers.loc[tiers[STRATEGY] == ADOPTED_TIER.label].iloc[0]
        favorite = math.prod(float(leg["そろえた1着の確率"].max()) for leg in legs)
        assert adopted["本命の確率の積"] == pytest.approx(favorite)
        assert (adopted[BUDGET], bool(adopted[LARGE_DAY])) == ((100, True) if favorite >= 0.0025 else (30, False))
        flat_50 = tiers.loc[tiers[STRATEGY] == "段階の予算（一律 50点）"].iloc[0]
        assert flat_50[STAKE] == ours.loc[ours[STRATEGY] == TIER_JUDGE.label, STAKE].iloc[0] and not flat_50[LARGE_DAY]


def _choice(points: int, hit: float, payout: float) -> FormationChoice:
    return FormationChoice(Formation(((1,) * 1, tuple(range(1, points + 1)), (1,), (1,), (1,))), hit, payout)


def test_段階の予算の候補は多く買う日の決め方ごとに予算を決める() -> None:
    judge, small, large = _choice(50, 0.02, 7_500.0), _choice(30, 0.015, 4_500.0), _choice(100, 0.03, 14_000.0)
    adopted = ADOPTED_TIER
    assert adopted.label == "段階の予算（本命の確率の積 0.0025 以上は 100点、ほか 30点）" and adopted.budgets == (30, 50, 100)
    assert adopted.is_large(judge, small, large, 0.0025) and not adopted.is_large(judge, small, large, 0.0024)
    assert adopted.budget_for(True) == 100 and adopted.budget_for(False) == 30
    flat = Win5TierStrategy(Win5TierSignal.FLAT, math.nan, 30, 30)
    assert flat.flat and flat.label == "段階の予算（一律 30点）" and not flat.is_large(judge, small, large, 0.9) and flat.budget_for(False) == 30
    by_hit = Win5TierStrategy(Win5TierSignal.HIT_PROBABILITY, 0.0175, 30, 100)
    assert by_hit.is_large(judge, small, large, 0.0) and not by_hit.is_large(_choice(50, 0.017, 7_500.0), small, large, 0.0)
    by_value = Win5TierStrategy(Win5TierSignal.EXPECTED_VALUE, 1.50, 30, 100)
    assert judge.expected_value == pytest.approx(1.5) and by_value.is_large(judge, small, large, 0.0)
    assert not by_value.is_large(_choice(50, 0.02, 7_000.0), small, large, 0.0)
    marginal = Win5TierStrategy(Win5TierSignal.MARGINAL_VALUE, 1.00, 30, 100)
    assert Win5TierSignal.MARGINAL_VALUE.value_of(judge, small, large, 0.0) == pytest.approx((14_000 - 4_500) / 7_000)
    assert marginal.is_large(judge, small, large, 0.0) and not marginal.is_large(judge, small, _choice(100, 0.03, 11_000.0), 0.0)
    assert not marginal.is_large(judge, small, small, 0.0)
    assert marginal.label == "段階の予算（追加の点の期待値 1.00 以上は 100点、ほか 30点）"
    assert TIER_BUDGETS == (30, 50, 100, 150, 200) and TIER_JUDGE.label == "1着の確率の順・50点・線1.25"
    assert len({strategy.label for strategy in TIER_CANDIDATES}) == len(TIER_CANDIDATES) and ADOPTED_TIER in TIER_CANDIDATES


def test_段階の予算の候補の表は期間ごとに多く買う日と年あたりの金額を出す() -> None:
    rows = []
    for label, days, big, stakes, payouts in (
        (ADOPTED_TIER.label, ("2019-01-06", "2020-02-02", "2025-03-02"), (True, False, True), (10_000, 3_000, 9_600), (0, 30_000, 0)),
        ("段階の予算（一律 30点）", ("2019-01-06", "2020-02-02", "2025-03-02"), (False, False, False), (3_000, 3_000, 3_000), (0, 30_000, 0)),
    ):
        for day, large, stake, payout in zip(days, big, stakes, payouts, strict=True):
            rows.append({STRATEGY: label, KIND: TIERED, BUDGET: 100 if large else 30, "開催日": day, STAKE: stake, PAYOUT: payout,
                         HIT: payout > 0, "キャリーオーバーの日": False, EXPECTED_VALUE: 1.4, LARGE_DAY: large, "本命の確率の積": 0.003,
                         "期間": EXPLORE if day < "2025" else CONFIRM})
    table = Win5TierReport().table(pd.DataFrame(rows))
    assert table.columns[:3] == ["決め方", "期間", "多く買う日"] and table.columns[-2:] == ["年あたりの金額（円）", "印"]
    by_key = {(row[0], row[1]): row for row in table.rows}
    adopted_explore = by_key[(ADOPTED_TIER.rule_text, EXPLORE)]
    assert adopted_explore[2] == 1 and adopted_explore[3] == 2 and adopted_explore[4] == 13_000 and adopted_explore[5] == 30_000
    assert adopted_explore[-2] == 6_500 and adopted_explore[-1] == ADOPTED_MARK
    adopted_confirm = by_key[(ADOPTED_TIER.rule_text, CONFIRM)]
    assert adopted_confirm[2] == 1 and adopted_confirm[3] == 1 and adopted_confirm[-2] == 9_600
    flat = by_key[("一律 30点", EXPLORE)]
    assert flat[2] == 0 and flat[4] == 6_000 and flat[-1] == ""
    assert by_key[("一律 200点", CONFIRM)][3] == 0
    assert len(table.rows) == 2 * len(TIER_CANDIDATES)


def test_実際の予想の記録は買う日で結果のある日だけ精算する(tmp_path: Path) -> None:
    folder = tmp_path / "記録"
    folder.mkdir()
    old = {"判断": "買う", "予算": 2, "買い目": [[1, 2], [3], [4], [5], [6]], "日の期待値": 1.4, "キャリーオーバー": 0}
    tiered = {**old, "判断": "買う（多く）", "予算": 4, "買い目": [[1, 2], [3], [4], [5], [6, 7]], "判断用の期待値": 1.3, "本命の確率の積": 0.003}
    (folder / "2024-05-26.json").write_bytes(json.dumps(old, ensure_ascii=False).encode("utf-8"))
    (folder / "2024-06-02.json").write_bytes(json.dumps({**old, "判断": "見送り"}, ensure_ascii=False).encode("utf-8"))
    (folder / "2024-06-09.json").write_bytes(json.dumps(tiered, ensure_ascii=False).encode("utf-8"))
    (folder / "2024-06-16.json").write_bytes(json.dumps({**tiered, "判断": "買う（少なく）"}, ensure_ascii=False).encode("utf-8"))
    outcomes = {"2024-05-26": Win5Outcome("2024-05-26", (((2, 3, 4, 5, 6), 9_000),), False, NOTHING, 1_000_000, 0),
                "2024-06-09": Win5Outcome("2024-06-09", (((1, 3, 4, 5, 7), 20_000),), False, NOTHING, 1_000_000, 0)}
    rows, note = Win5RecordBets(tmp_path).rows(outcomes)
    assert [row[STRATEGY] for row in rows] == [RECORDED, RECORDED]
    assert (rows[0][STAKE], rows[0][PAYOUT], rows[0][HIT], rows[0][LARGE_DAY]) == (200, 9_000, True, False)
    assert (rows[1][STAKE], rows[1][PAYOUT], rows[1][HIT], rows[1][LARGE_DAY], rows[1][BUDGET]) == (400, 20_000, True, True, 4)
    assert rows[1][EXPECTED_VALUE] == 1.3 and rows[1]["本命の確率の積"] == 0.003 and math.isnan(rows[0]["本命の確率の積"])
    assert "記録 4日" in note and "買う 3日" in note and "結果の出た日 2日" in note


@pytest.fixture(scope="module")
def win5_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    sample = Win5Sample()
    sample.build()
    return synth.build_db(tmp_path_factory.mktemp("win5_stats") / "win5.duckdb", sample.sample)


def _write_predictions(win5_db: Path, folder: Path) -> tuple[Path, Path]:
    """合成DB の過去の WIN5 の対象レースに、オッズから見た勝率に近い架空の1着の確率を付けた予測（テスト期間は 2024年3月から）。"""
    with db.open_db(win5_db) as con:
        runners = Win5LegRunnerHistoryRepository(con).read(FORECAST_DAY)
    probability = (1.0 / runners[WIN_ODDS]) * (1.0 + 0.05 * (runners[HORSE_NO] % 3))
    table = pd.DataFrame({
        "レースID": runners[RACE_ID], "開催日": pd.to_datetime(runners[RACE_DATE]), "馬ID": runners[RACE_ID] + runners[HORSE_NO].astype(str),
        "馬番": runners[HORSE_NO].astype("int32"), "LightGBM": probability, "CatBoost": probability, "確率": probability,
        "区切り": "2024年前半", "期間": np.where(runners[RACE_DATE] >= "2024-03-01", "テスト", "検証"), "区分": "全体",
    })
    paths = folder / "race_day.pkl", folder / "day_before.pkl"
    for path in paths:
        table.to_pickle(path)
    return paths


def test_win5の表を出して結果と精算をファイルに書く(win5_db: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    race_day, day_before = _write_predictions(win5_db, tmp_path)
    args = build_parser().parse_args(["--db", str(win5_db), "--win5", str(race_day), str(day_before), "--out-dir", str(tmp_path / "out")])
    Win5Stats(tmp_path / "予想の置き場所").run(args)
    report = (tmp_path / "out" / REPORT_NAME).read_text(encoding="utf-8")
    for title in ("WIN5 の確かめの条件", "WIN5 の確かめに使った日", "WIN5 の探索期間の 40 通り", "WIN5 の予算ごとのいちばん良い買い方",
                  "WIN5 の選んだ買い方と比べる相手", "WIN5 の採用の判定", "WIN5 の段階の予算の候補（探索期間と確認期間）",
                  "WIN5 の買い方ごと・期間ごとの成績", "1着の確率のレースの中のログ損失", "WIN5 の配当の見積もりの式"):
        assert title in report
    assert "選べる買い方なし" in report and "実際の予想の記録 0日" in report
    assert ADOPTED_TIER.label in report and ADOPTED_TIER.rule_text in report
    settled = pd.read_csv(tmp_path / "out" / SETTLED_NAME, encoding="utf-8-sig")
    with db.open_db(win5_db) as con:
        history = Win5HistoryRepository(con).read(FORECAST_DAY)
    tested_days = history.loc[history[RACE_DATE] >= "2024-03-01", RACE_DATE].nunique()
    assert settled.loc[settled[STRATEGY] == RULE, RACE_DATE].nunique() == tested_days
    assert settled.loc[settled[STRATEGY] == RULE, STAKE].eq(24_000).all()
    assert "WIN5 の探索期間の 40 通り" in capsys.readouterr().out
    assert settled[RACE_DATE].min() >= "2024-03-01"


def test_win5に渡す予測は2つか0(tmp_path: Path) -> None:
    args = build_parser().parse_args(["--win5", "only_one.pkl", "--out-dir", str(tmp_path)])
    with pytest.raises(ValueError, match="2つ"):
        main(args)


def test_予算を渡すとその予算の買い方の中から選ぶ(win5_db: Path, tmp_path: Path) -> None:
    race_day, day_before = _write_predictions(win5_db, tmp_path)
    args = build_parser().parse_args(["--db", str(win5_db), "--win5", str(race_day), str(day_before), "--win5-budget", "50",
                                      "--out-dir", str(tmp_path / "out")])
    Win5Stats(tmp_path / "予想の置き場所").run(args)
    report = (tmp_path / "out" / REPORT_NAME).read_text(encoding="utf-8")
    assert "予算 50点の買い方の中から選んだ" in report
    with pytest.raises(ValueError, match="--win5-budget"):
        Win5Stats._within_budget(pd.DataFrame({STRATEGY: []}), 30)
