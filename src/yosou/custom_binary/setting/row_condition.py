"""1つの特徴量に対する絞り込みの条件（YAML の conditions の1項目）。"""

from dataclasses import dataclass
import math

import pandas as pd

from yosou.shared.feature.feature_kind import FeatureKind
from yosou.shared.feature.value_types import as_numbers


@dataclass(frozen=True)
class RowCondition:
    """数値の特徴量は ``minimum``〜``maximum``（両端を含む）、カテゴリの特徴量は ``values`` のどれか。

    値が欠損している馬は、条件に当てはまらないものとして除く。
    """

    name: str
    kind: FeatureKind
    minimum: float | None = None
    maximum: float | None = None
    values: tuple[str, ...] = ()

    @classmethod
    def parse(cls, name: str, spec, kind: FeatureKind) -> "RowCondition":
        if kind is FeatureKind.CATEGORICAL:
            return cls._categorical(name, spec, kind)
        return cls._numeric(name, spec, kind)

    @classmethod
    def _categorical(cls, name: str, spec, kind: FeatureKind) -> "RowCondition":
        values = spec if isinstance(spec, list) else [spec]
        if not values or any(type(value) not in (str, int) or str(value).strip() == "" for value in values):
            raise ValueError(f"conditions.{name}はカテゴリの特徴量です。値を1つか、値のリストで指定してください")
        return cls(name, kind, values=tuple(str(value) for value in values))

    @classmethod
    def _numeric(cls, name: str, spec, kind: FeatureKind) -> "RowCondition":
        if not isinstance(spec, dict) or not spec or spec.keys() - {"min", "max"}:
            raise ValueError(f"conditions.{name}は数値の特徴量です。min・maxで指定してください（例: {{max: 1400}}）")
        for key, value in spec.items():
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError(f"conditions.{name}.{key}は有限な数値にしてください")
        minimum, maximum = spec.get("min"), spec.get("max")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError(f"conditions.{name}のminはmax以下にしてください")
        return cls(name, kind, minimum, maximum)

    def mask(self, column: pd.Series) -> pd.Series:
        if self.kind is FeatureKind.CATEGORICAL:
            return column.astype("string").isin(self.values).fillna(False).astype(bool)
        numbers = as_numbers(column)
        kept = numbers.notna()
        if self.minimum is not None:
            kept &= numbers >= self.minimum
        if self.maximum is not None:
            kept &= numbers <= self.maximum
        return kept

    def spec(self):
        if self.kind is FeatureKind.CATEGORICAL:
            return list(self.values)
        return {key: value for key, value in (("min", self.minimum), ("max", self.maximum)) if value is not None}

    def label(self) -> str:
        if self.kind is FeatureKind.CATEGORICAL:
            return f"{self.name}が{'・'.join(self.values)}"
        low = "" if self.minimum is None else f"{self.minimum:g}以上"
        high = "" if self.maximum is None else f"{self.maximum:g}以下"
        return f"{self.name}が{low}{high}"
