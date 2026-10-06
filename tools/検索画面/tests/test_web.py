"""画面のサーバーの契約: API が表を返す、CSV を返す、誤りを状態で返す、よそからの POST を断る。"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import pytest

from yosou.shared.tests import synthetic_season as season
from 合成DB import synth
from 検索画面 import server


#: 出馬表のテストの「今日」。合成DB の確定前のレース（2025-04-19）の前の木曜。
CARD_TODAY = date(2025, 4, 17)


def serve(db_path: Path, **options):
    srv, session = server.make_server(db_path, port=0, idle_seconds=60, **options)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown()
        srv.server_close()
        session.close()


@pytest.fixture
def web(synth_db: Path):
    yield from serve(synth_db)


@pytest.fixture
def card_web(card_db: Path):
    yield from serve(card_db, today=lambda: CARD_TODAY)


def get(base: str, path: str, params: dict | None = None, headers: dict | None = None):
    url = base + path + ("?" + urllib.parse.urlencode(params, doseq=True) if params else "")
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read()


def post(base: str, path: str, body: dict, headers: dict | None = None):
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(base + path, data=data, method="POST", headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def test_index_info_and_meta(web: str):
    status, headers, body = get(web, "/")
    assert status == 200 and "text/html" in headers["Content-Type"] and b"keiba-yosou" in body
    status, _, body = get(web, "/api/info")
    assert status == 200 and json.loads(body)["app"] == "keiba-yosou"
    meta = json.loads(get(web, "/api/meta")[2])
    assert [f["name"] for f in meta["filters"]][:3] == ["venue", "surface", "course"]
    assert any(d["key"] == "popularity" for d in meta["dimensions"]) and meta["events"]["lost"]["pop"] == "1"


def test_runners_json_and_csv(web: str):
    status, _, body = get(web, "/api/runners", {"venue": "東京", "pop": "1"})
    table = json.loads(body)
    assert status == 200 and table["meta"]["total"] == 5 and table["columns"][-1] == "hid"
    status, headers, body = get(web, "/api/runners", {"venue": "東京", "format": "csv"})
    assert status == 200 and headers["Content-Type"].startswith("text/csv") and "attachment" in headers["Content-Disposition"]
    assert body.startswith("﻿".encode("utf-8")) and body.count(b"\n") == 26


def test_status_tables_races_horses_events_perf(web: str):
    status_data = json.loads(get(web, "/api/status")[2])
    assert status_data["status"]["columns"] == ["項目", "値"] and status_data["session"]["open"]
    tables = json.loads(get(web, "/api/tables", {"from": "2024-04-07", "to": "2024-04-07"})[2])["tables"]
    assert next(t for t in tables if t["name"] == "ra")["rows_in_range"] == 2
    rows = json.loads(get(web, "/api/tables/rows", {"name": "se", "eq": "馬番=01", "limit": "3"})[2])
    assert rows["total"] == 6 and len(rows["rows"]) == 3
    races = json.loads(get(web, "/api/races", {"venue": "中山"})[2])
    rid = races["rows"][0][-1]
    detail = json.loads(get(web, "/api/races/detail", {"rid": rid})[2])
    assert detail["header"]["競馬場"] == "中山" and [t["title"] for t in detail["tables"]][0] == "出走表・結果"
    horses = json.loads(get(web, "/api/horses", {"name": "ウマ01"})[2])
    hid = horses["rows"][0][0]
    horse = json.loads(get(web, "/api/horses/detail", {"hid": hid, "before": "2025-01-01"})[2])
    assert horse["profile"]["馬名"] == "ウマ01" and len(horse["runs"]["rows"]) == 5
    events = json.loads(get(web, "/api/events", {"kind": "lost"})[2])
    assert events["meta"]["events"] == 2
    perf = json.loads(get(web, "/api/perf", {"dimension": "popularity", "venue": "東京", "cross": "condition"})[2])
    assert perf["columns"][:3] == ["単勝人気", "芝ダ", "馬場状態"] and perf["rows"][0][3] == "4"  # 東京の芝4レース


def test_errors_are_reported_with_status(web: str):
    status, _, body = get(web, "/api/tables/rows", {"name": "nope"})
    assert status == 400 and "知らない表" in json.loads(body)["error"]
    status, _, body = get(web, "/api/runners", {"venue": "月面"})
    assert status == 400
    status, _, body = get(web, "/api/perf", {"dimension": "nope"})
    assert status == 400
    status, _, _ = get(web, "/api/nothing")
    assert status == 404
    status, _, _ = get(web, "/api/check")
    assert status in (200, 404)  # ページがあれば比べ、無ければ 404


def test_sql_get_post_and_origin_check(web: str):
    status, body = post(web, "/api/sql", {"sql": "select count(*) as n from ra", "limit": 10})
    assert status == 200 and body["rows"] == [[6]]
    status, body = post(web, "/api/sql", {"sql": "create table t (a int)"})
    assert status == 400
    status, body = post(web, "/api/sql", {"sql": "select 1"}, headers={"Origin": "http://evil.example"})
    assert status == 403
    status, headers, body = get(web, "/api/sql", {"sql": "select 1 as a", "format": "csv"})
    assert status == 200 and headers["Content-Type"].startswith("text/csv") and body.endswith(b"a\n1\n")


def test_finish_is_a_filter_for_runners_but_a_rule_for_events(web: str):
    winners = json.loads(get(web, "/api/runners", {"finish": "1"})[2])
    assert winners["meta"]["total"] == 6
    lost = json.loads(get(web, "/api/events", {"kind": "lost", "finish": "2-", "venue": "東京"})[2])
    assert lost["meta"]["population"] == 5 and lost["meta"]["events"] == 4


def test_total_dimension_gives_one_row_for_the_conditions(web: str):
    table = json.loads(get(web, "/api/perf", {"dimension": "total", "venue": "東京", "pop": "1"})[2])
    assert table["columns"] == ["全体", "出走数", "着別度数", "勝率", "連対率", "複勝率", "馬券外率", "単勝回収率", "複勝回収率"]
    assert table["rows"] == [["全体", "5", "1-1-1-2", "20.0%", "40.0%", "60.0%", "40.0%", "40.0%", "66.0%"]]
    assert table["meta"]["filters"] == "東京 1番人気"


def test_explore_api_and_meta(web: str):
    meta = json.loads(get(web, "/api/meta")[2])
    assert meta["explore"]["dimensions"][0] == "venue" and meta["explore"]["threshold"] == 100
    table = json.loads(get(web, "/api/explore", {"venue": "東京", "dimensions": "popularity,frame", "min_runs": "1", "threshold": "100"})[2])
    assert table["columns"][0] == "切り口" and any(r[0] == "単勝人気" and r[1] == "4" for r in table["rows"])
    assert table["meta"]["dimensions"] == ["popularity", "frame"] and table["meta"]["threshold"] == 1.0


def test_cards_default_to_today_and_later(card_web: str):
    status, _, body = get(card_web, "/api/cards")
    table = json.loads(body)
    assert status == 200 and table["meta"]["from"] == "2025-04-17" and table["meta"]["days"] == ["2025-04-19"]
    assert [row[table["columns"].index("状態")] for row in table["rows"]] == ["出走馬名表", "出馬表"]
    later = json.loads(get(card_web, "/api/cards", {"from": "2025-04-20"})[2])
    assert later["rows"] == [] and "まだありません" in later["note"]
    status, headers, body = get(card_web, "/api/cards", {"from": "2025-04-19", "venue": "東京", "format": "csv"})
    assert status == 200 and headers["Content-Type"].startswith("text/csv") and body.count(b"\n") == 3


def test_card_detail_json_csv_and_errors(card_web: str):
    rid = json.loads(get(card_web, "/api/cards")[2])["rows"][1][-1]
    detail = json.loads(get(card_web, "/api/cards/detail", {"rid": rid, "runs": "2"})[2])
    assert detail["header"]["状態"] == "出馬表" and detail["title"].startswith("2025-04-19（土） 東京 2R")
    assert detail["entries"]["columns"][:3] == ["枠", "馬番", "馬名"] and len(detail["entries"]["rows"]) == 6
    assert detail["recent"]["columns"][:3] == ["馬番", "馬名", "走前"] and max(r[2] for r in detail["recent"]["rows"]) == 2
    assert [no for no, _ in detail["races"]] == [1, 2] and detail["races"][1][1] == rid
    status, headers, body = get(card_web, "/api/cards/detail", {"rid": rid, "part": "recent", "runs": "1", "format": "csv"})
    assert status == 200 and headers["Content-Type"].startswith("text/csv") and body.count(b"\n") == 6  # 見出し + 過去走のある5頭
    assert get(card_web, "/api/cards/detail", {"rid": rid, "part": "nope", "format": "csv"})[0] == 400
    assert get(card_web, "/api/cards/detail", {"rid": "2025041905010112"})[0] == 400
    assert json.loads(get(card_web, "/api/meta")[2])["card"] == {"runs": 5, "max_runs": 20}


def test_version_is_reported_and_matches_page(web: str):
    info = json.loads(get(web, "/api/info")[2])
    meta = json.loads(get(web, "/api/meta")[2])
    page = get(web, "/")[2].decode("utf-8")
    assert info["version"] == server.APP_VERSION == meta["version"]
    assert f'const PAGE_VERSION = "{server.APP_VERSION}";' in page


def test_shutdown_stops_server_only_from_local_origin(synth_db: Path):
    srv, session = server.make_server(synth_db, port=0, idle_seconds=60)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        status, body = post(base, "/api/shutdown", {}, headers={"Origin": "http://evil.example"})
        assert status == 403 and thread.is_alive()
        status, body = post(base, "/api/shutdown", {})
        assert status == 200 and body["stopped"] is True
        thread.join(timeout=10)
        assert not thread.is_alive()
    finally:
        srv.server_close()
        session.close()


@pytest.fixture
def trend_web(trend_db: Path, tmp_path: Path):
    yield from serve(trend_db, today=lambda: CARD_TODAY, ability_cache=tmp_path / "ability-cache")


def test_trend_json_csv_and_errors(trend_web: str):
    rid = "2025041905010102"  # 2025-04-19 東京 2R 出馬表
    loose = {"rid": rid, "condition": "良", "min_runs": "3", "min_z": "0"}
    status, _, body = get(trend_web, "/api/trend", loose)
    data = json.loads(body)
    assert status == 200 and data["horses"][0]["no"] == 4 and data["inputs"]["condition"] == "良" and data["options"]["min_runs"] == 3
    assert [no for no, _ in data["races"]] == [1, 2] and "人気" in data["missing"] and data["counts"] == {"plus": 89, "minus": 75}
    status, headers, body = get(trend_web, "/api/trend", {**loose, "part": "ranking", "format": "csv"})
    assert status == 200 and headers["Content-Type"].startswith("text/csv") and body.count(b"\n") == 7  # 見出し + 6頭
    assert get(trend_web, "/api/trend", {**loose, "part": "nope", "format": "csv"})[0] == 400
    assert get(trend_web, "/api/trend", {**loose, "pops": "99:1"})[0] == 400        # このレースにいない馬番
    assert get(trend_web, "/api/trend", {**loose, "pops": "x"})[0] == 400
    assert get(trend_web, "/api/trend", {"rid": "2030010105010101"})[0] == 400      # 無いレース
    assert get(trend_web, "/api/trend", {**loose, "scope": "nope"})[0] == 400
    meta = json.loads(get(trend_web, "/api/meta")[2])["trend"]
    assert [level["key"] for level in meta["levels"]] == ["same", "match4", "match3", "match2"] and meta["parts"][0] == "ranking"
    after = json.loads(get(trend_web, "/api/runners", {"venue": "東京"})[2])             # 採点のあとも、ほかの API は動く
    assert after["meta"]["total"] == 30  # 6レース × 出走5頭


def test_static_parts_are_served_by_name_only(web: str):
    status, headers, body = get(web, "/static/trend.js")
    assert status == 200 and "javascript" in headers["Content-Type"] and b"window.TrendView" in body
    assert get(web, "/static/index.html")[0] == 404 and get(web, "/static/../server.py")[0] == 404
    assert '<script src="/static/trend.js"></script>' in get(web, "/")[2].decode("utf-8")


def test_ability_json_csv_and_errors(trend_web: str):
    rid = "2025041905010102"  # 2025-04-19 東京 2R 出馬表
    status, _, body = get(trend_web, "/api/ability", {"rid": rid, "condition": "良"})
    data = json.loads(body)
    assert status == 200 and data["ranking"]["columns"][:4] == ["順位", "馬番", "馬名", "能力指数"]
    assert len(data["ranking"]["rows"]) == 6 and [no for no, _ in data["races"]] == [1, 2]
    assert data["history"]["columns"][-1] == "スピード指数"
    status, headers, body = get(trend_web, "/api/ability", {"rid": rid, "part": "ranking", "format": "csv"})
    assert status == 200 and headers["Content-Type"].startswith("text/csv") and body.count(b"\n") == 7  # 見出し + 6頭
    assert get(trend_web, "/api/ability", {"rid": rid, "part": "nope", "format": "csv"})[0] == 400
    assert get(trend_web, "/api/ability", {"rid": rid, "condition": "晴"})[0] == 400


@pytest.fixture
def stakes_web(tmp_path: Path):
    """月の最初の土曜に重賞「テスト記念」（G3・特別競走番号 9001）がある、架空の1シーズンの合成DB。"""
    yield from serve(synth.build_db(tmp_path / "season.duckdb", season.SeasonBuilder().build()))


def test_stakes_list_detail_csv_and_errors(stakes_web: str):
    table = json.loads(get(stakes_web, "/api/stakes")[2])
    assert [row[:3] for row in table["rows"]] == [["9001", "G3", "テスト記念"]]
    status, headers, _ = get(stakes_web, "/api/stakes", {"format": "csv"})
    assert status == 200 and headers["Content-Type"].startswith("text/csv")
    detail = json.loads(get(stakes_web, "/api/stakes/detail", {"no": "9001"})[2])
    assert detail["stakes_name"] == "テスト記念" and detail["markdown"].startswith("# テスト記念（G3）の攻略ポイント")
    by_name = json.loads(get(stakes_web, "/api/stakes/detail", {"name": "テスト", "before": "2024-06-01"})[2])
    assert by_name["stakes_no"] == "9001" and by_name["markdown"] != detail["markdown"]
    assert get(stakes_web, "/api/stakes/detail", {"no": "0000"})[0] == 400
    assert get(stakes_web, "/api/stakes", {"before": "2000-01-01"})[0] == 400


def test_overview_counts_races_and_forecasts(card_db: Path, tmp_path: Path):
    from datetime import datetime

    from 今週の予想.forecast_store import ForecastStore
    from 今週の予想.tests.test_forecast_store import sample_forecast

    store = ForecastStore(tmp_path / "forecasts")
    gen = serve(card_db, today=lambda: CARD_TODAY, forecasts=store, now=lambda: datetime(2025, 4, 19, 9, 0), store_url="http://127.0.0.1:1/",
                local_db=tmp_path / "no-nvdata.duckdb", local_store_url="http://127.0.0.1:1/")
    base = next(gen)
    try:
        cards = json.loads(get(base, "/api/cards", {"from": "2025-04-19"})[2])
        store.save(sample_forecast(cards["rows"][1][-1]))
        data = json.loads(get(base, "/api/overview")[2])
        assert data["day"] == "2025-04-19" and data["days"] == ["2025-04-19"] and data["db_error"] is None
        summary, days, races, sync, local_days, local_sync, models = data["tables"]
        items = dict(summary["rows"])
        assert summary["title"] == "今の状況" and items["中央: jvdata-store の画面"].startswith("止まっている（応答なし。")
        assert items["地方: DB のファイル"].startswith("無い") and local_days["title"].startswith("地方:") and local_days["rows"] == []
        assert days["rows"][0][:4] == ["2025-04-19", "土", "東京", 2]
        verdicts = [row[races["columns"].index("判定")] for row in races["rows"]]
        # 合成DB にオッズは無いので今の時点は木曜。前日の時点で作ってある予想は、後ろには戻さない
        assert verdicts == ["未予想", "最新（予想は前日の時点。今の DB の材料は木曜まで）"] and races["rows"][1][races["columns"].index("印")] == "◎3"
        past = json.loads(get(base, "/api/overview", {"date": "2024-04-06"})[2])
        assert past["day"] == "2024-04-06" and len(past["tables"][2]["rows"]) == 3
        status, _, body = get(base, "/api/overview", {"date": "x"})
        assert status == 400 and "error" in json.loads(body)
        # 短い読み取りのあとも、ほかの API は今までどおり動く
        assert json.loads(get(base, "/api/status")[2])["session"]["open"]
    finally:
        next(gen, None)


def test_forecasts_list_saved_and_detail(card_db: Path, tmp_path: Path):
    from 今週の予想.forecast_store import ForecastStore
    from 今週の予想.tests.test_forecast_store import sample_forecast

    store = ForecastStore(tmp_path / "forecasts")
    gen = serve(card_db, today=lambda: CARD_TODAY, forecasts=store)
    base = next(gen)
    try:
        cards = json.loads(get(base, "/api/cards")[2])
        first, second = (row[-1] for row in cards["rows"])
        store.save(sample_forecast(second))
        listed = json.loads(get(base, "/api/forecasts")[2])
        assert list(listed["saved"]) == [second] and listed["saved"][second]["marks"] == "◎3"
        assert listed["legend"]["marks"]["消"].startswith("危険な人気馬") and listed["legend"]["marks"]["－"].startswith("無印")
        assert "能力" in listed["legend"]["categories"]
        detail = json.loads(get(base, "/api/forecast", {"rid": second})[2])
        assert detail["forecast"]["horses"][0]["mark"] == "◎" and detail["title"].startswith("2025-04-19（土） 東京 2R")
        assert detail["forecast"]["tickets"][1]["label"] == "3→1→8"  # 買い目もそのまま渡す
        assert json.loads(get(base, "/api/forecast", {"rid": first})[2])["forecast"] is None
        # 予想し直すのは、この画面からの POST だけ
        status, _ = post(base, "/api/forecast/run", {"rid": first}, headers={"Origin": "http://evil.example"})
        assert status == 403
    finally:
        next(gen, None)
