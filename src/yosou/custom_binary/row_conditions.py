"""YAML の conditions: 特徴量の値で、学習・評価・予想の対象の馬を絞る。"""

from dataclasses import dataclass

import pandas as pd

from yosou.shared.feature import PredictionTiming

from .feature.registry import FeatureRegistry
from .row_condition import RowCondition


@dataclass(frozen=True)
class RowConditions:
    """すべての条件に当てはまる馬だけを残す（AND）。条件が無ければ全頭を残す。

    条件に使う特徴量は、モデルの入力（特徴量テキスト）に書いていなくても計算する。
    レース内の比較（順位など）は、絞る前の全頭で計算した値で判定する。
    """

    items: tuple[RowCondition, ...] = ()

    @classmethod
    def parse(cls, values, registry: FeatureRegistry, timing: PredictionTiming) -> "RowConditions":
        if not isinstance(values, dict):
            raise ValueError("conditionsは「特徴量の名前: 条件」の組で指定してください")
        items = []
        for name, spec in values.items():
            try:
                registry.order((name,), timing)
            except ValueError as error:
                raise ValueError(f"conditions.{name}: {error}") from error
            items.append(RowCondition.parse(name, spec, registry.definitions[name].kind))
        return cls(tuple(items))

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.items)

    def mask(self, frame: pd.DataFrame) -> pd.Series:
        kept = pd.Series(True, index=frame.index)
        for item in self.items:
            kept &= item.mask(frame[item.name])
        return kept

    def as_dict(self) -> dict:
        return {item.name: item.spec() for item in self.items}

    def label(self) -> str:
        return " かつ ".join(item.label() for item in self.items) or "なし"
