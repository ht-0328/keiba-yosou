"""レース前の材料の有無を読むリポジトリ。1つの SQL につき1つのクラス。

| クラス | 読む表 | 返すもの |
|---|---|---|
| ``RaceHeaderRepository`` | ``ra`` | レースの見出し（開催日・競馬場・発走時刻・データ区分・馬場状態コード …） |
| ``EntryCountRepository`` | ``se`` | レースごとの出走馬の数・馬番の決まった数・馬体重の出ている数 |
| ``AnnouncedOddsSummaryRepository`` | ``o1`` と ``o1__単勝オッズ`` | レースごとの、締め切り前のいちばん新しい断面の発表月日時分とオッズの付いた馬の数 |
"""

from .announced_odds_summary_repository import AnnouncedOddsSummaryRepository
from .entry_count_repository import EntryCountRepository
from .race_header_repository import RaceHeaderRepository

__all__ = ["AnnouncedOddsSummaryRepository", "EntryCountRepository", "RaceHeaderRepository"]
