"""N. 末脚の履歴（10個）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import EntryRecords

from .history import ClosingRunSummary


class ClosingHistoryFeatures:
    """N. この馬が、これまで後半にどう走ってきたか（設計書 09 の N）。``FeatureGroup`` を守る。"""

    def __init__(self) -> None:
        self._summary = ClosingRunSummary()

    def build(self, records: EntryRecords) -> pd.DataFrame:
        return self._summary.build(records.entries, records.past_runs)
