"""同じレース・同じ時点の展開の予測を、1回だけ動かして使い回す。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from yosou.race_development.workflow import DevelopmentPaceWorkflow
from yosou.shared.dataset import OddsInput
from yosou.shared.feature import PredictionTiming


class MemoizedPaceForecast:
    """``DevelopmentPaceWorkflow.run`` と同じ形（``run(con, race_id, timing, given_odds)``）で、直前と同じレース・時点なら前の表を返す。

    展開の予測は1レース 1分ほどかかる。同じレースで展開スコア（S）とバイアスの補正（U）の両方を足すときや、3着以内と1着の両方の
    予測用データに足すときに、展開のモデルを何度も動かさないための部品。
    """

    def __init__(self, models_root: Path) -> None:
        self._workflow = DevelopmentPaceWorkflow(models_root)
        self._last: tuple[tuple[str, PredictionTiming], pd.DataFrame] | None = None

    def run(self, con: duckdb.DuckDBPyConnection, race_id: str, timing: PredictionTiming,
            given_odds: OddsInput | None = None) -> pd.DataFrame:
        key = (race_id, timing)
        if self._last is None or self._last[0] != key:
            self._last = (key, self._workflow.run(con, race_id, timing, given_odds))
        return self._last[1]
