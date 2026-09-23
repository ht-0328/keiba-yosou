"""この予想だけのファイルの読み書き（SQL は持たない。元DB を読むリポジトリは ``yosou.shared.repository``）。

| リポジトリ | 読む・書くもの |
|---|---|
| ``DangerThresholdRepository`` | 時点ごと・人気帯ごとの危険度の線（学習のときに検証期間で決めたもの）のファイル |
"""

from .danger_threshold_repository import DangerThresholdRepository

__all__ = ["DangerThresholdRepository"]
