"""期待値の線と券種の配分を、確かめる年より前の年だけで選んだときの回収率を出す。"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from yosou.shared.betting import TicketType

from .column_names import EXPECTED_VALUE, PAYOUT, RULE, STAKE, TICKET_TYPE, YEAR
from .mark_ticket_rule import MODEL_MARK_RULE
from .return_summary import TOTAL_YEAR

#: 期待値の線の候補（設計書 15 の 15 の③。線は、確かめる年より前の年だけで選ぶ）。
VALUE_LINES: tuple[float, ...] = (1.0, 1.2, 1.5, 2.0, 3.0)
#: 候補に選べるのは、前の年までに、この点数以上買った候補だけ（数点の大当たりで選ばれないように。結果を見る前に決めた値）。
MIN_PRIOR_POINTS = 100
#: 期待値で買う買い方の名前（``ExpectedValueTicketRule`` の既定の名前）。
MODEL_VALUE_RULE = "期待値 1.0 以上（モデル）"
#: 出力の列。
CANDIDATE, TYPE_LABEL, YEAR_LABEL = "候補", "券種", "年"
POINTS, STAKE_TOTAL, PAYOUT_TOTAL, RETURN_RATE = "点数", "賭け金（円）", "払戻（円）", "回収率"
PRIOR_RATE, CHOSEN, POLICY = "前の年までの回収率", "選んだもの", "配分"
#: 券種の配分の決め方（名前 → 説明は設計書 16 の 7 の表5）。
BEST_ONE, OVER_BREAK_EVEN = "前の年までにいちばん良かった1つだけ", "前の年までに 100% を超えたものだけ"


class ValueLineChoice:
    """精算した買い目から、期待値の線と券種の配分を「確かめる年より前の年の回収率だけ」で選び、その年に当てはめる。

    候補は、券種ごとの「印どおり」と「期待値が線以上」（線は ``VALUE_LINES``）。期待値が線以上の買い目は、期待値
    1.0 以上で買った買い目のうち、期待値が線以上のものに絞って数える（線を上げても、精算し直す必要はない）。

    - ``line_totals``: 候補 × 券種 の、全部の年の合計（参考。これを見て線を選ぶと、確かめる年に合わせることになる）。
    - ``chosen_lines``: 券種ごとに、各年の線を、その年より前の年の回収率がいちばん高い線に決めて当てはめた結果。
    - ``allocation``: 各年に買う（候補・券種）を、その年より前の年の回収率で決めた結果（``BEST_ONE``・``OVER_BREAK_EVEN``）。

    最初の年は、前の年が無いので選べず、表に出さない。
    """

    def __init__(self, mark_rule: str = MODEL_MARK_RULE, value_rule: str = MODEL_VALUE_RULE,
                 lines: Sequence[float] = VALUE_LINES) -> None:
        self._mark_rule = mark_rule
        self._value_rule = value_rule
        self._lines = tuple(lines)

    def candidates(self, settled: pd.DataFrame) -> pd.DataFrame:
        """1行 = 候補 × 券種 × 年（列 ``候補``・``ticket_type``・``year``・点数・賭け金・払戻）。"""
        mark = settled[settled[RULE] == self._mark_rule]
        value = settled[settled[RULE] == self._value_rule]
        parts = [self._summed(mark, "印どおり"),
                 *(self._summed(value[value[EXPECTED_VALUE] >= line], f"期待値 {line:.1f} 以上") for line in self._lines)]
        return pd.concat(parts, ignore_index=True)

    def _summed(self, rows: pd.DataFrame, candidate: str) -> pd.DataFrame:
        """買い目を 券種 × 年 にまとめ、候補の名前を付ける。"""
        summed = rows.groupby([TICKET_TYPE, rows[YEAR].astype(str)], as_index=False).agg(
            **{POINTS: (STAKE, "size"), STAKE_TOTAL: (STAKE, "sum"), PAYOUT_TOTAL: (PAYOUT, "sum")},
        )
        return summed.assign(**{CANDIDATE: candidate})

    def line_totals(self, candidates: pd.DataFrame) -> pd.DataFrame:
        """候補 × 券種 の、全部の年の合計と回収率。"""
        totals = candidates.groupby([CANDIDATE, TICKET_TYPE], as_index=False)[[POINTS, STAKE_TOTAL, PAYOUT_TOTAL]].sum()
        totals[RETURN_RATE] = totals[PAYOUT_TOTAL] / totals[STAKE_TOTAL]
        return self._labeled(totals)[[CANDIDATE, TYPE_LABEL, POINTS, STAKE_TOTAL, PAYOUT_TOTAL, RETURN_RATE]]

    def chosen_lines(self, candidates: pd.DataFrame) -> pd.DataFrame:
        """券種 × 年（2年目から）と合計の行。列は 券種・年・選んだもの・前の年までの回収率・点数・賭け金・払戻・回収率。"""
        value_only = candidates[candidates[CANDIDATE] != "印どおり"]
        parts = [self._chosen_line(value_only[value_only[TICKET_TYPE] == ticket_type])
                 for ticket_type in value_only[TICKET_TYPE].unique()]
        table = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
        return self._labeled(table)[[TYPE_LABEL, YEAR_LABEL, CHOSEN, PRIOR_RATE, POINTS, STAKE_TOTAL, PAYOUT_TOTAL, RETURN_RATE]]

    def allocation(self, candidates: pd.DataFrame) -> pd.DataFrame:
        """配分 × 年（2年目から）と合計の行。列は 配分・年・選んだもの・点数・賭け金・払戻・回収率。"""
        keyed = candidates.assign(_key=candidates[CANDIDATE] + "・" + candidates[TICKET_TYPE].map(self._type_labels()))
        years = sorted(keyed[YEAR].unique())
        rows: list[list[object]] = []
        for policy in (BEST_ONE, OVER_BREAK_EVEN):
            policy_rows = [self._allocated(keyed, year, policy) for year in years[1:]]
            totals = [sum(int(row[position]) for row in policy_rows) for position in (3, 4, 5)]
            rows += [*policy_rows, [policy, TOTAL_YEAR, "", *totals]]
        table = pd.DataFrame(rows, columns=[POLICY, YEAR_LABEL, CHOSEN, POINTS, STAKE_TOTAL, PAYOUT_TOTAL])
        table[RETURN_RATE] = table[PAYOUT_TOTAL] / table[STAKE_TOTAL].where(table[STAKE_TOTAL] > 0)
        return table

    def _chosen_line(self, rows: pd.DataFrame) -> pd.DataFrame:
        """1つの券種の、年ごとに選んだ線と、その年の結果。"""
        years = sorted(rows[YEAR].unique())
        picked = [self._pick(rows, year) for year in years[1:]]
        table = pd.DataFrame([row for row in picked if row is not None])
        if table.empty:
            return table
        total = table[[POINTS, STAKE_TOTAL, PAYOUT_TOTAL]].sum().to_frame().T
        total = total.assign(**{TICKET_TYPE: rows[TICKET_TYPE].iloc[0], YEAR: TOTAL_YEAR, CHOSEN: "", PRIOR_RATE: float("nan")})
        table = pd.concat([table, total], ignore_index=True)
        table[RETURN_RATE] = table[PAYOUT_TOTAL] / table[STAKE_TOTAL].where(table[STAKE_TOTAL] > 0)
        return table.rename(columns={YEAR: YEAR_LABEL})

    def _pick(self, rows: pd.DataFrame, year: str) -> dict[str, object] | None:
        """その年より前の年の回収率がいちばん高い線と、その線で買ったその年の結果。選べる線が無ければ None。"""
        prior = self._prior_rates(rows, year, CANDIDATE)
        if prior.empty:
            return None
        best = str(prior.idxmax())
        current = rows[(rows[YEAR] == year) & (rows[CANDIDATE] == best)]
        return {TICKET_TYPE: rows[TICKET_TYPE].iloc[0], YEAR: year, CHOSEN: best, PRIOR_RATE: float(prior.max()),
                POINTS: int(current[POINTS].sum()), STAKE_TOTAL: int(current[STAKE_TOTAL].sum()),
                PAYOUT_TOTAL: int(current[PAYOUT_TOTAL].sum())}

    def _allocated(self, keyed: pd.DataFrame, year: str, policy: str) -> list[object]:
        """その年に買う（候補・券種）を前の年までで選び、その年の結果を1行にする。"""
        chosen = self._choose(self._prior_rates(keyed, year, "_key"), policy)
        current = keyed[(keyed[YEAR] == year) & keyed["_key"].isin(chosen)]
        return [policy, year, "、".join(chosen) or "（買わない）", int(current[POINTS].sum()),
                int(current[STAKE_TOTAL].sum()), int(current[PAYOUT_TOTAL].sum())]

    def _choose(self, prior: pd.Series, policy: str) -> list[str]:
        """前の年までの回収率から、買う（候補・券種）を選ぶ。選べるものが無ければ空。"""
        if policy == BEST_ONE:
            return [str(prior.idxmax())] if not prior.empty else []
        return [str(key) for key in prior[prior >= 1.0].index]

    def _prior_rates(self, rows: pd.DataFrame, year: str, key: str) -> pd.Series:
        """``key`` ごとの、その年より前の年の回収率（前の年までに ``MIN_PRIOR_POINTS`` 点以上買ったものだけ）。"""
        prior = rows[rows[YEAR] < year].groupby(key)[[POINTS, STAKE_TOTAL, PAYOUT_TOTAL]].sum()
        prior = prior[prior[POINTS] >= MIN_PRIOR_POINTS]
        return prior[PAYOUT_TOTAL] / prior[STAKE_TOTAL]

    def _labeled(self, table: pd.DataFrame) -> pd.DataFrame:
        """券種の鍵を名前（単勝 など）にし、券種の並び（単勝〜3連単）に並べ直す。"""
        if table.empty:
            return pd.DataFrame(columns=[CANDIDATE, TYPE_LABEL, YEAR_LABEL, CHOSEN, PRIOR_RATE, POINTS, STAKE_TOTAL,
                                         PAYOUT_TOTAL, RETURN_RATE])
        order = {ticket_type.key: position for position, ticket_type in enumerate(TicketType)}
        ordered = table.assign(_type=table[TICKET_TYPE].map(order)).sort_values("_type", kind="stable")
        return ordered.assign(**{TYPE_LABEL: ordered[TICKET_TYPE].map(self._type_labels())}).reset_index(drop=True)

    def _type_labels(self) -> dict[str, str]:
        return {ticket_type.key: ticket_type.label for ticket_type in TicketType}
