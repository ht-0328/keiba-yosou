"""保存した予想の結果から、レースごとの予想のペースの確率を集める（回顧の表2に残すため）。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from yosou.review import names

from 今週の予想.forecast_store import ForecastStore


class ForecastPaces:
    """``reports/今週の予想/<開催日>/<rid>.json`` の ``pace``（展開スコアを足した時点の予想で残る、ハイ・スローの確率）を、
    回顧の表2「レースの回顧」の予想のペースにする表（``race_id``・予想のハイの確率・予想のスローの確率）にする。無いレースは入れない。"""

    def __init__(self, store: ForecastStore) -> None:
        self._store = store

    def table(self) -> pd.DataFrame:
        rows = []
        for path in sorted(Path(self._store.folder).glob("*/*.json")):
            if not path.stem.isdigit():
                continue
            forecast = self._store.load(path.stem)
            pace = (forecast or {}).get("pace")
            if pace and pace.get("high") is not None:
                rows.append({names.RACE_ID: path.stem, names.FORECAST_HIGH: pace.get("high"), names.FORECAST_SLOW: pace.get("slow")})
        return pd.DataFrame(rows, columns=[names.RACE_ID, names.FORECAST_HIGH, names.FORECAST_SLOW])
