"""この予想の、学習データ・予測用データの決めごと（設計書 06 の図1・図2・08・10）。

学習データ・予測用データを作るクラスそのもの（``DatasetBuilder`` など）は ``yosou.shared.dataset``。
ここには、この予想だけの決めごとと、それを渡す組み立てを置く。

| 名前 | 仕事 |
|---|---|
| ``RunnerSelector`` | 入れる行を選ぶ（障害・取消を除き、**重賞だけ**にする）。``SampleSelector`` を守る |
| ``dataset_builder()`` | ``RunnerSelector``・共通の ``Top3TargetBuilder``（3着以内なら 1）・特徴量の一覧（``CATALOG``）と K を含むまとまりの並び・傾向のリポジトリを渡して、共通の ``DatasetBuilder`` を組み立てる関数 |
"""

from yosou.shared.dataset import TOP3, WIN, OddsInput, OddsResolver

from .dataset_assembly import dataset_builder
from .runner_selector import RunnerSelector

__all__ = ["dataset_builder", "RunnerSelector", "OddsInput", "OddsResolver", "TOP3", "WIN"]
