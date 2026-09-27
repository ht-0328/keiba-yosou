"""穴馬の予想の確率のずれを、7つの区切りで確かめる（issue #31「穴馬モデルの確率を較正して、期待値の計算に使えるようにする」）。

本番のモデルの確かめ方（``uv run python -m yosou.longshots_in_top3 calibration``。期間は設計書 16 の分け方）と同じ表を、
7つの区切りのテスト期間でも出し、較正（Platt scaling・isotonic regression）を足すとどうなるかを比べる。

| クラス | 仕事 |
|---|---|
| ``CalibrationFrameBuilder`` | 区切りごとの予測から、本番の ``CalibrationCheck`` と同じ列の材料の表を作る |
| ``PlattCalibration`` | Platt scaling（確率のロジットに傾きと切片を当てる）で確率をそろえ直す |
| ``IsotonicCalibration`` | isotonic regression（順を保った階段の形）で確率をそろえ直す |
| ``CalibrationComparison`` | 較正の方法ごとに、検証期間で学んでテスト期間に当て、ずれと期待値の当たり具合を比べる |
"""

from .calibration_comparison import RAW, CalibrationComparison
from .calibration_frame_builder import WINDOW_COLUMN, CalibrationFrameBuilder
from .isotonic_calibration import IsotonicCalibration
from .platt_calibration import PlattCalibration

__all__ = [
    "CalibrationFrameBuilder", "PlattCalibration", "IsotonicCalibration", "CalibrationComparison",
    "RAW", "WINDOW_COLUMN",
]
