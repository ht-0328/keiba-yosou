"""L. 同じレースの馬との比較（序盤）（9個）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import as_numbers

from .race_order_statistic import RaceOrderStatistic


class EarlyFieldComparisonFeatures:
    """L. このメンバーの中で、前に行けそうか（設計書 09 の L）。``FieldFeatureGroup`` を守る。

    K の値を、同じレースの全出走馬で比べる。内・外は馬番で分ける。馬番の決まっていない時点（木曜）は、
    内・外と相対馬番が欠損値になる（その時点のモデルは、この3個を使わない。設計書 07）。
    """

    def __init__(self) -> None:
        self._order = RaceOrderStatistic()

    def build(self, entries: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        race = entries["race_id"]
        lead = as_numbers(features["先頭率"])
        front = as_numbers(features["先団率"])
        recent = as_numbers(features["近5走の序盤の位置の平均"])
        others_lead = lead.groupby(race).transform("sum") - lead
        inner_lead = self._inner_sum(entries, lead)
        no_history = (as_numbers(features["近5走の序盤の記録の数"]) == 0).astype("float64")
        return pd.DataFrame({
            "ほかの馬の先頭率の合計": others_lead,
            "ほかの馬の先団率の合計": front.groupby(race).transform("sum") - front,
            "自分より内の馬の先頭率の合計": inner_lead,
            "自分より外の馬の先頭率の合計": others_lead - inner_lead,
            "先頭率のレース内順位": lead.groupby(race).rank(method="min", ascending=False),
            "近5走の序盤の位置の平均のレース内順位": recent.groupby(race).rank(method="min"),
            "先頭率がいちばん高い相手との差": lead - self._order.best_other(lead, race, largest=True),
            "序盤の記録が無い馬の数": no_history.groupby(race).transform("sum") - no_history,
            "相対馬番": as_numbers(entries["horse_no"]) / race.groupby(race).transform("size"),
        }, index=entries.index)

    def _inner_sum(self, entries: pd.DataFrame, lead: pd.Series) -> pd.Series:
        """馬番が自分より小さい馬の先頭率の合計。馬番が無ければ欠損値。"""
        horse_no = as_numbers(entries["horse_no"])
        ordered = pd.DataFrame({"race": entries["race_id"], "no": horse_no, "lead": lead}).sort_values(["race", "no"])
        inner = ordered.groupby("race", sort=False)["lead"].cumsum() - ordered["lead"]
        return inner.reindex(entries.index).where(horse_no.notna())
