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
#: 単勝オッズ: 今の断面の 約2分前・約5分前・約35分前の断面（細かい動きと長い動きを見る）。
ODDS_BACK_2 = "odds_back2"
ODDS_BACK_5 = "odds_back5"
ODDS_BACK_35 = "odds_back35"
#: 複勝オッズの下と上（今の断面）と、約10分前の断面の下。
PLACE_LOW = "place_low"
PLACE_HIGH = "place_high"
PLACE_LOW_A = "place_low_a"
#: 全頭の予想の確率。``*_MODEL`` は今のオッズを材料にした当日の時点、``*_FREE`` はオッズを使わない出馬表の時点。
WIN_MODEL = "win_model"
TOP3_MODEL = "top3_model"
WIN_FREE = "win_free"
TOP3_FREE = "top3_free"
MATERIAL_COLUMNS: tuple[str, ...] = (RACE_ID, HORSE_NO, RACE_DATE, FIELD_SIZE, ODDS_NOW, ODDS_A, ODDS_B, ODDS_FIRST,
                                     ODDS_BACK_2, ODDS_BACK_5, ODDS_BACK_35, PLACE_LOW, PLACE_HIGH, PLACE_LOW_A,
                                     WIN_MODEL, TOP3_MODEL, WIN_FREE, TOP3_FREE)

#: 学習用の表だけにある結果の列: 確定の単勝オッズ・1着か・確定オッズを材料にした当日の予想の 1着の確率（先生）。
FINAL_ODDS = "final_odds"
WON = "won"
WIN_TEACHER = "win_teacher"

#: オッズの今の値・前の断面からの大きな動き・予想と市場の差（市場の見立て・人気順・予想の確率など）。
BASE_FEATURES: tuple[str, ...] = (
    "lw", "mkt", "rank", "lplo", "lphi", "mom_a", "mom_b", "mom_first", "fav_lw", "over", "venue", "race_no", "field_size",
    "p1_thu", "p3_thu", "thu_gap", "p1_stn", "p3_st", "st_gap", "st_rank", "plc_gap", "dow", "mkt2", "ent",
)
#: 予想と人気の順位のずれ・レースの中のオッズの動きのばらつき・細かい断面（約2分前・約5分前・約35分前）の動き・複勝の動き・人気順の変化。
MOVEMENT_FEATURES: tuple[str, ...] = (
    "thu_rank", "st3_rank", "rank_gap", "rank_gap_thu", "p3_gap", "fav_mom", "mom_sd", "st_max", "st_ent",
    "mom_2", "mom_5", "mom_35", "plo_mom", "rank_chg",
)
#: モデルが使う特徴量（この並びで学び、この並びで当てる）。
FEATURES: tuple[str, ...] = BASE_FEATURES + MOVEMENT_FEATURES

#: モデルの出力の列: 買う馬らしさ（確定オッズを知っている予想が買う馬である確率）と、単勝を買ったときの戻りの見込み（1 が元）。
LIKENESS = "likeness"
PAYBACK = "payback"
