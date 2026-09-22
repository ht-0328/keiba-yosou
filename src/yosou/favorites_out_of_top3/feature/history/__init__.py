"""この予想だけが、過去の記録から数える部品。

「開催日より前のものだけを使う」決まり（設計書 11 の 2）は、共通の ``AsOfLookup`` が守る。

| クラス | 仕事 |
|---|---|
| ``PopularityRunSummary`` | 過去走を、馬ごとの「その走までの近5走の人気のまとめ」にする |
"""

from .popularity_run_summary import (
    AVERAGE_POPULARITY,
    SUMMARY_COLUMNS,
    WORSE_THAN_POPULARITY,
    PopularityRunSummary,
)

__all__ = [
    "PopularityRunSummary", "SUMMARY_COLUMNS", "WORSE_THAN_POPULARITY", "AVERAGE_POPULARITY",
]
