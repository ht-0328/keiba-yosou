"""この予想が予測を出す時点と、時点の呼び名、置き場所（設計書 07・04）。"""

from __future__ import annotations

from pathlib import Path

from yosou.shared.feature import LOCAL_FIRST_TIMING_LABEL, PredictionTiming

from ..yosou_name import YOSOU_NAME

#: keiba-yosou のリポジトリ直下（src/yosou/local_upset_level/workflow/ から4つ上）。
_PROJECT_ROOT = Path(__file__).resolve().parents[4]

#: この予想が学習し、予測を出す時点（出馬表・前日・当日の3つ全部）。
TIMINGS: tuple[PredictionTiming, ...] = tuple(PredictionTiming)
#: 時点 → 表に出す名前。地方には出走馬名表（木曜）の段階が無く、オッズのまだ無い最初の時点は出馬表（枠番・馬番は決まっている）。
#: プログラムの中では共通の値（``thursday``）をそのまま使い、表示だけを替える（地方の全頭の予想と同じ）。
TIMING_LABELS: dict[PredictionTiming, str] = {
    PredictionTiming.THURSDAY: LOCAL_FIRST_TIMING_LABEL,
    PredictionTiming.DAY_BEFORE: PredictionTiming.DAY_BEFORE.label,
    PredictionTiming.RACE_DAY: PredictionTiming.RACE_DAY.label,
}
#: 時点の書き方の案内（コマンドの説明に使う）。
TIMING_CHOICES = " / ".join(f"{TIMING_LABELS[timing]}（{timing.value}）" for timing in TIMINGS)
#: 学習したモデルの既定の置き場所（``<券種>/<時点>/``。地方競馬DATA から作ったもので公開しないので Git の対象外）。
DEFAULT_MODELS_DIR = _PROJECT_ROOT / "reports" / YOSOU_NAME / "models"
#: 学習データの pickle と、年ごとの過去の傾きの表をとっておく既定の場所（Git の対象外）。
DEFAULT_CACHE_DIR = _PROJECT_ROOT / "reports" / YOSOU_NAME / "cache"
