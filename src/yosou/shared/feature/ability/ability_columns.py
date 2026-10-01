"""馬の力の材料（まとまり M）の列の名前と、作り方の決まり。

研究「馬の力と展開でオッズに勝つ」の 197個の材料と、研究「一番人気を疑う」で足したセリの価格の5個。
名前は研究のまま（英字の列は事実表の列名）。ただし、ほかのまとまりと同じ名前になる2つ（競馬場・ブリンカー）は、
``競馬場コード``・``ブリンカーあり`` に付け直した。
"""

from __future__ import annotations

#: 事実表から、そのまま材料にする列（レースの条件・今回の馬の条件・今回より前の累積。26個）。
CONTEXT_COLUMNS: tuple[str, ...] = (
    "distance_m", "field_size", "class_order", "age", "sex_order", "carried", "body_weight", "weight_change",
    "frame_no", "interval_days", "condition_order", "surface_order", "month", "runs_before", "wins_before",
    "lead_runs_before", "course_runs_before", "course_wins_before", "course_places_before", "venue_wins_before",
    "dist_wins_before", "cond_places_before", "same_race_runs_before", "same_race_wins_before",
    "best_time_unit_rank", "best_time_dist_rank",
)
#: スピード指数と過去走の着順から作る列（12個。``SpeedFigureHistory``）。
FIGURE_COLUMNS: tuple[str, ...] = (
    "指数_前走", "指数_近5走の最高", "指数_近3走の平均", "指数_新しさの重み", "指数_条件の重み", "指数_伸び",
    "着順_前走", "着順_近3走の平均", "出走数", "前走からの日数", "距離の変化", "前走と芝ダが同じ",
)
#: 走ごとに作って、前走と近5走の平均を取る値（``PastRunHistory``）。
PER_RUN_VALUES: tuple[str, ...] = (
    "相対着順", "着差", "序盤の位置", "4角の位置", "末脚", "先頭", "相手の強さ", "ペース", "展開の不利", "末脚と着順のずれ",
)
#: 過去走から作る列（29個。``PastRunHistory``）。
PAST_RUN_COLUMNS: tuple[str, ...] = (
    *(f"{value}_{kind}" for value in PER_RUN_VALUES for kind in ("前走", "近5走の平均")),
    "相対着順_近5走の最良", "着差_近5走の最良", "先頭率_近5走", "クラス_前走との差", "斤量_前走との差",
    "騎手_前走と同じ", "芝ダ替わり", "休み明け_2走目", "体重_近走の平均との差",
)
#: 調教のまとめの列（12個。``WorkoutSummaryRepository`` が SQL で作る）。
WORKOUT_COLUMNS: tuple[str, ...] = (
    "坂路_本数14日", "坂路_本数30日", "坂路_4F最速14日", "坂路_1F最速14日", "坂路_直前4F", "坂路_直前1F",
    "坂路_直前からの日数", "ウッド_本数30日", "ウッド_5F最速30日", "ウッド_4F最速30日", "ウッド_1F最速30日",
    "ウッド_直前1F",
)
#: 通算の成績を数える区分（列の名前の頭 → 区分の列。13 × 3 = 39個。``CumulativeRecordRates``）。
RECORD_GROUPS: dict[str, tuple[str, ...]] = {
    "騎手": ("jockey_code",), "調教師": ("trainer_code",), "父": ("sire",), "母父": ("damsire",),
    "父×芝ダ": ("sire", "surface"), "騎手×競馬場": ("jockey_code", "venue_code"),
    "馬主": ("owner",), "生産者": ("breeder",), "母": ("dam",), "調教師×距離": ("trainer_code", "distance_m"),
    "枠の傾向": ("venue_code", "surface", "distance_m", "frame_no"), "父×距離": ("sire", "distance_m"),
    "騎手×調教師": ("jockey_code", "trainer_code"),
}
#: 区分ごとに作る3つの列の名前の後ろ。
RECORD_SUFFIXES: tuple[str, ...] = ("勝率", "3着内率", "出走数")
#: 騎手と調教師の直近の成績（5個。``RecentPeopleRates``）。
RECENT_COLUMNS: tuple[str, ...] = ("騎手_1年_勝率", "騎手_1年_3着内率", "騎手_格上げ", "調教師_1年_勝率", "調教師_60日_勝率")
#: レース内の位置に直す列（True は大きいほど良い。22 × 3 = 66個。``RaceRelativeColumns``）。
RELATIVE_COLUMNS: dict[str, bool] = {
    "指数_条件の重み": True, "指数_新しさの重み": True, "指数_近5走の最高": True, "指数_前走": True,
    "相対着順_近5走の平均": False, "着差_近5走の最良": False, "末脚_近5走の平均": False,
    "序盤の位置_近5走の平均": False, "相手の強さ_近5走の平均": True, "騎手_勝率": True, "調教師_勝率": True,
    "父×芝ダ_3着内率": True, "carried": False, "馬主_勝率": True, "生産者_勝率": True, "母_3着内率": True,
    "坂路_4F最速14日": False, "坂路_1F最速14日": False, "ウッド_1F最速30日": False, "ウッド_5F最速30日": False,
    "騎手_1年_勝率": True, "調教師_60日_勝率": True,
}
#: レース内の位置の3つの列の名前の後ろ。
RELATIVE_SUFFIXES: tuple[str, ...] = ("順位", "最良との差", "偏差")
#: レース単位の展開の手がかりと、今回の馬の条件を数にした列（8個。``RaceLevelColumns``）。
RACE_LEVEL_COLUMNS: tuple[str, ...] = (
    "先頭率の合計", "ほかの馬の先頭率の合計", "馬番の位置", "ハンデ戦", "競馬場コード", "所属_栗東", "ブリンカーあり", "減量騎手",
)
#: セリの価格の列（5個。``SalePriceColumns``）。
SALE_COLUMNS: tuple[str, ...] = (
    "セリの価格（log）", "セリで買われた", "セリの時の年齢", "セリの価格のレース内順位", "セリの価格とレースの最高との差",
)


def record_columns() -> tuple[str, ...]:
    """通算の成績の列（区分の順に、勝率・3着内率・出走数）。"""
    return tuple(f"{name}_{suffix}" for name in RECORD_GROUPS for suffix in RECORD_SUFFIXES)


def relative_columns() -> tuple[str, ...]:
    """レース内の位置の列（元の列の順に、順位・最良との差・偏差）。"""
    return tuple(f"{column}_{suffix}" for column in RELATIVE_COLUMNS for suffix in RELATIVE_SUFFIXES)


def ability_columns() -> tuple[str, ...]:
    """馬の力の材料の全部の列（202個）。並びは、研究の表の材料の並びにセリの価格を足した順。"""
    return (*CONTEXT_COLUMNS, *FIGURE_COLUMNS, *PAST_RUN_COLUMNS, *WORKOUT_COLUMNS, *record_columns(),
            *RECENT_COLUMNS, *relative_columns(), *RACE_LEVEL_COLUMNS, *SALE_COLUMNS)


#: 成績を数えるとき、件数が少ない区分を寄せる先の値（2011〜2026年の中央の全出走の勝率と3着内率）。
#: 研究ではその表の全体の平均に寄せていたが、学習と予測で同じ値になるように、決めた値にした（設計書 11 の 4）。
WIN_PRIOR, PLACE_PRIOR = 0.0716, 0.2148
#: 前日から分かる列（枠番・馬番と、前日発表の馬場状態を使うもの）。
DAY_BEFORE_COLUMNS: frozenset[str] = frozenset({
    "frame_no", "condition_order", "cond_places_before", "馬番の位置", "枠の傾向_勝率", "枠の傾向_3着内率", "枠の傾向_出走数",
})
#: 当日から分かる列（馬体重を使うもの）。
RACE_DAY_COLUMNS: frozenset[str] = frozenset({"body_weight", "weight_change", "体重_近走の平均との差"})
