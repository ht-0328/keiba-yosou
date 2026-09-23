"""元DB から、期間ぶんをまとめて読む（1 SQL = 1クラス）。表が無い DB（合成DB・取得前）では空で返る。

| クラス | 仕事 |
|---|---|
| ``RaceDayRange`` | 読む期間（開催日の範囲）。SQL の条件と引数を作る |
| ``RaceFactRepository`` | 事実表から、レースの属性（開催日・競馬場・レース番号・芝ダ・距離・クラス・グレード・頭数）を 1レース1行で読む |
| ``FinalOddsRepository`` | 1つの券種の確定オッズを、1組番1行で読む（o1〜o6。親の確定の断面と発表月日時分で結ぶ） |
| ``PayoutRepository`` | 1つの券種の払戻の明細を、1組番1行で読む（hr__<券種>払戻。複勝・ワイド・同着の複数行はそのまま） |
| ``PayoutFlagRepository`` | 払戻の親（hr）から、券種ごとの不成立・特払と、返還の有無を 1レース1行で読む |
"""

from .final_odds_repository import FinalOddsRepository
from .payout_flag_repository import REFUNDED, PayoutFlagRepository, void_column
from .payout_repository import PayoutRepository
from .race_day_range import RaceDayRange
from .race_fact_repository import RaceFactRepository

__all__ = [
    "RaceDayRange", "RaceFactRepository", "FinalOddsRepository", "PayoutRepository",
    "PayoutFlagRepository", "void_column", "REFUNDED",
]
