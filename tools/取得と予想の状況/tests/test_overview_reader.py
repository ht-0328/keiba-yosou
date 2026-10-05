"""取得と予想の状況をまとめる部品（``OverviewReader``）と表（``OverviewTables``）のテスト。合成DB と一時フォルダの予想・モデルで確かめる。"""

from __future__ import annotations

import contextlib
import functools
from datetime import datetime
from pathlib import Path

from 共通 import db
from 共通.render import Table
from 共通.tests.test_race_signals import CARD_RID, NAME_LIST_RID, build
from 取得と予想の状況.local_store_reader import LocalStoreReader
from 取得と予想の状況.model_file_scanner import ModelFileScanner
from 取得と予想の状況.overview_reader import OverviewReader
from 取得と予想の状況.overview_tables import (
    DAYS_TITLE, LOCAL_DAYS_TITLE, LOCAL_SYNC_TITLE, MODELS_TITLE, RACES_TITLE, SUMMARY_TITLE, SYNC_TITLE, VERDICT_COLUMN, OverviewTables,
)
from 取得と予想の状況.store_screen_probe import LOCAL_STORE_APP, StoreScreenProbe
from 取得と予想の状況.tests.test_local_store_reader import local_db
from 取得と予想の状況.tests.test_store_screen_probe import CLOSED_URL
from 今週の予想.forecast_store import ForecastStore
from 今週の予想.tests.test_forecast_store import sample_forecast

#: 合成DB の確定前のレースの日の朝。
RACE_MORNING = datetime(2025, 4, 19, 9, 0, 0)


def make_models(root: Path) -> Path:
    for folder in ("thursday", "1着/race_day"):
        (root / folder).mkdir(parents=True)
        (root / folder / "settings.json").write_text("{}", encoding="utf-8")
        (root / folder / "lightgbm.joblib").write_bytes(b"x")
    return root


def make_reader(path: Path, tmp_path: Path, *, now: datetime = RACE_MORNING, connect=None,
                local_path: Path | None = None) -> tuple[OverviewReader, ForecastStore]:
    """中央は ``path``、地方は ``local_path``（省くと地方の合成DB を作る）。"""
    store = ForecastStore(tmp_path / "forecasts")
    scanner = ModelFileScanner([("全頭", make_models(tmp_path / "models")), ("人気馬", tmp_path / "none")])
    local = LocalStoreReader(local_path or local_db(tmp_path / "nv.duckdb"), StoreScreenProbe(CLOSED_URL, LOCAL_STORE_APP, timeout=0.5))
    reader = OverviewReader(connect=connect or functools.partial(db.open_db, path), db_path=path, forecasts=store, now=lambda: now,
                           probe=StoreScreenProbe(CLOSED_URL, timeout=0.5), scanner=scanner, local=local)
    return reader, store


def summary_value(table: Table, item: str) -> str:
    return next(row[1] for row in table.rows if row[0] == item)


def test_今日のレースを数えて_予想の判定を付ける(tmp_path: Path) -> None:
    reader, store = make_reader(build(tmp_path / "a.duckdb", odds=True), tmp_path)
    store.save(sample_forecast(CARD_RID))  # 前日の予想（前日 20:00 作成）。DB には当日 10:00 のオッズが入っている
    overview = reader.read()
    assert overview.db_error is None and overview.day == "2025-04-19" and overview.results.races == 6 and overview.results.last_date == "2025-04-12"
    assert [record.dataspec for record in overview.sync_records] == ["RACE"] and overview.sync_records[0].fetched_at == datetime(2026, 9, 12)
    (day,) = overview.days
    acquired = day.acquisition
    assert (acquired.races, acquired.name_lists, acquired.cards, acquired.with_odds, acquired.weighed) == (2, 1, 1, 1, 0)
    assert (day.forecasted, day.fresh, day.redo, day.missing) == (1, 0, 1, 1)
    assert overview.races[1].verdict.kind.value == "オッズが新しい"
    assert acquired.venues == ("東京",) and acquired.latest_odds_at == datetime(2025, 4, 19, 10, 0) and day.timing_text() == "前日 1"
    assert [status.signals.rid for status in overview.races] == [NAME_LIST_RID, CARD_RID]
    assert overview.next_race.signals.rid == NAME_LIST_RID  # 15:00 発走の2レースのうち、並びの先
    assert [model.relative for model in overview.models] == ["1着/race_day", "thursday"] and overview.missing_model_roots == ["人気馬"]
    assert not overview.store.running and overview.db_file.exists
    assert overview.local.days[0].venues == ("大井",) and overview.local.results.races == 1  # 地方も同じ1回の確認で読む


def test_表にすると判定と要約が並ぶ(tmp_path: Path) -> None:
    reader, store = make_reader(build(tmp_path / "b.duckdb", odds=True, weights=True, going=True), tmp_path)
    store.save(sample_forecast(CARD_RID))  # 前日の予想のまま、DB は当日の材料まで入った
    tables = OverviewTables().tables(reader.read())
    titles = [SUMMARY_TITLE, DAYS_TITLE, f"{RACES_TITLE}: 2025-04-19（土）", SYNC_TITLE, LOCAL_DAYS_TITLE, LOCAL_SYNC_TITLE, MODELS_TITLE]
    assert [table.title for table in tables] == titles
    summary, days, races, sync, local_days, local_sync, models = tables
    assert summary_value(summary, "中央: DB の読み取り") == "読めた" and summary_value(summary, "中央: jvdata-store の画面").startswith("止まっている")
    assert summary_value(summary, "中央: 確定成績") == "2024-04-06 〜 2025-04-12（6 レース）"
    assert summary_value(summary, "中央: 今日以降のレース") == "2 レース: 2025-04-19（土）2"
    assert summary_value(summary, "中央: 次の発走").startswith("東京 1R 15:00（あと6時間0分）")
    assert summary_value(summary, "中央: 学習済みモデル").startswith("2 個")
    assert summary_value(summary, "地方: nvdata-store の画面").startswith("止まっている") and summary_value(summary, "地方: DB の読み取り") == "読めた"
    assert summary_value(summary, "地方: 確定成績") == "2025-04-12 〜 2025-04-12（1 レース）"
    assert summary_value(summary, "地方: 今日以降のレース") == "1 レース: 2025-04-19（土）1"
    assert local_days.rows == [["2025-04-19", "土", "大井", 1, 1, 0, 0, 0, "", 0]]
    assert local_sync.rows[0][:2] == ["RACE", "レース情報（出馬表・成績・払戻・オッズ）"]
    assert days.rows[0][:4] == ["2025-04-19", "土", "東京", 2] and days.rows[0][-3:] == [0, 1, 1]
    verdict_at, timing_at = races.columns.index(VERDICT_COLUMN), races.columns.index("今の時点")
    assert [row[verdict_at] for row in races.rows] == ["未予想", "時点が進んだ（前日 → 当日。予想し直すと当日のモデルになる）"]
    assert [row[timing_at] for row in races.rows] == ["木曜", "当日"] and races.rows[1][races.columns.index("印")] == "◎3"
    assert sync.rows[0][:2] == ["RACE", "レース情報"] and models.rows[0][0] == "全頭" and "人気馬" in models.note


def test_開催日を指定すると過去の日でも読み_今日にレースが無ければ次の開催日(tmp_path: Path) -> None:
    reader, _ = make_reader(build(tmp_path / "c.duckdb"), tmp_path, now=datetime(2025, 4, 17, 12, 0))
    overview = reader.read()
    assert overview.day == "2025-04-19" and overview.next_race is None and len(overview.races) == 2
    assert OverviewTables().summary(overview).rows[6] == ["中央: 次の発走", "今日はレースが無い"]
    past = reader.read("2024-04-06")
    assert past.day == "2024-04-06" and len(past.races) == 3 and all(status.verdict.kind.value == "未予想" for status in past.races)
    assert all(status.verdict.detail == "終了したレース" for status in past.races)
    nothing = reader.read("2030-01-01")
    assert nothing.races == [] and "無い" in OverviewTables().races(nothing).note


def test_DBが取得中で開けなくても_ほかの項目は出す(tmp_path: Path) -> None:
    @contextlib.contextmanager
    def busy():
        raise BlockingIOError("DB を別の画面（jvdata-store の取得など）で使用中です。")
        yield  # noqa: unreachable  文脈管理の形を保つため

    reader, _ = make_reader(build(tmp_path / "d.duckdb"), tmp_path, connect=busy)
    overview = reader.read()
    assert overview.db_error.startswith("DB を別の画面") and overview.days == [] and overview.results is None
    summary = OverviewTables().summary(overview)
    assert summary_value(summary, "中央: DB の読み取り").startswith("読めない")
    assert summary_value(summary, "中央: 今日以降のレース") == "（DB を読めていない）"
    assert len(overview.models) == 2 and summary_value(summary, "地方: DB の読み取り") == "読めた"  # 中央が読めなくても地方は出す


def test_地方のDBが無ければ地方の行にそう出す(tmp_path: Path) -> None:
    reader, _ = make_reader(build(tmp_path / "e.duckdb"), tmp_path, local_path=tmp_path / "none.duckdb")
    summary = OverviewTables().summary(reader.read())
    assert summary_value(summary, "地方: DB のファイル").startswith("無い")
    assert summary_value(summary, "地方: DB の読み取り") == "（DB のファイルが無い）"
