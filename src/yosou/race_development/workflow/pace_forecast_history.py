"""年ごとの確かめで作った前半・後半の予測を、ほかの予想の学習データの材料として読む。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from yosou.shared.feature import PredictionTiming

from ..feature import GroupForecast, PaceSourceTable
from ..repository import OutOfSampleRepository
from .forecast_group import ForecastGroup


class PaceForecastHistory:
    """``<root>/out_of_sample/`` の前半・後半の組の、その時点の年ごとの予測を全部つなぎ、まとまり P の元の予測の表にする。

    どの年の予測も、その年より前だけで学習した展開のモデルのもの（設計書 11 の決まり 11）なので、ほかの予想の学習データの
    材料にしてもリークにならない。作った条件（設定など）は問わない（``OutOfSampleRepository.stored``）。新しい年の予測は、
    ``backtest --timing <時点>`` で作る。
    """

    def __init__(self, root: Path) -> None:
        self._repository = OutOfSampleRepository(Path(root) / "out_of_sample")

    def read(self, timing: PredictionTiming) -> pd.DataFrame:
        """1行 = 1頭（列 ``race_id``・``horse_id`` と ``pace_forecast.SOURCE_COLUMNS``）。前半の予測が無ければ ``FileNotFoundError``。"""
        return PaceSourceTable().of(self._group(ForecastGroup.EARLY, timing), self._group(ForecastGroup.LATE, timing))

    def years(self, timing: PredictionTiming) -> dict[str, list[int]]:
        """組の値 → 予測が残っている年。"""
        return {group.value: self._repository.years(group.value, timing) for group in (ForecastGroup.EARLY, ForecastGroup.LATE)}

    def _group(self, group: ForecastGroup, timing: PredictionTiming) -> GroupForecast:
        years = self._repository.years(group.value, timing)
        if not years:
            raise FileNotFoundError(f"展開の予想の{group.label}の組の{timing.label}の予測がありません"
                                    f"（uv run python -m yosou.race_development backtest --timing {timing.label} で作る）")
        return GroupForecast.concat([self._repository.stored(group.value, timing, year) for year in years])
