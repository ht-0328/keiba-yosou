"""今のモデルの学習の表（2012年から）に型の材料を足し、人気薄の行だけの学習データにする。"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import pandas as pd

from yosou.shared.dataset import WinTargetData
from yosou.shared.feature import PredictionTiming

from 既存モデルの改善.analysis.tables import TableStore
from 複勝以外の回収率100超.analysis.retrain_targets import retrain_target_named

from .current_baseline import LOGIT, CurrentBaseline
from .longshot_data import HORSE_NO, RACE_ID, LongshotData
from .longshot_variant import CURRENT_BASELINE
from .type_features import COLUMNS as TYPE_COLUMNS

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
#: 今のモデルの学習の表（研究「複勝以外の回収率100超」が 2012年から用意したもの）。
DEFAULT_TABLES = _PROJECT_ROOT / "reports" / "複勝以外の回収率100超" / "tables-2012"
#: 時点 → 今のモデルの1着のモデル（研究「複勝以外の回収率100超」の学び直しの対象の名前）。
PRODUCTION_WIN: dict[PredictionTiming, str] = {PredictionTiming.RACE_DAY: "当日・1着", PredictionTiming.DAY_BEFORE: "前日・1着"}
#: 材料から外す列（人気の順位そのもの。市場の評価は出発点のオッズから見た勝率で渡す）。
DROPPED: tuple[str, ...] = ("人気順位",)
#: 評価用の列の名前。
_POPULARITY, _MARKET = "確定の単勝人気", "オッズから見た勝率"


@dataclass(frozen=True)
class LongshotDataset:
    """時点ごとに、今のモデルの1着の列（``DROPPED`` を除く）＋型の材料の、``min_popularity`` 番人気以下の行の学習データを作る。

    目的変数は1着、基準はオッズから見た勝率のロジット（レースの全頭で作ってから行を選ぶ。今のモデルの1着と同じ ``WinTargetData``）。"""

    type_features: pd.DataFrame
    tables: Path = DEFAULT_TABLES

    def build(self, timing: PredictionTiming, min_popularity: int, baseline: str | None = None) -> LongshotData:
        """``baseline`` が ``CURRENT_BASELINE`` なら、出発点を今のモデルのそろえた1着の確率のロジットに替え、その予測の無い行を除く。"""
        target = retrain_target_named(PRODUCTION_WIN[timing])
        data = TableStore(self.tables).read(target.variant.model, target.catalog)
        prepared = target.variant.prepare(WinTargetData().training(data))
        columns = [column for column in prepared.features.columns if column not in DROPPED]
        prepared = replace(prepared, features=prepared.features[columns])
        keys = prepared.ids[[RACE_ID, HORSE_NO]].astype({RACE_ID: str, HORSE_NO: int})
        added = keys.merge(self.type_features, on=[RACE_ID, HORSE_NO], how="left")[list(TYPE_COLUMNS)]
        features = pd.concat([prepared.features.reset_index(drop=True), added.reset_index(drop=True)], axis=1)
        frame = LongshotData(
            prepared.ids.reset_index(drop=True).astype({RACE_ID: str}), features, prepared.label.reset_index(drop=True).astype(int),
            prepared.baseline.values.reset_index(drop=True), prepared.evaluation[_POPULARITY].reset_index(drop=True).astype(float),
            prepared.evaluation[_MARKET].reset_index(drop=True).astype(float), prepared.categorical_columns,
        )
        frame = frame.where(frame.popularity >= min_popularity)
        return self._on_current(frame, timing) if baseline == CURRENT_BASELINE else frame

    @staticmethod
    def _on_current(frame: LongshotData, timing: PredictionTiming) -> LongshotData:
        keys = frame.ids[[RACE_ID, HORSE_NO]].astype({HORSE_NO: int}).reset_index(drop=True)
        logit = keys.merge(CurrentBaseline().of(timing), on=[RACE_ID, HORSE_NO], how="left")[LOGIT]
        known = logit.notna().to_numpy()
        replaced = replace(frame, baseline=pd.Series(logit.to_numpy(), index=frame.baseline.index))
        return replaced.where(known)
