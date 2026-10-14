"""流れを進めるクラス（この予想のもの。学習・予測・テスト期間の確かめは ``yosou.shared.workflow``）。

| 名前 | 仕事 |
|---|---|
| ``registration_prediction_workflow()`` | 共通の ``PredictionWorkflow`` を、この予想の決めごと（登録馬の行・オッズ無し・T を足す）で組み立てる |
| ``WindowedBacktestWorkflow`` | 7つの区切りでの確かめ（区切りごとに学習 → テスト期間を予測 → 特別競走の行で当たり具合を測る） |
| ``BacktestWindow``・``WINDOWS``・``windows_named()`` | 区切りの表と、名前で選ぶ |
| ``SpecialRaceEvaluation`` | テスト期間の特別競走の行だけで当たり具合を測る（頭数から見た割合の行も） |
| ``PredictionComparison`` | 中央の木曜のモデルの予測と、同じレース・同じ馬で比べる |
| ``RegistrationCheckWorkflow`` | 登録馬の確かめ（登録馬の全員に予測を出し、確定成績と突き合わせる） |
| ``WindowedBacktestResult``・``SpecialRaceRows``・``RegistrationCheckResult`` | 確かめの結果の入れ物（区切りごとの当たり具合、特別競走の行と確率、登録馬の確かめの表） |
| ``TIMINGS``・``TIMING_LABELS``・``WIN_FOLDER`` など | 時点（特別登録の1つ）と表示名、置き場所（``prediction_timings.py``） |
"""

from yosou.shared.workflow import PROBABILITY, WIN_PROBABILITY, PredictionWorkflow

from .backtest_windows import WINDOWS, BacktestWindow, windows_named
from .prediction_assembly import registration_prediction_workflow
from .prediction_comparison import COMPARISON_COLUMNS, PredictionComparison
from .prediction_timings import (
    DEFAULT_CHECK_MODELS_DIR,
    DEFAULT_PREDICTIONS_DIR,
    DEFAULT_WINDOW_MODELS_DIR,
    REGISTRATION_TIMING,
    REPORT_ROOT,
    TIMING_LABELS,
    TIMINGS,
    WIN_FOLDER,
)
from .registration_check_result import RegistrationCheckResult
from .registration_check_workflow import FILE_NAME, RACE_NAME, RAN, RegistrationCheckWorkflow
from .special_race_evaluation import SpecialRaceEvaluation
from .special_race_rows import SpecialRaceRows
from .windowed_backtest_result import WindowedBacktestResult
from .windowed_backtest_workflow import ALL_FEATURES, NO_FIELD_COMPARISON, VARIANTS, WHOLE_PERIOD, WindowedBacktestWorkflow

__all__ = [
    "PredictionWorkflow", "PROBABILITY", "WIN_PROBABILITY", "registration_prediction_workflow",
    "WindowedBacktestWorkflow", "WindowedBacktestResult", "ALL_FEATURES", "NO_FIELD_COMPARISON", "VARIANTS", "WHOLE_PERIOD",
    "BacktestWindow", "WINDOWS", "windows_named", "SpecialRaceEvaluation", "SpecialRaceRows",
    "PredictionComparison", "COMPARISON_COLUMNS", "RegistrationCheckWorkflow", "RegistrationCheckResult", "FILE_NAME", "RACE_NAME", "RAN",
    "REGISTRATION_TIMING", "TIMINGS", "TIMING_LABELS", "WIN_FOLDER", "REPORT_ROOT", "DEFAULT_WINDOW_MODELS_DIR",
    "DEFAULT_PREDICTIONS_DIR", "DEFAULT_CHECK_MODELS_DIR",
]
