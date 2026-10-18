"""組の確率を作るときの、4つのもとの重み（1つの券種ぶん）。"""

from __future__ import annotations

from dataclasses import asdict, dataclass

#: 重みの名前（``ComboBlendFeatures`` の特徴の列と同じ順）。
WEIGHT_NAMES: tuple[str, ...] = ("own", "trifecta", "harville", "ratio")


@dataclass(frozen=True)
class ComboBlendWeights:
    """組の確率 ∝ exp(own × log その券種自身の市場 + trifecta × log 3連単から見た市場 + harville × log モデルの Harville + ratio × log モデルの比)。

    重みは券種ごとに、当たった組の確率の対数の合計が最大になるように推定する（``ComboBlendFitter``）。
    例（架空）: own 0.5・trifecta 0・harville 0.6・ratio 0.9 なら、市場の確率を半分ほど信じ、モデルの Harville と比を強めに足す。
    """

    own: float
    trifecta: float
    harville: float
    ratio: float

    def values(self) -> tuple[float, ...]:
        return tuple(getattr(self, name) for name in WEIGHT_NAMES)

    def to_dict(self) -> dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, saved: dict[str, float]) -> ComboBlendWeights:
        return cls(**{name: float(saved[name]) for name in WEIGHT_NAMES})
