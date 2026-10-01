"""過去の全部の走のスピード指数を読む。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from 共通.ability import FIGURE, AbilitySettings, FigureCache
from 共通.ability.figure_cache import DEFAULT_FOLDER

__all__ = ["SpeedFigureRepository", "FIGURE_COLUMNS", "DEFAULT_FOLDER"]

#: 馬の力の材料に使う列（``FigureCache`` がとっておく列のうち）。
FIGURE_COLUMNS: tuple[str, ...] = (
    "race_id", "race_date", "horse_id", "venue_code", "surface", "distance_m", "condition", "finish",
)


class SpeedFigureRepository:
    """スピード指数の付いた過去の全部の走（1行 = 1頭の出走）を読む。

    SQL と計算は、道具「能力指数」と同じ ``FigureCache``（``tools/共通/ability/``）に任せ、同じ SQL を2か所に書かない。
    とっておいたファイル（``reports/能力指数/cache/``）が、DB の最後の確定の開催日と作り方の設定に合っていれば読むだけ、
    合っていなければ作り直す（1〜2分）。作り方は道具と同じ既定の設定（``AbilitySettings()``）にして、ファイルを共有する。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, folder: Path = DEFAULT_FOLDER) -> None:
        self._con = con
        self._cache = FigureCache(AbilitySettings(), folder)

    def read(self) -> pd.DataFrame:
        """列は ``FIGURE_COLUMNS`` と ``figure``（スピード指数。無い走は欠損値）。"""
        frame = self._cache.load(self._con)
        return frame[list(FIGURE_COLUMNS)].assign(figure=frame[FIGURE].astype("float64"))
