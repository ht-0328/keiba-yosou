"""馬の検索・プロフィール・過去走。

馬名から血統登録番号（hid）を探し、その馬の中央の出走を新しい順に並べる。
「前走の材料」を見るときは ``before`` に基準日を渡し、その日より前の出走だけにする（当日の結果を混ぜない）。
"""

from __future__ import annotations

from typing import Any

import duckdb

from . import codes, keys
from .facts import FACTS_TABLE, ensure_facts, has_table
from .filters import parse_date
from .render import Table

#: 過去走に出す列（事実表の列名, 見出し）。
HORSE_RUN_COLUMNS: tuple[tuple[str, str], ...] = (
    ("race_date", "日付"), ("venue", "場"), ("race_no", "R"), ("race_name", "レース名"), ("class_name", "クラス"),
    ("course", "コース"), ("distance_m", "距離"), ("condition", "馬場"), ("field_size", "頭数"),
    ("frame_no", "枠"), ("horse_no", "馬番"), ("popularity", "人気"), ("win_odds", "単勝"), ("finish", "着順"),
    ("abnormal_name", "異常"), ("jockey", "騎手"), ("carried", "斤量"), ("body_weight", "馬体重"), ("weight_change", "増減"),
    ("corner4", "4角"), ("last3f", "上がり"), ("finish_time", "タイム"), ("time_diff", "着差"),
    ("dm_rank", "タイム型"), ("tm_rank", "対戦型"), ("race_id", "rid"),
)
MAX_LIMIT = 1000
_PEDIGREE_TABLE = "um__3代血統情報"
#: 3代血統情報の連番。1 父・2 母・5 母父。
_SIRE, _DAM, _DAMSIRE = 1, 2, 5


def find_horses(con: duckdb.DuckDBPyConnection, name: str, *, limit: int = 50) -> Table:
    """馬名で探す（前方一致を先に、部分一致も）。``um`` が無ければ事実表の馬名から。"""
    text = name.strip()
    if not text:
        raise ValueError("馬名を指定してください")
    limit = max(1, min(int(limit), MAX_LIMIT))
    if has_table(con, "um"):
        cursor = con.execute(
            f"""
            SELECT u."血統登録番号" AS hid, trim(u."馬名") AS 馬名,
                   {codes.sql_case('u."性別コード"', codes.SEX_NAMES, "?")} AS 性別,
                   u."生年月日" AS 生年月日, trim(u."調教師名略称") AS 調教師,
                   p.sire AS 父, p.damsire AS 母父
            FROM um u LEFT JOIN ({_pedigree_sql(con)}) p ON p.hid = u."血統登録番号"
            WHERE contains(u."馬名", ?)
            ORDER BY starts_with(trim(u."馬名"), ?) DESC, u."生年月日" DESC, u."血統登録番号"
            LIMIT ?
            """, [text, text, limit],
        )
    else:
        ensure_facts(con)
        cursor = con.execute(
            f"""
            SELECT horse_id AS hid, horse_name AS 馬名, min(sex) AS 性別, NULL AS 生年月日, max(trainer) AS 調教師,
                   max(sire) AS 父, max(damsire) AS 母父
            FROM {FACTS_TABLE} WHERE contains(horse_name, ?) GROUP BY horse_id, horse_name
            ORDER BY starts_with(horse_name, ?) DESC, horse_id LIMIT ?
            """, [text, text, limit],
        )
    table = Table.from_cursor(cursor, title=f"馬名「{text}」の検索")
    table.note = f"{len(table.rows)} 頭" + ("（上限で打ち切り）" if len(table.rows) >= limit else "")
    return table


def _pedigree_sql(con: duckdb.DuckDBPyConnection) -> str:
    """血統登録番号ごとの父・母・母父。表が無ければ空。"""
    if not has_table(con, _PEDIGREE_TABLE):
        return "SELECT NULL::VARCHAR AS hid, NULL::VARCHAR AS sire, NULL::VARCHAR AS dam, NULL::VARCHAR AS damsire WHERE FALSE"
    return (
        f'SELECT "血統登録番号" AS hid, max(CASE WHEN "_連番" = {_SIRE} THEN trim("馬名") END) AS sire, '
        f'max(CASE WHEN "_連番" = {_DAM} THEN trim("馬名") END) AS dam, '
        f'max(CASE WHEN "_連番" = {_DAMSIRE} THEN trim("馬名") END) AS damsire FROM {keys.q(_PEDIGREE_TABLE)} GROUP BY 1'
    )


def horse_profile(con: duckdb.DuckDBPyConnection, hid: str) -> dict[str, Any]:
    """馬のプロフィール（``um`` から。無ければ出走の記録から馬名だけ）。見つからなければ ``LookupError``。"""
    hid = keys.validate_hid(hid)
    if has_table(con, "um"):
        row = con.execute(
            f"""
            SELECT trim(u."馬名"), u."性別コード", u."生年月日", trim(u."調教師名略称"), u."東西所属コード",
                   trim(u."生産者名(法人格無)"), trim(u."産地名"), trim(u."馬主名(法人格無)"), p.sire, p.dam, p.damsire
            FROM um u LEFT JOIN ({_pedigree_sql(con)}) p ON p.hid = u."血統登録番号"
            WHERE u."血統登録番号" = ?
            """, [hid],
        ).fetchone()
        if row is not None:
            name, sex, born, trainer, area, breeder, origin, owner, sire, dam, damsire = row
            return {
                "hid": hid, "馬名": name, "性別": codes.SEX_NAMES.get(sex, "?"), "生年月日": _date(born),
                "調教師": trainer, "所属": codes.AFFILIATION_NAMES.get(area, area), "父": sire, "母": dam, "母父": damsire,
                "生産者": breeder, "産地": origin, "馬主": owner,
            }
    ensure_facts(con)
    row = con.execute(
        f"SELECT max(horse_name), min(sex), max(trainer), max(sire), max(damsire) FROM {FACTS_TABLE} WHERE horse_id = ?", [hid]
    ).fetchone()
    if row is None or row[0] is None:
        raise LookupError(f"馬が見つかりません: {hid}")
    name, sex, trainer, sire, damsire = row
    return {"hid": hid, "馬名": name, "性別": sex, "生年月日": None, "調教師": trainer, "所属": None, "父": sire, "母": None,
            "母父": damsire, "生産者": None, "産地": None, "馬主": None}


def _date(raw: str | None) -> str | None:
    if not raw or len(raw) != 8 or not raw.isdigit():
        return raw or None
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"


def profile_table(profile: dict[str, Any]) -> Table:
    """プロフィールを「項目 | 値」の縦表にする。"""
    return Table(["項目", "値"], [[k, v] for k, v in profile.items()], title=f"{profile['馬名']}（{profile['hid']}）")


def horse_runs(con: duckdb.DuckDBPyConnection, hid: str, *, limit: int = 50, before: str | None = None) -> Table:
    """その馬の中央の出走（取消・除外も含む）。新しい順。``before`` を渡すとその日より前だけ。"""
    hid = keys.validate_hid(hid)
    ensure_facts(con)
    limit = max(1, min(int(limit), MAX_LIMIT))
    clauses, params = ["horse_id = ?"], [hid]
    if before:
        clauses.append("race_date < ?")
        params.append(parse_date(before))
    select = ", ".join(column for column, _ in HORSE_RUN_COLUMNS)
    cursor = con.execute(
        f"SELECT {select} FROM {FACTS_TABLE} WHERE {' AND '.join(clauses)} ORDER BY race_date DESC, race_id DESC LIMIT ?",
        [*params, limit],
    )
    rows = [list(row) for row in cursor.fetchall()]
    note = f"{len(rows)} 走" + (f"（{parse_date(before)} より前）" if before else "") + "。中央のレースだけ。"
    return Table([title for _, title in HORSE_RUN_COLUMNS], rows, title="過去走", note=note)
