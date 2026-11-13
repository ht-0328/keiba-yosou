"""詳しく見る日のレースごとに、予想「展開から着順を予想」の前半の組（ペースの確率・位置の確率）を予測する。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

from yosou.race_development.command.yosou_name import PROJECT_ROOT, YOSOU_NAME
from yosou.race_development.feature import PriorForecasts
from yosou.race_development.tendency import TendencyForecaster, TendencyModelStore
from yosou.race_development.workflow.forecast_group import ForecastGroup
from yosou.race_development.workflow.group_predictor import GroupPredictor
from yosou.race_development.workflow.kind_model_store import KindModelStore
from yosou.race_development.workflow.race_inputs import RaceInputs
from yosou.shared.feature import PredictionTiming

#: 予想「展開から着順を予想」の学習済みモデル（今毎週の予想が使うもの）。
DEFAULT_MODELS = PROJECT_ROOT / "reports" / YOSOU_NAME / "models"


@dataclass(frozen=True)
class DayPaceForecast:
    """予想「展開から着順を予想」の予測の流れのうち、傾向（既存の予想）→ 前半の組までを、渡した接続で1レースずつ動かす
    （予測の記録は書かない）。``races`` は race_id・p_slow・p_even・p_high、``horses`` は race_id・horse_id・p_leader・p_front・
    p_middle・p_back（年ごとの予測と同じ形）。予測できないレース（障害・オッズが無いなど）は飛ばす。"""

    models: Path = DEFAULT_MODELS

    def predict(self, con: duckdb.DuckDBPyConnection, race_ids: Sequence[str], timing: PredictionTiming) -> tuple[pd.DataFrame, pd.DataFrame]:
        store = KindModelStore(self.models)
        tendency = TendencyForecaster(TendencyModelStore(self.models))
        groups = GroupPredictor(store)
        races, horses = [], []
        for race_id in race_ids:
            try:
                inputs = RaceInputs.read(con, race_id, timing, None)
            except (ValueError, LookupError):
                continue
            priors = PriorForecasts(tendency.predict(inputs.tendency))
            early = groups.predict(ForecastGroup.EARLY, inputs.horses, inputs.races, priors, timing)
            races.append(early.races[["レースID", "p_slow", "p_even", "p_high"]])
            horses.append(early.horses[["レースID", "馬ID", "p_leader", "p_front", "p_middle", "p_back"]])
        race_table = pd.concat(races, ignore_index=True).rename(columns={"レースID": "race_id"}) if races else pd.DataFrame()
        horse_table = (pd.concat(horses, ignore_index=True).rename(columns={"レースID": "race_id", "馬ID": "horse_id"})
                       if horses else pd.DataFrame())
        return race_table.astype({"race_id": str}), horse_table.astype({"race_id": str, "horse_id": str})
