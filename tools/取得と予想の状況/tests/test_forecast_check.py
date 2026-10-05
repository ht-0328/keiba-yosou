"""予想の判定（``ForecastCheck``）のテスト。DB は使わず、材料の有無（``RaceSignals``）と予想の結果の JSON を直接組む。"""

from __future__ import annotations

from pathlib import Path

from 共通.race_signals import RaceSignals
from 取得と予想の状況.forecast_check import ForecastCheck
from 取得と予想の状況.verdict_kind import VerdictKind
from 今週の予想.forecast_store import ForecastStore
from 今週の予想.forecast_version import FORECAST_VERSION
from 今週の予想.tests.test_forecast_store import sample_forecast

RID = "2025041905010102"


def signals(*, stage: str = "2", odds_at: str | None = "04191000", odds_count: int = 6, weighed: int = 0, going: bool = False) -> RaceSignals:
    return RaceSignals(rid=RID, race_date="2025-04-19", venue_code="05", venue="東京", race_no=2, post_time="15:00", race_name="合成特別",
                       class_name="1勝クラス", course="芝・左", stage=stage, stage_name="出馬表", entries=6, numbered=6, weighed=weighed,
                       going="良" if going else "未発表", going_announced=going, odds_announced_at=odds_at, odds_count=odds_count)


def saved(store: ForecastStore, *, timing: str = "前日", made_at: str = "2025-04-19T11:00:00", version: int = FORECAST_VERSION) -> None:
    forecast = sample_forecast(RID)
    forecast.update({"timing": timing, "made_at": made_at, "version": version})
    store.save(forecast)


def test_予想が無ければ未予想(tmp_path: Path) -> None:
    verdict = ForecastCheck(ForecastStore(tmp_path)).check(signals())
    assert verdict.kind is VerdictKind.MISSING and not verdict.is_saved and verdict.current_timing == "前日" and verdict.label == "未予想"


def test_同じ時点で新しければ最新(tmp_path: Path) -> None:
    store = ForecastStore(tmp_path)
    saved(store)
    verdict = ForecastCheck(store).check(signals())
    assert verdict.kind is VerdictKind.FRESH and verdict.saved_timing == "前日" and verdict.marks == "◎3" and verdict.expectation == "高"
    assert verdict.made_at.isoformat() == "2025-04-19T11:00:00" and not verdict.kind.needs_redo


def test_馬体重と馬場状態が出ると時点が進んだ(tmp_path: Path) -> None:
    store = ForecastStore(tmp_path)
    saved(store)
    verdict = ForecastCheck(store).check(signals(weighed=4, going=True))
    assert verdict.kind is VerdictKind.TIMING_ADVANCED and verdict.current_timing == "当日" and "前日 → 当日" in verdict.label
    assert verdict.kind.needs_redo and verdict.kind.tone == "redo"


def test_先の時点で作った予想は_DBが追いついていなくても最新のまま(tmp_path: Path) -> None:
    store = ForecastStore(tmp_path)
    saved(store, timing="当日")
    verdict = ForecastCheck(store).check(signals())
    assert verdict.kind is VerdictKind.FRESH and verdict.detail == "予想は当日の時点。今の DB の材料は前日まで"


def test_作り方の版が違えば作り方が古い(tmp_path: Path) -> None:
    store = ForecastStore(tmp_path)
    saved(store, version=FORECAST_VERSION - 1)
    verdict = ForecastCheck(store).check(signals())
    assert verdict.kind is VerdictKind.VERSION_OLD and f"版 {FORECAST_VERSION - 1} → {FORECAST_VERSION}" in verdict.detail


def test_予想のあとに新しいオッズが入るとオッズが新しい(tmp_path: Path) -> None:
    store = ForecastStore(tmp_path)
    saved(store, made_at="2025-04-19T09:30:00")
    verdict = ForecastCheck(store).check(signals(odds_at="04191000"))
    assert verdict.kind is VerdictKind.ODDS_NEWER and "10:00 発表" in verdict.detail


def test_終わったレースと中止のレースは判定しない(tmp_path: Path) -> None:
    store = ForecastStore(tmp_path)
    saved(store)
    check = ForecastCheck(store)
    assert check.check(signals(stage="7")).kind is VerdictKind.FINISHED
    assert check.check(signals(stage="9")).kind is VerdictKind.CANCELLED
    missing = ForecastCheck(ForecastStore(tmp_path / "empty")).check(signals(stage="7"))
    assert missing.kind is VerdictKind.MISSING and missing.detail == "終了したレース"
