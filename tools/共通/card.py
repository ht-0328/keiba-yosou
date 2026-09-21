"""出馬表: これから走るレースの一覧と、1レースの出走馬（レース前に分かる材料）、各馬の近走。

生の表（``ra``・``se``）から読むので、確定前（データ区分 1 出走馬名表・2 出馬表）でも見られる。
木曜の出走馬名表は枠番・馬番が未定（空）で、金・土の出馬表で決まる。馬体重は当日の発表まで空。
近走と通算は事実表（中央・確定成績）の「そのレースの開催日より前」だけ。当日の結果を混ぜない。
結果（着順・タイム・払戻）はここでは出さない。それは ``race.race_detail``（レース詳細）が扱う。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import duckdb

from . import codes, keys, raw
from .facts import FACTS_TABLE, ensure_facts, has_table
from .filters import parse_date
from .render import Table

#: レースの一覧の見出し。
CARD_LIST_HEADERS: tuple[str, ...] = (
    "日付", "曜", "場", "R", "発走", "レース名", "クラス", "コース", "距離", "頭数", "状態", "rid",
)
#: 出馬表の見出し。
ENTRY_HEADERS: tuple[str, ...] = (
    "枠", "馬番", "馬名", "性齢", "斤量", "騎手", "調教師", "所属", "B", "馬体重", "人気", "単勝",
    "タイム型", "対戦型", "異常", "間隔(日)", "近走着順", "通算", "hid",
)
#: 近走に出す列（事実表の列名, 見出し）。
CARD_RUN_COLUMNS: tuple[tuple[str, str], ...] = (
    ("race_date", "日付"), ("venue", "場"), ("race_name", "レース名"), ("class_name", "クラス"),
    ("course", "コース"), ("distance_m", "距離"), ("condition", "馬場"), ("field_size", "頭数"),
    ("popularity", "人気"), ("win_odds", "単勝"), ("finish", "着順"), ("abnormal_name", "異常"),
    ("jockey", "騎手"), ("carried", "斤量"), ("body_weight", "馬体重"), ("corner4", "4角"),
    ("last3f", "上がり"), ("finish_time", "タイム"), ("time_diff", "着差"), ("race_id", "rid"),
)
#: 近走の表で、今回の馬を示す列（馬番・馬名）と、何走前か。
_RECENT_LEAD_HEADERS: tuple[str, ...] = ("馬番", "馬名", "走前")
#: 近走の表に出す走数の既定と上限。
DEFAULT_RUNS = 5
MAX_RUNS = 20
#: 「近走着順」に並べる走数。近走の表の走数とは別に、いつもこの数だけ見る。
FORM_RUNS = 5
#: 一覧に出すレース数の既定と上限。
DEFAULT_LIST_LIMIT = 300
MAX_LIST_LIMIT = 1000
#: 直前のマイニング予想（見出し, 子の表, 値の列, 良い順）。発走の前日以降に入る。無ければ空。
_MINING_TABLES: tuple[tuple[str, str, str, str], ...] = (
    ("タイム型", "dm__マイニング予想", "予想走破タイム", "ASC"),
    ("対戦型", "tm__マイニング予想", "予測スコア", "DESC"),
)
_WEEKDAYS = "月火水木金土日"
#: 天候・馬場状態がまだ出ていないときの表示。
_NOT_ANNOUNCED = "未発表"
_BLINKER_ON = "1"


@dataclass
class HorseForm:
    """1頭の、今回より前の中央の成績。``runs`` は新しい順で、1行 = ``CARD_RUN_COLUMNS`` の値。"""

    runs: list[list[Any]]
    career: str = ""
    last_run_date: str | None = None


@dataclass
class RaceCard:
    """1レースの出馬表。``header`` は見出しに使う項目、``entries`` が出走馬、``recent`` が各馬の近走。"""

    header: dict[str, Any]
    entries: Table
    recent: Table

    def title(self) -> str:
        """``2026-09-19（土） 中山 11R レース名（クラス 芝・右 1600m ハンデ 16頭 15:45 出馬表）``。"""
        return header_title(self.header)

    def tables(self) -> list[Table]:
        """出力用の表の並び。最初の表がレースの見出し。"""
        head = Table(["項目", "値"], [[k, v] for k, v in self.header.items()], title=self.title())
        return [head, self.entries, self.recent]


def weekday_of(day: str) -> str:
    """``YYYY-MM-DD`` の曜日（月〜日）。"""
    return _WEEKDAYS[date.fromisoformat(day).weekday()]


def list_cards(con: duckdb.DuckDBPyConnection, *, date_from: str, date_to: str | None = None,
               venue: str | None = None, limit: int = DEFAULT_LIST_LIMIT) -> Table:
    """開催日が ``date_from`` 以降（``date_to`` まで）の中央のレース。発走の早い順。確定前も確定後も出す。"""
    start = parse_date(date_from)
    end = parse_date(date_to) if date_to else None
    limit = max(1, min(int(limit), MAX_LIST_LIMIT))
    day = keys.race_date_expr()
    clauses, params = [keys.jra_only(), f"{day} >= ?"], [start]
    if end:
        clauses.append(f"{day} <= ?")
        params.append(end)
    if venue:
        clauses.append(f"{keys.q('競馬場コード')} = ?")
        params.append(codes.venue_code(venue))
    latest_races = (
        f"SELECT {day} AS race_date, \"競馬場コード\" AS venue_code, CAST(\"レース番号\" AS INTEGER) AS race_no, "
        f"\"発走時刻\" AS post, trim(\"競走名本題\") AS race_name, \"競走条件コード 最若年条件\" AS cond_code, "
        f"\"グレードコード\" AS grade, \"トラックコード\" AS track, \"距離\" AS distance, \"出走頭数\" AS field_size, "
        f"\"登録頭数\" AS entries, \"データ区分\" AS stage, {keys.rid_expr()} AS race_id "
        f"FROM ra WHERE {' AND '.join(clauses)} {keys.latest_qualify(keys.RACE_KEY)}"
    )
    total = con.execute(f"SELECT count(*) FROM ({latest_races})", params).fetchone()[0]
    found = con.execute(f"SELECT * FROM ({latest_races}) ORDER BY race_date, venue_code, race_no LIMIT ?", [*params, limit]).fetchall()
    rows = [_list_row(row) for row in found]
    period = f"{start} 〜 {end}" if end else f"{start} 以降"
    place = f" {codes.venue_name(codes.venue_code(venue))}" if venue else ""
    table = Table(list(CARD_LIST_HEADERS), rows, title=f"出馬表のあるレース: {period}{place}", note=_list_note(total, len(rows), start))
    table.meta = {"total": total, "from": start, "to": end, "venue": venue or "", "days": sorted({row[0] for row in rows})}
    return table


def _list_row(row: tuple) -> list[Any]:
    day, venue, race_no, post, name, cond_code, grade, track, distance, field_size, entries, stage, rid = row
    return [
        day, weekday_of(day), codes.venue_name(venue), race_no, raw.post_time(post), name, codes.class_name(cond_code, grade),
        codes.TRACK_NAMES.get(track, track), raw.to_int(distance), raw.to_int(field_size) or raw.to_int(entries),
        codes.STAGE_NAMES.get(stage, stage), rid,
    ]


def _list_note(total: int, shown: int, start: str) -> str:
    if not total:
        return (f"{start} 以降のレースは DB にまだありません。出走馬名表は木曜の夕方、出馬表は金・土に出るので、"
                "そのあとに jvdata-store で取得してください。過去の日付は開始日を変えれば見られます。")
    cut = f"（上限で {shown} レースに打ち切り）" if shown < total else ""
    return f"全 {total:,} レース{cut}。状態が「出走馬名表」のレースは枠番・馬番が未定。"


def same_day_races(con: duckdb.DuckDBPyConnection, rid: str) -> list[tuple[int, str]]:
    """同じ開催日・同じ競馬場のレース（レース番号, rid）。画面で前後のレースへ移るのに使う。"""
    key = keys.split_rid(rid)
    day = key["開催年"] + key["開催月日"]
    table = list_cards(con, date_from=day, date_to=day, venue=key["競馬場コード"])
    race_no, race_id = CARD_LIST_HEADERS.index("R"), CARD_LIST_HEADERS.index("rid")
    return [(row[race_no], row[race_id]) for row in table.rows]


def race_card(con: duckdb.DuckDBPyConnection, rid: str, *, runs: int = DEFAULT_RUNS) -> RaceCard:
    """1レースの出馬表と、各馬の近走（``runs`` 走まで。0 なら近走の表は空）。無ければ ``LookupError``。"""
    runs = max(0, min(int(runs), MAX_RUNS))
    cond, params = keys.rid_condition(rid)
    header = _header(con, rid, cond, params)
    entries = _entry_records(con, cond, params)
    forms = _horse_forms(con, [entry["hid"] for entry in entries], before=header["日付"], runs=max(runs, FORM_RUNS))
    mining = {title: _mining_ranks(con, table, value, order, cond, params) for title, table, value, order in _MINING_TABLES}
    return RaceCard(
        header=header,
        entries=_entries_table(entries, forms, mining, race_day=header["日付"]),
        recent=_recent_table(entries, forms, runs=runs, race_day=header["日付"]),
    )


def race_header(con: duckdb.DuckDBPyConnection, rid: str) -> dict[str, Any]:
    """1レースの見出しの項目（日付・競馬場・レース名・コース・距離 …）。無ければ ``LookupError``。"""
    cond, params = keys.rid_condition(rid)
    return _header(con, rid, cond, params)


def header_title(header: dict[str, Any]) -> str:
    """見出しの項目を1行にする。``2026-09-19（土） 中山 11R レース名（クラス 芝・右 1600m ハンデ 16頭 15:45 出馬表）``。"""
    h = header
    return (f"{h['日付']}（{h['曜']}） {h['競馬場']} {h['R']}R {h['レース名'] or ''}"
            f"（{h['クラス']} {h['コース']} {h['距離']}m {h['重量']} {h['頭数']}頭 {h['発走']} {h['状態']}）").replace("  ", " ")


def _header(con: duckdb.DuckDBPyConnection, rid: str, cond: str, params: list[str]) -> dict[str, Any]:
    row = con.execute(
        f"""
        SELECT {keys.race_date_expr()}, "競馬場コード", CAST("レース番号" AS INTEGER), "データ区分", trim("競走名本題"),
               "競走条件コード 最若年条件", "グレードコード", "距離", "トラックコード", "重量種別コード",
               "芝馬場状態コード", "ダート馬場状態コード", "天候コード", "出走頭数", "登録頭数", "発走時刻"
        FROM ra WHERE {cond} {keys.latest_qualify(keys.RACE_KEY)}
        """, params,
    ).fetchone()
    if row is None:
        raise LookupError(f"レースが見つかりません: {rid}")
    (day, venue, race_no, stage, name, cond_code, grade, distance, track, weight_type, turf, dirt, weather,
     field_size, entries, post) = row
    condition = dirt if codes.surface_of(track) == "ダート" or turf == "0" else turf
    return {
        "rid": rid, "日付": day, "曜": weekday_of(day), "競馬場": codes.venue_name(venue), "R": race_no, "レース名": name,
        "クラス": codes.class_name(cond_code, grade), "コース": codes.TRACK_NAMES.get(track, track),
        "距離": raw.to_int(distance), "重量": codes.WEIGHT_TYPE_NAMES.get(weight_type, ""),
        "頭数": raw.to_int(field_size) or raw.to_int(entries), "登録頭数": raw.to_int(entries), "発走": raw.post_time(post),
        "馬場": codes.TRACK_CONDITION.get(condition, _NOT_ANNOUNCED), "天候": codes.WEATHER_NAMES.get(weather, _NOT_ANNOUNCED),
        "状態": codes.STAGE_NAMES.get(stage, stage),
    }


def _entry_records(con: duckdb.DuckDBPyConnection, cond: str, params: list[str]) -> list[dict[str, Any]]:
    """出走馬を馬番の順に（馬番が未定なら馬名の順に）。値は表に出す形にしてある。"""
    cursor = con.execute(
        f"""
        SELECT "枠番", "馬番", "血統登録番号", trim("馬名"), "性別コード", "馬齢", "負担重量", trim("騎手名略称"),
               trim("調教師名略称"), "東西所属コード", "ブリンカー使用区分", "馬体重", "増減符号", "増減差",
               "単勝人気順", "単勝オッズ", "異常区分コード"
        FROM se WHERE {cond} {keys.latest_qualify((*keys.RACE_KEY, keys.HORSE_KEY))}
        ORDER BY TRY_CAST("馬番" AS INTEGER), trim("馬名")
        """, params,
    )
    return [_entry_record(row) for row in cursor.fetchall()]


def _entry_record(row: tuple) -> dict[str, Any]:
    (frame, num, hid, name, sex, age, carried, jockey, trainer, area, blinker, weight, sign, diff, pop, odds, abnormal) = row
    return {
        "枠": raw.to_int(frame), "馬番": raw.to_int(num), "馬名": name,
        "性齢": f"{codes.SEX_NAMES.get(sex, '?')}{raw.to_int(age) or ''}", "斤量": raw.tenths(carried), "騎手": jockey,
        "調教師": trainer, "所属": codes.AFFILIATION_NAMES.get(area, ""), "B": "B" if blinker == _BLINKER_ON else "",
        "馬体重": raw.body_weight(weight, sign, diff), "人気": raw.to_int(pop), "単勝": raw.tenths(odds),
        "異常": codes.ABNORMAL_NAMES.get(abnormal, abnormal), "hid": hid,
    }


def _mining_ranks(con: duckdb.DuckDBPyConnection, table: str, value_column: str, best_first: str,
                  cond: str, params: list[str]) -> dict[int, int]:
    """直前のマイニング予想の、レース内の順位（馬番 → 順位）。表が無い・まだ入っていないなら空。"""
    if not has_table(con, table):
        return {}
    value = f"TRY_CAST({keys.q(value_column)} AS INTEGER)"
    rows = con.execute(
        f"SELECT TRY_CAST(\"馬番\" AS INTEGER) AS horse_no, rank() OVER (ORDER BY max({value}) {best_first}) "
        f"FROM {keys.q(table)} WHERE {cond} AND TRY_CAST(\"馬番\" AS INTEGER) > 0 AND {value} > 0 GROUP BY horse_no", params,
    ).fetchall()
    return dict(rows)


def _horse_forms(con: duckdb.DuckDBPyConnection, hids: list[str], *, before: str, runs: int) -> dict[str, HorseForm]:
    """各馬の、``before``（今回の開催日）より前の中央の成績。出走しなかった行（取消・除外）は数えない。"""
    if not hids:
        return {}
    ensure_facts(con)
    earlier = f"FROM {FACTS_TABLE} WHERE ran AND race_date < ? AND horse_id IN (SELECT unnest(?::VARCHAR[]))"
    select = ", ".join(column for column, _ in CARD_RUN_COLUMNS)
    recent = con.execute(
        f"SELECT horse_id, {select} {earlier} "
        f"QUALIFY row_number() OVER (PARTITION BY horse_id ORDER BY race_date DESC, race_id DESC) <= ? "
        f"ORDER BY horse_id, race_date DESC, race_id DESC", [before, hids, runs],
    ).fetchall()
    careers = con.execute(
        f"SELECT horse_id, count(*) FILTER (finish = 1), count(*) FILTER (finish = 2), count(*) FILTER (finish = 3), "
        f"count(*) FILTER (finish IS NULL OR finish > 3), max(race_date) {earlier} GROUP BY horse_id", [before, hids],
    ).fetchall()
    forms = {hid: HorseForm(runs=[]) for hid in hids}
    for hid, *values in recent:
        forms[hid].runs.append(values)
    for hid, first, second, third, others, last_run_date in careers:
        forms[hid].career = f"{first}-{second}-{third}-{others}"
        forms[hid].last_run_date = last_run_date
    return forms


def _finish_mark(run: list[Any]) -> str:
    """近走着順の1走ぶん。着順が付かない走（競走中止・失格）は「中止」「失格」。"""
    columns = [column for column, _ in CARD_RUN_COLUMNS]
    finish, abnormal = run[columns.index("finish")], run[columns.index("abnormal_name")]
    return str(finish) if finish is not None else (abnormal or "").replace("競走", "")


def _entries_table(entries: list[dict[str, Any]], forms: dict[str, HorseForm], mining: dict[str, dict[int, int]],
                   *, race_day: str) -> Table:
    rows = []
    for entry in entries:
        form = forms[entry["hid"]]
        interval = (date.fromisoformat(race_day) - date.fromisoformat(form.last_run_date)).days if form.last_run_date else None
        derived = {
            "間隔(日)": interval, "近走着順": "-".join(_finish_mark(run) for run in form.runs[:FORM_RUNS]), "通算": form.career,
            **{title: ranks.get(entry["馬番"]) for title, ranks in mining.items()},
        }
        rows.append([{**entry, **derived}[header] for header in ENTRY_HEADERS])
    note = ("間隔・近走着順・通算は、この DB にある中央の確定成績（今回の開催日より前）から。地方・海外の出走は含まない。"
            "近走着順は左が前走。通算は 1着-2着-3着-着外。")
    return Table(list(ENTRY_HEADERS), rows, title="出馬表", note=note)


def _recent_table(entries: list[dict[str, Any]], forms: dict[str, HorseForm], *, runs: int, race_day: str) -> Table:
    rows = [
        [entry["馬番"], entry["馬名"], nth, *run]
        for entry in entries
        for nth, run in enumerate(forms[entry["hid"]].runs[:runs], start=1)
    ]
    columns = [*_RECENT_LEAD_HEADERS, *(title for _, title in CARD_RUN_COLUMNS)]
    note = f"各馬 {runs} 走まで（{race_day} より前）。走前 1 が前走。中央のレースだけ。"
    return Table(columns, rows, title="各馬の近走", note=note)
