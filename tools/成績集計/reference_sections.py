"""基準のページの各節（コース×馬場状態）に、上から順に置く表の一覧。前のページと同じ見出し・列・絞り方。"""

from __future__ import annotations

from 成績集計.distance_change_table_spec import DistanceChangeTableSpec
from 成績集計.mining_range_spec import MiningRangeSpec
from 成績集計.reference_group_spec import ReferenceGroupSpec
from 成績集計.reference_table_spec import ReferenceTableSpec

#: 騎手・調教師・血統を勝率で並べるときの件数と、要る出走数（少ないと率が極端になりやすい）。
RANKED_TOP, RANKED_MIN_RUNS = 10, 5
#: 馬を勝率で並べるときに要る出走数。同じコースを何度も走る馬は少ないので緩くする。
HORSE_MIN_RUNS = 2
#: 人気（1番人気・2番人気 …）で分ける、小見出しの中の表。
_BY_POPULARITY = ReferenceTableSpec("", ("人気",), ("popularity",))
_BY_DM = ReferenceTableSpec("", ("人気帯", "タイム型"), ("label_popularity_top", "label_dm_top"))
_BY_TM = ReferenceTableSpec("", ("人気帯", "対戦型"), ("label_popularity_top", "label_tm_top"))


def _ranked(title: str, column: str) -> ReferenceTableSpec:
    return ReferenceTableSpec(f"{title}（勝率の上位 {RANKED_TOP}・出走 {RANKED_MIN_RUNS} 以上）", (title,), (column,),
                              top=RANKED_TOP, min_runs=RANKED_MIN_RUNS)


def _plain(title: str, column: str) -> ReferenceTableSpec:
    return ReferenceTableSpec(title, (title,), (column,))


def _groups(title: str, column: str) -> tuple[ReferenceGroupSpec, ...]:
    """レースの属性（クラス・頭数・月）ごとの、人気・人気帯×タイム型・人気帯×対戦型 の3つ。"""
    return (ReferenceGroupSpec(f"{title} × 人気", column, _BY_POPULARITY),
            ReferenceGroupSpec(f"{title} × 人気帯 × タイム型", column, _BY_DM),
            ReferenceGroupSpec(f"{title} × 人気帯 × 対戦型", column, _BY_TM))


SECTION_TABLES = (
    _plain("単勝人気", "popularity"),
    _plain("枠番", "frame_no"),
    _plain("馬番", "horse_no"),
    _plain("単勝オッズ", "label_odds"),
    _ranked("騎手", "jockey"),
    _ranked("調教師", "trainer"),
    _ranked("父", "sire"),
    _ranked("父の父", "grandsire"),
    _ranked("母父", "damsire"),
    ReferenceTableSpec(f"馬（勝率の上位 {RANKED_TOP}・出走 {HORSE_MIN_RUNS} 以上）", ("馬",), ("horse_id", "horse_name"),
                       shown=(1,), top=RANKED_TOP, min_runs=HORSE_MIN_RUNS),
    _plain("脚質", "label_style"),
    _plain("上がり3F順位", "label_last3f_rank"),
    _plain("上がり3Fタイム", "label_last3f_time"),
    ReferenceTableSpec("性別（牡牝が混ざったレースだけ）", ("性別",), ("label_sex",)),
    ReferenceTableSpec("馬齢（年齢が混ざったレースだけ）", ("馬齢",), ("label_age",)),
    _plain("馬体重", "label_body_weight"),
    _plain("馬体重の増減", "label_weight_change"),
    _plain("前走からの間隔", "label_interval"),
    _plain("前走の着順", "label_prev_finish"),
    _plain("前走の人気", "label_prev_popularity"),
    DistanceChangeTableSpec("距離の変更", "距離の変更", "label_distance_change"),
    DistanceChangeTableSpec("距離の変更の幅", "距離の変更の幅", "label_distance_gap"),
    DistanceChangeTableSpec("距離の変更（穴馬）", "距離の変更（穴馬）", "label_longshot_distance_change"),
    MiningRangeSpec(),
    _plain("タイム型順位", "label_dm_rank"),
    _plain("対戦型順位", "label_tm_rank"),
    _plain("対戦型スコア", "label_tm_score"),
    _plain("タイム型順位と人気の差", "label_dm_gap"),
    _plain("対戦型順位と人気の差", "label_tm_gap"),
    ReferenceTableSpec("タイム型×対戦型", ("タイム型", "対戦型"), ("label_dm_top", "label_tm_top")),
    ReferenceTableSpec("人気帯×タイム型", ("人気帯", "タイム型"), ("label_popularity_top", "label_dm_top")),
    ReferenceTableSpec("人気帯×対戦型", ("人気帯", "対戦型"), ("label_popularity_top", "label_tm_top")),
    *_groups("クラス別", "label_class"),
    *_groups("出走頭数別", "label_field_size"),
    *_groups("月別", "month"),
)
