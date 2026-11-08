"""WIN5 の段（Win5Job・Win5Message・Win5Schedule・Win5Slot）のテスト。取り込み・予想・計画は差し替え、元DB は合成DB だけ。値は架空。"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from 合成DB import synth

from yosou.form_aptitude_win5_tickets.tests.win5_sample import FORECAST_DAY, NO_ODDS_DAY, Win5Sample

from 今週の予想.forecast_store import ForecastStore
from 今週の予想.plan_store import PlanStore
from 今週の予想.tests.test_day_summary import WALLET
from 今週の予想.tests.test_win5_plan import DAY, LEGS, sample_win5_record, write_win5_record
from 今週の予想.win5_plan import POLICY_NOTE, Win5Plan
from 今週の予想.win5_record import Win5Record
from 今週の予想.win5_record_store import Win5RecordStore

from 発走前の通知.win5_job import Win5Job
from 発走前の通知.win5_message import Win5Message
from 発走前の通知.win5_schedule import Win5Schedule
from 発走前の通知.win5_slot import Win5Slot

SLOT = Win5Slot(DAY.isoformat(), LEGS, (datetime(2025, 4, 20, 14, 50),) + (None,) * 4)


class _Source:
    """``found`` 回目の読み出しから WIN5 が見つかる。``locked`` 回目は元DB が使用中。"""

    def __init__(self, found: int = 1, locked: tuple[int, ...] = ()) -> None:
        self._found = found
        self._locked = set(locked)
        self.reads = 0

    def read(self, day: str) -> Win5Slot | None:
        self.reads += 1
        if self.reads in self._locked:
            raise BlockingIOError("使用中")
        return SLOT if self.reads >= self._found else None


class _Fetcher:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def fetch_win5(self, day: str) -> None:
        self._calls.append(f"fetch_win5 {day}")

    def fetch_races(self, day: str, rids: tuple[str, ...]) -> None:
        self._calls.append(f"fetch_races {len(rids)}")


class _Predictor:
    """WIN5 の予想をしたことにして、記録を書く（``silent`` なら書かない）。"""

    def __init__(self, root: Path, calls: list[str], silent: bool = False) -> None:
        self._root = root
        self._calls = calls
        self._silent = silent

    def run(self, arguments: list[str], label: str, day: str) -> None:
        self._calls.append(f"predict {' '.join(arguments)}")
        if not self._silent:
            write_win5_record(self._root, sample_win5_record(made_at="2025-04-20T14:26:00"))

    def log_path(self, day: str) -> Path:
        return Path(f"WIN5-{day}.log")


class _Planner:
    def __init__(self, calls: list[str], fail: bool = False) -> None:
        self._calls = calls
        self._fail = fail

    def run_plan(self, day: str) -> None:
        self._calls.append(f"plan {day}")
        if self._fail:
            raise RuntimeError("計画に失敗")


def _job(tmp_path: Path, calls: list[str], *, source: _Source | None = None, silent: bool = False, plan_fail: bool = False) -> Win5Job:
    records = Win5RecordStore(tmp_path / "win5")
    return Win5Job(schedule=source or _Source(), fetcher=_Fetcher(calls), predictor=_Predictor(tmp_path / "win5", calls, silent),
                   planner=_Planner(calls, plan_fail), message=Win5Message(records), records=records, log=calls.append)


def test_取り込み_予想_計画の順に進めて文を作る(tmp_path: Path) -> None:
    calls: list[str] = []
    notice = _job(tmp_path, calls).build(SLOT)
    assert calls == [f"fetch_win5 {DAY}", "fetch_races 5", f"predict --date {DAY}", f"plan {DAY}"]
    assert notice.text.startswith("**WIN5（1レース目 東京10R 14:50 発走）** 中央の予想")
    assert notice.attachments == ()


def test_予想の記録が新しくならなければ失敗にする(tmp_path: Path) -> None:
    write_win5_record(tmp_path / "win5", sample_win5_record())
    with pytest.raises(RuntimeError, match="WIN5 の予想の結果が作られませんでした"):
        _job(tmp_path, [], silent=True).build(SLOT)


def test_計画の決め直しに失敗しても文は出す(tmp_path: Path) -> None:
    calls: list[str] = []
    notice = _job(tmp_path, calls, plan_fail=True).build(SLOT)
    assert "判断: **買う**" in notice.text
    assert any("買う計画の決め直しに失敗しました" in call for call in calls)


def test_WIN5が元DBに無ければその日に1回だけ速報のWIN5を取り込んで探し直す(tmp_path: Path) -> None:
    calls: list[str] = []
    job = _job(tmp_path, calls, source=_Source(found=2))
    assert job.slot(DAY.isoformat()) == SLOT
    assert calls == [f"fetch_win5 {DAY}"]
    calls.clear()
    nothing = _job(tmp_path, calls, source=_Source(found=99))
    assert nothing.slot(DAY.isoformat()) is None
    assert nothing.slot(DAY.isoformat()) is None
    assert calls == [f"fetch_win5 {DAY}"]


def test_元DBが使用中なら前に読めたWIN5で続け_まだ無ければ呼ぶ側に任せる(tmp_path: Path) -> None:
    job = _job(tmp_path, [], source=_Source(locked=(2,)))
    assert job.slot(DAY.isoformat()) == SLOT
    assert job.slot(DAY.isoformat()) == SLOT
    with pytest.raises(BlockingIOError):
        _job(tmp_path, [], source=_Source(locked=(1,))).slot(DAY.isoformat())


def test_文は判断と買い目と当たる確率と楽しむ用の1行() -> None:
    record = Win5Record.from_dict(sample_win5_record())
    text = Win5Message().describe(record, None, SLOT)
    assert text.splitlines() == [
        "**WIN5（1レース目 東京10R 14:50 発走）** 中央の予想",
        "判断: **買う**（日の期待値 1.83 ≥ 線 1.50）",
        "買い目（48点 4,800円・ポリシー用の財布から）:",
        "- 1 東京10R: 10 馬10・5 馬5・3 馬3",
        "- 2 京都10R: 6 馬6・8 馬8",
        "- 3 福島11R: 2 馬2・5 馬5",
        "- 4 東京11R: 4 馬4",
        "- 5 京都11R: 11 馬11・4 馬4・10 馬10・15 馬15",
        "当たる確率 2.1%・日の期待値 1.83・キャリーオーバー なし",
        POLICY_NOTE,
    ]
    skipped = Win5Message().describe(Win5Record.from_dict(sample_win5_record("見送り", value=1.2)), None, SLOT)
    assert "判断: **見送り**（日の期待値 1.20 < 線 1.50）" in skipped
    assert "買い目（参考。買わない。48点 4,800円）:" in skipped


def test_文は財布の計画に従う_前の予想の計画は使わない(tmp_path: Path) -> None:
    forecasts = ForecastStore(tmp_path / "今週の予想")
    record = Win5Record.from_dict(sample_win5_record())
    short = Win5Plan(DAY.isoformat(), LEGS[0], "買う", False, 48, 0, record.formation, 0.021, 1.83, 1.5, "残高が足りないので買わない")
    PlanStore(forecasts).save(DAY, [], WALLET, short)
    write_win5_record(tmp_path / "win5", sample_win5_record())
    message = Win5Message(Win5RecordStore(tmp_path / "win5"), PlanStore(forecasts))
    assert "判断: **見送り**（残高が足りないので買わない）" in message.build(SLOT).text
    stale = Win5Plan(**{**short.to_dict(), "formation": "1/1/1/1/1"})
    assert "判断: **買う**" in message.describe(record, stale, SLOT)


def test_1レース目の発走時刻から始める時刻を決める() -> None:
    assert SLOT.first_post == datetime(2025, 4, 20, 14, 50)
    assert SLOT.due_at(25) == datetime(2025, 4, 20, 14, 25)
    unknown_first = Win5Slot(DAY.isoformat(), LEGS, (None, datetime(2025, 4, 20, 15, 20), datetime(2025, 4, 20, 15, 0), None, None))
    assert unknown_first.first_post == datetime(2025, 4, 20, 15, 0)


@pytest.fixture(scope="module")
def win5_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    builder = Win5Sample()
    builder.build()
    return synth.build_db(tmp_path_factory.mktemp("win5_schedule") / "win5.duckdb", builder.sample)


def test_元DBからWIN5の対象レースと発走時刻を読む(win5_db: Path) -> None:
    slot = Win5Schedule(win5_db).read(FORECAST_DAY.isoformat())
    assert slot is not None
    assert [rid[-2:] for rid in slot.race_ids] == ["07", "08", "09", "10", "11"]
    assert slot.first_post == datetime.combine(FORECAST_DAY, datetime.min.time()) + timedelta(hours=15)
    assert Win5Schedule(win5_db).read((NO_ODDS_DAY + timedelta(days=1)).isoformat()) is None


def test_記録の置き場所は今週の予想の隣(tmp_path: Path) -> None:
    store = Win5RecordStore.beside(ForecastStore(tmp_path / "今週の予想"))
    write_win5_record(tmp_path / "近走と適性からWIN5の買い目を決める", sample_win5_record())
    assert store.load(date(2025, 4, 20)) is not None
    assert json.loads((tmp_path / "近走と適性からWIN5の買い目を決める" / "記録" / "2025-04-20.json").read_bytes())["判断"] == "買う"
