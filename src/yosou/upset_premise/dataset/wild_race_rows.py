"""荒れたレースの行だけを学ぶ。"""

from __future__ import annotations

import duckdb

from 共通 import facts

from yosou.shared.dataset import RACE_DATE, RACE_ID, TrainingData
from yosou.shared.repository import RacePayoutRepository

from .obi_rules import WILD_LINE_YEN

#: レースごとの払戻の表の、3連単の払戻と、成立しなかったかの列（``RacePayoutRepository`` の列の名前）。
_TRIFECTA_YEN, _TRIFECTA_VOID = "trifecta_yen", "trifecta_void"


class WildRaceRows:
    """``TrainingRows`` の決まりを守る。3連単の払戻（100円あたり）が ``line_yen``（既定 10万円）以上のレースの行だけを残す（設計書 08 の 3）。

    手本の予想と同じ材料・同じ列の学習データを作ってから呼ぶ。払戻は ``RacePayoutRepository`` で、学習データの最初の日から読む。
    3連単が成立しなかったレース・払戻の無いレースは、荒れたかどうか分からないので残さない。
    """

    def __init__(self, line_yen: int = WILD_LINE_YEN) -> None:
        self._line_yen = line_yen

    def keep(self, con: duckdb.DuckDBPyConnection, data: TrainingData) -> TrainingData:
        if len(data) == 0:
            return data
        facts.ensure_facts(con)
        payouts = RacePayoutRepository(con).read(data.ids[RACE_DATE].min().date())
        settled = payouts[~payouts[_TRIFECTA_VOID].fillna(False).astype(bool)]
        wild = set(settled.loc[settled[_TRIFECTA_YEN].ge(self._line_yen), "race_id"])
        return data.where(data.ids[RACE_ID].isin(wild))
