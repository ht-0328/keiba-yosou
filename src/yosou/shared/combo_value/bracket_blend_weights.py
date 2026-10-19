"""枠連の組の確率を作るときの、4つのもとの重み。"""

from __future__ import annotations

from dataclasses import asdict, dataclass

#: 重みの名前（``BracketBlend`` のもとの順）。
BRACKET_WEIGHT_NAMES: tuple[str, ...] = ("own", "quinella", "trifecta", "harville")


@dataclass(frozen=True)
class BracketBlendWeights:
    """枠連の組の確率 ∝ exp(own × log 枠連の市場 + quinella × log 馬連の市場 + trifecta × log 3連単から見た市場 + harville × log モデルの Harville)。
    馬連の市場・3連単から見た市場・モデルの Harville は、その枠の組に入る馬の組の和（研究「レースの種類ごとの買い方」の docs/04 の 3）。

    例（架空）: own −0.4・quinella 0.9・trifecta 0・harville 0.6 なら、枠連の値段より馬連の値段を信じ、その差を割安とみる。
    """

    own: float
    quinella: float
    trifecta: float
    harville: float

    def values(self) -> tuple[float, ...]:
        return tuple(getattr(self, name) for name in BRACKET_WEIGHT_NAMES)

    def to_dict(self) -> dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, saved: dict[str, float]) -> BracketBlendWeights:
        return cls(**{name: float(saved[name]) for name in BRACKET_WEIGHT_NAMES})
