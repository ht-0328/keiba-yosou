"""YAML の popularity: 学習・評価・予想の対象にする人気の範囲。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PopularityRange:
    """人気範囲（最小・最大。片方だけでもよい。両端を含む）。"""

    minimum: int | None = None
    maximum: int | None = None

    def __post_init__(self) -> None:
        for value in (self.minimum, self.maximum):
            if value is not None and (type(value) is not int or value < 1):
                raise ValueError("人気範囲は1以上の整数で指定してください")
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("人気範囲のminはmax以下にしてください")

    @property
    def bounded(self) -> bool:
        return self.minimum is not None or self.maximum is not None

    def as_dict(self) -> dict:
        return {key: value for key, value in (("min", self.minimum), ("max", self.maximum)) if value is not None}
