"""検索画面のサーバー。標準ライブラリだけで、JSON の API と静的な ``index.html`` を返す。

API はすべて読むだけ。表を返す API は ``format=csv`` で CSV（BOM 付き）も返す。
絞り込みのパラメータ名は CLI のフラグ名と同じ（``共通.filters.FILTER_FIELDS``）。
"""

from __future__ import annotations

import json
import sys
import threading
import time
import webbrowser
from collections.abc import Callable
from dataclasses import asdict
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import browse, card, events, explore, facts, horse, perf, race, render, runners, trend, trend_html  # noqa: E402
from 共通.filters import FILTER_FIELDS, Filters  # noqa: E402
from 成績集計 import check  # noqa: E402
from 検索画面.session import DbSession  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
DEFAULT_PORT = 8767
APP_NAME = "keiba-yosou"
#: API の版。画面（index.html の PAGE_VERSION）と合わないときは、古いサーバーが動いていると分かる。API を変えたら両方を上げる。
APP_VERSION = "5"
#: 古い版のサーバーを止めて入れ替えるとき、ポートが空くのを待つ上限（秒）。
_REPLACE_TIMEOUT_SECONDS = 10.0
#: 画面が1度に出す行数の上限。
MAX_LIMIT = 1000
#: 出馬表の CSV で選べる表（``RaceCard`` の属性名）。
_CARD_PARTS: tuple[str, ...] = ("entries", "recent")
#: 傾向スコアの CSV で選べる表（``TrendReport`` のメソッド名）。
_TREND_PARTS: dict[str, str] = {"ranking": "ranking_table", "highlights": "highlight_table", "breakdown": "breakdown_table"}
#: 画面に配る部品（``共通/static`` のファイル名 → 種類）。ここに無い名前は配らない。
_STATIC_FILES: dict[str, str] = {"trend.js": "text/javascript; charset=utf-8"}
#: 誤りの種類と HTTP の状態。
_STATUS_OF: tuple[tuple[type[BaseException], int], ...] = (
    (BlockingIOError, 409), (TimeoutError, 408), (FileNotFoundError, 404), (LookupError, 400), (ValueError, 400),
)


def _first(query: dict[str, list[str]], name: str, default: str = "") -> str:
    return query.get(name, [default])[0]


def _int(query: dict[str, list[str]], name: str, default: int, *, low: int = 0, high: int = MAX_LIMIT) -> int:
    try:
        return max(low, min(int(_first(query, name, str(default))), high))
    except ValueError:
        raise ValueError(f"{name} は整数で指定してください") from None


def _float(query: dict[str, list[str]], name: str, default: float) -> float:
    try:
        return float(_first(query, name, str(default)))
    except ValueError:
        raise ValueError(f"{name} は数で指定してください") from None


def _flat(query: dict[str, list[str]]) -> dict[str, str]:
    return {name: values[0] for name, values in query.items() if values}


def _race_card(con: Any, query: dict[str, list[str]]) -> card.RaceCard:
    """``rid`` と ``runs``（近走の走数）から1レースの出馬表を作る。"""
    return card.race_card(con, _first(query, "rid"), runs=_int(query, "runs", card.DEFAULT_RUNS, high=card.MAX_RUNS))


def table_dict(table: render.Table) -> dict[str, Any]:
    """表を JSON にできる辞書にする。"""
    return {"title": table.title, "columns": table.columns, "rows": table.rows, "note": table.note, "meta": table.meta}


class Backend:
    """API の中身。1つの ``DbSession`` を使い回す。``today`` は「今日以降の出馬表」の基準日（テストで差し替える）。"""

    def __init__(self, session: DbSession, today: Callable[[], date] = date.today) -> None:
        self.session = session
        self.today = today

    def info(self) -> dict[str, Any]:
        return {"app": APP_NAME, "version": APP_VERSION, "db": str(self.session.path), "session": self.session.state()}

    def meta(self) -> dict[str, Any]:
        """画面がフォームを作るための目録。"""
        return {
            "version": APP_VERSION,
            "filters": [asdict(field) for field in FILTER_FIELDS],
            "dimensions": [{"key": d.name, "title": d.title, "note": d.note} for d in perf.DIMENSIONS.values()],
            "rank_keys": list(perf.RANK_KEYS), "sorts": list(runners.SORTS),
            "events": {kind: {"label": label, "pop": rule.pop.text() if rule.pop else "", "odds": rule.odds.text() if rule.odds else "",
                              "finish": rule.finish.text()} for kind, label in events.KINDS.items() for rule in (events.DEFAULTS[kind],)},
            "fact_columns": facts.FACT_COLUMNS,
            "limits": {"rows": browse.WEB_MAX_ROWS, "columns": browse.MAX_COLUMNS, "max_limit": MAX_LIMIT},
            "check": {"describe": f"{check.CHECK_SECTION} {check.CHECK_LABEL}番人気", "to": check.CHECK_DATE_TO},
            "explore": {"dimensions": list(explore.DEFAULT_DIMENSIONS), "min_runs": explore.DEFAULT_MIN_RUNS,
                        "threshold": explore.DEFAULT_THRESHOLD * 100, "targets": explore.TARGETS,
                        "max_pair_dimensions": explore.MAX_PAIR_DIMENSIONS, "top": explore.DEFAULT_TOP},
            "card": {"runs": card.DEFAULT_RUNS, "max_runs": card.MAX_RUNS},
            "trend": {"levels": [{"key": level.key, "title": level.title} for level in trend.LEVELS], "min_runs": trend.MIN_RUNS,
                      "good": trend.GOOD_RATIO, "bad": trend.BAD_RATIO, "min_z": trend.MIN_Z, "parts": list(_TREND_PARTS)},
        }

    def explore(self, query: dict[str, list[str]]) -> render.Table:
        names: list[str] = []
        for text in query.get("dimensions", []):
            names.extend(text.split(","))
        filters = Filters.from_mapping({k: v for k, v in _flat(query).items() if k not in ("dimensions",)})
        threshold = float(_first(query, "threshold", str(explore.DEFAULT_THRESHOLD * 100))) / 100
        with self.session.use() as con:
            return explore.explore(con, filters, names or None, min_runs=_int(query, "min_runs", explore.DEFAULT_MIN_RUNS, high=10_000_000),
                                   threshold=threshold, target=_first(query, "target", explore.DEFAULT_TARGET),
                                   pairs=_first(query, "pairs") == "1", top=_int(query, "top", explore.DEFAULT_TOP, low=1, high=10_000))

    def status(self) -> dict[str, Any]:
        with self.session.use() as con:
            status = browse.db_status(con, self.session.path)
            return {"status": table_dict(browse.status_table(status)), "years": table_dict(browse.year_counts(con)),
                    "session": self.session.state()}

    def tables(self, query: dict[str, list[str]]) -> dict[str, Any]:
        with self.session.use() as con:
            infos = browse.TableBrowser(con).list_tables(_first(query, "from") or None, _first(query, "to") or None)
        return {"tables": [asdict(info) for info in infos]}

    def table_rows(self, query: dict[str, list[str]]) -> dict[str, Any]:
        equals = {}
        for text in query.get("eq", []):
            equals.update(browse.parse_equals([text]))
        with self.session.use() as con:
            return browse.TableBrowser(con).read(
                _first(query, "name"), limit=_int(query, "limit", 50, low=1, high=browse.WEB_MAX_ROWS),
                offset=_int(query, "offset", 0, high=10_000_000), column_offset=_int(query, "column_offset", 0, high=1000),
                date_from=_first(query, "from") or None, date_to=_first(query, "to") or None, equals=equals or None,
            )

    def table_columns(self, query: dict[str, list[str]]) -> render.Table:
        with self.session.use() as con:
            return browse.TableBrowser(con).describe(_first(query, "name"))

    def races(self, query: dict[str, list[str]]) -> render.Table:
        with self.session.use() as con:
            return race.list_races(con, Filters.from_mapping(_flat(query)), limit=_int(query, "limit", 200, low=1),
                                   offset=_int(query, "offset", 0, high=10_000_000))

    def race_detail(self, query: dict[str, list[str]]) -> dict[str, Any]:
        with self.session.use() as con:
            detail = race.race_detail(con, _first(query, "rid"))
        return {"header": detail.header, "title": detail.title(), "tables": [table_dict(t) for t in detail.tables()[1:]]}

    def cards(self, query: dict[str, list[str]]) -> render.Table:
        """出馬表のあるレース。開始日を省くと今日以降。"""
        with self.session.use() as con:
            return card.list_cards(con, date_from=_first(query, "from") or self.today().isoformat(), date_to=_first(query, "to") or None,
                                   venue=_first(query, "venue") or None, limit=_int(query, "limit", card.DEFAULT_LIST_LIMIT, low=1))

    def card_detail(self, query: dict[str, list[str]]) -> dict[str, Any]:
        with self.session.use() as con:
            detail = _race_card(con, query)
            races = card.same_day_races(con, _first(query, "rid"))
        return {"header": detail.header, "title": detail.title(), "entries": table_dict(detail.entries),
                "recent": table_dict(detail.recent), "races": races}

    def card_table(self, query: dict[str, list[str]]) -> render.Table:
        """出馬表の表を1つ（CSV 用）。``part`` は ``entries``（出馬表）か ``recent``（各馬の近走）。"""
        part = _first(query, "part", _CARD_PARTS[0])
        if part not in _CARD_PARTS:
            raise ValueError(f"part は {', '.join(_CARD_PARTS)} のどれかです: {part}")
        with self.session.use() as con:
            return getattr(_race_card(con, query), part)

    def _trend_report(self, query: dict[str, list[str]]) -> trend.TrendReport:
        """``rid`` と、手で与える材料（``condition`` ``pops`` ``weights``）・線引きから採点する。"""
        inputs = trend.ManualInputs.parse(condition=_first(query, "condition") or None, popularity=_first(query, "pops") or None,
                                          weights=_first(query, "weights") or None)
        options = trend.Options(
            scope=_first(query, "scope") or None, min_runs=_int(query, "min_runs", trend.MIN_RUNS, low=1, high=10_000_000),
            good=_float(query, "good", trend.GOOD_RATIO), bad=_float(query, "bad", trend.BAD_RATIO), min_z=_float(query, "min_z", trend.MIN_Z),
        )
        with self.session.use() as con:
            return trend.score_race(con, _first(query, "rid"), inputs, options)

    def trend(self, query: dict[str, list[str]]) -> dict[str, Any]:
        """傾向スコア（画面のグラフ用）。同じ日・同じ競馬場のレースも添える。"""
        data = self._trend_report(query).to_dict()
        with self.session.use() as con:
            data["races"] = card.same_day_races(con, _first(query, "rid"))
        return data

    def trend_table(self, query: dict[str, list[str]]) -> render.Table:
        """傾向スコアの表を1つ（CSV 用）。``part`` は ``ranking`` ``highlights`` ``breakdown``。"""
        part = _first(query, "part", "ranking")
        if part not in _TREND_PARTS:
            raise ValueError(f"part は {', '.join(_TREND_PARTS)} のどれかです: {part}")
        return getattr(self._trend_report(query), _TREND_PARTS[part])()

    def horses(self, query: dict[str, list[str]]) -> render.Table:
        with self.session.use() as con:
            return horse.find_horses(con, _first(query, "name"), limit=_int(query, "limit", 50, low=1))

    def horse_detail(self, query: dict[str, list[str]]) -> dict[str, Any]:
        with self.session.use() as con:
            hid = _first(query, "hid")
            profile = horse.horse_profile(con, hid)
            runs = horse.horse_runs(con, hid, limit=_int(query, "limit", 50, low=1), before=_first(query, "before") or None)
        return {"profile": profile, "runs": table_dict(runs)}

    def runners(self, query: dict[str, list[str]]) -> render.Table:
        with self.session.use() as con:
            return runners.search_runners(con, Filters.from_mapping(_flat(query)), limit=_int(query, "limit", 200, low=1),
                                          offset=_int(query, "offset", 0, high=10_000_000), sort=_first(query, "sort", runners.DEFAULT_SORT))

    def events(self, query: dict[str, list[str]]) -> render.Table:
        rule = events.rule_from(_first(query, "kind", "lost"), pop=_first(query, "pop") or None,
                                odds=_first(query, "odds") or None, finish=_first(query, "finish") or None)
        # pop・odds・finish は事象の規則。絞り込み（分母）には使わない。
        filters = Filters.from_mapping({k: v for k, v in _flat(query).items() if k not in events.RULE_FIELDS})
        with self.session.use() as con:
            return events.search_events(con, rule, filters, limit=_int(query, "limit", 200, low=1),
                                        offset=_int(query, "offset", 0, high=10_000_000))

    def perf(self, query: dict[str, list[str]]) -> render.Table:
        dim = perf.dimension(_first(query, "dimension", "popularity"))
        crosses = [perf.dimension(name) for name in query.get("cross", []) if name]
        if crosses:
            dim = perf.cross(dim, *crosses)
        if _first(query, "by_popularity") == "1":
            dim = perf.by_popularity(dim)
        filters = Filters.from_mapping(_flat(query))
        top = _int(query, "top", 0, high=10_000) or None
        min_runs = _int(query, "min_runs", -1, low=-1, high=10_000_000)
        with self.session.use() as con:
            rows = perf.perf_rows(con, dim, filters, top=top, min_runs=None if min_runs < 0 else min_runs,
                                  rank_by=_first(query, "rank_by", perf.DEFAULT_RANK_KEY))
            cover = perf.coverage(con, filters, dim)
        return perf.perf_table(rows, dim, filters, cover)

    def check(self, query: dict[str, list[str]]) -> render.Table:
        with self.session.use() as con:
            result = check.run_check(con, date_to=_first(query, "to") or check.CHECK_DATE_TO)
        return check.check_table(result)

    def sql(self, sql: str, limit: int, timeout: float) -> render.Table:
        with self.session.use() as con:
            return browse.run_sql(con, sql, limit=limit, timeout_s=timeout)


def make_handler(backend: Backend) -> type[BaseHTTPRequestHandler]:
    """API の経路とサーバーを結ぶ Handler。"""

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args: Any) -> None:  # 画面の操作ごとにコンソールへ出さない
            pass

        def _send(self, body: bytes, content_type: str, status: int = 200, extra: dict[str, str] | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for name, value in (extra or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, data: Any, status: int = 200) -> None:
            self._send(json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"), "application/json; charset=utf-8", status)

        def _table(self, table: render.Table, query: dict[str, list[str]], filename: str) -> None:
            if _first(query, "format") == "csv":
                body = ("﻿" + render.to_csv(table)).encode("utf-8")
                self._send(body, "text/csv; charset=utf-8", extra={"Content-Disposition": f'attachment; filename="{filename}.csv"'})
                return
            self._json(table_dict(table))

        def _fail(self, error: BaseException) -> None:
            for kind, status in _STATUS_OF:
                if isinstance(error, kind):
                    return self._json({"error": str(error)}, status)
            return self._json({"error": f"{type(error).__name__}: {error}"}, 500)

        def do_GET(self) -> None:
            url = urlparse(self.path)
            query = parse_qs(url.query, keep_blank_values=False)
            try:
                self._route_get(url.path, query)
            except Exception as error:  # noqa: BLE001  画面に理由を返し、サーバは止めない
                self._fail(error)

        def _route_get(self, path: str, query: dict[str, list[str]]) -> None:
            if path in ("/", "/index.html"):
                return self._send((STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
            if path.startswith("/static/") and path.removeprefix("/static/") in _STATIC_FILES:
                name = path.removeprefix("/static/")
                return self._send((trend_html.STATIC_DIR / name).read_bytes(), _STATIC_FILES[name])
            if path == "/api/info":
                return self._json(backend.info())
            if path == "/api/meta":
                return self._json(backend.meta())
            if path == "/api/status":
                return self._json(backend.status())
            if path == "/api/tables":
                return self._json(backend.tables(query))
            if path == "/api/tables/rows":
                return self._json(backend.table_rows(query))
            if path == "/api/tables/columns":
                return self._table(backend.table_columns(query), query, "columns")
            if path == "/api/races":
                return self._table(backend.races(query), query, "races")
            if path == "/api/races/detail":
                return self._json(backend.race_detail(query))
            if path == "/api/cards":
                return self._table(backend.cards(query), query, "cards")
            if path == "/api/cards/detail":
                if _first(query, "format") == "csv":
                    return self._table(backend.card_table(query), query, "card")
                return self._json(backend.card_detail(query))
            if path == "/api/trend":
                if _first(query, "format") == "csv":
                    return self._table(backend.trend_table(query), query, "trend")
                return self._json(backend.trend(query))
            if path == "/api/horses":
                return self._table(backend.horses(query), query, "horses")
            if path == "/api/horses/detail":
                return self._json(backend.horse_detail(query))
            if path == "/api/runners":
                return self._table(backend.runners(query), query, "runners")
            if path == "/api/events":
                return self._table(backend.events(query), query, "events")
            if path == "/api/perf":
                return self._table(backend.perf(query), query, "perf")
            if path == "/api/check":
                return self._table(backend.check(query), query, "check")
            if path == "/api/explore":
                return self._table(backend.explore(query), query, "explore")
            if path == "/api/sql":
                return self._table(backend.sql(_first(query, "sql"), _int(query, "limit", browse.WEB_MAX_ROWS, low=1),
                                               float(_first(query, "timeout", str(browse.DEFAULT_TIMEOUT_SECONDS)))), query, "sql")
            return self._json({"error": "not found"}, 404)

        def do_POST(self) -> None:
            url = urlparse(self.path)
            if not _is_local_request(self.headers, self.server.server_address[1]):
                return self._json({"error": "この画面以外からの操作は受け付けません。"}, 403)
            try:
                if url.path == "/api/shutdown":
                    # 新しい版の起動が、古い版を止めて入れ替えるために使う。応答を返してから止める
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return self._json({"stopped": True, "version": APP_VERSION})
                if url.path != "/api/sql":
                    return self._json({"error": "not found"}, 404)
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"{}")
                table = backend.sql(str(body.get("sql", "")), max(1, min(int(body.get("limit", browse.WEB_MAX_ROWS)), MAX_LIMIT)),
                                    float(body.get("timeout", browse.DEFAULT_TIMEOUT_SECONDS)))
                return self._json(table_dict(table))
            except Exception as error:  # noqa: BLE001
                self._fail(error)

    return Handler


def _is_local_request(headers: Any, port: int) -> bool:
    """この画面（127.0.0.1 / localhost の同じポート）から来た操作か。よそのサイトからの横取りを断つ。"""
    host = headers.get("Host", "")
    if host not in (f"127.0.0.1:{port}", f"localhost:{port}"):
        return False
    origin = headers.get("Origin")
    return origin is None or origin == f"http://{host}"


class _Server(ThreadingHTTPServer):
    allow_reuse_address = False
    daemon_threads = True


def make_server(db_path: Path, port: int = DEFAULT_PORT, *, idle_seconds: float = 60.0,
                today: Callable[[], date] = date.today) -> tuple[_Server, DbSession]:
    """サーバーとセッションを作る（起動はしない）。テストは ``port=0`` で空きポートを使い、``today`` で基準日を固定する。"""
    session = DbSession(db_path, idle_seconds=idle_seconds)
    server = _Server(("127.0.0.1", port), make_handler(Backend(session, today)))
    return server, session


def _running_info(url: str) -> dict[str, Any] | None:
    """そのポートで動いている自分の画面の情報。自分の画面でなければ None。"""
    try:
        with urlopen(url + "api/info", timeout=2) as response:
            info = json.load(response)
    except Exception:  # noqa: BLE001  応答が読めなければ別の画面
        return None
    return info if info.get("app") == APP_NAME else None


def _replace_old_server(url: str, port: int) -> bool:
    """古い版の画面に止まるよう頼み、ポートが空くのを待つ。空いたら True。"""
    host = f"127.0.0.1:{port}"
    request = Request(url + "api/shutdown", method="POST", headers={"Host": host, "Origin": f"http://{host}"})
    try:
        urlopen(request, timeout=3).read()
    except Exception:  # noqa: BLE001  古すぎて止め方を知らない版
        return False
    deadline = time.monotonic() + _REPLACE_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if _running_info(url) is None:
            return True
        time.sleep(0.3)
    return False


def serve(db_path: Path, port: int = DEFAULT_PORT, open_browser: bool = False, *, idle_seconds: float = 60.0) -> None:
    """画面を起動して待ち受ける。Ctrl+C で止まる。

    同じポートに同じ版の自分の画面があれば、それを開くだけ。古い版が動いていれば止めて入れ替える。
    """
    url = f"http://127.0.0.1:{port}/"
    try:
        server, session = make_server(db_path, port, idle_seconds=idle_seconds)
    except OSError as error:
        info = _running_info(url)
        if info is None:
            raise SystemExit(f"ポート {port} は別の画面で使用中です。--port で変えてください。") from error
        if info.get("version") == APP_VERSION:
            print(f"起動済みの画面: {url}")
            if open_browser:
                webbrowser.open(url)
            return
        print(f"古い版の画面（版 {info.get('version', '?')}）が動いています。止めて入れ替えます。", flush=True)
        if not _replace_old_server(url, port):
            raise SystemExit("古い画面を止められませんでした。その黒い窓を閉じてから、もう一度起動してください。") from error
        server, session = make_server(db_path, port, idle_seconds=idle_seconds)
    print(f"keiba-yosou 検索画面: {url}", flush=True)
    print(f"元DB: {db_path}\n終了するには Ctrl+C", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        session.close()
    print("停止しました。", flush=True)
