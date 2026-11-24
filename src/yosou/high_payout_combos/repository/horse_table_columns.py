"""馬ごとの表（1頭1行。今の本番の予想の確率・印・危険な人気馬）の列の名前。"""

RACE_ID = "race_id"
RACE_DATE = "race_date"
HORSE_NO = "horse_no"
#: 予想の3着以内の確率・1着の確率。
TOP3_PROBABILITY = "probability"
WIN_PROBABILITY = "win_probability"
#: 単勝オッズから見た勝率・3着以内率。
MARKET_WIN = "market_win"
MARKET_TOP3 = "market_top3"
WIN_ODDS = "win_odds"
PLACE_ODDS_LOW = "place_odds_low"
PLACE_ODDS_HIGH = "place_odds_high"
#: 単勝人気と、予想の順位。
POPULARITY = "popularity"
RANK = "rank"
#: 危険な人気馬か（真偽）と、その点数。
IS_DANGER = "is_danger"
DANGER_SCORE = "danger_score"
#: 印（◎ ○ ▲ △ ☆ 注 － 消）。
MARK = "mark"
#: 予想の上げ下げ、単勝の期待値、複勝の期待値。
UPDOWN = "updown"
WIN_VALUE = "win_value"
PLACE_VALUE = "place_value"

#: 材料づくりに使う列（この予想が馬ごとの表から読むのはこれだけ）。
MATERIAL_COLUMNS: tuple[str, ...] = (
    RACE_ID, HORSE_NO, TOP3_PROBABILITY, WIN_PROBABILITY, MARKET_WIN, MARKET_TOP3, WIN_ODDS, PLACE_ODDS_LOW, PLACE_ODDS_HIGH,
    POPULARITY, RANK, IS_DANGER, DANGER_SCORE, MARK, UPDOWN, WIN_VALUE, PLACE_VALUE,
)
#: 保存した馬ごとの表から読む列（材料づくりの列と開催日）。
STORED_COLUMNS: tuple[str, ...] = (*MATERIAL_COLUMNS, RACE_DATE)
