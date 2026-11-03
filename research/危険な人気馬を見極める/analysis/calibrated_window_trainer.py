"""1つの区切り・1つの作り方で、オッズだけのモデルを先に学び、それを出発点にして人気馬の予想を学ぶ。"""

from __future__ import annotations

import time

import pandas as pd

from yosou.shared.dataset import TrainingData

from 既存モデルの改善.analysis.variants import ModelVariant
from 既存モデルの改善.analysis.walk_forward import PART_TEST, PART_VALID, WindowTrainer
from 既存モデルの改善.analysis.windows import TestWindow

from .odds_only_baseline import OddsOnlyBaseline

#: 予測の表に足す、オッズだけのモデルの確率（危険度の比べる相手）の列。
ODDS_ONLY_COLUMN = "オッズだけの確率"


class CalibratedWindowTrainer(WindowTrainer):
    """区分（人気帯）ごとに、本番の人気馬の予想と同じく2段で学ぶ。

    1. オッズの列だけのモデル（``OddsOnlyBaseline``）を学習期間で学ぶ。
    2. 学習・検証・テストの基準を、そのモデルの確率に置き換えて、作り方の列で人気馬の予想を学ぶ。

    予測の表には、ふつうの列に加えて、オッズだけのモデルの確率（``ODDS_ONLY_COLUMN``）を残す。
    危険度は「予想の4着以下の確率 − この確率」で、オッズが同じ馬より、どれだけ負けやすいかを表す。
    """

    def _segment(self, train: TrainingData, valid: TrainingData, test: TrainingData, window: TestWindow,
                 variant: ModelVariant, segment: str) -> tuple[pd.DataFrame, list[dict[str, object]]]:
        parts = {name: data.where(variant.rows_of(data, segment)) for name, data in
                 (("train", train), ("valid", valid), ("test", test))}
        started = time.perf_counter()
        baseline = OddsOnlyBaseline.fit(self._settings, parts["train"], parts["valid"], self._member_types)
        based = {name: baseline.attach(data) for name, data in parts.items()}
        members = [member_type.from_settings(self._settings).fit(based["train"], based["valid"])
                   for member_type in self._member_types]
        seconds = round(time.perf_counter() - started, 1)
        frames = [self._predict(members, based[key], window, part, segment)
                  .assign(**{ODDS_ONLY_COLUMN: baseline.probabilities(parts[key])})
                  for key, part in (("valid", PART_VALID), ("test", PART_TEST))]
        logs = [self._log_row(window, variant, segment, member, len(parts["train"]), seconds) for member in members]
        return pd.concat(frames, ignore_index=True), logs
