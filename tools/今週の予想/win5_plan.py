"""1日の WIN5 の買う計画（ポリシー用の財布から買うか・金額・理由）。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any

#: 通知とまとめに添える1行（予想「近走と適性からWIN5の買い目を決める」16 の「確かめた結果」と 15 の 8）。
POLICY_NOTE = "過去の確かめでは採用の基準に届いていないので、楽しむ用の財布（ポリシー用）で買う。"


@dataclass(frozen=True)
class Win5Plan:
    """開催日・1レース目のレース ID・予想の判断（買う／見送り）・財布の計画で買うか（``buys``）・点数・金額（買わなければ 0）・
    フォーメーションの文字・当たる確率・日の期待値・買う日の線・そう決めた理由（1文）。``plan.json`` の ``win5`` に書く。"""

    race_date: str
    race_id: str
    decision: str
    buys: bool
    points: int
    stake_yen: int
    formation: str
    hit_probability: float
    expected_value: float
    line: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Win5Plan:
        own = {field_.name for field_ in fields(cls)}
        return cls(**{key: value for key, value in data.items() if key in own})
