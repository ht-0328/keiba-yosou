"""第2段: 荒れたレースだけで学ぶ馬ごとの予想を、1つの区切りで学ぶ。"""

from __future__ import annotations

import time
from collections.abc import Set

import pandas as pd

from yosou.shared.dataset import RACE_ID, TrainingData
from yosou.shared.ml_model import MEMBER_TYPES, ProbabilityModel
from yosou.shared.setting import HyperparameterSettings

from 既存モデルの改善.analysis.variants import ModelVariant
from 既存モデルの改善.analysis.variants.model_variant import WHOLE
from 既存モデルの改善.analysis.walk_forward.prediction_frame import PART_TEST, PART_VALID, PredictionFrame
from 既存モデルの改善.analysis.windows import TestWindow


class WildOnlyWindowTrainer:
    """学習と検証（早期終了）には荒れたレース（``wild_races``）の行だけを使い、予測は検証とテストの期間の全部の行に出す。

    「このレースが荒れるとしたら、どの馬が来るか」を学ばせるため、荒れなかったレースは学びに使わない。
    予測を全部の行に出すのは、レースを選ぶ時点では荒れるかどうかが分からないため（選んだレースの全頭に当てはめる）。
    列と基準の作り方（``variant``）は今の本番と同じにする。
    """

    def __init__(self, settings: HyperparameterSettings, wild_races: Set[str]) -> None:
        self._settings = settings
        self._wild_races = frozenset(wild_races)
        self._frame = PredictionFrame()

    def run(self, data: TrainingData, window: TestWindow,
            variant: ModelVariant) -> tuple[pd.DataFrame, list[dict[str, object]]]:
        """（予測の表, 学習の記録の行）。"""
        prepared = variant.prepare(data)
        wild = prepared.where(prepared.ids[RACE_ID].isin(self._wild_races))
        train, valid = window.train(wild), window.valid(wild)
        started = time.perf_counter()
        members = [member_type.from_settings(self._settings).fit(train, valid) for member_type in MEMBER_TYPES]
        seconds = round(time.perf_counter() - started, 1)
        frames = [self._predict(members, part, window, name)
                  for part, name in ((window.valid(prepared), PART_VALID), (window.test(prepared), PART_TEST))]
        logs = [{"区切り": window.name, "作り方": variant.name, "モデル": member.name, "木の数": member.tree_count,
                 "学習の行数": len(train), "学習のレース数": int(train.ids[RACE_ID].nunique()),
                 "2つのモデルの学習の秒": seconds} for member in members]
        return pd.concat(frames, ignore_index=True), logs

    def _predict(self, members: list[ProbabilityModel], data: TrainingData, window: TestWindow, part: str) -> pd.DataFrame:
        probabilities = {member.name: member.predict_proba(data) for member in members}
        return self._frame.build(data, probabilities, window.name, part, WHOLE)
