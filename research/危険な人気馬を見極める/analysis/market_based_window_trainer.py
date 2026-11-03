"""1つの区切りで、オッズだけのモデルを先に学び、それを出発点にして全頭の予想（3着以内・1着）を学ぶ。"""

from __future__ import annotations

from dataclasses import replace
from itertools import chain

import pandas as pd

from yosou.shared.dataset import TrainingData

from 既存モデルの改善.analysis.variants import ModelVariant
from 既存モデルの改善.analysis.walk_forward import WindowTrainer
from 既存モデルの改善.analysis.windows import TestWindow

from .odds_only_baseline import OddsOnlyBaseline

#: 表の列の名前（レースID は ids、出走頭数は特徴量）。
_RACE, _FIELD_SIZE = "レースID", "出走頭数"


class MarketBasedWindowTrainer(WindowTrainer):
    """全頭の予想を、オッズだけのモデルの確率を出発点にして学ぶ。

    今の全頭の予想は、オッズから計算した確率（3着以内は Harville の式、1着はオッズから見た勝率）を出発点にしている。
    その計算は人気の度合いによって実際の結果とずれるので、モデルは学ぶ力の一部をそのずれを直すことに使い、
    「オッズより来る・来ない」の見分け（買い目の期待値の正しさ）が甘くなる。
    ここでは、目的変数（3着以内か1着）をオッズの列だけで学んだモデル（``OddsOnlyBaseline``）を学習期間で先に学び、
    学習・検証・テストの出発点をその確率に置き換えてから、作り方の列で学ぶ。
    作り方の列にオッズだけのモデルの列（出走頭数など）が無くてもよいように、オッズだけのモデルは時点の列すべての表で学ぶ。
    """

    def run(self, data: TrainingData, window: TestWindow,
            variant: ModelVariant) -> tuple[pd.DataFrame, list[dict[str, object]]]:
        if not variant.uses_baseline:
            raise ValueError(f"{variant.name}: オッズの分かる時点（出発点を使う作り方）だけを学べます")
        timed = self._with_field_size(data.for_timing(variant.timing))
        baseline = OddsOnlyBaseline.fit(self._settings, window.train(timed), window.valid(timed), self._member_types)
        prepared = replace(variant.prepare(data), baseline=baseline.attach(timed).baseline)
        train, valid, test = window.train(prepared), window.valid(prepared), window.test(prepared)
        results = [self._segment(train, valid, test, window, variant, segment) for segment in variant.segments(train)]
        frames = [frame for frame, _ in results]
        logs = list(chain.from_iterable(rows for _, rows in results))
        return pd.concat(frames, ignore_index=True), logs

    @staticmethod
    def _with_field_size(data: TrainingData) -> TrainingData:
        """表に出走頭数の列が無ければ、レースごとの行の数（出走した頭数）から足したデータ。"""
        if _FIELD_SIZE in data.features.columns:
            return data
        sizes = data.ids.groupby(_RACE)[_RACE].transform("size").to_numpy()
        return replace(data, features=data.features.assign(**{_FIELD_SIZE: sizes}))
