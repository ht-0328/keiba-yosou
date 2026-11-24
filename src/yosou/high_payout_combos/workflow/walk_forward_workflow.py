"""年ごとに学んで、次の年を予測する流れを進める（確かめ用）。"""

from __future__ import annotations

from collections.abc import Callable, Mapping

import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.setting import HyperparameterSettings

from ..dataset.column_names import HIT, MARKET_PROBABILITY, ODDS, PAYOUT
from ..dataset.table_columns import id_columns
from ..feature.own_market_features import FEATURE_LOG_Q
from ..repository import ComboTableRepository, PredictionStore
from .table_prediction import TablePrediction
from .ticket_model_trainer import TicketModelTrainer
from .walk_year_result import WalkYearResult
from .year_samples import YearSamples

#: 早期終了に使うのは、テストの年の何年前の行か（1年前）。学ぶのは、それより前の全部の年の行。
_VALID_YEARS_BEFORE = 1


class WalkForwardWorkflow:
    """テストの年 Y ごとに、Y−2年までの行で学び、Y−1年の行で早期終了し、Y年の対象の行を全部（間引かずに）予測して保存する。

    どの年の予測も、その年より前のレースだけで学んだモデルが出したものになる（本番と同じ条件で回収率を確かめるため）。
    学習の行は表のある最初の年から。予測は ``PredictionStore`` に年ごとに書く。
    例: 表が 2015〜2026年にあり ``first_year`` が 2020 なら、2020年は 2015〜2018年で学び 2019年で止め、…、2026年は 2015〜2024年で学び 2025年で止める。
    前に作った予測のある年は、``overwrite`` が偽なら飛ばす（途中で止まっても、続きの年から再開できる）。
    """

    def __init__(self, tables: ComboTableRepository, predictions: PredictionStore, settings: HyperparameterSettings,
                 samples: YearSamples | None = None, *, overwrite: bool = False,
                 progress: Callable[[str], None] | None = None) -> None:
        self._tables = tables
        self._predictions = predictions
        self._settings = settings
        self._samples = samples or YearSamples(tables)
        self._overwrite = overwrite
        self._progress = progress or (lambda message: None)

    def run(self, ticket_type: TicketType, first_year: int) -> list[WalkYearResult]:
        """``first_year`` から表のある最後の年までを、順に予測する。学ぶ年と止める年の両方がある年だけが対象。"""
        years = self._tables.years(ticket_type)
        test_years = [year for year in years if year >= first_year and self._has_earlier_years(year, years)]
        if not test_years:
            raise ValueError(
                f"{ticket_type.label}の表が足りません（ある年: {years}）。{first_year}年を予測するには、その2年前までと1年前の表が要ります"
            )
        done = [year for year in test_years if not self._overwrite and year in self._predictions.years(ticket_type)]
        pending = [year for year in test_years if year not in done]
        skipped = [self._skipped(ticket_type, year) for year in done]
        if not pending:
            return skipped
        samples = self._samples.by_year(ticket_type)
        predicted = [self._one_year(ticket_type, year, samples) for year in pending]
        return sorted(skipped + predicted, key=lambda result: result.year)

    def _has_earlier_years(self, year: int, years: list[int]) -> bool:
        """早期終了に使う年（1年前）と、学ぶ年（2年前まで）の表があるか。"""
        valid_year = year - _VALID_YEARS_BEFORE
        return valid_year in years and any(each < valid_year for each in years)

    def _skipped(self, ticket_type: TicketType, year: int) -> WalkYearResult:
        return WalkYearResult(ticket_type, year, 0, 0, {}, 0, self._predictions.path(ticket_type, year), was_skipped=True)

    def _one_year(self, ticket_type: TicketType, year: int, samples: Mapping[int, pd.DataFrame]) -> WalkYearResult:
        valid_year = year - _VALID_YEARS_BEFORE
        train_rows = pd.concat([rows for each, rows in samples.items() if each < valid_year], ignore_index=True)
        valid_rows = samples[valid_year]
        members = TicketModelTrainer(ticket_type, self._settings).fit(train_rows, valid_rows)
        table = self._tables.load(ticket_type, year)
        probabilities = TablePrediction(ticket_type, members).probabilities(table)
        predictions = pd.concat([table[[*id_columns(ticket_type), ODDS, PAYOUT, HIT]], probabilities], axis=1)
        predictions[MARKET_PROBABILITY] = np.exp(table[FEATURE_LOG_Q].astype(float))
        path = self._predictions.save(ticket_type, year, predictions)
        tree_counts = {member.name: member.tree_count for member in members}
        self._progress(f"{ticket_type.label} {year}年: 木の数 {tree_counts}・予測 {len(predictions):,} 行")
        return WalkYearResult(ticket_type, year, len(train_rows), len(valid_rows), tree_counts, len(predictions), path)
