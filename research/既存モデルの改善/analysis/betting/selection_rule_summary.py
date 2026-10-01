"""勝負するレースの選び方の決まりごとの、テスト期間の成績の表。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from 共通.render import Table

from yosou.shared.dataset import RACE_DATE

from ..comparison.table_formatter import TableFormatter
from ..scores import BootstrapInterval
from ..walk_forward import WINDOW
from .candidate_columns import RACE, RETURN, STAKE
from .race_columns import AXIS_PROBABILITY, GRADED
from .race_selection_rule import RaceSelectionRule
from .selection_rule_comparison import RULE

#: 軸の3着以内の確率の帯（成績を見るときの区切り）。
_AXIS_BANDS = [0.0, 0.5, 0.6, 0.7, 0.8, 1.01]


class SelectionRuleSummary:
    """決まりごとに、区切りごとの回収率・合計の成績（90% の幅つき）・検証期間で選んだ選び方の表を作る。

    - ``records``: 区切り × 決まり の記録（``SelectionRuleComparison`` の記録の行を並べたもの）。
    - ``bought``: 決まりごとにテスト期間に買った買い目（``RULE`` と ``WINDOW`` の列つき）。
    - ``races``: テスト期間のレース単位の表（開催日・重賞か・軸の3着以内の確率）。
    - ``rules``: 比べた決まり。最初の決まりを「今の買い方」として、それより良い区切りの数を数える。
    """

    def __init__(self, records: pd.DataFrame, bought: pd.DataFrame, races: pd.DataFrame,
                 rules: Sequence[RaceSelectionRule]) -> None:
        info = races[[RACE, RACE_DATE, GRADED, AXIS_PROBABILITY]].drop_duplicates(RACE)
        self._bought = bought.merge(info, on=RACE, how="left")
        self._records = records
        self._rules = tuple(rules)
        self._format = TableFormatter()

    def tables(self) -> list[Table]:
        return [self._by_window(), self._pooled(), self._choices(), self._by_axis_band()]

    def _by_window(self) -> Table:
        rates = self._records.pivot_table(index=WINDOW, columns=RULE, values="テストの回収率", aggfunc="first", sort=False)
        names = [rule.name for rule in self._rules if rule.name in rates.columns]
        frame = rates[names].reset_index()
        return self._format.table(frame, "勝負するレースの選び方ごとの、区切りごとの回収率（テスト期間）",
                                  note="券種の線と買う券種はどの選び方でも同じで、違うのは勝負するレースの選び方だけ。"
                                       "選び方の中の候補（1開催日のレース数・堅さの帯）は、区切りごとに検証期間で決めた。")

    def _pooled(self) -> Table:
        base = self._rules[0]
        base_rates = self._rates(base.name)
        rows = [self._pooled_row(rule, base_rates) for rule in self._rules]
        return self._format.table(pd.DataFrame(rows), "勝負するレースの選び方ごとの成績（7つの区切りのテスト期間の合計）",
                                  note=f"「今の買い方より良い区切り」は、区切りごとの回収率が「{base.name}」より高かった区切りの数。"
                                       "90%の幅は開催日を単位にしたブートストラップ。")

    def _pooled_row(self, rule: RaceSelectionRule, base_rates: pd.Series) -> dict[str, object]:
        rows = self._bought[self._bought[RULE] == rule.key]
        races = rows.drop_duplicates(RACE)
        per_day = races.groupby(RACE_DATE)[RACE].size()
        stake, payout = float(rows[STAKE].sum()), float(rows[RETURN].sum())
        low, high = BootstrapInterval().of(rows[RACE_DATE], rows[STAKE], rows[RETURN]) if len(rows) else (np.nan, np.nan)
        better = (self._rates(rule.name).reindex(base_rates.index) > base_rates).fillna(False)
        return {
            "選び方": rule.name, "勝負したレース数": len(races), "うち重賞": int(races[GRADED].fillna(False).sum()),
            "1開催日あたりのレース数（平均）": float(per_day.mean()) if len(per_day) else np.nan,
            "1開催日あたりのレース数（最大）": float(per_day.max()) if len(per_day) else np.nan,
            "投資（円）": int(stake), "払戻（円）": int(payout), "回収率": payout / stake if stake else np.nan,
            "回収率の90%の下限": low, "回収率の90%の上限": high,
            "今の買い方より良い区切り": f"{int(better.sum())} / {len(base_rates)}",
        }

    def _rates(self, name: str) -> pd.Series:
        chosen = self._records[self._records[RULE] == name]
        return chosen.set_index(WINDOW)["テストの回収率"]

    def _choices(self) -> Table:
        columns = [WINDOW, RULE, "検証期間で選んだ選び方", "検証の控えめな見積もり", "テストの勝負したレース数", "うち重賞",
                   "テストの回収率"]
        return self._format.table(self._records[columns], "区切りごとに、検証期間で選んだ勝負するレースの選び方",
                                  note="検証期間 = テストの直前の1年（最初の区切りだけ半年）。")

    def _by_axis_band(self) -> Table:
        """今の買い方で買ったレースを、軸の3着以内の確率の帯で分けた成績（堅いレースほど良いかを見る）。"""
        rows = self._bought[self._bought[RULE] == self._rules[0].key]
        band = pd.cut(rows[AXIS_PROBABILITY], _AXIS_BANDS, right=False)
        grouped = rows.groupby(band, observed=True).agg(勝負したレース数=(RACE, "nunique"), 投資=(STAKE, "sum"),
                                                        払戻=(RETURN, "sum"))
        grouped["回収率"] = grouped["払戻"] / grouped["投資"]
        grouped.index = [f"{interval.left:g}〜{min(interval.right, 1.0):g}" for interval in grouped.index]
        frame = grouped.rename_axis("軸の3着以内の確率").reset_index()
        return self._format.table(frame, f"{self._rules[0].name}で買ったレースの、軸の3着以内の確率の帯ごとの成績",
                                  note="軸 = 消を除いて、全頭の予想の3着以内の確率がいちばん高い馬。確率が高いほど、予想が迷わず1頭を選べている"
                                       "（研究「一番人気を疑う」の「◎が堅いレース」）。")
