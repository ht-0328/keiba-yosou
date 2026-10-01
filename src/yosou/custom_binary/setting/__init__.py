"""設定（YAML）を読み、学習・予想に共通の設定値にする（設計書 14）。

| 名前 | 仕事 |
|---|---|
| ``ModelSettings`` | 1つのモデルの設定を持つ値。YAML と、保存した設定から作る |
| ``UniqueKeyLoader`` | 同じキーと、文字列でないキーをエラーにする YAML の読み込み |
| ``YamlMapping`` | YAML の1つの組が、知っているキーだけでできているかを確かめる |
| ``PopularityRange`` | 人気範囲（最小・最大。片方だけでもよい） |
| ``TrainingPeriodReader`` | ``training``（期間の区切り）を読む |
| ``HyperparameterReader`` | ``lightgbm``・``catboost`` を、初期値の設定ファイルに上書きして読む |
| ``RowCondition`` | 条件1つ（1つの特徴量の値の範囲か、値のリスト） |
| ``RowConditions`` | 条件の組（すべてに当てはまる馬を残す） |
| ``DEFAULT_SETTINGS_PATH`` | この予想のハイパーパラメータの初期値のファイル（``default_settings.toml``） |

初期値の値は手本の予想と同じだが、予想のパッケージどうしで import しないよう、ファイルをここに持つ。
"""

from .default_settings_path import DEFAULT_SETTINGS_PATH
from .hyperparameter_reader import HyperparameterReader
from .model_settings import ModelSettings
from .popularity_range import PopularityRange
from .row_condition import RowCondition
from .row_conditions import RowConditions
from .training_period_reader import TrainingPeriodReader
from .unique_key_loader import UniqueKeyLoader
from .yaml_mapping import YamlMapping

__all__ = [
    "DEFAULT_SETTINGS_PATH", "HyperparameterReader", "ModelSettings", "PopularityRange", "RowCondition",
    "RowConditions", "TrainingPeriodReader", "UniqueKeyLoader", "YamlMapping",
]
