"""組の期待値で選ぶ買い方の、線 × オッズの上限 × 対象のレース を数える（開発の期間だけで選ぶため）。"""

from __future__ import annotations

from itertools import product

import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.combo_value import HIT
from yosou.shared.combo_value.combo_blend import VALUE

from 共通.bootstrap_interval import BootstrapInterval

from .combo_month_frames import PAYOUT

#: 試す線と、券種ごとのオッズの上限（docs/04 の 3）。
LINES: tuple[float, ...] = (1.0, 1.1, 1.2, 1.3)
CAPS: dict[TicketType, tuple[float, ...]] = {
    TicketType.WIDE: (30, 100, 300), TicketType.QUINELLA: (30, 100, 300, 1000), TicketType.EXACTA: (30, 100, 300, 1000),
    TicketType.TRIO: (100, 300, 1000), TicketType.TRIFECTA: (300, 1000, 3000),
}
#: 対象のレースと組。「全」「高」は1回目、「◎」「高◎」（◎ を含む組。3連単・馬単は ◎ が1着の組）は2回目に足した（docs/04 の 6）。
SCOPES: tuple[str, ...] = ("全", "高", "◎", "高◎")
#: 選ぶのに要る当たりの数。
MIN_HITS = 150


class ComboRuleGrid:
    """組の期待値を付けた表（``ComboMonthFrames`` の表に ``ComboBlend.of`` を掛けたもの。開発の期間だけ）から、
    対象 × 線 × 上限 ごとに、買ったレース・点数・当たり・回収率と、開催日を単位にしたブートストラップの 90% の幅を出す。
    当たりが ``MIN_HITS`` 回に届かない組み合わせは出さない。幅の下の端の高い順に並べる（いちばん上を選ぶ）。
    """

    def table(self, ticket_type: TicketType, valued: pd.DataFrame) -> pd.DataFrame:
        rows = [self._row(scope, line, cap, self._chosen(ticket_type, valued, scope, line, cap))
                for scope, line, cap in product(SCOPES, LINES, CAPS[ticket_type])]
        table = pd.DataFrame([row for row in rows if row is not None],
                             columns=["対象", "線", "上限", "レース", "点数", "的中", "回収率", "幅の下の端", "幅の上の端"])
        return table.sort_values("幅の下の端", ascending=False).reset_index(drop=True)

    def _chosen(self, ticket_type: TicketType, valued: pd.DataFrame, scope: str, line: float, cap: float) -> pd.DataFrame:
        chosen = valued[(valued[VALUE] >= line) & (valued["odds"] <= cap)]
        if "高" in scope:
            chosen = chosen[chosen["expectation"] == "高"]
        if "◎" in scope:
            chosen = chosen[self._has_top(ticket_type, chosen)]
        return chosen

    def _has_top(self, ticket_type: TicketType, frame: pd.DataFrame) -> pd.Series:
        """◎ を含む組か（着順を区別する券種は ◎ が1着の組）。"""
        if ticket_type.spec.is_ordered:
            return frame["h1"] == frame["top"]
        return pd.concat([frame[name] == frame["top"] for name in ("h1", "h2", "h3")[:ticket_type.spec.horse_count]], axis=1).any(axis=1)

    def _row(self, scope: str, line: float, cap: float, chosen: pd.DataFrame) -> list | None:
        if chosen[HIT].sum() < MIN_HITS:
            return None
        stake = pd.Series(100.0, index=chosen.index)
        low, high = BootstrapInterval().of(pd.to_datetime(chosen["race_date"]).dt.date, stake, chosen[PAYOUT])
        rate = chosen[PAYOUT].sum() / stake.sum()
        return [scope, line, cap, chosen["race_id"].nunique(), len(chosen), int(chosen[HIT].sum()),
                round(rate * 100, 1), round(low * 100, 1), round(high * 100, 1)]
