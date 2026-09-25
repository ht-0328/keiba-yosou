from dataclasses import dataclass
from types import SimpleNamespace

import pandas as pd
import pytest

from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.feature_kind import FeatureKind

from ..feature.builder import SelectedFeatureBuilder
from ..feature.builtin import GROUPS
from ..feature.registry import FeatureRegistry
from ..feature.registrations import default_registry


@dataclass
class ExampleFeature:
    name: str = "追加項目"
    dependencies: tuple[str, ...] = ()
    known_from: PredictionTiming = PredictionTiming.THURSDAY
    kind: FeatureKind = FeatureKind.NUMERIC
    description: str = "テスト用の1項目"
    calls: int = 0

    def compute(self, records, dependencies):
        self.calls += 1
        return sum(dependencies.values(), start=records.entries["value"].copy())


def test_dependency_order_single_execution_and_only_selected_columns():
    source = ExampleFeature("元")
    middle = ExampleFeature("中間", ("元",))
    result = ExampleFeature("出力", ("中間", "元"))
    registry = FeatureRegistry([result, middle, source])
    records = SimpleNamespace(entries=pd.DataFrame({"value": [2, 3]}, index=[7, 4]))
    builder = SelectedFeatureBuilder(registry, ("出力",), PredictionTiming.THURSDAY)
    first = builder.build(records)
    assert list(first.columns) == ["出力"]
    assert first["出力"].tolist() == [8, 12]
    assert [result.calls, middle.calls, source.calls] == [1, 1, 1]
    records.entries["value"] = [5, 7]
    assert builder.build(records)["出力"].tolist() == [20, 28]


@pytest.mark.parametrize("definitions,match", [
    ([ExampleFeature("x"), ExampleFeature("x")], "重複"),
    ([ExampleFeature("x", ("missing",))], "未登録"),
    ([ExampleFeature("x", ("y",)), ExampleFeature("y", ("x",))], "循環"),
])
def test_invalid_registry(definitions, match):
    with pytest.raises(ValueError, match=match):
        FeatureRegistry(definitions)


def test_dependency_timing_is_checked():
    registry = FeatureRegistry([ExampleFeature("x", ("y",)), ExampleFeature("y", known_from=PredictionTiming.RACE_DAY)])
    with pytest.raises(ValueError, match="使えない.*y"):
        SelectedFeatureBuilder(registry, ("x",), PredictionTiming.THURSDAY)


def test_wrong_row_order_is_rejected():
    class WrongFeature(ExampleFeature):
        def compute(self, records, dependencies):
            return records.entries["value"].iloc[::-1]

    builder = SelectedFeatureBuilder(FeatureRegistry([WrongFeature()]), ("追加項目",), PredictionTiming.THURSDAY)
    with pytest.raises(ValueError, match="インデックス"):
        builder.build(SimpleNamespace(entries=pd.DataFrame({"value": [1, 2]})))


def test_legacy_group_is_cached_only_within_one_build(monkeypatch):
    calls = []

    def build(records):
        calls.append(1)
        return pd.DataFrame({"馬齢": [3, 4], "斤量": [55, 56]}, index=records.entries.index)

    monkeypatch.setattr(GROUPS["B"], "build", build)
    registry = default_registry()
    builder = SelectedFeatureBuilder(registry, ("斤量", "馬齢"), PredictionTiming.THURSDAY)
    records = SimpleNamespace(entries=pd.DataFrame(index=[4, 7]))
    assert list(builder.build(records).columns) == ["斤量", "馬齢"]
    assert len(calls) == 1
    builder.build(records)
    assert len(calls) == 2
