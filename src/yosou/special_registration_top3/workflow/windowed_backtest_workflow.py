"""7つの区切りでの確かめの流れを進める。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from yosou.ability_score import AbilityScoreAttachment
from yosou.shared.dataset import HORSE_ID, RACE_ID, TOP3, WIN, PeriodSplitter, RowsUntil, TrainingData, WinTargetData
from yosou.shared.evaluation import Evaluation
from yosou.shared.ml_model import MEMBER_TYPES
from yosou.shared.repository import ModelRepository
from yosou.shared.workflow import BacktestWorkflow, TrainingWorkflow
from yosou.shared.workflow.backtest_workflow import PREDICTION_COLUMNS

from ..dataset import FieldComparisonFreeData
from .backtest_windows import BacktestWindow
from .prediction_comparison import PredictionComparison
from .prediction_timings import REGISTRATION_TIMING, TIMINGS, WIN_FOLDER
from .special_race_evaluation import SpecialRaceEvaluation, SpecialRaceRows

#: 材料の版の名前（``--variant``）。
ALL_FEATURES = "全部"
NO_FIELD_COMPARISON = "相手と比べない"
VARIANTS: tuple[str, ...] = (ALL_FEATURES, NO_FIELD_COMPARISON)
#: 全期間をつなげた行の名前。
WHOLE_PERIOD = "全期間"
#: 予測の表の「レースID」「馬ID」「区切り」の列。
_RACE_COLUMN, _HORSE_COLUMN, _WINDOW_COLUMN = PREDICTION_COLUMNS[0], PREDICTION_COLUMNS[2], PREDICTION_COLUMNS[5]


@dataclass(frozen=True)
class WindowedBacktestResult:
    """7つの区切りでの確かめの結果。

    - ``special``: 目的変数 → [(区切りの名前か「全期間」, 特別競走の行の当たり具合)]。
    - ``all_rows``: 目的変数 → [(区切りの名前, 全レースの行の当たり具合。参考)]。
    - ``prediction_paths``: 目的変数 → 書いた予測の表（道具「印の成績」が読む形。区切りの列付き）。
    - ``comparisons``: 目的変数 → 木曜のモデルとの比べ（``--compare`` を渡したときだけ）。
    - ``feature_count``: 学んだ特徴量の数。``variant``: 材料の版の名前。
    """

    special: dict[str, list[tuple[str, list[Evaluation]]]]
    all_rows: dict[str, list[tuple[str, list[Evaluation]]]]
    prediction_paths: dict[str, Path]
    feature_count: int
    variant: str
    comparisons: dict[str, pd.DataFrame] = field(default_factory=dict)


class WindowedBacktestWorkflow:
    """過去で学習して次の半年を予想する確かめを、7つの区切りで行う（設計書 05 の図5・16 の 4）。

    学習データは全期間で1回作って受け取り、T（能力スコア）を足し、区切りごとに終わりの日で行を切り（``RowsUntil``）、その区切りの期間で
    共通の ``TrainingWorkflow.train()`` を呼んで ``<models_root>/<区切り>/`` に 3着以内と1着のモデルを保存し、共通の ``BacktestWorkflow.run()``
    でテスト期間を予測して、特別競走の行だけの当たり具合（``SpecialRaceEvaluation``）を測る。予測の表は、特別競走の行だけを区切りの名前を
    付けて1つにまとめ、``<predictions_root>/thursday<-1着><-版>.pkl`` に書く（道具「印の成績」が特別競走で測るため。設計書 16 の 6）。``variant`` が「相手と比べない」なら、相手と比べる材料の 70列を外してから同じ手順を通す。
    ``compare``（目的変数 → 木曜のモデルの予測の表）が渡されれば、同じレース・同じ馬で比べる（``PredictionComparison``）。
    ハイパーパラメータは初期値（``defaults_path``）のまま。
    """

    def __init__(self, models_root: Path, predictions_root: Path, defaults_path: Path, warmup_first_day: date,
                 train_first_day: date, variant: str = ALL_FEATURES, compare: dict[str, Path] | None = None) -> None:
        if variant not in VARIANTS:
            raise ValueError(f"材料の版は {' / '.join(VARIANTS)} のどれかです: {variant}")
        self._models_root = Path(models_root)
        self._predictions_root = Path(predictions_root)
        self._defaults_path = defaults_path
        self._warmup_first_day = warmup_first_day
        self._train_first_day = train_first_day
        self._variant = variant
        self._compare = dict(compare or {})
        self._evaluation = SpecialRaceEvaluation()
        self._comparison = PredictionComparison()

    def run(self, data: TrainingData, windows: Sequence[BacktestWindow]) -> WindowedBacktestResult:
        """``data`` は全期間の学習データ（T はまだ無くてよい）。"""
        prepared = AbilityScoreAttachment().apply(data)
        if self._variant == NO_FIELD_COMPARISON:
            prepared = FieldComparisonFreeData().training(prepared)
        special: dict[str, list[tuple[str, list[Evaluation]]]] = {TOP3: [], WIN: []}
        all_rows: dict[str, list[tuple[str, list[Evaluation]]]] = {TOP3: [], WIN: []}
        joined: dict[str, SpecialRaceRows | None] = {TOP3: None, WIN: None}
        predictions: dict[str, list[pd.DataFrame]] = {TOP3: [], WIN: []}
        for window in windows:
            period = window.period(self._warmup_first_day, self._train_first_day)
            rows = RowsUntil(window.end).keep(None, prepared)
            root = self._models_root / window.name
            self._train(rows, period, root)
            report = BacktestWorkflow(root, TIMINGS, root / "predictions", win_folder=WIN_FOLDER).run(rows, period)
            test = PeriodSplitter(period).split(rows).test
            for label, target in ((TOP3, test), (WIN, WinTargetData().training(test))):
                table = pd.read_pickle(report.prediction_paths[label][REGISTRATION_TIMING]).assign(**{_WINDOW_COLUMN: window.name})
                window_rows = self._evaluation.rows_of(target, table, window.name)
                predictions[label].append(self._special_only(table, window_rows))
                special[label].append((window.name, self._evaluation.evaluate(REGISTRATION_TIMING, window_rows)))
                all_rows[label].append((window.name, report.evaluations[label]))
                joined[label] = window_rows if joined[label] is None else joined[label].joined(window_rows)
        for label in (TOP3, WIN):
            if joined[label] is not None and len(windows) > 1:
                special[label].append((WHOLE_PERIOD, self._evaluation.evaluate(REGISTRATION_TIMING, joined[label])))
        paths = {label: self._write(label, pd.concat(tables, ignore_index=True)) for label, tables in predictions.items() if tables}
        comparisons = {label: self._comparison.compare(joined[label], pd.read_pickle(path))
                       for label, path in self._compare.items() if joined.get(label) is not None}
        return WindowedBacktestResult(special, all_rows, paths, len(prepared.catalog.columns_for(REGISTRATION_TIMING)),
                                      self._variant, comparisons)

    def _train(self, rows: TrainingData, period, root: Path) -> None:
        """区切りの行で、3着以内のモデル（``root``）と1着のモデル（``root/1着``）を学んで保存する。"""
        self._workflow(period, root).train(rows, None)
        self._workflow(period, root / WIN_FOLDER).train(WinTargetData().training(rows), None)

    def _workflow(self, period, root: Path) -> TrainingWorkflow:
        return TrainingWorkflow(None, period, ModelRepository(root, MEMBER_TYPES), TIMINGS, self._defaults_path)

    def _special_only(self, table: pd.DataFrame, rows: SpecialRaceRows) -> pd.DataFrame:
        """予測の表のうち、特別競走の行（``rows`` にあるレースID・馬ID）だけ。"""
        keys = pd.DataFrame({_RACE_COLUMN: rows.data.ids[RACE_ID].astype(str).to_numpy(),
                             _HORSE_COLUMN: rows.data.ids[HORSE_ID].astype(str).to_numpy()})
        typed = table.assign(**{_RACE_COLUMN: table[_RACE_COLUMN].astype(str), _HORSE_COLUMN: table[_HORSE_COLUMN].astype(str)})
        return typed.merge(keys.drop_duplicates(), on=[_RACE_COLUMN, _HORSE_COLUMN], how="inner")

    def _write(self, label: str, table: pd.DataFrame) -> Path:
        """区切りをまとめた予測の表（特別競走の行だけ）を書く（道具「印の成績」が読む形）。"""
        self._predictions_root.mkdir(parents=True, exist_ok=True)
        label_suffix = "" if label == TOP3 else f"-{label}"
        variant_suffix = "" if self._variant == ALL_FEATURES else f"-{self._variant}"
        path = self._predictions_root / f"{REGISTRATION_TIMING.value}{label_suffix}{variant_suffix}.pkl"
        table.to_pickle(path)
        return path
