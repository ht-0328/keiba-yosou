"""前の組の「学習に使っていない予測」を、組・時点・年ごとにファイルに読み書きする。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from yosou.shared.feature import PredictionTiming

from ..feature import GroupForecast


class OutOfSampleRepository:
    """年ごとの予測を ``<root>/<組>/<時点>/<年>.pkl`` に書き、読む（設計書 04 の「repository/」・05 の図5）。

    予測と一緒に、作ったときの条件（設定ファイルの中身・学習データの範囲・前の組の予測）を表す文字列（``signature``）を
    書いておく。読むときに条件が違えば「まだ無い」と答え、作り直させる。予測は JV-Data から作ったものなので、
    ``root`` は Git の対象外（``reports/``）にする。parquet の道具（pyarrow）が無い環境なので、pickle で書く。
    """

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def load(self, group: str, timing: PredictionTiming, year: int, signature: str) -> GroupForecast | None:
        """同じ条件で作った予測があれば返す。無いか、条件が違えば None。"""
        path = self._path(group, timing, year)
        if not path.exists():
            return None
        saved = pd.read_pickle(path)
        if saved.get("signature") != signature:
            return None
        return GroupForecast(saved["horses"], saved["races"])

    def save(self, group: str, timing: PredictionTiming, year: int, signature: str, forecast: GroupForecast) -> Path:
        path = self._path(group, timing, year)
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.to_pickle({"signature": signature, "horses": forecast.horses, "races": forecast.races}, path)
        return path

    def _path(self, group: str, timing: PredictionTiming, year: int) -> Path:
        return self._root / group / timing.value / f"{year}.pkl"
