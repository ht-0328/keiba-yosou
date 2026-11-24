"""本番のモデルを学習して保存する流れを進める。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.setting import HyperparameterSettings

from ..dataset import ModelDataFactory
from ..dataset.column_names import RACE_DATE
from ..evaluation import MarketComparison
from ..repository import ComboTableRepository, TicketModelRepository
from .production_training_result import ProductionTrainingResult
from .ticket_model_trainer import TicketModelTrainer
from .year_samples import YearSamples

#: 検証（早期終了）に使う期間の長さ。表のある最後の開催日から、さかのぼって1年。
_VALID_PERIOD = pd.DateOffset(years=1)


class ProductionTraining:
    """これからのレースの予測に使うモデルを、券種ごとに学習して保存する。

    表のある最後の開催日の1年前までの行で学び、最後の1年の行で早期終了して木の数を決める。
    例: 最後の開催日が 2026-06-28 なら、2025-06-28 までで学び、2025-06-29〜2026-06-28 で止める。
    保存は ``TicketModelRepository``。検証の行での当たり具合（対数損失を市場の確率と比べたもの）も返す。
    検証の行は木の数を決めるのに使っているので、この当たり具合は目安（未見の年での確かめは ``walk``）。
    """

    def __init__(self, tables: ComboTableRepository, models: TicketModelRepository, settings: HyperparameterSettings,
                 samples: YearSamples | None = None) -> None:
        self._tables = tables
        self._models = models
        self._settings = settings
        self._samples = samples or YearSamples(tables)

    def run(self, ticket_type: TicketType) -> ProductionTrainingResult:
        by_year = self._samples.by_year(ticket_type)
        if not by_year:
            raise FileNotFoundError(f"{ticket_type.label}の組の表がありません（先に tables で作ってください）")
        rows = pd.concat(list(by_year.values()), ignore_index=True)
        valid_last_day = rows[RACE_DATE].max()
        train_last_day = valid_last_day - _VALID_PERIOD
        is_train = rows[RACE_DATE] <= train_last_day
        train_rows, valid_rows = rows[is_train].reset_index(drop=True), rows[~is_train].reset_index(drop=True)
        members = TicketModelTrainer(ticket_type, self._settings).fit(train_rows, valid_rows)
        folder = self._models.save(ticket_type, members, self._settings)
        losses = MarketComparison().losses(ModelDataFactory(ticket_type).training(valid_rows), members)
        tree_counts = {member.name: member.tree_count for member in members}
        return ProductionTrainingResult(
            ticket_type, train_rows[RACE_DATE].max().date(), valid_last_day.date(), len(train_rows), len(valid_rows),
            tree_counts, losses, folder,
        )
