"""事実表: 1行 = 1頭の出走。レース・馬・市場・結果・払戻・前走を型付きの列に並べる。

元DB の生の表（列名は日本語、値は文字列）から、検索・集計・事象が使う形を1度だけ作る。
**型変換はすべてここに集約する。** ここから先は数と日付として扱ってよい。

- 中央競馬の確定成績（``keys.FINAL_STAGES``）だけ。同じレース・馬に複数の行があれば最新の1行。
- ``ran``: 出走したか（出走取消・発走除外・競走除外は False）。
- ``finish``: 確定着順。着順が付かない（競走中止・失格・未確定）なら NULL。
- 払戻は円（当たらなければ 0）。オッズは倍（無ければ NULL）。人気は整数（無ければ NULL）。
- 馬場状態は、ダートのコースならダートの、芝と障害なら芝の（芝が 0 ならダートの）。
- 無い表（払戻・血統・マイニング）は空の関係で代替し、列は NULL か 0 になる。

    from 共通 import facts
    facts.ensure_facts(con)          # TEMP TABLE facts を作る（あれば何もしない）
    con.execute("select count(*) from facts where ran")

確定前のレース（出走馬名表・出馬表）の出走馬にも同じ列を付けたいときは ``build_entry_facts`` を使う。
事実表と同じ SQL を「確定成績 + そのレース」に当てるので、前走・累積の定義が二重にならない。
"""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import duckdb

from . import codes, keys
from .render import Table

#: 事実表の名前（接続ごとの一時表）。
FACTS_TABLE = "facts"
#: 1レースの出走馬に事実表と同じ列を付けた一時表の名前。
ENTRY_TABLE = "entry_facts"

#: 事実表の列と意味。SQL の式はこの列名を使う。
FACT_COLUMNS: dict[str, str] = {
    "race_id": "rid（16桁）", "race_date": "開催日 YYYY-MM-DD", "month": "開催月（1〜12）",
    "venue_code": "競馬場コード", "venue": "競馬場名", "race_no": "レース番号", "race_name": "競走名（特別競走だけ）",
    "track_code": "トラックコード", "surface": "芝 / ダート / 障害", "surface_order": "芝ダの並び順",
    "course": "コース（芝・右外 など）", "distance_m": "距離（m）",
    "condition_code": "馬場状態コード（1〜4）", "condition": "馬場状態（良 / 稍重 / 重 / 不良）", "condition_order": "馬場状態の並び順",
    "class_name": "クラス", "class_order": "クラスの並び順", "grade_code": "グレードコード",
    "field_size": "出走頭数", "frame_no": "枠番", "horse_no": "馬番", "horse_id": "血統登録番号", "horse_name": "馬名",
    "sex": "性別", "sex_order": "性別の並び順", "age": "馬齢",
    "jockey_code": "騎手コード", "jockey": "騎手（略称）", "trainer_code": "調教師コード", "trainer": "調教師（略称）",
    "carried": "負担重量（kg）", "body_weight": "馬体重（kg）", "weight_change": "馬体重の増減（kg）",
    "popularity": "単勝人気（確定）", "win_odds": "単勝オッズ（確定、倍）",
    "abnormal": "異常区分コード", "abnormal_name": "異常区分（出走取消 など。正常は空）", "ran": "出走したか",
    "finish": "確定着順（着順が付かなければ NULL）", "finish_time": "走破タイム（秒）", "time_diff": "タイム差（秒。1着は負）",
    "corner4": "4コーナーでの順位", "last3f": "上がり3ハロン（秒）", "last3f_rank": "上がり3ハロンのレース内順位",
    "style": "脚質（レース後の判定）", "style_order": "脚質の並び順",
    "sire": "父", "grandsire": "父の父", "damsire": "母父",
    "prev_finish": "前走の確定着順", "prev_popularity": "前走の単勝人気", "interval_days": "前走からの日数",
    "win_payout": "単勝払戻（100円あたり、円。当たらなければ 0）", "place_payout": "複勝払戻（同上）",
    "mixed_sex": "そのレースに牡（セン）と牝の両方が出走したか", "mixed_age": "そのレースに違う年齢の馬が出走したか",
    "dm_rank": "タイム型マイニング予想の順位（直前予想。無ければ NULL）",
    "tm_rank": "対戦型マイニング予想のスコアをレース内で高い順に並べた順位（無ければ NULL）",
    "tm_score": "対戦型マイニング予想の予測スコア（0〜100）",
    "year": "開催年",
    "winner_style": "そのレースの勝ち馬の脚質（結果側）",
    "prev_style": "前走の脚質", "prev_last3f": "前走の上がり3ハロン（秒）",
    "prev_last3f_rank": "前走の上がり3ハロンを、今回の出走馬の中で速い順に並べた順位",
    "prev_time_diff": "前走の着差（秒。勝っていれば負）", "prev_corner4": "前走の4コーナーでの順位",
    "prev_field_size": "前走の出走頭数", "prev_distance_m": "前走の距離（m）", "prev_surface": "前走の芝ダ", "prev_venue": "前走の競馬場",
    "surface_change": "芝ダ替わり（同じ / 芝→ダート / ダート→芝 / 前走なし …）",
    "distance_change": "距離の変更（延長 / 短縮 / 同じ / 前走なし）",
    "class_change": "クラスの変更（昇級 / 降級 / 同級 / 前走なし / 不明）",
    "jockey_change": "騎手の乗り替わり（継続 / 乗り替わり / 前走なし）",
    "venue_change": "前走と同じ競馬場か（同じ / 別 / 前走なし）",
    "runs_before": "この DB にある中央の出走数（今回より前）", "wins_before": "同じく勝利数",
    "lead_runs_before": "今回より前に逃げた回数", "course_runs_before": "同じ競馬場・コース・距離での出走数（今回より前）",
    "course_wins_before": "同じ競馬場・コース・距離での勝利数（今回より前）",
    "best_time_unit": "同じ競馬場・コース・距離・馬場状態での持ち時計（今回より前の最速、秒）",
    "best_time_unit_rank": "その持ち時計を今回の出走馬の中で速い順に並べた順位（無ければ NULL）",
    "best_time_dist": "同じ芝ダ・距離・馬場状態での持ち時計（競馬場を問わない）",
    "best_time_dist_rank": "その持ち時計の今回の出走馬の中での順位",
    "affiliation": "所属（美浦 / 栗東 / 招待）", "blinker": "ブリンカー（あり / なし）", "apprentice": "騎手の減量（減量あり / 減量なし）",
    "max_horse_no": "そのレースのいちばん外の馬番",
    "course_places_before": "同じ競馬場・コース・距離での3着内の数（今回より前）",
    "venue_wins_before": "同じ競馬場・同じ芝ダでの勝利数（今回より前）",
    "dist_wins_before": "同じ芝ダ・同じ距離での勝利数（今回より前）",
    "cond_places_before": "同じ芝ダ・同じ馬場状態での3着内の数（今回より前）",
    "same_race_runs_before": "同じ競走名のレースへの出走数（今回より前。競走名の無い平場は NULL）",
    "same_race_wins_before": "同じ競走名のレースでの勝利数（同上）",
    "same_race_places_before": "同じ競走名のレースでの3着内の数（同上）",
    "style_before": "推定脚質（今回より前の直近3走の脚質の中央。過去走が無ければ NULL）",
    "lead_candidates": "そのレースで推定脚質が逃げの馬の数",
}
#: 途中の計算にだけ使い、事実表には残さない列。
_HELPER_COLUMNS = (
    "cond_code", "style_code", "prev_class_order", "prev_jockey_code",
    "area_code", "has_blinker", "is_apprentice", "style_no",
)
#: 推定脚質に使う近走の数。3走の中央を取る（2走なら前寄り、1走ならその脚質）。
STYLE_BEFORE_RUNS = 3
#: 騎手見習コード（コード表 2303）のうち、減量のあるもの。
_APPRENTICE_CODES: tuple[str, ...] = ("1", "2", "3", "4", "9")
#: 確定前のレースで、まだ決まっていない馬場状態の値。
_UNDECIDED_CONDITION = "0"
#: そのレースの行として使わないデータ区分（削除・レース中止）。
_DEAD_STAGES: tuple[str, ...] = ("0", "9")

#: 払戻の子の表の列。無いときの空の関係を作るのに使う。
_PAYOUT_COLUMNS = (*keys.RACE_KEY, "馬番", "払戻金")
_PEDIGREE_COLUMNS = (keys.HORSE_KEY, "_連番", "馬名")
_TM_COLUMNS = (*keys.RACE_KEY, "馬番", "予測スコア")
#: 3代血統情報の連番。1 父・3 父父・5 母父。
_SIRE_SEQ, _GRANDSIRE_SEQ, _DAMSIRE_SEQ = 1, 3, 5
#: 4コーナーの列名。
_CORNER4 = "4コーナーでの順位"


def has_table(con: duckdb.DuckDBPyConnection, table: str) -> bool:
    """その名前の表があるか。"""
    return bool(con.execute("SELECT count(*) FROM duckdb_tables() WHERE table_name = ?", [table]).fetchone()[0])


def optional_relation(con: duckdb.DuckDBPyConnection, table: str, columns: Sequence[str]) -> str:
    """表があればその名前、無ければ同じ列を持つ空の関係。取得途中の DB や合成DB で落ちないようにする。"""
    if has_table(con, table):
        return keys.q(table)
    empty = ", ".join(f"NULL::VARCHAR AS {keys.q(column)}" for column in columns)
    return f"(SELECT {empty} WHERE FALSE)"


@dataclass(frozen=True)
class EntryScope:
    """事実表と同じ列を付けたい1レース（確定前でもよい）。

    ``condition_code`` は手で与える当日の馬場状態（1〜4）。確定前のレースは馬場状態が未発表なので、
    与えなければそのレースの馬場状態は NULL になり、馬場状態で分ける累積（持ち時計など）も NULL になる。
    """

    rid: str
    condition_code: str | None = None

    def __post_init__(self) -> None:
        keys.split_rid(self.rid)
        if self.condition_code is not None and self.condition_code not in codes.TRACK_CONDITION:
            raise ValueError(f"馬場状態コードは {', '.join(codes.TRACK_CONDITION)} のどれかです: {self.condition_code}")


def _row_scope(entry: EntryScope | None) -> tuple[str, str, str]:
    """``ra``・``se``・血統の表から読む行の条件。既定は中央の確定成績だけ（血統は全部）。

    ``entry`` があれば、そのレースの行（確定前でもよい）を足し、``se`` はそのレースの出走馬の行だけに絞る。
    確定前のレースは、いちばん新しいデータ区分の行だけを使う（出走馬名表にだけ居て出馬表で消えた馬を拾わない）。
    rid は検証済みの16桁の数字なので、そのまま SQL に埋める。
    """
    final = f"{keys.jra_only()} AND {keys.final_only()}"
    if entry is None:
        return final, final, "TRUE"
    this_race = f"{keys.rid_expr()} = '{entry.rid}'"
    alive = f"{keys.q('データ区分')} NOT IN {keys.sql_list(_DEAD_STAGES)}"
    newest = f"(SELECT max({keys.q('データ区分')}) FROM se WHERE {this_race} AND {alive})"
    horses = f"(SELECT {keys.q(keys.HORSE_KEY)} FROM se WHERE {this_race})"
    race_rows = f"{keys.jra_only()} AND ({keys.final_only()} OR ({this_race} AND {alive}))"
    runner_rows = (f"{keys.jra_only()} AND ({keys.final_only()} OR ({this_race} AND {keys.q('データ区分')} = {newest})) "
                   f"AND {keys.q(keys.HORSE_KEY)} IN {horses}")
    return race_rows, runner_rows, f"{keys.q(keys.HORSE_KEY)} IN {horses}"


def _condition_code_sql(entry: EntryScope | None) -> str:
    """馬場状態コードの式。ダートのコースはダートの、芝と障害は芝の（芝が 0 ならダートの）馬場状態。

    ``entry`` のレースだけは、手で与えた値を優先し、未発表（0）なら NULL にする。
    """
    recorded = ("CASE WHEN r.track_code BETWEEN '23' AND '29' THEN r.dirt_cond "
                "WHEN r.turf_cond <> '0' THEN r.turf_cond ELSE r.dirt_cond END")
    if entry is None:
        return recorded
    given = codes.sql_literal(entry.condition_code) if entry.condition_code else "NULL"
    return (f"CASE WHEN r.race_id = '{entry.rid}' THEN coalesce({given}, NULLIF({recorded}, '{_UNDECIDED_CONDITION}')) "
            f"ELSE {recorded} END")


def facts_sql(con: duckdb.DuckDBPyConnection, entry: EntryScope | None = None) -> str:
    """事実表を作る SQL。列の意味は ``FACT_COLUMNS``。

    ``entry`` を渡すと、確定成績に加えてそのレースの行も読み、そのレースの出走馬の行だけに絞る
    （``build_entry_facts`` が使う。そのレース以外の行はレース単位の列が正しくないので使わない）。
    """
    rid = keys.rid_expr()
    race_rows, runner_rows, pedigree_rows = _row_scope(entry)
    not_ran = keys.sql_list(keys.NOT_RAN_CODES)
    no_place = keys.sql_list(keys.OUT_OF_RACE_CODES)
    win_table = optional_relation(con, "hr__単勝払戻", _PAYOUT_COLUMNS)
    place_table = optional_relation(con, "hr__複勝払戻", _PAYOUT_COLUMNS)
    pedigree_table = optional_relation(con, "um__3代血統情報", _PEDIGREE_COLUMNS)
    tm_table = optional_relation(con, "tm__マイニング予想", _TM_COLUMNS)
    sex_order = {name: index for index, name in enumerate(codes.SEX_NAMES.values())}
    style_order = {code: index for index, code in enumerate(codes.STYLE_NAMES)}
    return f"""
    WITH race AS (
        SELECT {rid} AS race_id, {keys.race_date_expr()} AS race_date,
               CAST(substr("開催月日", 1, 2) AS INTEGER) AS month,
               "競馬場コード" AS venue_code, CAST("レース番号" AS INTEGER) AS race_no,
               trim("競走名本題") AS race_name, "トラックコード" AS track_code,
               TRY_CAST("距離" AS INTEGER) AS distance_m,
               "芝馬場状態コード" AS turf_cond, "ダート馬場状態コード" AS dirt_cond,
               "競走条件コード 最若年条件" AS cond_code, trim("グレードコード") AS grade_code,
               coalesce(TRY_CAST(NULLIF("出走頭数", '00') AS INTEGER), TRY_CAST(NULLIF("登録頭数", '00') AS INTEGER)) AS field_size
        FROM ra
        WHERE {race_rows}
        {keys.latest_qualify(keys.RACE_KEY)}
    ), runner AS (
        SELECT {rid} AS race_id,
               TRY_CAST(NULLIF("枠番", '0') AS INTEGER) AS frame_no,
               TRY_CAST(NULLIF("馬番", '00') AS INTEGER) AS horse_no,
               "血統登録番号" AS horse_id, trim("馬名") AS horse_name, "性別コード" AS sex_code,
               TRY_CAST(NULLIF("馬齢", '00') AS INTEGER) AS age,
               "騎手コード" AS jockey_code, trim("騎手名略称") AS jockey,
               "調教師コード" AS trainer_code, trim("調教師名略称") AS trainer,
               TRY_CAST(NULLIF("負担重量", '000') AS INTEGER) / 10.0 AS carried,
               TRY_CAST(NULLIF(NULLIF("馬体重", '000'), '999') AS INTEGER) AS body_weight,
               "増減符号" AS weight_sign, TRY_CAST("増減差" AS INTEGER) AS weight_diff,
               "異常区分コード" AS abnormal,
               CASE WHEN "異常区分コード" IN {no_place} THEN NULL
                    ELSE TRY_CAST(NULLIF("確定着順", '00') AS INTEGER) END AS finish,
               TRY_CAST(NULLIF("走破タイム", '0000') AS INTEGER) AS time_raw,
               "タイム差" AS diff_raw,
               TRY_CAST(NULLIF({keys.q(_CORNER4)}, '00') AS INTEGER) AS corner4,
               TRY_CAST(NULLIF("単勝人気順", '00') AS INTEGER) AS popularity,
               TRY_CAST(NULLIF("単勝オッズ", '0000') AS INTEGER) / 10.0 AS win_odds,
               TRY_CAST(NULLIF(NULLIF("後3ハロンタイム", '000'), '999') AS INTEGER) / 10.0 AS last3f,
               "今回レース脚質判定" AS style_code,
               TRY_CAST(NULLIF("マイニング予想順位", '00') AS INTEGER) AS dm_rank,
               "東西所属コード" AS area_code, "ブリンカー使用区分" = '1' AS has_blinker,
               "騎手見習コード" IN {keys.sql_list(_APPRENTICE_CODES)} AS is_apprentice
        FROM se
        WHERE {runner_rows}
        {keys.latest_qualify((*keys.RACE_KEY, keys.HORSE_KEY))}
    ), win_payout AS (
        SELECT {rid} AS race_id, TRY_CAST("馬番" AS INTEGER) AS horse_no,
               max(TRY_CAST("払戻金" AS BIGINT)) AS win_payout
        FROM {win_table} GROUP BY ALL
    ), place_payout AS (
        SELECT {rid} AS race_id, TRY_CAST("馬番" AS INTEGER) AS horse_no,
               max(TRY_CAST("払戻金" AS BIGINT)) AS place_payout
        FROM {place_table} GROUP BY ALL
    ), pedigree AS (
        SELECT "血統登録番号" AS horse_id,
               max(CASE WHEN "_連番" = {_SIRE_SEQ} THEN trim("馬名") END) AS sire,
               max(CASE WHEN "_連番" = {_GRANDSIRE_SEQ} THEN trim("馬名") END) AS grandsire,
               max(CASE WHEN "_連番" = {_DAMSIRE_SEQ} THEN trim("馬名") END) AS damsire
        FROM {pedigree_table} WHERE {pedigree_rows} GROUP BY ALL
    ), tm_rows AS (
        SELECT {rid} AS race_id, TRY_CAST("馬番" AS INTEGER) AS horse_no,
               max(TRY_CAST("予測スコア" AS INTEGER)) / 10.0 AS tm_score
        FROM {tm_table}
        WHERE TRY_CAST("馬番" AS INTEGER) > 0 AND TRY_CAST("予測スコア" AS INTEGER) > 0
        GROUP BY ALL
    ), tm_pred AS (
        SELECT race_id, horse_no, tm_score,
               rank() OVER (PARTITION BY race_id ORDER BY tm_score DESC) AS tm_rank
        FROM tm_rows
    ), joined AS (
        SELECT r.race_id, r.race_date, r.month, r.venue_code,
               {codes.sql_case("r.venue_code", codes.VENUE_NAMES, "?")} AS venue,
               r.race_no, r.race_name, r.track_code,
               {codes.surface_sql("r.track_code")} AS surface,
               {codes.sql_case("r.track_code", codes.TRACK_NAMES, "?")} AS course,
               r.distance_m,
               {_condition_code_sql(entry)} AS condition_code,
               r.cond_code, r.grade_code, r.field_size,
               s.frame_no, s.horse_no, s.horse_id, s.horse_name,
               {codes.sql_case("s.sex_code", codes.SEX_NAMES, "?")} AS sex,
               s.age, s.jockey_code, s.jockey, s.trainer_code, s.trainer, s.carried, s.body_weight,
               CASE WHEN s.weight_sign = '+' THEN s.weight_diff
                    WHEN s.weight_sign = '-' THEN -s.weight_diff
                    WHEN s.weight_diff = 0 AND s.body_weight IS NOT NULL THEN 0 END AS weight_change,
               s.popularity, s.win_odds, s.abnormal,
               {codes.sql_case("s.abnormal", codes.ABNORMAL_NAMES, "?")} AS abnormal_name,
               s.abnormal NOT IN {not_ran} AS ran,
               s.finish,
               CASE WHEN s.time_raw IS NULL THEN NULL
                    ELSE (s.time_raw // 1000) * 60 + (s.time_raw % 1000) / 10.0 END AS finish_time,
               CASE WHEN s.diff_raw IS NULL OR trim(s.diff_raw) = '' OR s.diff_raw = '9999' THEN NULL
                    ELSE TRY_CAST(s.diff_raw AS INTEGER) / 10.0 END AS time_diff,
               s.corner4, s.last3f,
               {codes.sql_case("s.style_code", codes.STYLE_NAMES, "不明")} AS style,
               s.style_code,
               p.sire, p.grandsire, p.damsire,
               coalesce(w.win_payout, 0) AS win_payout,
               coalesce(pl.place_payout, 0) AS place_payout,
               s.dm_rank, t.tm_rank, t.tm_score,
               s.area_code, s.has_blinker, s.is_apprentice
        FROM runner s
        JOIN race r USING (race_id)
        LEFT JOIN pedigree p USING (horse_id)
        LEFT JOIN win_payout w ON w.race_id = s.race_id AND w.horse_no = s.horse_no
        LEFT JOIN place_payout pl ON pl.race_id = s.race_id AND pl.horse_no = s.horse_no
        LEFT JOIN tm_pred t ON t.race_id = s.race_id AND t.horse_no = s.horse_no
    ), typed AS (
        SELECT *,
               {codes.sql_case("surface", codes.SURFACE_ORDER, 9)} AS surface_order,
               {codes.sql_case("condition_code", codes.TRACK_CONDITION, "?")} AS condition,
               coalesce(TRY_CAST(condition_code AS INTEGER), 9) AS condition_order,
               {codes.class_name_sql("cond_code", "grade_code")} AS class_name,
               {codes.sql_case(codes.class_name_sql("cond_code", "grade_code"), codes.CLASS_ORDER, 99)} AS class_order,
               {codes.sql_case("sex", sex_order, 9)} AS sex_order,
               {codes.sql_case("style_code", style_order, 9)} AS style_order,
               CAST(substr(race_date, 1, 4) AS INTEGER) AS year,
               {codes.sql_case("area_code", codes.AFFILIATION_NAMES, "不明")} AS affiliation,
               CASE WHEN has_blinker THEN 'あり' ELSE 'なし' END AS blinker,
               CASE WHEN is_apprentice THEN '減量あり' ELSE '減量なし' END AS apprentice,
               CASE WHEN ran AND style_code IN {keys.sql_list(codes.STYLE_NAMES)} THEN CAST(style_code AS INTEGER) END AS style_no
        FROM joined
    ), enriched AS (
        -- 前走（lag）と「今回より前」の累積（ROWS ... 1 PRECEDING）。当日の結果は入らない
        SELECT *,
               CASE WHEN last3f IS NOT NULL AND ran THEN
                    rank() OVER (PARTITION BY race_id, (last3f IS NOT NULL AND ran) ORDER BY last3f)
               END AS last3f_rank,
               lag(finish) OVER horse AS prev_finish,
               lag(popularity) OVER horse AS prev_popularity,
               date_diff('day', lag(CAST(race_date AS DATE)) OVER horse, CAST(race_date AS DATE)) AS interval_days,
               lag(style) OVER horse AS prev_style,
               lag(last3f) OVER horse AS prev_last3f,
               lag(time_diff) OVER horse AS prev_time_diff,
               lag(corner4) OVER horse AS prev_corner4,
               lag(field_size) OVER horse AS prev_field_size,
               lag(distance_m) OVER horse AS prev_distance_m,
               lag(surface) OVER horse AS prev_surface,
               lag(venue) OVER horse AS prev_venue,
               lag(class_order) OVER horse AS prev_class_order,
               lag(jockey_code) OVER horse AS prev_jockey_code,
               coalesce(sum(CASE WHEN ran THEN 1 ELSE 0 END) OVER horse_before, 0) AS runs_before,
               coalesce(sum(CASE WHEN finish = 1 THEN 1 ELSE 0 END) OVER horse_before, 0) AS wins_before,
               coalesce(sum(CASE WHEN ran AND style_code = '1' THEN 1 ELSE 0 END) OVER horse_before, 0) AS lead_runs_before,
               coalesce(sum(CASE WHEN ran THEN 1 ELSE 0 END) OVER course_before, 0) AS course_runs_before,
               coalesce(sum(CASE WHEN finish = 1 THEN 1 ELSE 0 END) OVER course_before, 0) AS course_wins_before,
               min(finish_time) OVER unit_before AS best_time_unit,
               min(finish_time) OVER dist_before AS best_time_dist,
               bool_or(ran AND sex = '牝') OVER race AND bool_or(ran AND sex <> '牝') OVER race AS mixed_sex,
               min(CASE WHEN ran THEN age END) OVER race <> max(CASE WHEN ran THEN age END) OVER race AS mixed_age,
               max(CASE WHEN finish = 1 THEN style END) OVER race AS winner_style,
               max(horse_no) OVER race AS max_horse_no,
               coalesce(sum(CASE WHEN finish <= 3 THEN 1 ELSE 0 END) OVER course_before, 0) AS course_places_before
        FROM typed
        WINDOW horse AS (PARTITION BY horse_id ORDER BY race_date, race_id),
               horse_before AS (PARTITION BY horse_id ORDER BY race_date, race_id
                                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),
               course_before AS (PARTITION BY horse_id, venue_code, track_code, distance_m ORDER BY race_date, race_id
                                 ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),
               unit_before AS (PARTITION BY horse_id, venue_code, track_code, distance_m, condition_code ORDER BY race_date, race_id
                               ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),
               dist_before AS (PARTITION BY horse_id, surface, distance_m, condition_code ORDER BY race_date, race_id
                               ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),
               race AS (PARTITION BY race_id)
    ), narrow AS (
        -- 下の累積に要る列だけ。列の多い行のまま窓を増やすと、並べ替えが重くなる
        SELECT race_id, horse_id, race_date, venue_code, surface, distance_m, condition_code, race_name, ran, finish, style_no
        FROM typed
    ), experience AS (
        SELECT race_id, horse_id, ran,
               {", ".join(f"lag(style_no, {n} IGNORE NULLS) OVER horse AS style_{n}" for n in range(1, STYLE_BEFORE_RUNS + 1))},
               coalesce(sum(CASE WHEN finish = 1 THEN 1 ELSE 0 END) OVER venue_before, 0) AS venue_wins_before,
               coalesce(sum(CASE WHEN finish = 1 THEN 1 ELSE 0 END) OVER distance_before, 0) AS dist_wins_before,
               coalesce(sum(CASE WHEN finish <= 3 THEN 1 ELSE 0 END) OVER going_before, 0) AS cond_places_before,
               -- 競走名の無い平場どうしを「同じレース」にしない
               CASE WHEN race_name <> '' THEN coalesce(sum(CASE WHEN ran THEN 1 ELSE 0 END) OVER same_race_before, 0) END AS same_race_runs_before,
               CASE WHEN race_name <> '' THEN coalesce(sum(CASE WHEN finish = 1 THEN 1 ELSE 0 END) OVER same_race_before, 0) END AS same_race_wins_before,
               CASE WHEN race_name <> '' THEN coalesce(sum(CASE WHEN finish <= 3 THEN 1 ELSE 0 END) OVER same_race_before, 0) END AS same_race_places_before
        FROM narrow
        WINDOW horse AS (PARTITION BY horse_id ORDER BY race_date, race_id),
               venue_before AS (PARTITION BY horse_id, venue_code, surface ORDER BY race_date, race_id
                                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),
               distance_before AS (PARTITION BY horse_id, surface, distance_m ORDER BY race_date, race_id
                                   ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),
               going_before AS (PARTITION BY horse_id, surface, condition_code ORDER BY race_date, race_id
                                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),
               same_race_before AS (PARTITION BY horse_id, race_name ORDER BY race_date, race_id
                                    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)
    ), styled AS (
        -- 推定脚質: 直近3走の中央（タイが起きない）。2走なら前寄り、1走ならその脚質、過去走が無ければ NULL
        SELECT * EXCLUDE (style_1, style_2, style_3),
               CASE WHEN style_1 IS NULL THEN NULL WHEN style_2 IS NULL THEN style_1
                    WHEN style_3 IS NULL THEN least(style_1, style_2)
                    ELSE style_1 + style_2 + style_3 - least(style_1, style_2, style_3) - greatest(style_1, style_2, style_3)
               END AS style_before_no
        FROM experience
    ), history AS (
        SELECT * EXCLUDE (ran, style_before_no),
               CASE style_before_no {" ".join(f"WHEN {code} THEN '{name}'" for code, name in codes.STYLE_NAMES.items())} END AS style_before,
               sum(CASE WHEN ran AND style_before_no = 1 THEN 1 ELSE 0 END) OVER (PARTITION BY race_id) AS lead_candidates
        FROM styled
    ), complete AS (
        SELECT * FROM enriched JOIN history USING (race_id, horse_id)
    )
    SELECT * EXCLUDE ({", ".join(_HELPER_COLUMNS)}),
           CASE WHEN best_time_unit IS NOT NULL THEN
                rank() OVER (PARTITION BY race_id, (best_time_unit IS NOT NULL) ORDER BY best_time_unit) END AS best_time_unit_rank,
           CASE WHEN best_time_dist IS NOT NULL THEN
                rank() OVER (PARTITION BY race_id, (best_time_dist IS NOT NULL) ORDER BY best_time_dist) END AS best_time_dist_rank,
           CASE WHEN prev_last3f IS NOT NULL THEN
                rank() OVER (PARTITION BY race_id, (prev_last3f IS NOT NULL) ORDER BY prev_last3f) END AS prev_last3f_rank,
           CASE WHEN prev_surface IS NULL THEN '前走なし' WHEN prev_surface = surface THEN '同じ'
                ELSE prev_surface || '→' || surface END AS surface_change,
           CASE WHEN prev_distance_m IS NULL THEN '前走なし' WHEN prev_distance_m < distance_m THEN '延長'
                WHEN prev_distance_m > distance_m THEN '短縮' ELSE '同じ' END AS distance_change,
           CASE WHEN prev_class_order IS NULL THEN '前走なし' WHEN prev_class_order = 99 OR class_order = 99 THEN '不明'
                WHEN prev_class_order < class_order THEN '昇級' WHEN prev_class_order > class_order THEN '降級'
                ELSE '同級' END AS class_change,
           CASE WHEN prev_jockey_code IS NULL THEN '前走なし' WHEN prev_jockey_code = jockey_code THEN '継続'
                ELSE '乗り替わり' END AS jockey_change,
           CASE WHEN prev_venue IS NULL THEN '前走なし' WHEN prev_venue = venue THEN '同じ' ELSE '別' END AS venue_change
    FROM complete
    """


def facts_ready(con: duckdb.DuckDBPyConnection, name: str = FACTS_TABLE) -> bool:
    """事実表が既にあるか。"""
    return bool(con.execute("SELECT count(*) FROM duckdb_tables() WHERE table_name = ? AND temporary", [name]).fetchone()[0])


def ensure_facts(con: duckdb.DuckDBPyConnection, name: str = FACTS_TABLE) -> str:
    """事実表（一時表）が無ければ作る。表の名前を返す。"""
    if not facts_ready(con, name):
        con.execute(f"CREATE TEMP TABLE {keys.q(name)} AS {facts_sql(con)}")
    return name


def build_entry_facts(con: duckdb.DuckDBPyConnection, entry: EntryScope, *,
                      popularity: Mapping[int, int] | None = None,
                      popularity_by_name: Mapping[str, int] | None = None,
                      weights: Mapping[int, tuple[int, int | None]] | None = None, name: str = ENTRY_TABLE) -> str:
    """1レースの出走馬に事実表と同じ列を付けた一時表を作る（あれば作り直す）。表の名前を返す。

    ``popularity`` は 馬番 → 単勝人気、``popularity_by_name`` は 馬名 → 単勝人気、``weights`` は 馬番 → （馬体重, 増減）。
    発走前の DB に無い値を手で与える。馬番がまだ決まっていないレース（木曜の出走馬名表）には、人気を馬名で与える
    （馬名は事実表と同じく前後の空白を除いたもの）。レースが無ければ ``LookupError``、いない馬番・馬名なら ``ValueError``。
    """
    table = keys.q(name)
    con.execute(f"CREATE OR REPLACE TEMP TABLE {table} AS SELECT * FROM ({facts_sql(con, entry)}) WHERE race_id = '{entry.rid}'")
    known = {no for (no,) in con.execute(f"SELECT horse_no FROM {table}").fetchall()}
    if not known:
        con.execute(f"DROP TABLE IF EXISTS {table}")
        raise LookupError(f"レースが見つかりません: {entry.rid}")
    unknown = sorted({*(popularity or {}), *(weights or {})} - known)
    if unknown:
        raise ValueError(f"馬番 {unknown[0]} はこのレースにいません（出走馬名表の間は馬番が未定で、人気・馬体重を与えられません）")
    _check_names_known(con, table, popularity_by_name or {})
    for horse_no, rank in (popularity or {}).items():
        con.execute(f"UPDATE {table} SET popularity = ? WHERE horse_no = ?", [rank, horse_no])
    for horse_name, rank in (popularity_by_name or {}).items():
        con.execute(f"UPDATE {table} SET popularity = ? WHERE horse_name = ?", [rank, horse_name])
    for horse_no, (weight, change) in (weights or {}).items():
        con.execute(f"UPDATE {table} SET body_weight = ?, weight_change = ? WHERE horse_no = ?", [weight, change, horse_no])
    return name


def _check_names_known(con: duckdb.DuckDBPyConnection, table: str, popularity_by_name: Mapping[str, int]) -> None:
    """馬名で与えた人気の馬名が、そのレースの出走馬にあるか。無ければ ``ValueError``。"""
    known = {name for (name,) in con.execute(f"SELECT horse_name FROM {table}").fetchall()}
    unknown = sorted(set(popularity_by_name) - known)
    if unknown:
        raise ValueError(f"馬名 {unknown[0]} はこのレースにいません（出走馬名表の馬名とそのまま一致させてください）")


def rebuild_timing(con: duckdb.DuckDBPyConnection, name: str = FACTS_TABLE) -> tuple[int, float]:
    """事実表を作り直して、行数と秒を返す（速さを確かめるため）。"""
    con.execute(f"DROP TABLE IF EXISTS {keys.q(name)}")
    started = time.perf_counter()
    ensure_facts(con, name)
    elapsed = round(time.perf_counter() - started, 2)
    rows = con.execute(f"SELECT count(*) FROM {keys.q(name)}").fetchone()[0]
    return rows, elapsed


def timing_table(con: duckdb.DuckDBPyConnection) -> Table:
    """行数と秒を「項目 | 値」の表にする。"""
    rows, elapsed = rebuild_timing(con)
    ran = con.execute(f"SELECT count(*) FROM {FACTS_TABLE} WHERE ran").fetchone()[0]
    return Table(["項目", "値"], [["事実表の行数", rows], ["うち出走した行", ran], ["作成にかかった秒", elapsed]], title="事実表")


def columns_table() -> Table:
    """列の一覧（列名と意味）。"""
    return Table(["列", "意味"], [[name, meaning] for name, meaning in FACT_COLUMNS.items()], title="事実表の列")
