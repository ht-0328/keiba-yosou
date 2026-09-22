"""この予想の、学習データ・予測用データの決めごと（設計書 06 の図1・図2・08・10）。

学習データ・予測用データを作るクラスそのもの（``DatasetBuilder`` など）は ``yosou.shared.dataset``。
ここには、この予想だけの決めごとと、それを渡す組み立てを置く。

| 名前 | 仕事 |
|---|---|
| ``RunnerSelector`` | 入れる行を選ぶ（障害・取消を除く、学習データの始まり以降）。``SampleSelector`` を守る |
| ``TargetBuilder`` | 目的変数（3着以内・1着）を付ける。``TargetLabeler`` を守る |
| ``OddsInput`` | 利用者が ``--odds`` で渡した「馬番 → 単勝オッズ」を表す値 |
| ``OddsResolver`` | 予測に使う単勝オッズを決める（渡されたオッズ → 締め切り前のオッズ → 元DB のオッズ） |
| ``dataset_builder()`` | 上の決めごとと特徴量の一覧（``CATALOG``）を渡して、共通の ``DatasetBuilder`` を組み立てる関数 |

目的変数の列の名前（3着以内・1着）は ``column_names.py``。
"""

from .column_names import TOP3, WIN
from .dataset_assembly import dataset_builder
from .odds_input import OddsInput
from .odds_resolver import OddsResolver
from .runner_selector import RunnerSelector
from .target_builder import TargetBuilder

__all__ = [
    "dataset_builder", "RunnerSelector", "TargetBuilder", "OddsInput", "OddsResolver", "TOP3", "WIN",
]
