"""買い目の型（軸・相手の頭数・2列目の置き方・期待値の線）と、券種ごとの候補。"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from yosou.shared.betting import TicketType

#: 軸の頭数の候補（◎ だけ・◎○・◎○▲）。
AXIS_SIZES: tuple[int, ...] = (1, 2, 3)
#: 相手の候補。整数は頭数（3着以内の確率の高い順にその数）、小数は確率の線（3着以内の確率がその値以上の馬全部。◎・消を除く）。
#: 全頭に流す候補は置かない（利用者の決定: 予想が馬を選ぶ）。
PARTNER_COUNTS: tuple[int, ...] = (2, 4, 6)
PARTNER_THRESHOLDS: tuple[float, ...] = (0.5, 0.25)
PARTNERS: tuple[int | float, ...] = (*PARTNER_COUNTS, *PARTNER_THRESHOLDS)
#: 2列目の置き方（3連複・3連単だけ）。流し = 2列目は軸と相手、2列目も軸 = 2列目は軸だけ。
FLOW, DOUBLE_AXIS = "流し", "2列目も軸"
SECOND_COLUMNS: tuple[str, ...] = (FLOW, DOUBLE_AXIS)
#: 期待値の線の候補（None は絞らない）。
VALUE_LINES: tuple[float | None, ...] = (None, 1.0, 1.2)
#: 1レース・1券種の点数の上限（利用者の決定「1レース 最大 1万円」。1点 100円で 8券種に均等に分けると 1,250円 = 12点。docs/01 の 2）。
#: 2回目（docs/01 の 7）から、上限 1点（最小の額）の型も候補にする。
MAX_POINTS = 12
TOKEN_POINTS = 1
MAX_POINTS_CHOICES: tuple[int, ...] = (MAX_POINTS, TOKEN_POINTS)
#: 3頭の券種（2列目の置き方がある）。
THREE_HORSE: tuple[TicketType, ...] = (TicketType.TRIO, TicketType.TRIFECTA)
#: 軸の頭数 → 印の並び。
_AXIS_LABELS: dict[int, str] = {1: "◎", 2: "◎○", 3: "◎○▲"}


@dataclass(frozen=True)
class Formation:
    """1つの型。``axis_size`` は軸の頭数（1〜3）、``partners`` は相手（整数なら頭数、小数なら3着以内の確率の線）、``second_column`` は2列目の置き方
    （3頭の券種だけ。ほかは ``FLOW``）、``value_line`` は期待値の線（None は絞らない）、``max_points`` は1レースの点数の上限（docs/01 の 4）。
    """

    axis_size: int
    partners: int | float
    second_column: str = FLOW
    value_line: float | None = None
    max_points: int = MAX_POINTS

    @property
    def label(self) -> str:
        """人が読む名前。例: ``◎○ − 相手 4頭・流し・期待値 1.0 以上``。"""
        partners = f"確率 {self.partners:.0%} 以上の馬" if self.by_threshold else f"{self.partners}頭"
        line = "絞らない" if self.value_line is None else f"期待値 {self.value_line:.1f} 以上"
        return f"{_AXIS_LABELS[self.axis_size]} − 相手 {partners}・{self.second_column}・{line}・{self.max_points}点まで"

    @property
    def axis_limit(self) -> float:
        """軸になる位置の上限（位置 ≤ この値なら軸）。"""
        return float(self.axis_size - 1)

    @property
    def by_threshold(self) -> bool:
        """相手を確率の線で決める型か（頭数で決める型なら偽）。"""
        return isinstance(self.partners, float)

    @property
    def partner_limit(self) -> float:
        """相手を頭数で決める型の、軸か相手になる位置の上限（位置 ≤ この値なら軸か相手）。確率の線の型では使わない（``FormationMask`` がレースごとに出す）。"""
        if self.by_threshold:
            raise ValueError("確率の線で相手を決める型には、固定の上限が無い")
        return float(self.axis_size - 1 + int(self.partners))

    @property
    def threshold_column(self) -> str:
        """確率の線の型が使う、レースごとの「線以上の馬の数」の列の名前（例: ``n50``）。"""
        return f"n{int(round(self.partners * 100))}"


def candidates(ticket_type: TicketType | str) -> list[Formation]:
    """券種の型の候補。点数の上限（12点・1点）でも変える。3連複・3連単は 2列目の置き方も変える（180 個）。ほかは 90 個。"""
    seconds = SECOND_COLUMNS if ticket_type in THREE_HORSE else (FLOW,)
    return [Formation(axis, partners, second, line, points)
            for axis, partners, second, line, points in product(AXIS_SIZES, PARTNERS, seconds, VALUE_LINES, MAX_POINTS_CHOICES)]
