"""この予想が予測を出す時点と、時点の呼び名、モデルと予測の表の置き場所（設計書 07・04）。"""

from __future__ import annotations

from pathlib import Path

from yosou.shared.feature import REGISTRATION_TIMING_LABEL, PredictionTiming

from ..yosou_name import YOSOU_NAME

#: keiba-yosou のリポジトリ直下（src/yosou/special_registration_top3/workflow/ から4つ上）。
_PROJECT_ROOT = Path(__file__).resolve().parents[4]

#: この予想が学習し、予測を出す時点。特別登録（月曜・ハンデ発表後）の1つだけ。
#: プログラムの中では中央と共通の木曜の枠（``thursday``）を使い、表示だけを「特別登録」にする（設計書 07 の「時点の表し方」）。
REGISTRATION_TIMING = PredictionTiming.THURSDAY
TIMINGS: tuple[PredictionTiming, ...] = (REGISTRATION_TIMING,)
#: 時点 → 表に出す名前。
TIMING_LABELS: dict[PredictionTiming, str] = {REGISTRATION_TIMING: REGISTRATION_TIMING_LABEL}
#: 1着のモデル（目的変数「1着」。設計書 10）の置き場所（3着以内のモデルの置き場所の下のフォルダの名前）。
WIN_FOLDER = "1着"
#: この予想の出力の置き場所（Git の対象外の reports/）。
REPORT_ROOT = _PROJECT_ROOT / "reports" / YOSOU_NAME
#: 7つの区切りでの確かめ（``backtest``）が区切りごとのモデルを置く場所と、予測の表を書く既定の場所。
DEFAULT_WINDOW_MODELS_DIR = REPORT_ROOT / "models-区切り"
DEFAULT_PREDICTIONS_DIR = REPORT_ROOT / "predictions"
#: 登録馬の確かめ（``registrations``）が既定で使うモデル（2026年の区切り。学習は 2025年6月まで）。
DEFAULT_CHECK_MODELS_DIR = DEFAULT_WINDOW_MODELS_DIR / "2026年"
