"""予想「近走と適性からWIN5の買い目を決める」の predict が自動で書いた、1日の WIN5 の予想の記録。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from 今週の予想.win5_combo import combo_text
from 今週の予想.win5_leg import Win5Leg

#: 予想の判断の「買う」（``DayDecision.BUY`` の名前と同じ）。
BUY = "買う"


@dataclass(frozen=True)
class Win5Record:
    """開催日・予想した時刻・判断（買う／見送り）・予算（点）・点数・代金（円）・買い目のどれかが当たる確率・日の期待値・買う日の線・
    キャリーオーバー（円）・対象レース5つ（``Win5Leg``。発売の順）。値は ``Win5Forecast.to_dict()`` の記録をそのまま読んだもの。"""

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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Win5Record:
        return cls(
            race_date=str(data["開催日"]), made_at=str(data.get("予想した時刻", "")), decision=str(data["判断"]), budget=int(data["予算"]),
            points=int(data["点数"]), stake=int(data["代金"]), hit_probability=float(data["当たる確率"]),
            expected_value=float(data["日の期待値"]), line=float(data["買う日の線"]), carry=int(data.get("キャリーオーバー") or 0),
            legs=tuple(Win5Leg.from_dict(leg) for leg in data["対象レース"]),
        )

    @property
    def buys(self) -> bool:
        """予想の判断が「買う」（日の期待値が線以上）か。"""
        return self.decision == BUY

    @property
    def formation(self) -> str:
        """買い目のフォーメーションの文字（``3,5/6/...``。買い目の記録の「買い目」の列と同じ形）。"""
        return combo_text([leg.numbers for leg in self.legs])

    def value_text(self) -> str:
        """日の期待値と線の比べ（``日の期待値 1.83 ≥ 線 1.50``）。"""
        sign = "≥" if self.expected_value >= self.line else "<"
        return f"日の期待値 {self.expected_value:.2f} {sign} 線 {self.line:.2f}"

    def carry_text(self) -> str:
        """キャリーオーバー（無ければ「なし」）。"""
        return f"{self.carry:,}円" if self.carry else "なし"
