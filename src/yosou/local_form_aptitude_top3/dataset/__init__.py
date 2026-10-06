"""この予想の、学習データ・予測用データの組み立て（設計書 06 の図1・08・10）。

学習データ・予測用データを作るクラスそのもの（``DatasetBuilder``・``RunnerSelector``・``Top3TargetBuilder`` など）は
``yosou.shared.dataset``。ここには、地方の決めごとを渡して組み立てるところと、学習データの期間の既定を置く。

| 名前 | 仕事 |
|---|---|
| ``local_dataset_builder()`` | 地方の事実表（``LOCAL_FACTS_SOURCE``）・出走別着度数地方（``LOCAL_CAREER_LAYOUT``）・L・N・O・Q の元の記録を渡して、共通の ``DatasetBuilder`` を組み立てる関数 |
| ``LOCAL_WARMUP_FIRST_DAY`` | ウォームアップ期間の既定の始まり（2016年1月1日。DB にある最初の年） |
| ``LOCAL_TRAIN_FIRST_DAY`` | 学習データの既定の始まり（2019年1月1日） |
| ``LOCAL_HISTORY_FIRST_DAY`` | 対戦レーティングの元の記録を読み始める日（2016年1月1日） |
"""

from .dataset_assembly import LOCAL_HISTORY_FIRST_DAY, LOCAL_TRAIN_FIRST_DAY, LOCAL_WARMUP_FIRST_DAY, local_dataset_builder

__all__ = ["local_dataset_builder", "LOCAL_WARMUP_FIRST_DAY", "LOCAL_TRAIN_FIRST_DAY", "LOCAL_HISTORY_FIRST_DAY"]
