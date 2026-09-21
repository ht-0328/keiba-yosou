"""レースの一覧と、1レースの詳細（出走表・結果・ラップ・通過順・払戻）。

一覧は事実表（中央・確定成績）から。詳細は生の表（``ra``・``se``・``hr__*``・``ra__コーナー通過順位``）から読むので、
確定前の出馬表（データ区分 1・2）でも見られる。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import duckdb

from . import codes, keys, raw
from .facts import FACTS_TABLE, ensure_facts, has_table
from .filters import Filters, parse_date
from .render import Table

#: 一覧に出す列（事実表の列名, 見出し）。レース単位の列だけ。
RACE_LIST_COLUMNS: tuple[tuple[str, str], ...] = (
    ("race_date", "日付"), ("venue", "場"), ("race_no", "R"), ("race_name", "レース名"), ("class_name", "クラス"),
    ("course", "コース"), ("distance_m", "距離"), ("condition", "馬場"), ("field_size", "頭数"), ("race_id", "rid"),
)
MAX_LIMIT = 1000
#: 払戻の券種と、子の表・組の列。
PAYOUT_TABLES: tuple[tuple[str, str, str], ...] = (
    ("単勝", "hr__単勝払戻", "馬番"), ("複勝", "hr__複勝払戻", "馬番"), ("枠連", "hr__枠連払戻", "組番"),
    ("馬連", "hr__馬連払戻", "組番"), ("ワイド", "hr__ワイド払戻", "組番"), ("馬単", "hr__馬単払戻", "組番"),
    ("3連複", "hr__3連複払戻", "組番"), ("3連単", "hr__3連単払戻", "組番"),
)
#: ラップの区間の数（JV-Data の繰返し数）。
_LAP_COUNT = 25
_CORNER_TABLE = "ra__コーナー通過順位"
#: 出走表の見出し。
RUNNER_HEADERS: tuple[str, ...] = (
    "枠", "馬番", "馬名", "性齢", "斤量", "騎手", "調教師", "馬体重", "人気", "単勝", "着順", "異常",
    "タイム", "着差", "通過", "上がり", "予想順位", "脚質", "hid",
)


@dataclass
class RaceDetail:
    """1レースの詳細。``header`` は見出しに使う項目、ほかは表。"""

    header: dict[str, Any]
    runners: Table
    laps: Table
    corners: Table
    payouts: Table

    def title(self) -> str:
        """``2026-09-06 中山 11R レース名（クラス 芝・右 1600m 良 16頭 15:45）``。"""
        h = self.header
        return (f"{h['日付']} {h['競馬場']} {h['R']}R {h['レース名'] or ''}"
                f"（{h['クラス']} {h['コース']} {h['距離']}m {h['馬場']} {h['頭数']}頭 {h['発走']}）").replace("  ", " ")

    def tables(self) -> list[Table]:
        """出力用の表の並び。最初の表がレースの見出し。"""
        head = Table(["項目", "値"], [[k, v] for k, v in self.header.items()], title=self.title())
        return [head, self.runners, self.laps, self.corners, self.payouts]


def list_races(con: duckdb.DuckDBPyConnection, filters: Filters, *, limit: int = 200, offset: int = 0) -> Table:
    """条件に合うレース（馬の条件は「その馬が出たレース」）。新しい順。``meta["total"]`` に総件数。"""
    ensure_facts(con)
    where, params = filters.where()
    limit = max(1, min(int(limit), MAX_LIMIT))
    offset = max(0, int(offset))
    total = con.execute(f"SELECT count(DISTINCT race_id) FROM {FACTS_TABLE} WHERE ran AND {where}", params).fetchone()[0]
    select = ", ".join(column for column, _ in RACE_LIST_COLUMNS)
    cursor = con.execute(
        f"SELECT {select} FROM {FACTS_TABLE} WHERE ran AND {where} GROUP BY ALL "
        f"ORDER BY race_date DESC, race_id DESC LIMIT ? OFFSET ?", [*params, limit, offset],
    )
    rows = [list(row) for row in cursor.fetchall()]
    shown = f"{offset + 1}〜{offset + len(rows)} 件" if rows else "該当なし"
    table = Table([title for _, title in RACE_LIST_COLUMNS], rows, title=f"レースの一覧: {filters.describe()}",
                  note=f"全 {total:,} レースのうち {shown}")
    table.meta = {"total": total, "offset": offset, "limit": limit, "filters": filters.describe()}
    return table


def resolve_rid(con: duckdb.DuckDBPyConnection, date: str, venue: str, race_no: int | str) -> str:
    """開催日・競馬場・レース番号から rid を引く。無ければ ``LookupError``。"""
    day = parse_date(date).replace("-", "")
    code = codes.venue_code(venue)
    rows = con.execute(
        f"SELECT DISTINCT {keys.rid_expr()} FROM ra WHERE {keys.q('開催年')} = ? AND {keys.q('開催月日')} = ? "
        f"AND {keys.q('競馬場コード')} = ? AND {keys.q('レース番号')} = ?", [day[:4], day[4:], code, f"{int(race_no):02d}"],
    ).fetchall()
    if not rows:
        raise LookupError(f"レースが見つかりません: {parse_date(date)} {codes.venue_name(code)} {int(race_no)}R")
    return rows[0][0]


def race_detail(con: duckdb.DuckDBPyConnection, rid: str) -> RaceDetail:
    """1レースの詳細。無ければ ``LookupError``。"""
    cond, params = keys.rid_condition(rid)
    header = _header(con, rid, cond, params)
    return RaceDetail(
        header=header,
        runners=_runners(con, cond, params),
        laps=_laps(header.pop("_laps"), header),
        corners=_corners(con, cond, params),
        payouts=_payouts(con, cond, params),
    )


def _header(con: duckdb.DuckDBPyConnection, rid: str, cond: str, params: list[str]) -> dict[str, Any]:
    laps = ", ".join(keys.q(f"ラップタイム_{i:02d}") for i in range(1, _LAP_COUNT + 1))
    row = con.execute(
        f"""
        SELECT {keys.race_date_expr()}, "競馬場コード", CAST("レース番号" AS INTEGER), "データ区分",
               trim("競走名本題"), "競走条件コード 最若年条件", "グレードコード", "距離", "トラックコード",
               "芝馬場状態コード", "ダート馬場状態コード", "天候コード", "出走頭数", "登録頭数", "発走時刻",
               "前3ハロン", "後3ハロン", "前4ハロン", "後4ハロン", {laps}
        FROM ra WHERE {cond} {keys.latest_qualify(keys.RACE_KEY)}
        """, params,
    ).fetchone()
    if row is None:
        raise LookupError(f"レースが見つかりません: {rid}")
    (date, venue, race_no, stage, name, cond_code, grade, distance, track, turf, dirt, weather,
     field_size, entries, post, f3, l3, f4, l4, *lap_values) = row
    surface = codes.surface_of(track)
    condition = dirt if surface == "ダート" or turf == "0" else turf
    return {
        "rid": rid, "日付": date, "競馬場": codes.venue_name(venue), "R": race_no, "レース名": name,
        "クラス": codes.class_name(cond_code, grade), "コース": codes.TRACK_NAMES.get(track, track),
        "距離": int(distance) if distance and distance.isdigit() else distance,
        "馬場": codes.TRACK_CONDITION.get(condition, "?"), "天候": codes.WEATHER_NAMES.get(weather, "?"),
        "頭数": int(field_size) if field_size and field_size.isdigit() else field_size, "登録頭数": entries,
        "発走": raw.post_time(post),
        "データ区分": codes.STAGE_NAMES.get(stage, stage),
        "前3F": raw.tenths(f3), "後3F": raw.tenths(l3), "前4F": raw.tenths(f4), "後4F": raw.tenths(l4), "_laps": lap_values,
    }


def _runners(con: duckdb.DuckDBPyConnection, cond: str, params: list[str]) -> Table:
    cursor = con.execute(
        f"""
        SELECT "枠番", "馬番", trim("馬名"), "性別コード", "馬齢", "負担重量", trim("騎手名略称"), trim("調教師名略称"),
               "馬体重", "増減符号", "増減差", "単勝人気順", "単勝オッズ", "確定着順", "異常区分コード", "走破タイム", "タイム差",
               "1コーナーでの順位", "2コーナーでの順位", "3コーナーでの順位", "4コーナーでの順位",
               "後3ハロンタイム", "マイニング予想順位", "今回レース脚質判定", "血統登録番号"
        FROM se WHERE {cond} {keys.latest_qualify((*keys.RACE_KEY, keys.HORSE_KEY))}
        ORDER BY TRY_CAST("馬番" AS INTEGER)
        """, params,
    )
    rows = [_runner_row(row) for row in cursor.fetchall()]
    return Table(list(RUNNER_HEADERS), rows, title="出走表・結果")


def _runner_row(row: tuple) -> list[Any]:
    (frame, num, name, sex, age, carried, jockey, trainer, weight, sign, diff, pop, odds, finish, abnormal, time_raw,
     diff_raw, c1, c2, c3, c4, last3f, mining, style, hid) = row
    return [
        raw.to_int(frame), raw.to_int(num), name, f"{codes.SEX_NAMES.get(sex, '?')}{raw.to_int(age) or ''}", raw.tenths(carried), jockey, trainer,
        raw.body_weight(weight, sign, diff), raw.to_int(pop), raw.tenths(odds), raw.to_int(finish), codes.ABNORMAL_NAMES.get(abnormal, abnormal),
        raw.race_time(time_raw), raw.time_diff(diff_raw), "-".join(str(raw.to_int(c)) for c in (c1, c2, c3, c4) if raw.to_int(c)),
        raw.tenths(last3f), raw.to_int(mining), codes.STYLE_NAMES.get(style, ""), hid,
    ]


def _laps(lap_values: list[str], header: dict[str, Any]) -> Table:
    laps = [raw.tenths(v) for v in lap_values]
    laps = [v for v in laps if v is not None]
    columns = [f"{i}F" for i in range(1, len(laps) + 1)]
    note = f"前3F {header['前3F'] or '—'} / 後3F {header['後3F'] or '—'}"
    return Table(columns, [laps] if laps else [], title="ラップ（200mごとの秒）", note=note)


def _corners(con: duckdb.DuckDBPyConnection, cond: str, params: list[str]) -> Table:
    if not has_table(con, _CORNER_TABLE):
        return Table(["コーナー", "周回", "通過順"], [], title="通過順")
    cursor = con.execute(
        f"SELECT \"コーナー\", \"周回数\", trim(\"各通過順位\") FROM {keys.q(_CORNER_TABLE)} WHERE {cond} "
        f"AND trim(\"各通過順位\") <> '' ORDER BY \"_連番\"", params,
    )
    return Table(["コーナー", "周回", "通過順"], [list(r) for r in cursor.fetchall()], title="通過順")


def _payouts(con: duckdb.DuckDBPyConnection, cond: str, params: list[str]) -> Table:
    rows: list[list[Any]] = []
    for label, table, combo in PAYOUT_TABLES:
        if not has_table(con, table):
            continue
        cursor = con.execute(
            f"SELECT trim({keys.q(combo)}), TRY_CAST(\"払戻金\" AS BIGINT), TRY_CAST(\"人気順\" AS INTEGER) "
            f"FROM {keys.q(table)} WHERE {cond} AND TRY_CAST(\"払戻金\" AS BIGINT) > 0 ORDER BY \"_連番\"", params,
        )
        rows.extend([label, *row] for row in cursor.fetchall())
    return Table(["式別", "組番", "払戻（円）", "人気"], rows, title="払戻")
