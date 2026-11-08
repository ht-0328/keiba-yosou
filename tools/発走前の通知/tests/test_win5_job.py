"""WIN5 の段（Win5Job・Win5Message・Win5Schedule・Win5Slot・DatabaseSnapshot・FigureCacheCopy・BackgroundProgram）のテスト。
取り込み・裏の予想は差し替え、元DB は合成DB と一時ファイルだけ。値は架空。"""

from __future__ import annotations

import json
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from 共通.db_lock import DatabaseLock
from 合成DB import synth

from yosou.form_aptitude_win5_tickets.tests.win5_sample import FORECAST_DAY, NO_ODDS_DAY, Win5Sample

from 今週の予想.forecast_store import ForecastStore
from 今週の予想.tests.test_win5_plan import DAY, LEGS, _wallet, sample_win5_record, write_win5_record
from 今週の予想.win5_plan import POLICY_NOTE
from 今週の予想.win5_planner import Win5Planner
from 今週の予想.win5_record import Win5Record
from 今週の予想.win5_record_store import Win5RecordStore

from 発走前の通知.background_program import BackgroundProgram
from 発走前の通知.database_snapshot import SNAPSHOT_NAME, DatabaseSnapshot
from 発走前の通知.figure_cache_copy import FOLDER_NAME, FigureCacheCopy
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


class _Snapshot:
    def __init__(self, root: Path, calls: list[str]) -> None:
        self._root = root
        self._calls = calls

    def take(self, day: str) -> Path:
        self._calls.append(f"snapshot {day}")
        return self._root / day / SNAPSHOT_NAME

    def remove(self, day: str) -> None:
        self._calls.append(f"remove {day}")


class _Figures:
    def copy(self, snapshot_db: Path) -> Path:
        return snapshot_db.parent / FOLDER_NAME


class _Background:
    """裏の予想の代わり。``start`` で引数を覚え、``finish`` を呼ぶと終わったことになる（``writes`` なら記録を書く）。"""

    def __init__(self, root: Path, calls: list[str], *, writes: bool = True, returncode: int = 0) -> None:
        self._root = root
        self._calls = calls
        self._writes = writes
        self._code = returncode
        self.done = False
        self.killed = False

    def start(self, arguments: list[str], label: str, day: str) -> None:
        self._calls.append(f"background {' '.join(arguments)}")

    def finish(self) -> None:
        if self._writes:
            write_win5_record(self._root, sample_win5_record(made_at="2025-04-20T14:26:00"))
        self.done = True

    def finished(self) -> bool:
        return self.done

    @property
    def returncode(self) -> int | None:
        return self._code if self.done else None

    def tail(self) -> str:
        return "Traceback\nLookupError: オッズが無い"

    def kill(self) -> None:
        self.killed = True

    def log_path(self, day: str) -> Path:
        return Path(f"WIN5-{day}.log")


def _job(tmp_path: Path, calls: list[str], *, source: _Source | None = None, background: _Background | None = None) -> Win5Job:
    records = Win5RecordStore(tmp_path / "win5")
    return Win5Job(schedule=source or _Source(), fetcher=_Fetcher(calls), snapshot=_Snapshot(tmp_path / "snap", calls), figures=_Figures(),
                   predictor=background or _Background(tmp_path / "win5", calls), message=Win5Message(records), records=records,
                   log=calls.append)


def test_始めるときは取り込みと元DBの写しだけを済ませ_予想は写しに向けて裏で始める(tmp_path: Path) -> None:
    calls: list[str] = []
    background = _Background(tmp_path / "win5", calls)
    job = _job(tmp_path, calls, background=background)
    job.start(SLOT)
    snapshot = tmp_path / "snap" / DAY.isoformat() / SNAPSHOT_NAME
    assert calls == [f"fetch_win5 {DAY}", "fetch_races 5", f"snapshot {DAY}",
                     f"background --date {DAY} --db {snapshot} --figure-cache {snapshot.parent / FOLDER_NAME}"]
    assert not job.finished()
    background.finish()
    assert job.finished()
    notice = job.build(SLOT)
    assert calls[-1] == f"remove {DAY}"
    assert notice.text.startswith("**WIN5（1レース目 東京10R 14:50 発走）** 中央の予想")


def test_裏の予想が失敗したら記録の最後を添えて失敗にする(tmp_path: Path) -> None:
    calls: list[str] = []
    failed = _Background(tmp_path / "win5", calls, writes=False, returncode=1)
    job = _job(tmp_path, calls, background=failed)
    job.start(SLOT)
    failed.finish()
    with pytest.raises(RuntimeError, match="WIN5 の予想に失敗しました") as failure:
        job.build(SLOT)
    assert str(failure.value).endswith("LookupError: オッズが無い")


def test_予想の記録が新しくならなければ失敗にする(tmp_path: Path) -> None:
    write_win5_record(tmp_path / "win5", sample_win5_record())
    calls: list[str] = []
    silent = _Background(tmp_path / "win5", calls, writes=False)
    job = _job(tmp_path, calls, background=silent)
    job.start(SLOT)
    silent.finish()
    with pytest.raises(RuntimeError, match="WIN5 の予想の結果が作られませんでした"):
        job.build(SLOT)


def test_止めると裏の予想を止めて写しを消す(tmp_path: Path) -> None:
    calls: list[str] = []
    background = _Background(tmp_path / "win5", calls)
    job = _job(tmp_path, calls, background=background)
    job.start(SLOT)
    job.cancel()
    assert background.killed and calls[-1] == f"remove {DAY}"


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


def test_文の財布の判断は買う計画と同じ決まりでその場で出す(tmp_path: Path) -> None:
    write_win5_record(tmp_path / "win5", sample_win5_record())
    _, short = _wallet(tmp_path, policy=3_000)
    text = Win5Message(Win5RecordStore(tmp_path / "win5"), Win5Planner(short)).build(SLOT).text
    assert "判断: **見送り**（日の期待値 1.83 ≥ 線 1.50 だが、ポリシー用の財布の残高 3,000円 が代金 4,800円 に足りないので買わない）" in text
    (tmp_path / "enough").mkdir()
    _, enough = _wallet(tmp_path / "enough")
    assert "判断: **買う**（日の期待値 1.83 ≥ 線 1.50 なので、ポリシー用の財布から買う）" in \
        Win5Message(Win5RecordStore(tmp_path / "win5"), Win5Planner(enough)).build(SLOT).text


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


def test_元DBの写しはロックを取って作り_使用中なら待ってやり直す側に任せる(win5_db: Path, tmp_path: Path) -> None:
    snapshot = DatabaseSnapshot(win5_db, tmp_path / "写し", lock_timeout=0.2)
    copied = snapshot.take(FORECAST_DAY.isoformat())
    assert copied == tmp_path / "写し" / FORECAST_DAY.isoformat() / SNAPSHOT_NAME
    assert Win5Schedule(copied).read(FORECAST_DAY.isoformat()) is not None
    snapshot.remove(FORECAST_DAY.isoformat())
    assert not copied.parent.exists()
    holder = DatabaseLock(win5_db)
    assert holder.acquire(timeout=1)
    try:
        with pytest.raises(BlockingIOError, match="使用中"):
            snapshot.take(FORECAST_DAY.isoformat())
    finally:
        holder.release()


def test_スピード指数のとっておきは写しの隣に写し_印の場所だけ写しにする(tmp_path: Path) -> None:
    source = tmp_path / "cache"
    source.mkdir()
    (source / "figures.parquet").write_bytes(b"PAR1")
    (source / "stamp.json").write_text(json.dumps({"db": "C:/元DB/jvdata.duckdb", "latest": "2025-04-13", "settings": "s"}), encoding="utf-8")
    snapshot_db = tmp_path / "写し" / "2025-04-20" / SNAPSHOT_NAME
    snapshot_db.parent.mkdir(parents=True)
    copied = FigureCacheCopy(source).copy(snapshot_db)
    assert (copied / "figures.parquet").read_bytes() == b"PAR1"
    stamp = json.loads((copied / "stamp.json").read_bytes())
    assert stamp == {"db": str(snapshot_db.resolve()), "latest": "2025-04-13", "settings": "s"}
    assert json.loads((source / "stamp.json").read_text(encoding="utf-8"))["db"] == "C:/元DB/jvdata.duckdb"
    assert not any(FigureCacheCopy(tmp_path / "無い").copy(snapshot_db.parent / "other" / SNAPSHOT_NAME).iterdir())


class _Process:
    """``subprocess.Popen`` の代わり。``polls`` 回目の ``poll`` で終わる。"""

    def __init__(self, polls: int, code: int = 0) -> None:
        self._polls = polls
        self._code = code
        self.returncode: int | None = None
        self.killed = False

    def poll(self) -> int | None:
        self._polls -= 1
        if self._polls <= 0:
            self.returncode = self._code
        return self.returncode

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9

    def wait(self) -> int:
        return self.returncode or 0


def test_裏の処理は待たずに始め_終わったかを確かめ_止められる(tmp_path: Path) -> None:
    launched: list[list[str]] = []
    process = _Process(polls=2, code=0)

    def popen(command, **options):
        launched.append(list(command))
        assert options["stderr"] is subprocess.STDOUT
        options["stdout"].write("進み具合\n")
        return process

    program = BackgroundProgram(program=("python", "-m", "yosou.form_aptitude_win5_tickets", "predict"), project=Path("proj"),
                                log_folder=tmp_path, log_name="WIN5-", popen=popen, uv="uv", now=lambda: datetime(2025, 4, 20, 14, 25),
                                log=lambda _: None)
    assert program.finished()
    program.start(["--date", "2025-04-20"], "WIN5 の予想", "2025-04-20")
    assert launched == [["uv", "run", "--project", "proj", "python", "-m", "yosou.form_aptitude_win5_tickets", "predict", "--date", "2025-04-20"]]
    assert not program.finished()
    assert program.finished() and program.returncode == 0
    assert "# WIN5 の予想（2025-04-20 14:25。裏の処理）" in (tmp_path / "WIN5-2025-04-20.log").read_text(encoding="utf-8")
    assert program.tail().endswith("進み具合")
    slow = _Process(polls=99)
    program = BackgroundProgram(program=("python",), project=Path("proj"), log_folder=tmp_path, popen=lambda command, **_: slow, uv="uv",
                                log=lambda _: None)
    program.start([], "WIN5 の予想", "2025-04-20")
    program.kill()
    assert slow.killed and program.finished()


def test_記録の置き場所は今週の予想の隣(tmp_path: Path) -> None:
    store = Win5RecordStore.beside(ForecastStore(tmp_path / "今週の予想"))
    write_win5_record(tmp_path / "近走と適性からWIN5の買い目を決める", sample_win5_record())
    assert store.load(date(2025, 4, 20)) is not None
