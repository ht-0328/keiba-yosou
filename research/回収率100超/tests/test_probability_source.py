"""確率の出どころを替えて比べる部品のテスト。架空の値だけを使い、元DB もモデルの学習も使わない。"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from yosou.form_aptitude_top3.setting import DEFAULT_SETTINGS_PATH
from yosou.shared.setting import HyperparameterSettings

from 既存モデルの改善.analysis.walk_forward import PART, PART_TEST, PART_VALID, PREDICTION_COLUMN, SEGMENT, WINDOW
from 回収率100超.analysis.backtest import (
    TOTAL_LABEL,
    LineStudyTable,
    PaybackInterval,
    PaybackSummary,
    PlaceLineChoice,
    PlaceLineResult,
    PlaceLineStudy,
    StakedPayback,
    YearlyPaybackTable,
)
from 回収率100超.analysis.probability_source import (
    AVERAGE,
    MODEL,
    MODEL_PROBABILITY,
    ORIGINAL,
    SOURCES,
    ProbabilitySourceBacktest,
    ProbabilitySourceTable,
    RaceDayModelPredictions,
    SourceAdoptionRule,
    SourceComparisonReport,
    SourceLogLoss,
    SourceResult,
    SourceVerdicts,
    TrainingThreads,
    YearlyWindows,
)


def test_年ごとの区切りは直前の1年で木の本数を決めその年を予測する() -> None:
    windows = YearlyWindows(2019, 2021).build()
    assert [window.name for window in windows] == ["2019年", "2020年", "2021年"]
    first = windows[0]
    assert (first.valid_first_day, first.test_first_day, first.test_last_day) == (date(2018, 1, 1), date(2019, 1, 1),
                                                                                  date(2019, 12, 31))
    with pytest.raises(ValueError):
        YearlyWindows(2022, 2021)


class _FakeRunner:
    """学習の代わりに、渡した予測の表をそのまま返す。"""

    def __init__(self, predictions: pd.DataFrame) -> None:
        self._predictions = predictions
        self.variant = None

    def run(self, data, variant):
        self.variant = variant
        return self._predictions, pd.DataFrame({"木の数": [3]})


def test_当日のモデルの予測はテストの年の行だけを元の予測と同じ鍵にする() -> None:
    predictions = pd.DataFrame({
        "レースID": [2019010101010101, 2019010101010101, 2018010101010101], "開催日": pd.to_datetime(["2019-01-05", "2019-01-05", "2018-01-05"]),
        "馬ID": ["a", "b", "c"], "馬番": [1.0, 2.0, 1.0], PREDICTION_COLUMN: [0.6, 0.2, 0.5],
        WINDOW: ["2019年"] * 3, PART: [PART_TEST, PART_TEST, PART_VALID], SEGMENT: ["全体"] * 3,
    })
    runner = _FakeRunner(predictions)
    frame, log = RaceDayModelPredictions(runner, variant="pool").run(data=None)
    assert runner.variant == "pool" and list(log.columns) == ["木の数"]
    assert frame["rid"].tolist() == ["2019010101010101"] * 2 and frame["horse_no"].tolist() == [1, 2]
    assert frame["year"].tolist() == [2019, 2019] and frame[MODEL_PROBABILITY].tolist() == [0.6, 0.2]


def _original(rid: str, horses: list[int], probabilities: list[float], year: int = 2019) -> pd.DataFrame:
    return pd.DataFrame({"rid": rid, "horse_no": horses, "year": year, "day": date(year, 1, 5), "win_odds": 5.0,
                         "placed": [1] + [0] * (len(horses) - 1), "place_payout": [150] + [0] * (len(horses) - 1),
                         "3着以内の確率": probabilities, "想定払戻倍率": 2.0, "複勝の期待値": [p * 2.0 for p in probabilities]})


def test_新しい確率はレース内で対象着順の数にそろえ直してから元の行と突き合わせる() -> None:
    # 8頭立て（3着まで）。元の予測には 1〜7番だけがある（8番は複勝オッズが無かった想定）
    original = _original("r1", list(range(1, 8)), [0.6, 0.5, 0.4, 0.4, 0.4, 0.4, 0.3])
    model = pd.DataFrame({"rid": "r1", "horse_no": list(range(1, 9)), "year": 2019,
                          MODEL_PROBABILITY: [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]})
    table = ProbabilitySourceTable().build(original, model)
    assert len(table) == 7, "両方にある馬だけ残る"
    # 8頭で合計 3 にそろえるので 1頭 0.375。元の行に絞る前にそろえ直す
    assert table[MODEL].tolist() == pytest.approx([0.375] * 7)
    assert table[AVERAGE].tolist() == pytest.approx([(p + 0.375) / 2 for p in [0.6, 0.5, 0.4, 0.4, 0.4, 0.4, 0.3]])
    assert table["想定払戻倍率"].tolist() == [2.0] * 7 and list(table.columns[:3]) == ["rid", "horse_no", "year"]


def test_7頭以下のレースは2着までにそろえ直す() -> None:
    original = _original("r2", [1, 2, 3, 4, 5], [0.4] * 5)
    model = pd.DataFrame({"rid": "r2", "horse_no": [1, 2, 3, 4, 5], "year": 2019, MODEL_PROBABILITY: [0.2] * 5})
    table = ProbabilitySourceTable().build(original, model)
    assert table[MODEL].sum() == pytest.approx(2.0)


def _table(rows_per_year: int = 400) -> pd.DataFrame:
    """2019〜2026年。期待値 1.2 の馬（当たりで払戻 150）と、期待値 1.1 の馬（外れ）が同じ数ずつ。"""
    frames = []
    for year in range(2019, 2027):
        count = rows_per_year
        frames.append(pd.DataFrame({
            "rid": [f"{year}-{i}" for i in range(count)] * 2, "horse_no": [1] * count + [2] * count, "year": year,
            "day": [date(year, 1, 1 + i % 28) for i in range(count)] * 2, "win_odds": 5.0,
            "placed": [1] * count + [0] * count, "place_payout": [150] * count + [0] * count, "想定払戻倍率": 2.0,
            ORIGINAL: [0.6] * count + [0.55] * count, MODEL: [0.55] * count + [0.6] * count,
        }))
    table = pd.concat(frames, ignore_index=True)
    table[AVERAGE] = (table[ORIGINAL] + table[MODEL]) / 2
    return table


def _fast_backtest() -> ProbabilitySourceBacktest:
    return ProbabilitySourceBacktest(PlaceLineChoice(StakedPayback(rounds=50)), YearlyPaybackTable(PaybackInterval(rounds=50)))


def test_出どころごとに線を前半だけで選び選んだ線の買い目で年ごとの成績を出す() -> None:
    result = _fast_backtest().run(_table(), ORIGINAL)
    # 期待値 1.2 の馬だけを買える線のうち、いちばん低い 1.15 が選ばれる（1.10 以下は外れの馬も入って回収率が下がる）
    assert result.line == 1.15 and len(result.bought) == 400 * 8
    assert result.total_rate == pytest.approx(150.0) and result.total_low > 100
    assert result.yearly["年"].tolist() == [*range(2019, 2027), TOTAL_LABEL]
    assert result.late is not None and result.late.rate == pytest.approx(150.0)


def test_新しい確率が外れの馬を高く見ると線が選べず買い目は空になる() -> None:
    result = _fast_backtest().run(_table(), MODEL)
    assert result.line is None and result.bought.empty and result.late is None
    assert np.isnan(result.total_rate)


def _result(name: str, line: float | None, total_rate: float, total_low: float, late_rate: float,
            late_low: float) -> SourceResult:
    summary = PaybackSummary(100, 10, 10000.0, late_rate * 100, late_rate, late_low, late_rate + 10)
    chosen = None if line is None else PlaceLineResult(line, summary, summary)
    yearly = pd.DataFrame([{"年": TOTAL_LABEL, "買い目": 100, "的中率": 0.1, "回収率": total_rate,
                            "90%の下限": total_low, "90%の上限": total_rate + 10}])
    return SourceResult(name, PlaceLineStudy((), chosen), pd.DataFrame(), yearly)


def test_採用の基準は全期間と後半の両方で見る() -> None:
    rule = SourceAdoptionRule()
    original = _result(ORIGINAL, 1.25, 120.0, 106.0, 124.0, 104.0)
    better = rule.judge(_result(MODEL, 1.2, 125.0, 108.0, 130.0, 105.0), original)
    assert better.usable and better.better_than_original and better.text == "採用できる（元より良い）"
    not_better = rule.judge(_result(MODEL, 1.2, 125.0, 108.0, 120.0, 105.0), original)
    assert not_better.usable and not not_better.better_than_original
    assert not_better.text == "100% は超えるが、元より良いとは言えない"
    low_bound = rule.judge(_result(MODEL, 1.2, 125.0, 99.0, 130.0, 105.0), original)
    assert not low_bound.usable and low_bound.text == "採用できない"
    no_line = rule.judge(_result(MODEL, None, float("nan"), float("nan"), 0.0, 0.0), original)
    assert not no_line.usable
    weak_late_bound = rule.judge(_result(MODEL, 1.2, 125.0, 108.0, 130.0, 99.0), original)
    assert weak_late_bound.usable and not weak_late_bound.better_than_original


def test_判定の集まりは元より良い出どころがあるかを答える() -> None:
    rule = SourceAdoptionRule()
    original = _result(ORIGINAL, 1.25, 120.0, 106.0, 124.0, 104.0)
    verdicts = SourceVerdicts({MODEL: rule.judge(_result(MODEL, 1.2, 90.0, 80.0, 90.0, 80.0), original),
                               AVERAGE: rule.judge(_result(AVERAGE, 1.2, 125.0, 108.0, 130.0, 105.0), original)})
    assert verdicts.any_better and not verdicts.of(MODEL).usable and verdicts.of(AVERAGE).better_than_original


def test_ログ損失は年ごとと全期間を出す() -> None:
    table = pd.DataFrame({"year": [2019, 2019, 2020, 2020], "placed": [1, 0, 1, 0],
                          ORIGINAL: [0.9, 0.1, 0.9, 0.1], MODEL: [0.5, 0.5, 0.5, 0.5]})
    frame = SourceLogLoss().by_year(table, (ORIGINAL, MODEL))
    assert frame["年"].tolist() == [2019, 2020, TOTAL_LABEL] and frame["頭数"].tolist() == [2, 2, 4]
    assert frame[MODEL].tolist() == pytest.approx([round(float(np.log(2)), 5)] * 3)
    assert (frame[ORIGINAL] < frame[MODEL]).all()


def test_スレッド数だけを設定に入れる() -> None:
    defaults = HyperparameterSettings.load(None, defaults=DEFAULT_SETTINGS_PATH)
    changed = TrainingThreads(4).apply(defaults)
    assert changed.lightgbm.params["n_jobs"] == 4 and changed.catboost.params["thread_count"] == 4
    assert changed.lightgbm.params["learning_rate"] == defaults.lightgbm.params["learning_rate"]
    assert "n_jobs" not in defaults.lightgbm.params, "元の設定は変えない"
    with pytest.raises(ValueError):
        TrainingThreads(0)


def test_結果の文書は判定と出どころごとの表を持つ() -> None:
    table = _table(rows_per_year=320)
    backtest = _fast_backtest()
    results = {source: backtest.run(table, source) for source in SOURCES}
    rule = SourceAdoptionRule()
    verdicts = SourceVerdicts({name: rule.judge(result, results[ORIGINAL]) for name, result in results.items()
                               if name != ORIGINAL})
    text = SourceComparisonReport().build(results, verdicts, SourceLogLoss().by_year(table, SOURCES), len(table), (2019, 2026))
    assert text.startswith("# 回収率100超 — 確率の出どころを替えて")
    assert "## 判定" in text and f"## {ORIGINAL}" in text and f"## {MODEL}" in text and f"## {AVERAGE}" in text
    assert "## 確率の当たり具合" in text and "## 元と同じ買い目をどれだけ買ったか" in text
    assert "採用できない" in text, "新しい確率は線が選べないので採用できない"


def test_年ごとの表と線の表は共通の部品で作る() -> None:
    bought = pd.DataFrame({"year": [2019, 2019, 2020], "day": ["a", "a", "b"], "place_payout": [0, 300, 0]})
    yearly = YearlyPaybackTable(PaybackInterval(rounds=20)).build(bought)
    assert yearly["年"].tolist() == [2019, 2020, TOTAL_LABEL] and yearly["回収率"].tolist() == [150.0, 0.0, 100.0]
    summary = PaybackSummary(10, 1, 1000.0, 1200.0, 120.0, 90.0, 150.0)
    study = PlaceLineStudy((PlaceLineResult(1.0, summary, summary),), None)
    line_table = LineStudyTable().build(study)
    assert line_table.loc[0, "線"] == 1.0 and line_table.loc[0, "後半の回収率"] == 120.0
