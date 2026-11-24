"""組の表に、開催日と、当たったか・払戻を付ける。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.repository.payout_repository import COMBO as PAYOUT_COMBO
from yosou.shared.repository.payout_repository import YEN

from .column_names import COMBO, HIT, PAYOUT, RACE_DATE, RACE_ID
from .table_columns import stored_columns


class HitLabeler:
    """材料の付いた組の表（``ComboTableBuilder.build``）に、開催日・払戻（``payout``。100円あたりの円。外れは 0）・
    目的変数（``hit``。払戻があれば 1）を付けて、保存する列の並び（``table_columns.stored_columns``）にする。

    ``payouts`` は払戻の明細（``PayoutRepository.read``。列 ``race_id``・``combo``・``yen``）。同じ組が複数行あれば合計する
    （同着など）。``race_dates`` は ``race_id`` を index にした開催日。
    """

    def label(self, ticket_type: TicketType, table: pd.DataFrame, payouts: pd.DataFrame, race_dates: pd.Series) -> pd.DataFrame:
        paid = payouts.assign(**{RACE_ID: payouts[RACE_ID].astype(str), COMBO: payouts[PAYOUT_COMBO].astype(str)})
        totals = paid.groupby([RACE_ID, COMBO], as_index=False)[YEN].sum().rename(columns={YEN: PAYOUT})
        labeled = table.merge(totals[[RACE_ID, COMBO, PAYOUT]], on=[RACE_ID, COMBO], how="left")
        labeled[PAYOUT] = labeled[PAYOUT].fillna(0.0).astype(float)
        labeled[HIT] = (labeled[PAYOUT] > 0).astype(np.int8)
        labeled[RACE_DATE] = race_dates.reindex(labeled[RACE_ID]).to_numpy()
        return labeled[stored_columns(ticket_type)]
