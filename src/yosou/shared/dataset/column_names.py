"""学習データ・予測用データの、特徴量ではない列の名前（設計書 08 の「列の種類」）。

目的変数の列の名前は予想ごとに決まるので、ここには置かず、予想のパッケージの ``dataset/column_names.py`` に置く。
"""

#: ID 列。どのレースのどの馬かを示し、特徴量にしない。馬番と馬名は、結果を人が見るために置く。
RACE_ID = "レースID"
RACE_DATE = "開催日"
HORSE_ID = "馬ID"
HORSE_NO = "馬番"
HORSE_NAME = "馬名"
#: レース単位の予想の ID 列。馬の列の代わりに、どのレースかを人が見るために置く。
VENUE = "競馬場"
RACE_NO = "レース番号"

#: 評価用の列（1頭ごと）。回収率などを計算するためだけに置き、モデルに渡さない。
FINISH = "確定着順"
WIN_ODDS = "確定の単勝オッズ"
POPULARITY = "確定の単勝人気"
WIN_PAYOUT = "単勝の払戻"
PLACE_PAYOUT = "複勝の払戻"
#: 複勝オッズの最低と最高（終わったレースは確定の値）。複勝の期待値を見積もるのに使う（既存モデルの修正計画の 2）。
PLACE_ODDS_LOW = "複勝オッズ（最低）"
PLACE_ODDS_HIGH = "複勝オッズ（最高）"

#: 評価用の列（レース単位。``RaceResultSummary`` が作る）。どれもそのレースの結果で、特徴量にしない。
WINNER_POPULARITY = "勝ち馬の人気"
TOP3_POPULARITY_SUM = "1〜3着の人気の和"
FAVORITE_FINISH = "1番人気の確定着順"
FAVORITE_ODDS = "1番人気の確定オッズ"
UPPER_MAX_ODDS = "2〜5番人気の最大の確定オッズ"
FIELD_SIZE = "確定の出走頭数"
