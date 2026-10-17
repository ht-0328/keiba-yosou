"""学習は決めた範囲のレースだけで行い、予測は全部のレースに出す。"""

from __future__ import annotations

import time
from collections.abc import Sequence
from itertools import chain

import pandas as pd

from yosou.shared.dataset import TrainingData
from yosou.shared.ml_model import MEMBER_TYPES, ProbabilityModel
from yosou.shared.setting import HyperparameterSettings

from 既存モデルの改善.analysis.variants import ModelVariant
from 既存モデルの改善.analysis.walk_forward import PART_TEST, PART_VALID, PredictionFrame
from 既存モデルの改善.analysis.windows import TestWindow

from .race_scope import RaceScope


class ScopedWindowTrainer:
    """1つの区切り・1つの作り方で、``scope`` のレースの行だけで LightGBM と CatBoost を学び（木を足すのを止める判断も
    ``scope`` の検証期間の行で行う）、検証期間とテスト期間の**全部の行**を予測する。

    G1 を予想するために作ったモデルを、G2・G3 にもそのまま当てて、どれだけ当たるかを見るためのもの。
    返す形は研究「既存モデルの改善」の ``WindowTrainer`` と同じ（予測の表と学習の記録の行）なので、``WalkForwardRunner`` に渡せる。
    """

    def __init__(self, settings: HyperparameterSettings, scope: RaceScope,
                 member_types: Sequence[type[ProbabilityModel]] = MEMBER_TYPES) -> None:
        self._settings = settings
        self._scope = scope
        self._member_types = tuple(member_types)
        self._frame = PredictionFrame()

    def run(self, data: TrainingData, window: TestWindow,
            variant: ModelVariant) -> tuple[pd.DataFrame, list[dict[str, object]]]:
        prepared = variant.prepare(data)
        train, valid, test = window.train(prepared), window.valid(prepared), window.test(prepared)
        results = [self._segment(train, valid, test, window, variant, segment) for segment in variant.segments(train)]
        return (pd.concat([frame for frame, _ in results], ignore_index=True),
                list(chain.from_iterable(rows for _, rows in results)))

    def _segment(self, train: TrainingData, valid: TrainingData, test: TrainingData, window: TestWindow,
                 variant: ModelVariant, segment: str) -> tuple[pd.DataFrame, list[dict[str, object]]]:
        in_segment = {name: data.where(variant.rows_of(data, segment)) for name, data in
                      (("train", train), ("valid", valid), ("test", test))}
        fit_train, fit_valid = (self._scope.apply(in_segment[name]) for name in ("train", "valid"))
        started = time.perf_counter()
        members = [member_type.from_settings(self._settings).fit(fit_train, fit_valid) for member_type in self._member_types]
        seconds = round(time.perf_counter() - started, 1)
        frames = [self._frame.build(in_segment[name], {member.name: member.predict_proba(in_segment[name]) for member in members},
                                    window.name, part, segment)
                  for name, part in (("valid", PART_VALID), ("test", PART_TEST))]
        logs = [{"区切り": window.name, "作り方": variant.name, "区分": segment, "モデル": member.name, "木の数": member.tree_count,
                 "学習の行数": len(fit_train), "2つのモデルの学習の秒": seconds} for member in members]
        return pd.concat(frames, ignore_index=True), logs
