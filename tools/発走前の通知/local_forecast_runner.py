"""地方の予想（local_predict.py。予想モデルの predict と荒れ具合の予想）を別プロセスで動かす。"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

from 発走前の通知.folders import LOCAL_LOG_NAME, LOCAL_PREDICT_SCRIPT
from 発走前の通知.forecast_runner import ForecastRunner
from 発走前の通知.local_forecast_store import LocalForecastStore

#: 予測する時点（predict の --timing）。
RACE_DAY = "当日"
DAY_BEFORE = "前日"
#: 当日の時点が「馬体重がまだ DB にありません」で失敗したと見る言葉。
_WEIGHT_MISSING = "馬体重"


def _stderr(text: str) -> None:
    print(text, file=sys.stderr, flush=True)


class LocalForecastRunner:
    """地方には朝の全レースの予想（複勝の勝負レースの計画）が無いので、``run_day`` は何もしない。
    発走前は当日の時点で予想し、馬体重がまだ DB に無くて失敗したら前日の時点（オッズだけ）で予想する
    （地方競馬DATA の馬体重は発走の 15 分前まで届かないことがある）。結果は predict の JSON と券種ごとの中荒れ以上の確率
    （推奨買目の 3連複の条件が読む）を ``LocalForecastStore`` の場所に書く。2つは ``local_predict.py`` が同じ接続で出す
    （地方の全成績の事実表を作るのが1回で済む。毎回新しいプロセスなので、レースを重ねても遅くならない）。
    別プロセスの動かし方と記録は中央と同じ ``ForecastRunner``（``program`` に local_predict.py を渡す）。"""

    def __init__(self, *, store: LocalForecastStore | None = None, process: ForecastRunner | None = None,
                 log: Callable[[str], None] = _stderr) -> None:
        self._store = store or LocalForecastStore()
        self._process = process or ForecastRunner(program=("python", str(LOCAL_PREDICT_SCRIPT)), log_name=LOCAL_LOG_NAME)
        self._log = log

    def run_day(self, day: str) -> None:
        self._log(f"{day}: 地方は朝の全レースの予想を作らない（レースごとに発走前に予想する）")

    def run_race(self, rid: str, day: str) -> None:
        self._store.path(rid).parent.mkdir(parents=True, exist_ok=True)
        try:
            self._predict(rid, day, RACE_DAY)
        except RuntimeError as error:
            if _WEIGHT_MISSING not in str(error):
                raise
            self._log(f"{rid}: 馬体重がまだ DB に無いので、前日の時点（オッズだけ）で予想します")
            self._predict(rid, day, DAY_BEFORE)

    def log_path(self, day: str) -> Path:
        return self._process.log_path(day)

    def _predict(self, rid: str, day: str, timing: str) -> None:
        arguments = ["--upset-out", str(self._store.upset_path(rid)),
                     "predict", rid, "--timing", timing, "--format", "json", "--out", str(self._store.path(rid))]
        self._process.run(arguments, f"{rid} の予想（{timing}の時点）", day)
