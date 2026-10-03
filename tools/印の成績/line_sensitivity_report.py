"""期待値の線を動かしたときの、3連複・3連単の買い目の成績の表を作る。"""

from __future__ import annotations

import pandas as pd

from 共通.bootstrap_interval import BootstrapInterval
from 共通.perf import percent
from 共通.render import Table

from 印の成績.axis_ticket_rule import AxisTicketRule
from 印の成績.mark_tickets import RULE, VALUE
from 印の成績.ticket_payouts import PAYOUT
from 印の成績.ticket_report import TARGETS
from 印の成績.ticket_rules import BET_RULES, COMBO_VALUE_LINE, POINT_YEN
from 印の成績.torigami_filter import DROPPED, NO_ODDS

#: 動かす線。
LINES: tuple[float, ...] = (1.0, 1.1, 1.2, 1.3, 1.5, 2.0)


class LineSensitivityReport:
    """3連複・3連単の全点の買い目（期待値で絞らない軸のルール）に、線を変えて「期待値が線以上」で絞ったときの成績の表（表9）を作る。

    線は 1.0 で固定と決めてあり（``COMBO_VALUE_LINE``）、この表は線を選ぶためのものではなく、線を動かすと点数と回収率がどう変わるかを見る参考。
    テスト期間の結果を見て線を選び直すと、採用の証拠にならない。トリガミは外さない（線ごとに外す買い目が変わるため）。オッズ無しの組は外す。
    """

    def table(self, tickets: pd.DataFrame) -> Table:
        base = tickets[tickets[DROPPED] != NO_ODDS]
        rows = []
        for target in TARGETS:
            for rule in BET_RULES:
                if not isinstance(rule, AxisTicketRule) or rule.value_line is not None:
                    continue
                chosen = base[base[RULE] == rule.label]
                if target != TARGETS[0]:
                    chosen = chosen[chosen["expectation"] == target.split()[-1]]
                for line in LINES:
                    rows.append(self._row(rule.label, target, line, chosen[chosen[VALUE] >= line]))
        note = (f"表7 の全点の買い目（3連複の流し・3連単のマルチ）を、組の期待値が線以上のものだけにしたときの成績（1点 100円）。本番の線は {COMBO_VALUE_LINE:.1f} で固定。"
                "この表は線を選ぶためではなく、線を動かすと点数と回収率がどう変わるかを見る参考（テスト期間の結果を見て線を選び直すと、採用の証拠にならない）。"
                "トリガミは外していない（線ごとに外す買い目が変わるため）。オッズ無しの組は外す。")
        return Table(["買い方", "対象", "線", "買ったレース", "点数", "1レースの点数", "的中レース", "回収率", "回収率の90%の幅"], rows,
                     title="9. 期待値の線を動かしたときの 3連複・3連単の成績（参考）", note=note)

    def _row(self, label: str, target: str, line: float, chosen: pd.DataFrame) -> list[str]:
        if chosen.empty:
            return [label, target, f"{line:.1f}", "0", "0", "—", "0", "—", "—"]
        races = chosen["race_id"].nunique()
        stake = POINT_YEN * len(chosen)
        payout = float(chosen[PAYOUT].sum())
        low, high = BootstrapInterval().of(chosen["race_date"], pd.Series(float(POINT_YEN), index=chosen.index), chosen[PAYOUT])
        hits = chosen[chosen[PAYOUT] > 0]["race_id"].nunique()
        return [label, target, f"{line:.1f}", f"{races:,}", f"{len(chosen):,}", f"{len(chosen) / races:.1f}", f"{hits:,}",
                percent(payout / stake), f"{percent(low)}〜{percent(high)}"]
