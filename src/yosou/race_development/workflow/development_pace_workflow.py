"""1レースの前半・後半の展開を予測し、ほかの予想に渡す元の予測の表にする。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from yosou.shared.dataset import OddsInput
from yosou.shared.feature import PredictionTiming

from ..feature import PaceSourceTable, PriorForecasts
from ..tendency import TendencyForecaster, TendencyModelStore
from .forecast_group import ForecastGroup
from .group_predictor import GroupPredictor
from .kind_model_store import KindModelStore
from .race_inputs import RaceInputs


class DevelopmentPaceWorkflow:
    """1レースを、その時点の保存したモデルで傾向（既存の予想）→ 前半 → 後半の順に予測し、前半・後半の予測を
    まとまり P の元の予測の表（``PaceSourceTable``）にして返す。着順（⑦）は予測しない。

    近走と適性の予想が、予測のときに展開の予想の結果（まとまり P）を作るのに使う。呼ぶ側が開いている元DB の接続を受け取る
    （同じ元DB を、同じプロセスでもう一度開かない）。ほかのクラスを順に呼ぶだけで、自分では計算しない。
    """

    def __init__(self, models_root: Path) -> None:
        self._tendency = TendencyForecaster(TendencyModelStore(models_root))
        self._groups = GroupPredictor(KindModelStore(models_root))

    def run(self, con: duckdb.DuckDBPyConnection, race_id: str, timing: PredictionTiming,
            given_odds: OddsInput | None = None) -> pd.DataFrame:
        """モデルが無ければ ``FileNotFoundError``（先に ``yosou.race_development train`` で学習する）。"""
        inputs = RaceInputs.read(con, race_id, timing, given_odds)
        priors = PriorForecasts(self._tendency.predict(inputs.tendency))
        priors = priors.with_early(self._groups.predict(ForecastGroup.EARLY, inputs.horses, inputs.races, priors, timing))
        late = self._groups.predict(ForecastGroup.LATE, inputs.horses, inputs.races, priors, timing)
        return PaceSourceTable().of(priors.early, late)
