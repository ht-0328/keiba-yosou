import numpy as np
import pandas as pd
import pytest

from yosou.custom_binary.feature.registrations import default_registry
from yosou.shared.feature.feature_kind import FeatureKind

from 特徴量の組み合わせ探索.analysis.condition_bins import ConditionBins
from 特徴量の組み合わせ探索.analysis.model_configs import model_configs
from 特徴量の組み合わせ探索.analysis.popularity_bands import PopularityBands
from 特徴量の組み合わせ探索.analysis.race_segments import RaceSegments
from 特徴量の組み合わせ探索.analysis.roi_scan import NO_CONDITION, RoiScan
from 特徴量の組み合わせ探索.analysis.rule_selection import RuleSelection
from 特徴量の組み合わせ探索.analysis.search_periods import SearchPeriods


def test_numeric_bins_cover_all_values_and_match_conditions():
    values = pd.Series([float(v) for v in range(1, 11)] + [None])
    bins = ConditionBins.fit("枠番", values, FeatureKind.NUMERIC, np.ones(len(values), dtype=bool))
    assert (bins.codes[:-1] >= 0).all() and bins.codes[-1] == -1
    # 番号ごとの範囲（YAML に書く値）が、実際に入った値をちょうど含む。
    for code, (_, spec) in bins.labels.items():
        inside = values[bins.codes == code]
        assert inside.min() >= spec.get("min", -np.inf) and inside.max() <= spec.get("max", np.inf)
    assert "min" not in bins.labels[0][1] and "max" not in bins.labels[max(bins.labels)][1]


def test_categorical_bins_skip_rare_and_missing(monkeypatch):
    import 特徴量の組み合わせ探索.analysis.condition_bins as module
    monkeypatch.setattr(module, "MIN_VALUE_RUNS", 2)
    values = pd.Series(["東京", "東京", "中山", "nan", "nan", "nan"])
    bins = ConditionBins.fit("競馬場", values, FeatureKind.CATEGORICAL, np.ones(6, dtype=bool))
    assert bins.labels == {0: ("競馬場が東京", ["東京"])}
    assert bins.codes.tolist() == [0, 0, -1, -1, -1, -1]


def test_segments_and_scan_counts():
    frame = pd.DataFrame({
        "芝ダ": ["芝", "芝", "ダート", "芝"], "競馬場": ["東京"] * 4, "馬場状態": ["良"] * 4,
        "距離": [1200.0, 1200.0, 1800.0, 2400.0],
    })
    segments = RaceSegments.of(frame)
    labels = segments.labels["芝ダ×距離帯"]
    names = {labels[code][0]: labels[code][1] for code in segments.codes["芝ダ×距離帯"]}
    assert names["芝・短距離"] == {"芝ダ": ["芝"], "距離": {"max": 1400}}
    assert names["芝・長距離"] == {"芝ダ": ["芝"], "距離": {"min": 2201}}
    rows = pd.DataFrame({"win_payout": [500, 0, 0, 0], "place_payout": [200, 150, 0, 0], "popularity": [8, 1, 2, 12]})
    periods = pd.Series(["見つける"] * 4)
    counts = RoiScan(rows, periods, segments, PopularityBands(rows["popularity"])).run([])
    sprint = counts[(counts["区分"] == "芝・短距離") & (counts["人気帯"] == "全人気") & (counts["特徴量"] == NO_CONDITION)]
    assert sprint[["点数", "単勝払戻", "複勝払戻", "複勝的中"]].iloc[0].tolist() == [2, 5.0, 3.5, 2]
    bands = counts[(counts["区分の段"] == "全レース") & (counts["人気帯"] == "10番人気以下")]
    assert bands["点数"].iloc[0] == 1 and bands["人気の範囲"].iloc[0] == {"min": 10}


def test_rule_selection_uses_discover_then_confirm():
    base = {"区分の段": "全レース", "区分": "全レース", "人気帯": "全人気", "特徴量": "x", "区分の条件": {},
            "人気の範囲": {}, "馬の条件の値": None, "単勝払戻2乗": 1.0, "単勝的中": 1, "複勝払戻": 0.0,
            "複勝払戻2乗": 0.0, "複勝的中": 0}
    rows = []
    for rule, (discover, confirm) in {"通過": (1.2, 1.05), "確かめで落ちる": (1.2, 0.9), "候補外": (1.0, 1.5)}.items():
        for period, rate, bets in (("見つける", discover, 300), ("確かめる", confirm, 100), ("テスト", 1.0, 100)):
            rows.append({**base, "馬の条件": rule, "期間": period, "点数": bets, "単勝払戻": rate * bets})
    wide = RuleSelection().wide(pd.DataFrame(rows), "単勝")
    assert RuleSelection().adopted(wide)["馬の条件"].tolist() == ["通過"]
    assert wide.loc[wide["馬の条件"] == "通過", "見つける_回収率"].iloc[0] == pytest.approx(1.2)


def test_periods_are_ordered():
    days = pd.Series(pd.to_datetime(["2016-12-31", "2017-01-01", "2023-01-01", "2025-06-01"]))
    names = SearchPeriods().names(days)
    assert pd.isna(names.iloc[0]) and names.iloc[1:].tolist() == ["見つける", "確かめる", "テスト"]


@pytest.mark.parametrize("group", ["form", "pool"])
def test_every_model_config_is_a_valid_custom_binary_setting(group):
    registry = default_registry()
    configs = model_configs(group)
    assert len({config.name for config in configs}) == len(configs)
    for config in configs:
        settings = config.settings(registry, SearchPeriods())
        assert settings.selected == config.features
        assert "人気順位" not in settings.selected or "odds" in config.name
