"""この予想の、学習データ・予測用データの決めごと（設計書 06 の図1・図2・08・10）。

学習データ・予測用データを作るクラスそのもの（``DatasetBuilder`` など）は ``yosou.shared.dataset``。
ここには、この予想だけの決めごとと、それを渡す組み立てを置く。

| 名前 | 仕事 |
|---|---|
| ``RunnerSelector`` | 入れる行を選ぶ（障害・取消を除く、学習データの始まり以降）。``SampleSelector`` を守る |
| ``dataset_builder()`` | ``RunnerSelector``・共通の ``Top3TargetBuilder``（3着以内なら 1）・特徴量の一覧（``CATALOG``）とまとまりの並びを渡して、共通の ``DatasetBuilder`` を組み立てる関数（今の材料 79個。券種のオッズが無いときの当日のモデル・展開の予想・研究が使う） |
| ``pool_dataset_builder()`` | 今の材料に N（券種ごとのオッズから見た支持）を足した ``DatasetBuilder``（``POOL_CATALOG``。研究の比べに使う） |
| ``race_day_dataset_builder()`` | 今の材料に N と M を足した ``DatasetBuilder``（``RACE_DAY_CATALOG``。当日のモデル） |
| ``PoolFreeData`` | 学習データ・予測用データから N を外す（当日に券種のオッズが無いときのモデル） |
| ``PoolAvailability`` | 予測するレースの券種のオッズがあるかを確かめる |
| ``ABILITY_TRAIN_FIRST_DAY`` | 馬の力の材料のモデルの学習データの始まり（2012年1月1日） |
| ``ability_dataset_builder()`` | 馬の力の材料（M と J）の ``DatasetBuilder``（``ABILITY_CATALOG``。木曜・前日のモデル） |

目的変数（3着以内・1着）を付ける部品と、その列の名前（``TOP3``・``WIN``）は、穴馬の予想とも共通なので
``yosou.shared.dataset`` にある。利用者が ``--odds`` で渡すオッズ（``OddsInput``）と、予測に使うオッズの決め方
（``OddsResolver``）も、荒れ具合の予想と共通なので ``yosou.shared.dataset`` に移した。
"""

from yosou.shared.dataset import TOP3, WIN, OddsInput, OddsResolver

from .dataset_assembly import (
    ABILITY_TRAIN_FIRST_DAY,
    ability_dataset_builder,
    dataset_builder,
    pool_dataset_builder,
    race_day_dataset_builder,
)
from .pool_availability import PoolAvailability
from .pool_free_data import PoolFreeData
from .runner_selector import RunnerSelector

__all__ = ["dataset_builder", "pool_dataset_builder", "race_day_dataset_builder", "ability_dataset_builder", "ABILITY_TRAIN_FIRST_DAY",
           "PoolFreeData", "PoolAvailability", "RunnerSelector", "OddsInput", "OddsResolver", "TOP3", "WIN"]
