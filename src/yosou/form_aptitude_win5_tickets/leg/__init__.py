"""対象レース1つの1着の確率（設計書 06 の図1、07 の「対象レースごとの確率の選び方」、10 の 1.）。

| クラス | 仕事 |
|---|---|
| ``LegModel`` | 対象レースで使う確率を表す値（列挙。今のモデルの当日・今のモデルの前日・オッズだけ） |
| ``LegModelChoice`` | 選んだ確率と、選んだ理由の文と、使ったオッズの断面 |
| ``LegModelChooser`` | 障害なら「オッズだけ」。平地なら ``TimingChooser`` で今のモデルの時点を選び、木曜なら止める |
| ``LegWinPredictor`` | 選んだ時点で、対象レースの全頭の今のモデルの1着の確率を出す（オッズだけのときは、オッズから見た勝率） |
| ``RaceWinShare`` | 1レースの全頭の1着の確率を合計 1 にそろえ、オッズから見た勝率と上乗せの列を足す |

``leg_columns.py`` は、そろえた1着の確率・オッズから見た勝率・上乗せの列の名前。
"""

from .leg_columns import EDGE, MARKET, SHARE
from .leg_model import LegModel
from .leg_model_choice import LegModelChoice
from .leg_model_chooser import LegModelChooser
from .leg_win_predictor import COLUMNS, LegWinPredictor
from .race_win_share import RaceWinShare

__all__ = [
    "LegModel", "LegModelChoice", "LegModelChooser", "LegWinPredictor", "RaceWinShare", "SHARE", "MARKET", "EDGE", "COLUMNS",
]
