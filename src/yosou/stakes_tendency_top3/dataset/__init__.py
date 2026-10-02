"""この予想の、学習データ・予測用データの決めごと（設計書 06 の図1・図2・08・10）。

学習データ・予測用データを作るクラスそのもの（``DatasetBuilder`` など）は ``yosou.shared.dataset``。
ここには、この予想だけの決めごとと、それを渡す組み立てを置く。

| 名前 | 仕事 |
|---|---|
| ``RunnerSelector`` | 入れる行を選ぶ（障害・取消を除き、**重賞だけ**にする）。``SampleSelector`` を守る |
| ``ability_dataset_builder()`` | 木曜・前日のモデルの ``DatasetBuilder``（手本の M・J に K を足した ``ABILITY_CATALOG``） |
| ``race_day_dataset_builder()`` | 当日のモデルの ``DatasetBuilder``（手本の当日の A〜L・N・M に K を足した ``RACE_DAY_CATALOG``） |
| ``PoolFreeData``・``PoolAvailability``・``POOL_FREE_FOLDER`` | 当日に券種のオッズが無いときに N を外すための部品。手本（近走と適性）のものをそのまま使う |

``PoolFreeData``・``PoolAvailability`` は、本来は ``yosou.shared`` に置いて両方の予想から使うもの。``shared`` と手本を
別の作業が同時に変えているあいだは手本から借り、落ち着いたら ``shared`` に移す（設計書 04 の 1）。
"""

from yosou.form_aptitude_top3.dataset import PoolAvailability, PoolFreeData
from yosou.form_aptitude_top3.workflow import POOL_FREE_FOLDER
from yosou.shared.dataset import TOP3, WIN, OddsInput, OddsResolver

from .dataset_assembly import ability_dataset_builder, race_day_dataset_builder
from .runner_selector import RunnerSelector

__all__ = ["ability_dataset_builder", "race_day_dataset_builder", "RunnerSelector", "PoolAvailability", "PoolFreeData",
           "POOL_FREE_FOLDER", "OddsInput", "OddsResolver", "TOP3", "WIN"]
