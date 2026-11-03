"""馬の集まりから組む3連複（``PoolTrioTicketRule``）で、1頭目・2頭目・3頭目に入れる馬の集まり。"""

from __future__ import annotations

from dataclasses import dataclass

#: 人気馬: 5番人気までで危険な人気馬（消）でない馬（線は使わない）。
FAVORITES = "人気馬"
#: 強い人気馬: 人気馬のうち、3着以内の確率 − 複勝オッズから見た3着以内率が線以上の馬。
STRONG_FAVORITES = "強い人気馬"
#: 6番人気以下: 6番人気以下で、3着以内の確率 − 複勝オッズから見た3着以内率が線以上の馬。
LONGSHOTS = "6番人気以下"
#: 消を除いた全頭（線は使わない）。
NOT_DANGER = "消を除いた全頭"
#: 予想の上位: 消でない馬のうち、3着以内の確率の高い順に ``count`` 頭（線は使わない）。
MODEL_TOP = "予想の上位"
#: N番人気まで: ``count`` 番人気までで消でない馬（中穴まで）。線があれば、そのうち 3着以内の確率 − 複勝オッズから見た3着以内率が線以上の馬。
UP_TO = "番人気まで"


@dataclass(frozen=True)
class HorsePool:
    """馬の集まりの種類（``kind``）と、3着以内の確率 − 複勝オッズから見た3着以内率の線（``edge``）と、頭数か人気の上限（``count``）。
    馬を選ぶのは ``MarkTickets``。"""

    kind: str
    edge: float | None = None
    count: int | None = None

    @property
    def label(self) -> str:
        """表に出す名前。例: ``強い人気馬（複勝オッズとの差 -0.05 以上）``・``予想の上位4頭（消を除く）``・``9番人気まで（消を除く・複勝オッズとの差 -0.05 以上）``。"""
        if self.kind == MODEL_TOP:
            return f"{self.kind}{self.count}頭（消を除く）"
        if self.kind == UP_TO:
            line = f"・複勝オッズとの差 {self.edge:+.2f} 以上" if self.edge is not None else ""
            return f"{self.count}{self.kind}（消を除く{line}）"
        return self.kind if self.edge is None else f"{self.kind}（複勝オッズとの差 {self.edge:+.2f} 以上）"
