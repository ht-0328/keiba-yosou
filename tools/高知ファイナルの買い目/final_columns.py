"""高知ファイナルの予想の、表の列名と特徴量の並び。"""

from __future__ import annotations

#: 事実表から読む列（``KochiRunRepository`` の SQL と同じ並び）。
RAW_COLUMNS: tuple[str, ...] = (
    "race_id", "race_date", "race_no", "race_name", "horse_id", "horse_no", "frame_no", "field_size", "ran", "finish",
    "corner4", "first_corner_rank", "time_diff", "finish_time", "last3f", "last3f_rank", "popularity", "win_odds",
    "distance_m", "class_order", "condition_order", "carried", "body_weight", "weight_change", "age", "sex", "interval_days",
    "jockey_code", "trainer_code", "jockey_change", "prev_finish", "prev_popularity", "prev_time_diff", "prev_corner4",
    "runs_before", "wins_before",
)
#: 馬・騎手・レースの条件の材料。
BASE: tuple[str, ...] = (
    "field_size", "distance_m", "condition_order", "class_order", "frame_no", "horse_no", "age", "female", "carried", "body_weight", "weight_change",
    "interval_days", "runs_before", "wins_before", "prev_finish", "prev_popularity", "prev_time_diff", "prev_corner4", "prev_is_final",
    "c4rel_m3", "c4rel_m5", "c1rel_m3", "c1rel_m5", "c4rel_min5", "td_m3", "td_m5", "td_min5", "top3_s3", "top3_s5", "pop_m3", "pop_m5", "fin_m3", "fin_m5",
    "l3rank_m5", "l3rank_min5", "prev_l3rank", "f_runs", "f_places", "f_wins", "f_rate", "d_runs", "d_places", "d_rate", "d_td_m",
    "j_n", "j_win", "j_top3", "j_c4", "j_lift", "dist_diff", "class_diff", "carried_diff", "jchg",
)
#: その日の、そのレースより前のレースから作る材料（馬場の傾向・騎手のその日の成績）。
DAY: tuple[str, ...] = ("day_races", "day_c4", "day_c1", "day_frame", "day_pop", "day_win_c4", "day_fav_win", "jday_win", "jday_top3", "jday_n", "bias_fit", "frame_fit")
#: レースの中での順位と偏差も材料にする列。
RANKED: tuple[str, ...] = ("c4rel_m3", "c1rel_m3", "td_m3", "td_min5", "top3_s5", "pop_m3", "j_top3", "l3rank_m5", "f_rate", "bias_fit")
#: 単勝オッズから作る材料（学ぶときは確定オッズ、予想するときは発走前の断面）。
MARKET: tuple[str, ...] = ("lm", "pop_now", "lm_gap", "pop_gap")
#: 速さの指数（その日・その距離の全馬の時計の真ん中との差）の材料。
SPEED: tuple[str, ...] = ("sp_last", "sp_m3", "sp_max5", "l3_last", "l3_m3", "l3_max5", "sp_trend", "sp_m3_rk", "sp_m3_z", "sp_max5_rk", "sp_max5_z",
                          "sp_last_rk", "sp_last_z", "l3_m3_rk", "l3_m3_z")
#: レースの中での順位と偏差を付ける、速さの指数の列（大きいほど良いので、大きい順に順位を付ける）。
SPEED_RANKED: tuple[str, ...] = ("sp_m3", "sp_max5", "sp_last", "l3_m3")
#: 調教師の材料。
TRAINER: tuple[str, ...] = ("t_n", "t_win", "t_top3", "t_top3_30", "t_n30", "t_form", "tday_win", "tday_top3", "tday_n")
#: 馬と騎手の組み合わせの材料。
PAIR: tuple[str, ...] = ("hj_n", "hj_top3", "hj_lift", "hj_share", "h_n", "h_top3")
#: モデルに渡す特徴量（この並びで学び、この並びで予想する）。
FEATURES: tuple[str, ...] = (*BASE, *DAY, *(f"{column}{suffix}" for column in RANKED for suffix in ("_rk", "_z")), *MARKET, *SPEED, *TRAINER, *PAIR)

#: 予想の結果の列。
WIN = "win_probability"
TOP3 = "top3_probability"
MARKET_SHARE = "mkt"
VALUE = "value"
POPULARITY_NOW = "pop_now"
PLACE_LOW = "place_low"
HORSE_NO = "horse_no"
RACE_ID = "race_id"
#: 学ぶレース・予想するレースの条件（距離と頭数）。
MIN_DISTANCE = 1300
MAX_DISTANCE = 1600
MIN_FIELD = 9
