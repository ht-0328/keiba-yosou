"""馬の力の材料（まとまり M）を作る部品（近走と適性の予想の木曜・前日の設計書 09 の M）。

研究「馬の力と展開でオッズに勝つ」のオッズを使わない 197個の材料と、研究「一番人気を疑う」で足したセリの価格の5個を、
まだ走っていないレースにも付けられる形にして移したもの。どの列も、そのレースより前の記録だけから作る。

| 名前 | 仕事 |
|---|---|
| ``AbilitySources`` | 元の記録の入れ物（過去の全出走と対象の出走・スピード指数・調教のまとめ・セリの取引） |
| ``AbilityTableBuilder`` | 入口。下の部品を順に呼んで、対象の出走ごとの材料の表を作る |
| ``SpeedFigureHistory`` | スピード指数と過去走の着順から、「そのレースの時点での馬の力」の列 |
| ``RaceStrength`` | レースの強さ（出走馬の力の上位5頭の平均） |
| ``RacePace`` | レースの前半の速さ（同じ条件のそれより前のレースと比べた z） |
| ``PastRunHistory`` | 過去走（着順・着差・位置取り・末脚・相手の強さ・ペース）の前走と近5走のまとめ |
| ``CumulativeRecordRates`` | 騎手・調教師・父・馬主などの区分ごとの、前日までの通算の成績 |
| ``RecentRecordRates`` | 区分ごとの、直近の期間だけの成績 |
| ``RecentPeopleRates`` | 騎手と調教師の直近の成績と、騎手の格上げ |
| ``RaceRelativeColumns`` | 列を、同じレースの馬の中での位置（順位・最良との差・偏差）に直す |
| ``RaceLevelColumns`` | レース単位の展開の手がかり（先頭率の合計）と、今回の馬の条件を数にした列 |
| ``SalePriceColumns`` | セリの取引価格 |

列の名前と、どの時点から分かるかは ``ability_columns.py``。
"""

from .ability_columns import DAY_BEFORE_COLUMNS, RACE_DAY_COLUMNS, ability_columns
from .ability_sources import AbilitySources
from .ability_table_builder import AbilityTableBuilder

__all__ = ["AbilitySources", "AbilityTableBuilder", "ability_columns", "DAY_BEFORE_COLUMNS", "RACE_DAY_COLUMNS"]
