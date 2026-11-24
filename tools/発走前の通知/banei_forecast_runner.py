"""ばんえいの予想（道具「ばんえいの予想」の predict.py）を別プロセスで動かす。"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

from 発走前の通知.banei_forecast_store import BaneiForecastStore
from 発走前の通知.folders import BANEI_LOG_NAME, BANEI_PREDICT_SCRIPT
from 発走前の通知.forecast_runner import ForecastRunner


def _stderr(text: str) -> None:
    print(text, file=sys.stderr, flush=True)


class BaneiForecastRunner:
    """朝の全レースの予想は作らない。発走前に1レースを予想し、結果を ``BaneiForecastStore`` の場所に書く。
    ばんえいの予想はオッズを使わないので、時点の違い（前日・当日）は無い。馬体重と馬場水分の速報は、元DB にあれば predict が使う。
    別プロセスの動かし方と記録は中央と同じ ``ForecastRunner``（``program`` に predict.py を渡す）。"""

    def __init__(self, *, store: BaneiForecastStore | None = None, process: ForecastRunner | None = None,
                 log: Callable[[str], None] = _stderr) -> None:
        self._store = store or BaneiForecastStore()
        self._process = process or ForecastRunner(program=("python", str(BANEI_PREDICT_SCRIPT)), log_name=BANEI_LOG_NAME)
        self._log = log

    def run_day(self, day: str) -> None:
        self._log(f"{day}: ばんえいは朝の全レースの予想を作らない（レースごとに発走前に予想する）")

    def run_race(self, rid: str, day: str) -> None:
        self._process.run([rid, "--out", str(self._store.path(rid))], f"{rid} の予想（ばんえい）", day)

    def log_path(self, day: str) -> Path:
        return self._process.log_path(day)
