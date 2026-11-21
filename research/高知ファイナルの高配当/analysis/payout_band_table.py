"""配当の帯の表: 3連単の配当の帯ごとのレース数・割合・配当の中央値。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table
from 地方の万馬券.analysis.payout_band import PAYOUT_BANDS, PayoutBand

COLUMNS: tuple[str, ...] = ("配当の帯", "レース数", "割合", "配当の中央値")
_ALL = "全部"


@dataclass(frozen=True)
class PayoutBandTable:
    """``races``（``payout_band``・``trifecta_payout`` を持つレースの表）→ 帯ごとの行と、全部の行。"""

    payout: PayoutBand = PayoutBand()

    def build(self, races: pd.DataFrame, *, title: str) -> Table:
        rows = [self._row(band, races[races["payout_band"] == band], len(races)) for band in PAYOUT_BANDS]
        rows.append(self._row(_ALL, races, len(races)))
        return Table.from_records(rows, COLUMNS, title=title, note=self.payout.label)

    def _row(self, name: str, in_band: pd.DataFrame, total: int) -> dict:
        median = int(in_band["trifecta_payout"].median()) if len(in_band) else 0
        share = len(in_band) / total if total else 0.0
        return {"配当の帯": name, "レース数": len(in_band), "割合": f"{share:.1%}", "配当の中央値": median}
