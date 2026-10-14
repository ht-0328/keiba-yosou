"""学習データ・予測用データを作る（組み立てと、この予想だけの部品。ほかは ``yosou.shared.dataset``）。

| 名前 | 仕事 |
|---|---|
| ``registration_dataset_builder()`` | 共通の ``DatasetBuilder`` を、この予想の決めごとで組み立てる |
| ``RegistrationRecordsLoader`` | 予測用に、1レースの登録馬の記録を集める（速報とオッズは読まない） |
| ``RegistrationCutoff`` | 登録日相当（材料の締めの日。開催日より前の直近の月曜日）の SQL の式と Python の関数 |
| ``FieldComparisonFreeData`` | 学習データ・予測用データから、同じレースの相手と比べる材料の 70列を外す |
| ``NoOddsResolver`` | 予測に使うオッズを決めない（オッズを使わない予想の ``PredictionWorkflow`` に渡す） |
| ``WARMUP_FIRST_DAY``・``TRAIN_FIRST_DAY`` | 学習データの既定の期間（2011年・2012年の1月1日） |
"""

from yosou.shared.dataset import TOP3, WIN

from .dataset_assembly import TRAIN_FIRST_DAY, WARMUP_FIRST_DAY, registration_dataset_builder
from .field_comparison_free_data import FieldComparisonFreeData
from .no_odds_resolver import NoOddsResolver
from .registration_cutoff import RegistrationCutoff
from .registration_records_loader import RegistrationRecordsLoader

__all__ = [
    "registration_dataset_builder", "RegistrationRecordsLoader", "RegistrationCutoff", "FieldComparisonFreeData",
    "NoOddsResolver", "WARMUP_FIRST_DAY", "TRAIN_FIRST_DAY", "TOP3", "WIN",
]
