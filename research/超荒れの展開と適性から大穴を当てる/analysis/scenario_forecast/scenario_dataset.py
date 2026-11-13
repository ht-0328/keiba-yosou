"""今のモデルの学習の表（2012年から）に、展開・その日の馬場の傾向・ハンデの材料を足し、12頭以上のレースの全頭の学習データにする。"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import pandas as pd

from yosou.shared.dataset import WinTargetData
from yosou.shared.feature import PredictionTiming

from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_data import HORSE_NO, RACE_ID, LongshotData
from 既存モデルの改善.analysis.tables import TableStore
from 複勝以外の回収率100超.analysis.retrain_targets import retrain_target_named

from .scenario_materials import PACE
from .scenario_variant import TOP3, ScenarioVariant

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
#: 今のモデルの学習の表（研究「複勝以外の回収率100超」が 2012年から用意したもの）。
DEFAULT_TABLES = _PROJECT_ROOT / "reports" / "複勝以外の回収率100超" / "tables-2012"
#: （目的変数, 時点）→ 今のモデルの学び直しの対象の名前。
TARGETS: dict[tuple[str, PredictionTiming], str] = {
    (TOP3, PredictionTiming.DAY_BEFORE): "前日・3着以内", (TOP3, PredictionTiming.RACE_DAY): "当日・3着以内",
    ("win", PredictionTiming.DAY_BEFORE): "前日・1着", ("win", PredictionTiming.RACE_DAY): "当日・1着",
}
#: 材料から外す列（人気の順位そのもの。市場の評価は出発点で渡す）。
DROPPED: tuple[str, ...] = ("人気順位",)
#: 学ぶレースの頭数の下限（11頭以下ではほとんど荒れない）。
MIN_FIELD = 12
_POPULARITY, _FIELD = "確定の単勝人気", "確定の出走頭数"
_MARKET = {TOP3: "オッズから見た3着以内率", "win": "オッズから見た勝率"}


@dataclass(frozen=True)
class ScenarioDataset:
    """時点と作り方ごとに、今のモデルの列（``DROPPED`` を除く）＋足す材料の、12頭以上のレースの全頭の学習データを作る。

    目的変数と出発点は今のモデルと同じ（3着以内はオッズから見た3着以内率のロジット、1着はオッズから見た勝率のロジット）。
    ``market`` は出発点の元の率（確かめに使う）。今のモデルの列と同じ名前の材料（馬番の位置）は今のモデルの列を使う。
    展開の型を混ぜない作りでは、展開の型の列を外す。"""

    materials: pd.DataFrame
    tables: Path = DEFAULT_TABLES

    def build(self, timing: PredictionTiming, variant: ScenarioVariant) -> LongshotData:
        target = retrain_target_named(TARGETS[(variant.target, timing)])
        data = TableStore(self.tables).read(target.variant.model, target.catalog)
        data = data if variant.target == TOP3 else WinTargetData().training(data)
        prepared = target.variant.prepare(data)
        columns = [column for column in prepared.features.columns if column not in DROPPED]
        prepared = replace(prepared, features=prepared.features[columns])
        keys = prepared.ids[[RACE_ID, HORSE_NO]].astype({RACE_ID: str}).astype({HORSE_NO: float})
        added = keys.rename(columns={RACE_ID: "race_id", HORSE_NO: "horse_no"}).merge(
            self.materials, on=["race_id", "horse_no"], how="left").drop(columns=["race_id", "horse_no"])
        added = added.drop(columns=[column for column in added.columns if column in prepared.features.columns])
        if not variant.mixed:
            added = added.drop(columns=[PACE])
        features = pd.concat([prepared.features.reset_index(drop=True), added.reset_index(drop=True)], axis=1)
        evaluation = prepared.evaluation.reset_index(drop=True)
        frame = LongshotData(
            prepared.ids.reset_index(drop=True).astype({RACE_ID: str}), features, prepared.label.reset_index(drop=True).astype(int),
            prepared.baseline.values.reset_index(drop=True), evaluation[_POPULARITY].astype(float),
            evaluation[_MARKET[variant.target]].astype(float), prepared.categorical_columns,
        )
        return frame.where(evaluation[_FIELD].astype(float) >= MIN_FIELD)
