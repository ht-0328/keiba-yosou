"""確かめる作り方（組の確率の出どころ × 3連単を直すか × 上げ下げの強さ）。"""

from __future__ import annotations

from dataclasses import dataclass

from 回収率100超.analysis.tickets import TicketKind

from .market_source import ORIGIN_NAMES, OWN, TRIFECTA, TRIO

#: 馬ごとの上げ下げの強さ。0 は市場の確率そのまま（案①）、1 はモデルの比をそのまま掛ける。
STRENGTHS: tuple[float, ...] = (0.0, 0.5, 1.0)


@dataclass(frozen=True)
class Variant:
    """1つの作り方。

    - ``origin``: 組の確率を作る元の券種（その券種自身・3連単・3連複）。
    - ``corrected``: 3連単の人気薄の組の買われすぎを、先に直すか（3連単から作るときだけ）。
    - ``strength``: 馬ごとの上げ下げの強さ。
    """

    origin: str
    corrected: bool
    strength: float

    @property
    def name(self) -> str:
        fixed = "（3連単を直す）" if self.corrected else ""
        return f"{ORIGIN_NAMES[self.origin]}{fixed}・上げ下げ {self.strength:g}"


def variants_for(kind: TicketKind) -> list[Variant]:
    """券種ごとに試す作り方。3連単より売上の大きい券種は無いので、3連単はその券種自身からだけ作る。"""
    origins = [(OWN, False)]
    if kind.key != "trifecta":
        origins += [(TRIFECTA, False), (TRIFECTA, True)]
    if kind.key == "wide":
        origins.append((TRIO, False))
    return [Variant(origin, corrected, strength) for origin, corrected in origins for strength in STRENGTHS]
