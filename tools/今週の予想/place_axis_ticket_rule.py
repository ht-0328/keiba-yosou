"""複勝で買う馬を軸にして、印の上位に流す買い目（ワイド・馬連）のルール。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.shared.betting import TicketType

#: 軸から流す相手の印（◎ と、3着以内の確率の高い ○▲）。結果を見る前に決めた（研究「複勝以外の回収率100超」の docs/03）。
PARTNER_MARKS: tuple[str, ...] = ("◎", "○", "▲")


@dataclass(frozen=True)
class PlaceAxisTicketRule:
    """複勝の買い目の馬（複勝の期待値が線以上の馬。最大3頭）を軸にして、◎○▲ に流す券種のルール（研究「複勝以外の回収率100超」の手順4）。

    複勝で回収率が 100% を超えるのは、モデルが「この馬は市場の見立てより3着以内に来る」と見た馬を買っているからである。
    その同じ馬を軸に、3着以内に来やすい印の上位と組めば、同じ見立てを配当の大きい券種で使える、という考えを確かめる。
    軸が ◎○▲ に入っているときは、その馬を相手から除く。同じ組は1点にまとめる（軸どうしの組も1点）。
    ``totals`` は、この買い方を入れる合計の組（``ticket_rules.TOTAL_GROUPS``。採用していなければ空で、比べるための行）。
    """

    ticket_type: TicketType
    stake_units: float
    totals: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.ticket_type.spec.is_ordered or self.ticket_type.spec.horse_count != 2:
            raise ValueError(f"順不同の2頭の券種だけを組めます: {self.ticket_type.label}")

    @property
    def label(self) -> str:
        """表に出す買い方の名前。例: ``ワイド（複勝の馬軸−◎○▲）``。"""
        return f"{self.ticket_type.label}（複勝の馬軸−{''.join(PARTNER_MARKS)}）"

    @property
    def value_line(self) -> float | None:
        """組の期待値では絞らない（軸は複勝の期待値で選んである）。"""
        return None

    def combos(self, place_horses: list[int], by_mark: dict[str, list[int]]) -> list[tuple[int, ...]]:
        """``place_horses`` は複勝の買い目の馬番、``by_mark`` は印 → 馬番の並び。"""
        partners = [horse for mark in PARTNER_MARKS for horse in by_mark.get(mark, [])]
        return sorted({tuple(sorted((axis, partner))) for axis in place_horses for partner in partners if partner != axis})
