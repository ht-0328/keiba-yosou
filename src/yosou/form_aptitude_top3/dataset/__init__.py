"""この予想の、学習データ・予測用データの決めごと（設計書 06 の図1・図2・08・10）。

学習データ・予測用データを作るクラスそのもの（``DatasetBuilder`` など）は ``yosou.shared.dataset``。
ここには、この予想だけの決めごとと、それを渡す組み立てを置く。

| 名前 | 仕事 |
|---|---|
| ``dataset_builder()`` | ``RunnerSelector``・共通の ``Top3TargetBuilder``（3着以内なら 1）・特徴量の一覧（``CATALOG``）とまとまりの並びを渡して、共通の ``DatasetBuilder`` を組み立てる関数（今の材料 79個。券種のオッズが無いときの当日のモデル・展開の予想・研究が使う） |
| ``pool_dataset_builder()`` | 今の材料に N（券種ごとのオッズから見た支持）を足した ``DatasetBuilder``（``POOL_CATALOG``。研究の比べに使う） |
| ``race_day_dataset_builder()`` | 今の材料に N と M を足した ``DatasetBuilder``（``RACE_DAY_CATALOG``。当日のモデル） |
| ``ABILITY_TRAIN_FIRST_DAY`` | 馬の力の材料のモデルの学習データの始まり（2012年1月1日） |
| ``ability_dataset_builder()`` | 馬の力の材料（M と O と J）の ``DatasetBuilder``（``ABILITY_CATALOG``。木曜・前日のモデル） |

目的変数（3着以内・1着）を付ける部品と、その列の名前（``TOP3``・``WIN``）は、穴馬の予想とも共通なので
``yosou.shared.dataset`` にある。利用者が ``--odds`` で渡すオッズ（``OddsInput``）と、予測に使うオッズの決め方
（``OddsResolver``）も、荒れ具合の予想と共通なので ``yosou.shared.dataset`` に移した。
行の選び方（``RunnerSelector``）・券種の支持の有無と外し方（``PoolAvailability``・``PoolFreeData``）・勝ち切る材料の外し方
（``FinishPowerFreeData``）・1着のモデル用の持ち替え（``WinTargetData``）・展開の予想の結果の付け方（``PaceAttachment``）は、
地方の予想（``local_form_aptitude_top3``）と同じものなので ``yosou.shared.dataset`` にある（ここから同じ名前で使える）。
"""

from yosou.shared.dataset import (
    TOP3,
    WIN,
    FinishPowerFreeData,
    OddsInput,
    OddsResolver,
    PaceAttachment,
    PoolAvailability,
    PoolFreeData,
    RunnerSelector,
    WinTargetData,
)

from .dataset_assembly import (
    ABILITY_TRAIN_FIRST_DAY,
    ability_dataset_builder,
    dataset_builder,
    pool_dataset_builder,
    race_day_dataset_builder,
)

__all__ = ["dataset_builder", "pool_dataset_builder", "race_day_dataset_builder", "ability_dataset_builder", "ABILITY_TRAIN_FIRST_DAY",
           "PoolFreeData", "FinishPowerFreeData", "WinTargetData", "PoolAvailability", "PaceAttachment", "RunnerSelector", "OddsInput", "OddsResolver", "TOP3", "WIN"]
