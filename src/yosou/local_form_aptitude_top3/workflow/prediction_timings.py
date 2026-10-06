"""この予想が予測を出す時点と、時点の呼び名、モデルの置き場所（設計書 07・04）。"""

from __future__ import annotations

from pathlib import Path

from yosou.shared.feature import LOCAL_FIRST_TIMING_LABEL, PredictionTiming

from ..command.yosou_name import YOSOU_NAME

#: keiba-yosou のリポジトリ直下（src/yosou/local_form_aptitude_top3/workflow/ から4つ上）。
_PROJECT_ROOT = Path(__file__).resolve().parents[4]

#: この予想が学習し、予測を出す時点（出馬表・前日・当日の3つ全部）。
TIMINGS: tuple[PredictionTiming, ...] = tuple(PredictionTiming)
#: 時点 → 表に出す名前。地方には出走馬名表（木曜）の段階が無く、オッズのまだ無い最初の時点は出馬表（枠番・馬番は決まっている）。
#: プログラムの中では共通の値（``thursday``）をそのまま使い、表示だけを替える（設計書 07）。
TIMING_LABELS: dict[PredictionTiming, str] = {
    PredictionTiming.THURSDAY: LOCAL_FIRST_TIMING_LABEL,
    PredictionTiming.DAY_BEFORE: PredictionTiming.DAY_BEFORE.label,
    PredictionTiming.RACE_DAY: PredictionTiming.RACE_DAY.label,
}
#: 当日に券種のオッズが無いときに使う、N を使わないモデルの置き場所（モデルの置き場所の下のフォルダの名前）。
POOL_FREE_FOLDER = "券種オッズなし"
#: 1着のモデル（目的変数「1着」。設計書 10）の置き場所（3着以内のモデルの置き場所の下のフォルダの名前。
#: 券種オッズなしの1着のモデルは ``券種オッズなし/1着/``）。
WIN_FOLDER = "1着"
#: テスト期間の確かめ（``backtest``）が書く予測の表の既定の置き場所（Git の対象外の reports/）。
DEFAULT_PREDICTIONS_DIR = _PROJECT_ROOT / "reports" / YOSOU_NAME / "predictions"
