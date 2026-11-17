"""道具「地方の直前の買い目」の表の列名と、モデルが使う特徴量の並び。"""

from __future__ import annotations

#: 材料の表（1頭1行）の列。オッズは全部「買い目を決める時刻より前の断面」のもの。
RACE_ID = "race_id"
HORSE_NO = "horse_no"
RACE_DATE = "race_date"
FIELD_SIZE = "field_size"
#: 単勝オッズ: 今・約10分前・約20分前・その日の最初の断面。
ODDS_NOW = "odds_now"
ODDS_A = "odds_a"
ODDS_B = "odds_b"
ODDS_FIRST = "odds_first"
#: 複勝オッズの下と上（今の断面）。
PLACE_LOW = "place_low"
PLACE_HIGH = "place_high"
#: 全頭の予想の確率。``*_MODEL`` は今のオッズを材料にした当日の時点、``*_FREE`` はオッズを使わない出馬表の時点。
WIN_MODEL = "win_model"
TOP3_MODEL = "top3_model"
WIN_FREE = "win_free"
TOP3_FREE = "top3_free"
MATERIAL_COLUMNS: tuple[str, ...] = (RACE_ID, HORSE_NO, RACE_DATE, FIELD_SIZE, ODDS_NOW, ODDS_A, ODDS_B, ODDS_FIRST, PLACE_LOW, PLACE_HIGH,
                                     WIN_MODEL, TOP3_MODEL, WIN_FREE, TOP3_FREE)

#: 学習用の表だけにある結果の列: 確定の単勝オッズ・1着か・確定オッズを材料にした当日の予想の 1着の確率（先生）。
FINAL_ODDS = "final_odds"
WON = "won"
WIN_TEACHER = "win_teacher"

#: モデルが使う特徴量（この並びで学び、この並びで当てる）。
FEATURES: tuple[str, ...] = (
    "lw", "mkt", "rank", "lplo", "lphi", "mom_a", "mom_b", "mom_first", "fav_lw", "over", "venue", "race_no", "field_size",
    "p1_thu", "p3_thu", "thu_gap", "p1_stn", "p3_st", "st_gap", "st_rank", "plc_gap", "dow", "mkt2", "ent",
)

#: モデルの出力の列: 買う馬らしさ（確定オッズを知っている予想が買う馬である確率）と、単勝を買ったときの戻りの見込み（1 が元）。
LIKENESS = "likeness"
PAYBACK = "payback"
