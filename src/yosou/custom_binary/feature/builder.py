"""依存順に1回ずつ計算し、指定された列（モデルの入力と、絞り込みの条件に使う列）だけを返す。"""

from types import MappingProxyType

import pandas as pd

from yosou.shared.feature import EntryRecords, PredictionTiming
from yosou.shared.feature.value_types import typed_features

from .builtin import GroupColumn
from .registry import FeatureRegistry


class SelectedFeatureBuilder:
    def __init__(self, registry: FeatureRegistry, selected: tuple[str, ...], timing: PredictionTiming,
                 extra: tuple[str, ...] = ()) -> None:
        self.registry = registry
        self.selected = selected
        self.timing = timing
        # extra はモデルに渡さない列（絞り込みの条件など）。返す表には selected の後ろに付ける。
        self.columns = tuple(dict.fromkeys((*selected, *extra)))
        self.order = registry.order(self.columns, timing)
        self.catalog = registry.catalog(selected)
        self._typing = registry.catalog(self.columns)
        # 計算する特徴量（依存先を含む）が使う追加の元データ。重ねずに、出てきた順。
        self.sources = tuple(dict.fromkeys(
            source for name in self.order for source in getattr(registry.definitions[name], "sources", ())
        ))

    def build(self, records: EntryRecords) -> pd.DataFrame:
        values: dict[str, pd.Series] = {}
        groups: dict[str, pd.DataFrame] = {}
        for name in self.order:
            definition = self.registry.definitions[name]
            dependencies = MappingProxyType({key: values[key] for key in definition.dependencies})
            if isinstance(definition, GroupColumn):
                value = definition.compute_cached(records, dependencies, groups)
            else:
                value = definition.compute(records, dependencies)
            if not isinstance(value, pd.Series) or not value.index.equals(records.entries.index):
                raise ValueError(f"特徴量の行・インデックスが出走馬と一致しません: {name}")
            values[name] = value
        frame = pd.DataFrame({name: values[name] for name in self.columns}, index=records.entries.index)
        return typed_features(frame, self._typing.categorical)
