"""成績7つの集計と、切り口（次元）の目録。

**「成績」とは次の7つのこと。** 独自の指標に置き換えない。

- 着別度数（``1着-2着-3着-着外`` の回数）
- 勝率（1着÷出走）、連対率（2着以内÷出走）、複勝率（3着以内÷出走）、馬券外率（4着以下÷出走。競走中止・失格を含む）
- 単勝回収率（単勝の払戻合計÷出走×100円）、複勝回収率（複勝の払戻合計÷出走×100円）

対象は事実表（``facts``）の出走した行（``ran``）。切り口は ``DIMENSIONS`` に載っているものだけで、
足すときは ``DIMENSIONS`` に1つ加えるだけで集計・表示・CLI・画面が変わらないようにしてある。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import duckdb

from .facts import FACTS_TABLE, ensure_facts
from .filters import Filters
from .render import Table

#: 値が無いときの表示。帯に分ける切り口で共通に使う。
UNKNOWN = "不明"
#: 「不明」を並べる位置。どの帯よりも後ろ。
_UNKNOWN_ORDER = 99
#: 払戻は 100 円あたりの金額。回収率の分母に使う。
STAKE_YEN = 100
#: 成績の列の並び。
PERF_COLUMNS: tuple[str, ...] = ("出走数", "着別度数", "勝率", "連対率", "複勝率", "馬券外率", "単勝回収率", "複勝回収率")
#: 順位を付ける鍵にできる列。
RANK_KEYS: tuple[str, ...] = ("出走数", "勝率", "連対率", "複勝率", "単勝回収率", "複勝回収率")
DEFAULT_RANK_KEY = "勝率"
#: 率で並べるときの同点の決め方。勝率が同じなら連対率、次に複勝率、最後に出走数の多い順。
_TIE_BREAKERS: tuple[str, ...] = ("勝率", "連対率", "複勝率", "出走数")
#: 騎手・調教師・血統を率で並べるときに要る出走数。これ未満は率が極端になりやすい。
RANKED_MIN_RUNS = 5
#: 馬を率で並べるときに要る出走数。同じコースを何度も走る馬は少ないので緩くする。
HORSE_MIN_RUNS = 2
#: 切り口の値を知るのに要る材料（``Dimension.needs``）。これから走るレースの馬に当てはめるとき、無ければその切り口は使えない。
NEED_GATE = "枠"          # 枠番・馬番。金・土の出馬表で決まる
NEED_POPULARITY = "人気"  # 単勝人気・オッズ。発走前の DB には無い
NEED_GOING = "馬場"       # 当日の馬場状態。発走前の DB には無い
NEED_WEIGHT = "体重"      # 当日の馬体重。発走前の DB には無い
NEED_MINING = "マイニング"  # 直前のマイニング予想。発走前の DB には無い
NEED_RESULT = "結果"      # レースが終わってから分かる値。当てはめには使えない


@dataclass(frozen=True)
class Column:
    """切り口を表す1列。``sql`` は事実表の列を使った式で、``name`` が表の見出しになる。"""

    name: str
    sql: str


@dataclass(frozen=True)
class Band:
    """数値を帯に分ける。``edges`` の各値を「その値未満」の境目にして、``labels`` を付ける。

    ``labels`` は ``edges`` より1つ多い。例: edges=(2, 3)、labels=("1位", "2位", "3位以下")。
    値が NULL の行は ``unknown`` の帯に入る。
    """

    expr: str
    edges: tuple[float, ...]
    labels: tuple[str, ...]
    unknown: str = UNKNOWN

    def __post_init__(self) -> None:
        if len(self.labels) != len(self.edges) + 1:
            raise ValueError(f"帯の名前は境目より1つ多く要ります: {self.labels}")

    def label_sql(self) -> str:
        """帯の名前を返す CASE 式。"""
        whens = "".join(f" WHEN {self.expr} < {edge} THEN '{label}'" for edge, label in zip(self.edges, self.labels))
        return f"CASE WHEN {self.expr} IS NULL THEN '{self.unknown}'{whens} ELSE '{self.labels[-1]}' END"

    def order_sql(self) -> str:
        """帯の並び順（小さい値の帯が先、不明が最後）を返す CASE 式。"""
        whens = "".join(f" WHEN {self.expr} < {edge} THEN {index}" for index, edge in enumerate(self.edges))
        return f"CASE WHEN {self.expr} IS NULL THEN {_UNKNOWN_ORDER}{whens} ELSE {len(self.edges)} END"


@dataclass(frozen=True)
class Dimension:
    """1つの切り口。表示する列と、並べ方を持つ。

    ``ranked`` の切り口（騎手・血統・馬など、値の種類が多いもの）は成績（既定は勝率）の順に並べ、上位 N 件だけ出す。
    ``where_sql`` は数える行を絞る条件（性別なら「牡と牝が混ざったレース」だけ）。
    ``needs`` は、これから走るレースの馬の値を知るのに要る材料（``NEED_*``）。過去の集計には関係しない。
    """

    name: str
    title: str
    columns: tuple[Column, ...]
    order_sql: tuple[str, ...]
    ranked: bool = False
    min_runs: int = 0
    note: str = ""
    where_sql: str = "TRUE"
    needs: frozenset[str] = frozenset()

    @property
    def column_names(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.columns)


def _needs(*names: str) -> frozenset[str]:
    return frozenset(names)


def _banded(name: str, title: str, band: Band, *, note: str = "", where_sql: str = "TRUE", needs: frozenset[str] = frozenset()) -> Dimension:
    """帯で分ける切り口。"""
    return Dimension(name=name, title=title, columns=(Column(title, band.label_sql()),), order_sql=(band.order_sql(),), note=note,
                     where_sql=where_sql, needs=needs)


def _plain(name: str, title: str, sql: str, order_sql: str | None = None, *, ranked: bool = False, min_runs: int = 0,
           note: str = "", where_sql: str = "TRUE", needs: frozenset[str] = frozenset()) -> Dimension:
    """事実表の列をそのまま1列で使う切り口。"""
    return Dimension(name=name, title=title, columns=(Column(title, sql),), order_sql=(order_sql or sql,), ranked=ranked,
                     min_runs=min_runs, note=note, where_sql=where_sql, needs=needs)


# --------------------------------------------------------------- 帯の境目（見やすさで決めた値。仕様ではない）
ODDS_BAND = Band(
    "win_odds", (1.5, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0, 15.0, 20.0, 30.0, 50.0, 100.0),
    ("1.0〜1.4倍", "1.5〜1.9倍", "2.0〜2.9倍", "3.0〜3.9倍", "4.0〜4.9倍", "5.0〜6.9倍", "7.0〜9.9倍",
     "10〜14.9倍", "15〜19.9倍", "20〜29.9倍", "30〜49.9倍", "50〜99.9倍", "100倍以上"),
)
LAST3F_RANK_BAND = Band("last3f_rank", (2, 3, 4, 6), ("1位", "2位", "3位", "4〜5位", "6位以下"))
LAST3F_TIME_BAND = Band(
    "last3f", (33.0, 34.0, 35.0, 36.0, 37.0, 38.0, 39.0),
    ("32秒台以下", "33秒台", "34秒台", "35秒台", "36秒台", "37秒台", "38秒台", "39秒以上"),
)
AGE_BAND = Band("age", (3, 4, 5, 6, 7), ("2歳", "3歳", "4歳", "5歳", "6歳", "7歳以上"))
FIELD_SIZE_BAND = Band("field_size", (9, 13, 16), ("8頭以下", "9〜12頭", "13〜15頭", "16〜18頭"))
BODY_WEIGHT_BAND = Band("body_weight", (420, 460, 500, 540), ("419kg以下", "420〜459kg", "460〜499kg", "500〜539kg", "540kg以上"))
WEIGHT_CHANGE_BAND = Band("weight_change", (-9, -3, 4, 10), ("−10kg以下", "−9〜−4kg", "−3〜+3kg", "+4〜+9kg", "+10kg以上"), unknown="不明・初出走")
INTERVAL_BAND = Band("interval_days", (10, 17, 24, 38, 66), ("連闘", "中1週", "中2週", "中3〜4週", "中5〜8週", "中9週以上"), unknown="前走なし・不明")
PREV_FINISH_BAND = Band("prev_finish", (2, 3, 4, 6, 10), ("1着", "2着", "3着", "4〜5着", "6〜9着", "10着以下"), unknown="前走なし・不明")
PREV_POPULARITY_BAND = Band("prev_popularity", (2, 4, 6, 10), ("1番人気", "2〜3番人気", "4〜5番人気", "6〜9番人気", "10番人気以下"), unknown="前走なし・不明")
POPULARITY_TOP_BAND = Band("popularity", (2, 3, 4), ("1番人気", "2番人気", "3番人気", "4番人気以下"))
_MINING_RANK_EDGES, _MINING_RANK_LABELS = (2, 3, 4, 6, 10), ("1位", "2位", "3位", "4〜5位", "6〜9位", "10位以下")
_MINING_TOP_EDGES, _MINING_TOP_LABELS = (2, 4), ("1位", "2〜3位", "4位以下")
DM_RANK_BAND = Band("dm_rank", _MINING_RANK_EDGES, _MINING_RANK_LABELS)
TM_RANK_BAND = Band("tm_rank", _MINING_RANK_EDGES, _MINING_RANK_LABELS)
DM_TOP_BAND = Band("dm_rank", _MINING_TOP_EDGES, _MINING_TOP_LABELS)
TM_TOP_BAND = Band("tm_rank", _MINING_TOP_EDGES, _MINING_TOP_LABELS)
_GAP_EDGES = (-2, 0, 1, 3)
_GAP_LABELS = ("人気より3つ以上高評価", "人気より1〜2つ高評価", "人気と同じ", "人気より1〜2つ低評価", "人気より3つ以上低評価")
DM_GAP_BAND = Band("(dm_rank - popularity)", _GAP_EDGES, _GAP_LABELS)
TM_GAP_BAND = Band("(tm_rank - popularity)", _GAP_EDGES, _GAP_LABELS)
TM_SCORE_BAND = Band(
    "tm_score", (30, 40, 50, 60, 65, 70, 75, 80),
    ("30未満", "30〜39.9", "40〜49.9", "50〜59.9", "60〜64.9", "65〜69.9", "70〜74.9", "75〜79.9", "80以上"),
)
#: 距離帯。出走別着度数（``ck``）の距離の区切りと同じにしてある（血統・馬の適性を、同じ物差しで見るため）。
DISTANCE_BAND = Band(
    "distance_m", (1201, 1401, 1601, 1801, 2001, 2201, 2401, 2801),
    ("1200m以下", "1201〜1400m", "1401〜1600m", "1601〜1800m", "1801〜2000m", "2001〜2200m",
     "2201〜2400m", "2401〜2800m", "2801m以上"),
)
#: 「今回より前」の回数の帯（同コース出走・逃げ経験など）。
COUNT_BAND_EDGES, COUNT_BAND_LABELS = (1, 2, 4), ("なし", "1回", "2〜3回", "4回以上")
COURSE_RUNS_BAND = Band("course_runs_before", COUNT_BAND_EDGES, COUNT_BAND_LABELS)
COURSE_WINS_BAND = Band("course_wins_before", (1, 2), ("なし", "1回", "2回以上"))
LEAD_EXP_BAND = Band("lead_runs_before", COUNT_BAND_EDGES, COUNT_BAND_LABELS)
RUNS_BEFORE_BAND = Band("runs_before", (1, 4, 10), ("初出走", "1〜3走", "4〜9走", "10走以上"))
WINS_BEFORE_BAND = Band("wins_before", (1, 2, 4), ("0勝", "1勝", "2〜3勝", "4勝以上"))
#: 持ち時計の順位（今回の出走馬の中で速い順）。持ち時計が無い馬は「なし」。
_RANK_EDGES, _RANK_LABELS = (2, 3, 4, 6), ("1位", "2位", "3位", "4〜5位", "6位以下")
BEST_TIME_UNIT_RANK_BAND = Band("best_time_unit_rank", _RANK_EDGES, _RANK_LABELS, unknown="持ち時計なし")
BEST_TIME_DIST_RANK_BAND = Band("best_time_dist_rank", _RANK_EDGES, _RANK_LABELS, unknown="持ち時計なし")
PREV_LAST3F_RANK_BAND = Band("prev_last3f_rank", _RANK_EDGES, _RANK_LABELS, unknown="前走なし・不明")
PREV_LAST3F_BAND = Band("prev_last3f", LAST3F_TIME_BAND.edges, LAST3F_TIME_BAND.labels, unknown="前走なし・不明")
PREV_MARGIN_BAND = Band("prev_time_diff", (0.0, 0.4, 1.0, 2.0),
                        ("前走勝ち", "0.0〜0.3秒差", "0.4〜0.9秒差", "1.0〜1.9秒差", "2.0秒以上"), unknown="前走なし・不明")
PREV_CORNER4_BAND = Band("prev_corner4", (2, 4, 7, 10), ("先頭", "2〜3番手", "4〜6番手", "7〜9番手", "10番手以降"), unknown="前走なし・不明")
PREV_FIELD_BAND = Band("prev_field_size", FIELD_SIZE_BAND.edges, FIELD_SIZE_BAND.labels, unknown="前走なし")
#: 枠帯。内 = 1〜2枠、中 = 3〜6枠、外 = 7〜8枠。
FRAME_BAND = Band("frame_no", (3, 7), ("内枠", "中枠", "外枠"))
CARRIED_BAND = Band("carried", (53, 55, 56, 57, 58), ("52.5kg以下", "53〜54.5kg", "55〜55.5kg", "56〜56.5kg", "57〜57.5kg", "58kg以上"))
LEAD_CANDIDATES_BAND = Band("lead_candidates", (1, 2, 3), ("0頭", "1頭", "2頭", "3頭以上"))
VENUE_WINS_BAND = Band("venue_wins_before", (1, 2), ("なし", "1回", "2回以上"))
DIST_WINS_BAND = Band("dist_wins_before", (1, 2), ("なし", "1回", "2回以上"))
COND_PLACES_BAND = Band("cond_places_before", COUNT_BAND_EDGES, COUNT_BAND_LABELS)
PREV_DISTANCE_BAND = Band(
    "prev_distance_m", (1300, 1500, 1700, 1900, 2100, 2500),
    ("1200m以下", "1300〜1400m", "1500〜1600m", "1700〜1800m", "1900〜2000m", "2100〜2400m", "2500m以上"), unknown="前走なし",
)
_PREV_NOTE = "前走はこの DB にある中央のレースだけ。"
_HAS_DM, _HAS_TM = "dm_rank IS NOT NULL", "tm_rank IS NOT NULL"
_DM_NOTE = "タイム型データマイニング予想の順位（直前予想。発走前に分かる）。予想の無い出走は数えない。"
_TM_NOTE = "対戦型データマイニング予想の予測スコアを、レース内で高い順に並べた順位（直前予想。発走前に分かる）。予想の無い出走は数えない。"
_GAP_NOTE = "マイニング予想の順位 − 単勝人気。負なら市場より高く評価している。"
_RESULT_NOTE = "レースが終わってから分かる値。傾向を知るためのもので、そのまま予想の条件にはできない。"
_STYLE_BEFORE_NOTE = "推定脚質 = 今回より前の直近3走の脚質の中央。レース前に分かる。過去走が無ければ「不明」。"
_GATE, _POP, _GOING, _WEIGHT = _needs(NEED_GATE), _needs(NEED_POPULARITY), _needs(NEED_GOING), _needs(NEED_WEIGHT)
_RESULT, _MINING = _needs(NEED_RESULT), _needs(NEED_MINING)
#: 前 = 逃げ・先行、後 = 差し・追込。
_STYLE_SIDE_SQL = "CASE WHEN style_before IN ('逃げ', '先行') THEN '前' WHEN style_before IN ('差し', '追込') THEN '後' ELSE '不明' END"
#: 同じ競走名のレースでの、今回より前の実績。
_SAME_RACE_EXP_SQL = ("CASE WHEN coalesce(same_race_runs_before, 0) = 0 THEN '出走なし' WHEN same_race_wins_before >= 1 THEN '勝利あり' "
                      "WHEN same_race_places_before >= 1 THEN '3着内あり' ELSE '着外のみ' END")
#: 同じ競馬場・コース・距離での、今回より前の実績。
_COURSE_PLACE_SQL = ("CASE WHEN course_runs_before = 0 THEN '出走なし' WHEN course_wins_before >= 1 THEN '勝利あり' "
                     "WHEN course_places_before >= 1 THEN '3着内あり' ELSE '着外のみ' END")
_EXPERIENCE_ORDER = {"勝利あり": 0, "3着内あり": 1, "着外のみ": 2, "出走なし": 3}

def sql_case_order(expr: str, labels: Sequence[str]) -> str:
    """名前の式を、``labels`` の並び順（無い名前は最後）にする CASE 式。"""
    from .codes import sql_case
    return sql_case(expr, {label: index for index, label in enumerate(labels)}, len(labels))


def _sql_style_order(column: str) -> str:
    """脚質の名前の列を並び順にする CASE 式。"""
    from .codes import sql_case
    return sql_case(column, {name: index for index, name in enumerate(STYLE_NAME_LIST)}, 9)


#: 脚質の名前（並び順）。
STYLE_NAME_LIST: tuple[str, ...] = ("逃げ", "先行", "差し", "追込")

# ------------------------------------------------------------- 切り口の目録
COURSE = Dimension(
    name="course", title="競馬場・コース・距離・馬場状態",
    columns=(Column("競馬場", "venue"), Column("コース", "course"), Column("距離", "distance_m"), Column("馬場状態", "condition")),
    order_sql=("venue_code", "surface_order", "distance_m", "condition_order"),
    note="全馬で見ると勝率は「1÷頭数」に近づく。--pop 1 のように馬を絞って使う。",
)

DIMENSIONS: dict[str, Dimension] = {
    dimension.name: dimension for dimension in (
        _plain("total", "全体", "'全体'", note="切り口で分けず、条件に合う全出走を1行にまとめる。"),
        COURSE,
        _plain("venue", "競馬場", "venue", "venue_code"),
        _plain("surface", "芝ダ", "surface", "surface_order"),
        _plain("going", "馬場状態", "condition", "condition_order"),
        _banded("distance-band", "距離帯", DISTANCE_BAND,
                note="出走別着度数（ck）と同じ距離の区切り。"),
        Dimension(name="track", title="競馬場・コース・距離",
                  columns=(Column("競馬場", "venue"), Column("コース", "course"), Column("距離", "distance_m")),
                  order_sql=("venue_code", "surface_order", "distance_m"), note="馬場状態をまとめた course。"),
        Dimension(name="condition", title="芝ダート・馬場状態", columns=(Column("芝ダ", "surface"), Column("馬場状態", "condition")),
                  order_sql=("surface_order", "condition_order")),
        _plain("frame", "枠番", "frame_no", needs=_GATE),
        _plain("number", "馬番", "horse_no", needs=_GATE),
        _plain("popularity", "単勝人気", "popularity", where_sql="popularity IS NOT NULL", needs=_POP),
        _banded("odds", "単勝オッズ", ODDS_BAND, needs=_POP),
        _plain("jockey", "騎手", "jockey", ranked=True, min_runs=RANKED_MIN_RUNS),
        _plain("trainer", "調教師", "trainer", ranked=True, min_runs=RANKED_MIN_RUNS),
        _plain("sire", "父", "sire", ranked=True, min_runs=RANKED_MIN_RUNS),
        _plain("grandsire", "父の父", "grandsire", ranked=True, min_runs=RANKED_MIN_RUNS),
        _plain("damsire", "母父", "damsire", ranked=True, min_runs=RANKED_MIN_RUNS),
        Dimension(name="horse", title="馬", columns=(Column("馬", "horse_name"),), order_sql=("horse_id",), ranked=True,
                  min_runs=HORSE_MIN_RUNS, note="同じ名前の馬を混ぜないよう血統登録番号で分ける。"),
        _plain("style", "脚質", "style", "style_order", note=_RESULT_NOTE, needs=_RESULT),
        _banded("last3f", "上がり3F順位", LAST3F_RANK_BAND, note=_RESULT_NOTE, needs=_RESULT),
        _banded("last3f-time", "上がり3Fタイム", LAST3F_TIME_BAND, note=_RESULT_NOTE, needs=_RESULT),
        _plain("sex", "性別", "sex", "sex_order", where_sql="mixed_sex",
               note="牡（セン）と牝が混ざったレースだけで数える。牝馬限定戦では全馬が牝で、比べる相手がいないため。"),
        _banded("age", "馬齢", AGE_BAND, where_sql="mixed_age",
                note="年齢が混ざったレースだけで数える。2歳戦・3歳限定戦では全馬が同じ年齢で、勝率が 1÷頭数 になるため。"),
        _plain("class", "クラス", "class_name", "class_order"),
        _banded("field-size", "出走頭数", FIELD_SIZE_BAND),
        _banded("body-weight", "馬体重", BODY_WEIGHT_BAND, needs=_WEIGHT),
        _banded("weight-change", "馬体重の増減", WEIGHT_CHANGE_BAND, needs=_WEIGHT),
        _banded("interval", "前走からの間隔", INTERVAL_BAND, note="前走はデータベースにある中央のレースだけで数える。"),
        _banded("prev-finish", "前走の着順", PREV_FINISH_BAND),
        _banded("prev-popularity", "前走の人気", PREV_POPULARITY_BAND),
        _plain("month", "月", "month"),
        _banded("popularity-top", "人気帯", POPULARITY_TOP_BAND, where_sql="popularity IS NOT NULL", needs=_POP,
                note="1番人気・2番人気・3番人気・4番人気以下。ほかの切り口と --cross で組み合わせて使う。"),
        _banded("dm-rank", "タイム型順位", DM_RANK_BAND, where_sql=_HAS_DM, note=_DM_NOTE, needs=_MINING),
        _banded("dm-top", "タイム型", DM_TOP_BAND, where_sql=_HAS_DM, note=_DM_NOTE, needs=_MINING),
        _banded("dm-gap", "タイム型順位と人気の差", DM_GAP_BAND, where_sql=f"{_HAS_DM} AND popularity IS NOT NULL", note=_GAP_NOTE,
                needs=_MINING | _POP),
        _banded("tm-rank", "対戦型順位", TM_RANK_BAND, where_sql=_HAS_TM, note=_TM_NOTE, needs=_MINING),
        _banded("tm-top", "対戦型", TM_TOP_BAND, where_sql=_HAS_TM, note=_TM_NOTE, needs=_MINING),
        _banded("tm-score", "対戦型スコア", TM_SCORE_BAND, where_sql=_HAS_TM, note=_TM_NOTE, needs=_MINING),
        _banded("tm-gap", "対戦型順位と人気の差", TM_GAP_BAND, where_sql=f"{_HAS_TM} AND popularity IS NOT NULL", note=_GAP_NOTE,
                needs=_MINING | _POP),
        Dimension(name="mining-pair", title="タイム型×対戦型",
                  columns=(Column("タイム型", DM_TOP_BAND.label_sql()), Column("対戦型", TM_TOP_BAND.label_sql())),
                  order_sql=(DM_TOP_BAND.order_sql(), TM_TOP_BAND.order_sql()), where_sql=f"{_HAS_DM} AND {_HAS_TM}",
                  note="タイム型と対戦型の順位を、それぞれ 1位 / 2〜3位 / 4位以下 に分けた組み合わせ。", needs=_MINING),
        # --- 単独の値と、前走との比較 ---
        _plain("year", "開催年", "year"),
        _plain("distance", "距離", "distance_m"),
        _plain("course-name", "コース", "course", "track_code", note="コースの名前（芝・右外 など）だけ。競馬場・距離はまとめる。"),
        Dimension(name="prev-style", title="前走の脚質", columns=(Column("前走の脚質", "coalesce(prev_style, '前走なし')"),),
                  order_sql=("CASE WHEN prev_style IS NULL THEN 9 ELSE " + _sql_style_order("prev_style") + " END",), note=_PREV_NOTE),
        _plain("winner-style", "勝ち馬の脚質", "coalesce(winner_style, '不明')", _sql_style_order("winner_style"),
               note="そのレースを勝った馬の脚質。" + _RESULT_NOTE, needs=_RESULT),
        _banded("course-runs", "同コース出走経験", COURSE_RUNS_BAND, note="同じ競馬場・コース・距離での、今回より前の出走数。"),
        _banded("course-win", "同コース勝利経験", COURSE_WINS_BAND, note="同じ競馬場・コース・距離での、今回より前の勝利数。"),
        _banded("lead-exp", "逃げ経験", LEAD_EXP_BAND, note="今回より前に逃げた回数。"),
        _banded("runs-before", "キャリア", RUNS_BEFORE_BAND, note="この DB にある中央の出走数（今回より前）。"),
        _banded("wins-before", "通算勝利数", WINS_BEFORE_BAND, note="この DB にある中央の勝利数（今回より前）。"),
        _banded("best-time-rank", "持ち時計順位（同競馬場・同コース・同距離・同馬場）", BEST_TIME_UNIT_RANK_BAND, needs=_GOING,
                note="同じ競馬場・コース・距離・馬場状態での今回より前の最速タイムを、今回の出走馬の中で速い順に並べた順位。"),
        _banded("best-time-dist-rank", "持ち時計順位（同芝ダ・同距離・同馬場）", BEST_TIME_DIST_RANK_BAND, needs=_GOING,
                note="競馬場を問わず、同じ芝ダ・距離・馬場状態での持ち時計の順位。"),
        _plain("surface-change", "芝ダ替わり", "surface_change", note=_PREV_NOTE),
        _plain("distance-change", "距離の変更", "distance_change", note=_PREV_NOTE),
        _plain("class-change", "クラスの変更", "class_change", note=_PREV_NOTE),
        _plain("jockey-change", "騎手の乗り替わり", "jockey_change", note=_PREV_NOTE),
        _plain("venue-change", "前走と同じ競馬場か", "venue_change", note=_PREV_NOTE),
        _banded("prev-last3f", "前走の上がり3F", PREV_LAST3F_BAND, note=_PREV_NOTE),
        _banded("prev-last3f-rank", "前走の上がり3F順位（今回の出走馬の中で）", PREV_LAST3F_RANK_BAND, note=_PREV_NOTE),
        _banded("prev-margin", "前走の着差", PREV_MARGIN_BAND, note=_PREV_NOTE),
        _banded("prev-corner4", "前走の4角位置", PREV_CORNER4_BAND, note=_PREV_NOTE),
        _banded("prev-field", "前走の頭数", PREV_FIELD_BAND, note=_PREV_NOTE),
        # --- 枠帯・推定脚質・実績（傾向スコアの項目が使う）---
        _banded("frame-band", "枠帯", FRAME_BAND, where_sql="frame_no IS NOT NULL", needs=_GATE, note="内枠 = 1〜2枠、中枠 = 3〜6枠、外枠 = 7〜8枠。"),
        _plain("number-parity", "馬番の偶数・奇数", "CASE WHEN horse_no % 2 = 0 THEN '偶数' ELSE '奇数' END", where_sql="horse_no IS NOT NULL",
               needs=_GATE, note="偶数の馬番はゲートに後から入る。"),
        _plain("gate-edge", "最内・大外", "CASE WHEN horse_no = 1 THEN '最内' WHEN horse_no = max_horse_no THEN '大外' ELSE 'その他' END",
               "CASE WHEN horse_no = 1 THEN 0 WHEN horse_no = max_horse_no THEN 2 ELSE 1 END", where_sql="horse_no IS NOT NULL", needs=_GATE,
               note="最内 = 1番、大外 = そのレースのいちばん外の馬番。"),
        _plain("style-before", "推定脚質", "coalesce(style_before, '不明')", _sql_style_order("style_before"), note=_STYLE_BEFORE_NOTE),
        _plain("style-side", "前後", _STYLE_SIDE_SQL, sql_case_order(_STYLE_SIDE_SQL, ("前", "後")),
               note="前 = 推定脚質が逃げ・先行、後 = 差し・追込。" + _STYLE_BEFORE_NOTE),
        _banded("lead-candidates", "逃げ候補の数", LEAD_CANDIDATES_BAND, note="そのレースの出走馬のうち、推定脚質が逃げの馬の数。"),
        _plain("same-race-exp", "同レースの実績", _SAME_RACE_EXP_SQL, sql_case_order(_SAME_RACE_EXP_SQL, tuple(_EXPERIENCE_ORDER)),
               note="同じ競走名のレースでの、今回より前の実績。平場（競走名なし）は「出走なし」。"),
        _plain("course-place", "同コースの実績", _COURSE_PLACE_SQL, sql_case_order(_COURSE_PLACE_SQL, tuple(_EXPERIENCE_ORDER)),
               note="同じ競馬場・コース・距離での、今回より前の実績。"),
        _banded("venue-win", "同じ競馬場の勝利経験", VENUE_WINS_BAND, note="同じ競馬場・同じ芝ダでの、今回より前の勝利数。"),
        _banded("dist-win", "同じ距離の勝利経験", DIST_WINS_BAND, note="同じ芝ダ・同じ距離での、今回より前の勝利数。"),
        _banded("cond-place", "同じ馬場状態の3着内経験", COND_PLACES_BAND, needs=_GOING, note="同じ芝ダ・同じ馬場状態での、今回より前の3着内の数。"),
        _plain("affiliation", "所属", "affiliation"),
        _plain("apprentice", "減量騎手", "apprentice"),
        _plain("blinker", "ブリンカー", "blinker"),
        _banded("carried", "斤量", CARRIED_BAND),
        _plain("prev-venue", "前走の競馬場", "coalesce(prev_venue, '前走なし')", note=_PREV_NOTE),
        _banded("prev-distance", "前走の距離", PREV_DISTANCE_BAND, note=_PREV_NOTE),
    )
}

#: 「値×人気」で組み合わせる人気の軸。人気の無い出走は数えない。
_POPULARITY_AXIS = Dimension(name="popularity", title="人気", columns=(Column("人気", "popularity"),),
                             order_sql=("popularity",), where_sql="popularity IS NOT NULL")


def cross(*dimensions: Dimension) -> Dimension:
    """複数の切り口を組み合わせる。列と並び順をつなぎ、数える行はすべての条件を満たすものにする。"""
    if not dimensions:
        raise ValueError("組み合わせる切り口を1つ以上渡してください")
    names = [column.name for d in dimensions for column in d.columns]
    duplicated = sorted({name for name in names if names.count(name) > 1})
    if duplicated:
        raise ValueError(f"同じ見出しの列が重なるので組み合わせられません: {', '.join(duplicated)}")
    return Dimension(
        name="+".join(d.name for d in dimensions), title="×".join(d.title for d in dimensions),
        columns=tuple(column for d in dimensions for column in d.columns),
        order_sql=tuple(sql for d in dimensions for sql in d.order_sql),
        ranked=dimensions[0].ranked, min_runs=max(d.min_runs for d in dimensions),
        note=" ".join(dict.fromkeys(d.note for d in dimensions if d.note)),
        where_sql=" AND ".join(f"({d.where_sql})" for d in dimensions),
        needs=frozenset().union(*(d.needs for d in dimensions)),
    )


def by_popularity(base: Dimension) -> Dimension:
    """切り口の値×単勝人気で分ける（``cross`` の人気版）。クラス・頭数・月のようなレースの属性に使う。"""
    return cross(base, _POPULARITY_AXIS)


def dimension(name: str) -> Dimension:
    """名前から切り口を引く。無い名前は、選べる名前を添えて落とす。"""
    try:
        return DIMENSIONS[name]
    except KeyError:
        raise LookupError(f"知らない切り口です: {name}\n選べるもの: {', '.join(DIMENSIONS)}") from None


def catalog() -> Table:
    """切り口の一覧（名前・表題・注意）。"""
    return Table(["切り口", "表題", "注意"], [[d.name, d.title, d.note] for d in DIMENSIONS.values()], title="切り口の一覧")


# ------------------------------------------------------------------ 集計

@dataclass(frozen=True)
class PerfRow:
    """1行ぶんの成績。``labels`` は切り口の値。率は 0〜1 の数。"""

    labels: tuple[Any, ...]
    runs: int
    first: int
    second: int
    third: int
    win_return: int
    place_return: int

    @property
    def out(self) -> int:
        return self.runs - self.first - self.second - self.third

    def counts(self) -> str:
        """``1着-2着-3着-着外``。"""
        return f"{self.first}-{self.second}-{self.third}-{self.out}"

    def rates(self) -> dict[str, float]:
        """率と回収率（0〜1）。"""
        n = self.runs
        return {
            "出走数": n, "勝率": self.first / n, "連対率": (self.first + self.second) / n,
            "複勝率": (self.first + self.second + self.third) / n, "馬券外率": self.out / n,
            "単勝回収率": self.win_return / (n * STAKE_YEN), "複勝回収率": self.place_return / (n * STAKE_YEN),
        }

    def cells(self) -> list[str]:
        """表のセル（``PERF_COLUMNS`` の順）。"""
        rates = self.rates()
        return [str(self.runs), self.counts(), *(percent(rates[name]) for name in PERF_COLUMNS[2:])]


def percent(value: float) -> str:
    """0.384 を ``38.4%`` にする。"""
    return f"{value * 100:.1f}%"


#: 成績7つを数える集計の式（``facts`` の行に対して）。``perf_row_from`` と対で使う。
AGGREGATES_SQL = """
    count(*), sum(CASE WHEN finish = 1 THEN 1 ELSE 0 END), sum(CASE WHEN finish = 2 THEN 1 ELSE 0 END),
    sum(CASE WHEN finish = 3 THEN 1 ELSE 0 END), sum(win_payout), sum(place_payout)
"""


def perf_row_from(labels: tuple[Any, ...], values: Sequence[Any]) -> PerfRow:
    """``AGGREGATES_SQL`` の結果（6つの数）から1行の成績を作る。"""
    return PerfRow(labels, *(int(v or 0) for v in values))


def summary_row(con: duckdb.DuckDBPyConnection, filters: Filters = Filters()) -> PerfRow:
    """条件に合う出走全体の成績（切り口で分けない1行）。"""
    ensure_facts(con)
    where, params = filters.where()
    values = con.execute(f"SELECT {AGGREGATES_SQL} FROM {FACTS_TABLE} WHERE ran AND {where}", params).fetchone()
    return perf_row_from(("全体",), values)


def summary_text(row: PerfRow) -> str:
    """成績7つを1行の文にする。例: ``着別度数 1-1-1-10 / 勝率 7.7% 連対率 15.4% …``。出走が無ければ「該当なし」。"""
    if row.runs == 0:
        return "該当なし"
    rates = row.rates()
    parts = " ".join(f"{name} {percent(rates[name])}" for name in PERF_COLUMNS[2:])
    return f"出走 {row.runs:,} 着別度数 {row.counts()} / {parts}"


def summary_dict(row: PerfRow) -> dict[str, Any]:
    """成績7つを辞書にする（画面の meta 用）。"""
    cells = row.cells() if row.runs else [str(row.runs), "0-0-0-0", *["—"] * (len(PERF_COLUMNS) - 2)]
    return dict(zip(PERF_COLUMNS, cells))


def perf_rows(con: duckdb.DuckDBPyConnection, dim: Dimension, filters: Filters = Filters(), *,
              top: int | None = None, min_runs: int | None = None, rank_by: str = DEFAULT_RANK_KEY) -> list[PerfRow]:
    """切り口ごとの成績。``ranked`` の切り口は ``rank_by`` の高い順に並べ ``top`` 件だけ返す。"""
    if rank_by not in RANK_KEYS:
        raise ValueError(f"順位の鍵は {', '.join(RANK_KEYS)} のどれかです: {rank_by}")
    ensure_facts(con)
    threshold = dim.min_runs if min_runs is None else min_runs
    where, params = filters.where()
    labels = ", ".join(f"{column.sql} AS {_label_alias(index)}" for index, column in enumerate(dim.columns))
    orders = ", ".join(f"{sql} AS _order{index}" for index, sql in enumerate(dim.order_sql))
    order_by = ", ".join(f"_order{index}" for index in range(len(dim.order_sql)))
    label_count = len(dim.columns)
    cursor = con.execute(
        f"""
        SELECT {labels}, {orders},
               count(*) AS runs,
               sum(CASE WHEN finish = 1 THEN 1 ELSE 0 END) AS first,
               sum(CASE WHEN finish = 2 THEN 1 ELSE 0 END) AS second,
               sum(CASE WHEN finish = 3 THEN 1 ELSE 0 END) AS third,
               sum(win_payout) AS win_return, sum(place_payout) AS place_return
        FROM {FACTS_TABLE}
        WHERE ran AND {where} AND ({dim.where_sql})
        GROUP BY ALL
        HAVING count(*) >= ?
        ORDER BY {order_by}
        """, [*params, threshold],
    )
    rows = [PerfRow(tuple(row[:label_count]), *(int(v) for v in row[-6:])) for row in cursor.fetchall()]
    if dim.ranked:
        rows.sort(key=lambda row: tuple(-row.rates()[key] for key in (rank_by, *_TIE_BREAKERS)))
    return rows[:top] if top else rows


def _label_alias(index: int) -> str:
    return f"_label{index}"


@dataclass(frozen=True)
class Coverage:
    """集計の元になったデータの範囲。表の見出しに書く。"""

    first_date: str | None
    last_date: str | None
    races: int
    runs: int

    def text(self) -> str:
        if not self.runs:
            return "該当なし"
        return f"{self.first_date}〜{self.last_date}、{self.races:,} レース・{self.runs:,} 頭"


def coverage(con: duckdb.DuckDBPyConnection, filters: Filters = Filters(), dim: Dimension | None = None) -> Coverage:
    """条件に合う出走の範囲（最初と最後の開催日、レース数、出走数）。"""
    ensure_facts(con)
    where, params = filters.where()
    counted = dim.where_sql if dim else "TRUE"
    first, last, races, runs = con.execute(
        f"SELECT min(race_date), max(race_date), count(DISTINCT race_id), count(*) FROM {FACTS_TABLE} "
        f"WHERE ran AND {where} AND ({counted})", params,
    ).fetchone()
    return Coverage(first, last, races, runs)


def perf_table(rows: Sequence[PerfRow], dim: Dimension, filters: Filters = Filters(),
               cover: Coverage | None = None) -> Table:
    """成績の行を表にする。列は切り口の列 + 成績7つ。"""
    title = f"{dim.title} — {filters.describe()}" + (f"（{cover.text()}）" if cover else "")
    table = Table([*dim.column_names, *PERF_COLUMNS], [[*row.labels, *row.cells()] for row in rows], title=title, note=dim.note)
    table.meta = {"dimension": dim.name, "filters": filters.describe(), "rows": len(rows)}
    return table


def find_row(rows: Sequence[PerfRow], label: Any) -> PerfRow | None:
    """1列の切り口で、値が ``label`` の行を探す。"""
    for row in rows:
        if str(row.labels[0]) == str(label):
            return row
    return None
