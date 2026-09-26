"""この予想の読み書き（ファイル）。元DB を読むリポジトリは ``yosou.shared.repository``。

| クラス | 読む・書くもの |
|---|---|
| ``OutOfSampleRepository`` | 前の組の「学習に使っていない予測」（組・時点・年ごと）。作った条件が同じなら、次からは読むだけ |
| ``DatasetRepository`` | 元DB から作った1頭ごと・1レースごとの学習データ（元DB が変わっていなければ、次からは読むだけ） |
| ``PredictionArchiveRepository`` | 予測のたびに、予測用データ（特徴量）と予測を書き足す（上書きしない） |
| ``BacktestArtifactRepository`` | 年ごとの確かめの、年ごとの予測・精算の表と、結果の表（Markdown） |

どれも JV-Data から作ったものなので、置き場所は Git の対象外の ``reports/race_development/`` にする。
"""

from .backtest_artifact_repository import BacktestArtifactRepository
from .dataset_repository import DatasetRepository
from .out_of_sample_repository import OutOfSampleRepository
from .prediction_archive_repository import PredictionArchiveRepository

__all__ = ["OutOfSampleRepository", "BacktestArtifactRepository", "DatasetRepository", "PredictionArchiveRepository"]
