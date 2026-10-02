"""学習データ・予測用データに持たせる列（モデルには渡さない列）の決まり。"""

from yosou.shared.dataset import column_names as columns
from yosou.shared.feature import EntryColumns

#: 馬を見分ける列。
IDS = EntryColumns({
    columns.RACE_ID: "race_id", columns.RACE_DATE: "race_date", columns.HORSE_ID: "horse_id",
    columns.HORSE_NO: "horse_no", columns.HORSE_NAME: "horse_name",
})
#: 回収率の計算に使う。モデルには渡さない。
EVALUATION = EntryColumns({
    columns.FINISH: "finish", columns.POPULARITY: "popularity", columns.WIN_ODDS: "win_odds",
    columns.WIN_PAYOUT: "win_payout", columns.PLACE_PAYOUT: "place_payout", columns.PLACE_ODDS_LOW: "place_odds_low",
    columns.FIELD_SIZE: "field_size",
})
#: 予測の結果に出す、人気範囲の判定に使った人気の列の名前。
USED_POPULARITY = "使用した人気"
#: 予測のときの期待値の材料（その時点のオッズと頭数）。モデルには渡さない。
MARKET = EntryColumns({"単勝オッズ": "win_odds", "複勝オッズ（最低）": "place_odds_low"})
MARKET_FIELD_SIZE = "出走頭数"
MARKET_WHOLE_FIELD = "全頭が対象"
