"""重賞の予想の作り直しの確かめ（表・作り方・重賞の行の取り出し・採用の基準・比べ方の表）。合成データだけを使う。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID
from yosou.shared.feature import PredictionTiming

from 既存モデルの改善.analysis.stakes_rebuild import (
    MIN_BETTER_WINDOWS,
    REBUILD_COMPARISONS,
    REBUILD_TABLES,
    REBUILD_VARIANTS,
    AdoptionRule,
    StakesRebuildComparison,
    StakesRowFilter,
    rebuild_table_named,
)
from 既存モデルの改善.analysis.walk_forward import PART, PART_TEST, PREDICTION_COLUMN, WINDOW
from 既存モデルの改善.analysis.windows import STAKES_WINDOWS

from .test_stakes_walk_forward import _predictions, _synthetic_stakes


def test_the_tables_cover_the_stakes_and_the_form_materials_from_2012():
    names = [table.name for table in REBUILD_TABLES]
    assert names == ["stakes_ability", "stakes_race_day", "form_ability", "form_race_day",
                     "stakes_ability_floor", "stakes_race_day_floor"]
    assert all(table.period.train_first_day.year == 2012 for table in REBUILD_TABLES)
    # 重賞だけの表は、同じ材料の全レースの表に K の10個を足したもの
    for stakes, form in (("stakes_ability", "form_ability"), ("stakes_race_day", "form_race_day")):
        assert rebuild_table_named(stakes).catalog.names == rebuild_table_named(form).catalog.names + tuple(
            feature.name for feature in rebuild_table_named(stakes).catalog.features if feature.group == "K")


def test_the_variants_use_the_columns_of_their_timing_and_baseline_from_day_before():
    keys = [variant.key for variant in REBUILD_VARIANTS]
    assert len(set(keys)) == len(keys) == 14
    for variant in REBUILD_VARIANTS:
        catalog = rebuild_table_named(variant.model).catalog
        assert set(variant.columns) <= set(catalog.columns_for(variant.timing))
        assert variant.uses_baseline == (variant.timing is not PredictionTiming.THURSDAY)
    # 時点ごとの比べ方は3つで、木曜のオッズだけは当日のもの。作り直しと傾向を外したものの差は K だけ
    assert [spec.timing for spec in REBUILD_COMPARISONS] == list(PredictionTiming)
    thursday = REBUILD_COMPARISONS[0]
    assert thursday.odds_reference.key == "odds_only-race_day" and thursday.general.model == "form_ability"
    assert len(set(thursday.candidate.columns) - set(thursday.without_tendency.columns)) == 9
    race_day = REBUILD_COMPARISONS[2]
    assert len(set(race_day.candidate.columns) - set(race_day.without_tendency.columns)) == 10


def test_the_row_filter_keeps_only_the_stakes_runners():
    stakes_ids = pd.DataFrame({RACE_ID: ["r1", "r1"], HORSE_ID: ["a", "b"]})
    predictions = pd.DataFrame({RACE_ID: ["r1", "r1", "r2"], HORSE_ID: ["a", "b", "c"], PREDICTION_COLUMN: [0.5, 0.4, 0.3]})
    kept = StakesRowFilter(stakes_ids).apply(predictions)
    assert kept[HORSE_ID].tolist() == ["a", "b"] and list(kept.columns) == list(predictions.columns)


def test_the_adoption_rule_needs_five_windows_and_the_overall():
    rule = AdoptionRule()
    windows = [f"{year}年" for year in range(2020, 2027)]
    reference = pd.Series([0.41] * 7, index=windows)
    five_better = pd.Series([0.40] * 5 + [0.42] * 2, index=windows)
    verdict = rule.verdict(five_better, reference, 0.405, 0.41)
    assert verdict.better_windows == MIN_BETTER_WINDOWS == 5 and verdict.passes
    four_better = pd.Series([0.40] * 4 + [0.42] * 3, index=windows)
    assert not rule.verdict(four_better, reference, 0.405, 0.41).passes
    # 区切りでは勝っても、全期間で負ければ合格しない。採用は両方の比べ先に合格したときだけ
    assert not rule.verdict(five_better, reference, 0.412, 0.41).passes
    assert rule.adopted(verdict, verdict) and not rule.adopted(verdict, rule.verdict(four_better, reference, 0.405, 0.41))


def test_the_comparison_judges_the_candidate_against_both_references():
    data = _synthetic_stakes(np.random.default_rng(2))
    base = data.evaluation["オッズから見た3着以内率"]
    sharper = base * 0.5 + data.label * 0.5
    spec = REBUILD_COMPARISONS[2]
    predictions = {
        spec.candidate.key: _predictions(data, sharper), spec.floor.key: _predictions(data, base),
        spec.without_tendency.key: _predictions(data, sharper * 0.98 + 0.01),
        spec.general.key: _predictions(data, base), spec.odds_reference.key: _predictions(data, base),
    }
    comparison = StakesRebuildComparison(spec, data, predictions, STAKES_WINDOWS[:2])
    tables = comparison.tables()
    assert [table.title for table in tables][:2] == [
        "重賞の作り直し（当日）: 区切りごとの確率の誤差（テスト期間）", "重賞の作り直し（当日）: 採用の基準に照らした判定"]
    by_window = tables[0]
    assert {"作り直しがオッズだけより小さい", "作り直しが手本より小さい"} <= set(by_window.columns)
    assert all(row[-1] == "はい" and row[-2] == "はい" for row in by_window.rows)
    against_odds, against_general = comparison.verdicts()
    assert against_odds.better_windows == 2 and against_general.overall_better
    # 2つの区切りしか無いので 5 / 7 には届かず、判定の表の最後の行は「採用しない」
    assert tables[1].rows[-1][-1].startswith("採用しない")
    assert any("1番人気を上回った区切り" in column for column in tables[3].columns)


def test_the_comparison_uses_only_the_rows_every_variant_has():
    data = _synthetic_stakes(np.random.default_rng(3))
    base = data.evaluation["オッズから見た3着以内率"]
    spec = REBUILD_COMPARISONS[2]
    full = _predictions(data, base)
    partial = full[~((full[PART] == PART_TEST) & (full[WINDOW] == STAKES_WINDOWS[0].name) & (full[HORSE_ID] == "h1"))]
    predictions = {key: full for key in (spec.candidate.key, spec.floor.key, spec.without_tendency.key, spec.odds_reference.key)}
    predictions[spec.general.key] = partial
    pooled = StakesRebuildComparison(spec, data, predictions, STAKES_WINDOWS[:2]).tables()[2]
    heads = [row[1] for row in pooled.rows]
    assert len(set(heads)) == 1 and heads[0] == len(partial[partial[PART] == PART_TEST])


def test_the_tendency_floor_zeroes_the_gaps_of_races_with_few_editions():
    from yosou.shared.dataset import TrainingData
    from yosou.stakes_tendency_top3.feature import RACE_DAY_CATALOG

    from 既存モデルの改善.analysis.stakes_rebuild import MIN_EDITIONS, TendencyFloor

    names = list(RACE_DAY_CATALOG.names)
    features = pd.DataFrame(0.05, index=[0, 1], columns=names).assign(**{"重賞の過去開催の数": [MIN_EDITIONS - 1, MIN_EDITIONS]})
    data = TrainingData(pd.DataFrame({RACE_ID: ["r1", "r2"]}), features, pd.DataFrame({"3着以内": [0, 1]}),
                        pd.DataFrame(index=[0, 1]), RACE_DAY_CATALOG, "3着以内")
    floored = TendencyFloor().apply(data).features
    # 開催が少ないレースは K のずれが 0。過去開催の数と K 以外の列、開催の多いレースはそのまま
    assert floored.loc[0, "1番人気の信頼度のずれ"] == 0.0 and floored.loc[0, "重賞の過去開催の数"] == MIN_EDITIONS - 1
    assert floored.loc[0, "単勝オッズ"] == 0.05 and floored.loc[1, "1番人気の信頼度のずれ"] == 0.05
    assert data.features.loc[0, "1番人気の信頼度のずれ"] == 0.05  # 元の表は変えない
