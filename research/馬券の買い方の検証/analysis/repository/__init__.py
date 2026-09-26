"""元DB から、期間ぶんをまとめて読む（1 SQL = 1クラス）。表が無い DB（合成DB・取得前）では空で返る。

| クラス | 仕事 |
|---|---|
| ``RaceFactRepository`` | 事実表から、レースの属性（開催日・競馬場・レース番号・芝ダ・距離・クラス・グレード・頭数）を 1レース1行で読む |

確定オッズ（``FinalOddsRepository``）・払戻の明細（``PayoutRepository``）・払戻のフラグ（``PayoutFlagRepository``）と、
読む期間（``RaceDayRange``）は、共通の ``yosou.shared.repository`` のものを使う。
"""

from .race_fact_repository import RaceFactRepository

__all__ = ["RaceFactRepository"]
