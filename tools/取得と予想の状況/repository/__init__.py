"""取得の状況を読むリポジトリ。1つの SQL につき1つのクラス。

| クラス | 読む表 | 返すもの |
|---|---|---|
| ``SyncRecordRepository`` | ``_meta`` | 鍵と値（同期の記録 ``sync:RACE`` など） |
| ``FinalResultRangeRepository`` | ``ra`` | 確定成績の最初と最後の開催日・レース数（中央だけか、地方の DB の全部） |

レースごとの材料の有無（出馬表・馬体重・オッズ）は ``共通.race_signals`` のリポジトリが読む。
"""

from .final_result_range_repository import FinalResultRangeRepository
from .sync_record_repository import SyncRecordRepository

__all__ = ["FinalResultRangeRepository", "SyncRecordRepository"]
