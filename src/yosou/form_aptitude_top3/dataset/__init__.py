"""この予想の、学習データ・予測用データの決めごと（設計書 06 の図1・図2・08・10）。

学習データ・予測用データを作るクラスそのもの（``DatasetBuilder`` など）は ``yosou.shared.dataset``。
ここには、この予想だけの決めごとと、それを渡す組み立てを置く。

| 名前 | 仕事 |
|---|---|
| ``RunnerSelector`` | 入れる行を選ぶ（障害・取消を除く、学習データの始まり以降）。``SampleSelector`` を守る |
| ``OddsInput`` | 利用者が ``--odds`` で渡した「馬番 → 単勝オッズ」を表す値 |
| ``OddsResolver`` | 予測に使う単勝オッズを決める（渡されたオッズ → 締め切り前のオッズ → 元DB のオッズ） |
| ``dataset_builder()`` | ``RunnerSelector``・共通の ``Top3TargetBuilder``（3着以内なら 1）・特徴量の一覧（``CATALOG``）とまとまりの並びを渡して、共通の ``DatasetBuilder`` を組み立てる関数 |

目的変数（3着以内・1着）を付ける部品と、その列の名前（``TOP3``・``WIN``）は、穴馬の予想とも共通なので
``yosou.shared.dataset`` にある。
"""

from yosou.shared.dataset import TOP3, WIN

from .dataset_assembly import dataset_builder
from .odds_input import OddsInput
from .odds_resolver import OddsResolver
from .runner_selector import RunnerSelector

__all__ = ["dataset_builder", "RunnerSelector", "OddsInput", "OddsResolver", "TOP3", "WIN"]
