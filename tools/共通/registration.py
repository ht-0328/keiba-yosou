"""特別登録（tk・tk__登録馬毎情報）から、ra・se と同じ列の「登録馬の行」を作る SQL。

特別登録の予想（docs/design/特別登録馬の近走と適性から3着以内を予想/ の 04 の 3）が、出走馬名表の無い時点に、
事実表と同じ SQL（``facts.facts_sql``）で登録馬に前走・累積・クラスの並び順を付けるために使う。
事実表の列の定義はここに写さず、``ra``・``se`` と同じ名前の列を作って ``facts.EntryRows`` として渡す。
"""

from __future__ import annotations

import duckdb

from . import keys
from .facts import EntryRows, optional_relation

#: 特別登録の表と子表。
TABLE = "tk"
RUNNER_TABLE = "tk__登録馬毎情報"
#: 読む版（1 = ハンデ発表前の日曜の版、2 = ハンデ発表後の月曜の版）。削除（0）は読まない。月曜の版を優先する。
STAGES: tuple[str, ...] = ("1", "2")
#: 登録馬の行の異常区分（出走するとみなす）。
_NORMAL = "0"
#: ``se`` と同じ名前で、登録の時点には無い列（この時点には無い値。木曜以降に DB にあっても読まない）。
_UNKNOWN_RUNNER_COLUMNS: tuple[str, ...] = (
    "枠番", "馬番", "騎手コード", "騎手名略称", "馬体重", "増減符号", "増減差", "確定着順", "入線順位", "走破タイム", "タイム差",
    "1コーナーでの順位", "2コーナーでの順位", "3コーナーでの順位", "4コーナーでの順位", "単勝人気順", "単勝オッズ",
    "後3ハロンタイム", "後4ハロンタイム", "今回レース脚質判定", "マイニング予想順位", "ブリンカー使用区分", "騎手見習コード", "馬主コード",
)
#: ``ra`` と同じ名前で、登録の時点には無い列（馬場状態・天候・出走頭数・ラップ）。
_UNKNOWN_RACE_COLUMNS: tuple[str, ...] = (
    "競走条件名称", "出走頭数", "入線頭数", "天候コード", "芝馬場状態コード", "ダート馬場状態コード", "前3ハロン", "後3ハロン",
)
#: ``tk`` から ``ra`` と同じ名前でそのまま使う列。
_SAME_RACE_COLUMNS: tuple[str, ...] = (
    "データ区分", "データ作成年月日", "特別競走番号", "競走名本題", "競走名略称10文字", "グレードコード", "競走種別コード",
    "競走記号コード", "重量種別コード", "競走条件コード 2歳条件", "競走条件コード 3歳条件", "競走条件コード 4歳条件",
    "競走条件コード 5歳以上条件", "競走条件コード 最若年条件", "距離", "トラックコード", "コース区分",
)
#: ``tk__登録馬毎情報`` から ``se`` と同じ名前でそのまま使う列。
_SAME_RUNNER_COLUMNS: tuple[str, ...] = ("血統登録番号", "馬名", "性別コード", "調教師コード", "調教師名略称", "負担重量")
#: 表が無い DB（特別登録を取り込む前・合成DB）で代わりに使う空の関係の列。
_TABLE_COLUMNS: tuple[str, ...] = (*keys.RACE_KEY, *_SAME_RACE_COLUMNS, "登録頭数")
_RUNNER_TABLE_COLUMNS: tuple[str, ...] = (*keys.RACE_KEY, *_SAME_RUNNER_COLUMNS, "調教師東西所属コード", "交流区分")


def table_relation(con: duckdb.DuckDBPyConnection) -> str:
    """``tk`` があればその名前、無ければ同じ列を持つ空の関係。"""
    return optional_relation(con, TABLE, _TABLE_COLUMNS)


def runner_table_relation(con: duckdb.DuckDBPyConnection) -> str:
    """``tk__登録馬毎情報`` があればその名前、無ければ同じ列を持つ空の関係。"""
    return optional_relation(con, RUNNER_TABLE, _RUNNER_TABLE_COLUMNS)


def this_race_condition(rid: str, alias: str = "") -> str:
    """そのレース（rid）の行を選ぶ条件。rid は検証済みの16桁の数字なので、そのまま SQL に埋める。"""
    values = keys.split_rid(rid)
    return " AND ".join(f"{keys.col(name, alias)} = '{values[name]}'" for name in keys.RACE_KEY)


def chosen_registration_sql(con: duckdb.DuckDBPyConnection, rid: str) -> str:
    """そのレースの特別登録のうち、使う版（月曜の版。無ければ日曜の版。同じ版が複数なら作成日の新しいもの）の1行。"""
    stages = keys.sql_list(STAGES)
    return (f"(SELECT * FROM {table_relation(con)} WHERE {this_race_condition(rid)} AND {keys.q('データ区分')} IN {stages} "
            f"QUALIFY row_number() OVER (ORDER BY {keys.q('データ区分')} DESC, {keys.q('データ作成年月日')} DESC) = 1)")


def registration_race_sql(con: duckdb.DuckDBPyConnection, rid: str) -> str:
    """``ra`` と同じ列の、登録のレースの行（1行）。馬場状態・天候・出走頭数は NULL（未発表。登録頭数も使わないので NULL）。"""
    same = ", ".join(keys.q(column) for column in _SAME_RACE_COLUMNS)
    unknown = ", ".join(f"NULL::VARCHAR AS {keys.q(column)}" for column in (*_UNKNOWN_RACE_COLUMNS, "登録頭数"))
    return f"(SELECT {keys.key_list()}, {same}, {unknown} FROM {chosen_registration_sql(con, rid)})"


def registration_runner_sql(con: duckdb.DuckDBPyConnection, rid: str) -> str:
    """``se`` と同じ列の、登録馬ごとの出走の行（1行 = 1頭）。

    馬齢は開催年 − 血統登録番号の先頭4桁（生年）。異常区分は無し（出走するとみなす）。東西所属は調教師の所属。
    馬番・枠番・騎手・ブリンカー・馬体重・オッズ・着順は NULL。交流区分（1 地方馬・2 外国馬）も列に残す。
    """
    same = ", ".join(f"r.{keys.q(column)}" for column in _SAME_RUNNER_COLUMNS)
    unknown = ", ".join(f"NULL::VARCHAR AS {keys.q(column)}" for column in _UNKNOWN_RUNNER_COLUMNS)
    horse = f"r.{keys.q(keys.HORSE_KEY)}"
    age = (f"lpad(CAST(CAST(t.{keys.q('開催年')} AS INTEGER) - TRY_CAST(substr({horse}, 1, 4) AS INTEGER) AS VARCHAR), 2, '0')"
           f" AS {keys.q('馬齢')}")
    return f"""(SELECT {keys.key_list('t')}, t.{keys.q('データ区分')}, t.{keys.q('データ作成年月日')}, {same}, {age},
               r.{keys.q('調教師東西所属コード')} AS {keys.q('東西所属コード')}, '{_NORMAL}' AS {keys.q('異常区分コード')},
               r.{keys.q('交流区分')}, {unknown}
        FROM {chosen_registration_sql(con, rid)} AS t
        JOIN {runner_table_relation(con)} AS r USING ({keys.key_list()})
        WHERE nullif(trim({horse}), '') IS NOT NULL AND {horse} <> '0000000000')"""


def registration_rows_sql(con: duckdb.DuckDBPyConnection, rid: str) -> EntryRows:
    """事実表の SQL に渡す関係。そのレースの ``ra``・``se`` の行を外し、代わりに登録馬の行を足したもの。

    木曜以降に出走馬名表・出馬表が DB にあっても読まない（特別登録の設計書 11 の 7）。ほかのレースの確定成績はそのまま読む。
    特別登録の表が無い DB では登録馬の行が無く、事実表の SQL はそのレースを見つけられない（``LookupError``）。
    """
    excluded = f"NOT ({this_race_condition(rid)})"
    race = f"(SELECT * FROM ra WHERE {excluded} UNION ALL BY NAME SELECT * FROM {registration_race_sql(con, rid)})"
    runner = f"(SELECT * FROM se WHERE {excluded} UNION ALL BY NAME SELECT * FROM {registration_runner_sql(con, rid)})"
    return EntryRows(race=race, runner=runner)
