"""対戦レーティング（まとまり O）を作る部品（近走と適性の予想の設計書 09 の O）。

同じレースを走った馬どうしの着順の勝ち負けから、Elo のレーティングを開催日の順に更新して作る。どの列も、そのレースの
開催日より前のレースの結果だけから作る（設計書 11 の 2）。

| 名前 | 仕事 |
|---|---|
| ``RatingTableBuilder`` | 入口。下の部品を順に呼んで、対象の出走ごとの7列の表を作る |
| ``EloRaceUpdate`` | 1レースの着順から、出走馬ごとの上げ下げを出す（2頭の組ごとの Elo の式を、相手の数で平均する） |
| ``RatingHistoryBuilder`` | 全出走を開催日の順にたどって、出走ごとの「そのレースの前日までのレーティング」と対戦数を作る |
| ``RatingChangeColumns`` | 履歴から、前走と近5走でどれだけ動いたかの列を作る |
| ``RatingFieldColumns`` | レーティングを、同じレースの出走馬の中での順位・偏差・平均との差に直す |

列の名前とレーティングの決めごと（初期値 1500・尺度 400・K）は ``head_to_head_columns.py``。
"""

from .head_to_head_columns import HEAD_TO_HEAD_NAMES
from .rating_table_builder import RatingTableBuilder

__all__ = ["HEAD_TO_HEAD_NAMES", "RatingTableBuilder"]
