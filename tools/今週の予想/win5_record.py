"""予想「近走と適性からWIN5の買い目を決める」の predict が自動で書いた、1日の WIN5 の予想の記録。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from yosou.form_aptitude_win5_tickets.formation import DayDecision
from yosou.form_aptitude_win5_tickets.payout import TICKET_YEN

from 今週の予想.win5_combo import combo_text
from 今週の予想.win5_leg import Win5Leg


@dataclass(frozen=True)
class Win5Record:
    """開催日・予想した時刻・判断（買う（多く）／買う（少なく）／見送り）・買う買い目の予算（点）・点数・代金（円）・買い目のどれかが当たる確率・
    日の期待値・買う日の線・キャリーオーバー（円）・対象レース5つ（``Win5Leg``。発売の順）と、段階の予算の値（判断用の買い目の予算と日の期待値・
    本命の確率の積・多く買う日の線・少なく買う日と多く買う日の予算・段階）。値は ``Win5Forecast.to_dict()`` の記録をそのまま読んだもの。

    段階の予算より前の記録（予算が1つで、判断が「買う」）も読める。そのときは判断用の買い目を買う買い目と同じとみなし、本命の確率の積と
    多く買う日の線は無し（None）、段階は空にする。
    """

    race_date: str
    made_at: str
    decision: str
    budget: int
    points: int
    stake: int
    hit_probability: float
    expected_value: float
    line: float
    carry: int
    legs: tuple[Win5Leg, ...]
    judge_budget: int
    judge_value: float
    favorite_product: float | None
    favorite_line: float | None
    small_budget: int | None
    large_budget: int | None
    tier: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Win5Record:
        favorite_product = data.get("本命の確率の積")
        favorite_line = data.get("多く買う日の線")
        return cls(
            race_date=str(data["開催日"]), made_at=str(data.get("予想した時刻", "")), decision=str(data["判断"]), budget=int(data["予算"]),
            points=int(data["点数"]), stake=int(data["代金"]), hit_probability=float(data["当たる確率"]),
            expected_value=float(data["日の期待値"]), line=float(data["買う日の線"]), carry=int(data.get("キャリーオーバー") or 0),
            legs=tuple(Win5Leg.from_dict(leg) for leg in data["対象レース"]),
            judge_budget=int(data.get("判断用の予算", data["予算"])), judge_value=float(data.get("判断用の期待値", data["日の期待値"])),
            favorite_product=None if favorite_product is None else float(favorite_product),
            favorite_line=None if favorite_line is None else float(favorite_line),
            small_budget=None if data.get("少なく買う日の予算") is None else int(data["少なく買う日の予算"]),
            large_budget=None if data.get("多く買う日の予算") is None else int(data["多く買う日の予算"]),
            tier=str(data.get("段階") or ""),
        )

    @property
    def buys(self) -> bool:
        """予想の判断が買う日（多くでも少なくでも。判断用の買い目の日の期待値が線以上）か。"""
        return DayDecision.buys_text(self.decision)

    @property
    def tiered(self) -> bool:
        """段階の予算の記録か（前の形の記録なら False）。"""
        return self.favorite_line is not None and self.small_budget is not None and self.large_budget is not None

    @property
    def formation(self) -> str:
        """買い目のフォーメーションの文字（``3,5/6/...``。買い目の記録の「買い目」の列と同じ形）。"""
        return combo_text([leg.numbers for leg in self.legs])

    def value_text(self) -> str:
        """判断用の買い目の日の期待値と線の比べ（``判断用の買い目（50点）の期待値 1.83 ≥ 線 1.25``）。"""
        sign = "≥" if self.judge_value >= self.line else "<"
        return f"判断用の買い目（{self.judge_budget}点）の期待値 {self.judge_value:.2f} {sign} 線 {self.line:.2f}"

    def tier_text(self) -> str:
        """多く買う日か少なく買う日かの理由（``本命の確率の積 0.31% ≥ 0.25% なので多く買う（予算 100点 10,000円）``）。
        見送りの日と、段階の予算より前の記録は空。"""
        if not self.buys or not self.tiered or self.favorite_product is None or not self.tier:
            return ""
        sign = "≥" if self.favorite_product >= self.favorite_line else "<"
        return (f"本命の確率の積 {self.favorite_product:.2%} {sign} {self.favorite_line:.2%} なので{self.tier}買う"
                f"（予算 {self.budget}点 {self.budget * TICKET_YEN:,}円）")

    def reason_text(self) -> str:
        """判断の理由（買う日は線の比べと段階の理由、見送りの日は線の比べだけ）。"""
        tier = self.tier_text()
        return f"{self.value_text()}。{tier}" if tier else self.value_text()

    def tiers_text(self) -> str:
        """段階の予算の決まりの1行（段階の予算より前の記録は空）。"""
        if not self.tiered:
            return ""
        return (f"多く買う日 {self.large_budget}点（{self.large_budget * TICKET_YEN:,}円）・少なく買う日 {self.small_budget}点"
                f"（{self.small_budget * TICKET_YEN:,}円）。本命の確率の積 {self.favorite_line:.2%} 以上なら多く買う。"
                f"買うかどうかは判断用の買い目（{self.judge_budget}点）の期待値が線 {self.line:.2f} 以上か")

    def carry_text(self) -> str:
        """キャリーオーバー（無ければ「なし」）。"""
        return f"{self.carry:,}円" if self.carry else "なし"
