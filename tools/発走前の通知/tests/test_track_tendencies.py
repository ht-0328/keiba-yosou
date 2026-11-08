"""TrackTendencies（先に終わった同じ芝ダのレースから馬場の傾向を出す）のテスト。架空の元DB のファイルを作る。"""

from __future__ import annotations

from pathlib import Path

import duckdb

from 発走前の通知.position_counts import PositionCounts
from 発走前の通知.tests.test_venue_run_repository import make_tables
from 発走前の通知.track_tendencies import TrackTendencies

#: 4頭立て（位置は 0・1/3・2/3・1）で、1〜3着が4コーナー 1〜3番手（前・中・中）。
_FRONT_WIN = [(1, "01", "01"), (2, "02", "02"), (3, "03", "03"), (4, "04", "04")]
#: 4頭立てで、1〜3着が4コーナー 4・3・2番手（後ろ・中・中）。
_BACK_WIN = [(1, "04", "01"), (2, "03", "02"), (3, "02", "03"), (4, "01", "04")]


def _db(tmp_path: Path) -> Path:
    path = tmp_path / "jvdata.duckdb"
    with duckdb.connect(str(path)) as con:
        make_tables(con, [
            ("08", "20261108", 1, "17", _FRONT_WIN),                        # 今日の芝
            ("08", "20261108", 2, "24", _FRONT_WIN),                        # 今日のダート
            ("08", "20261108", 3, "17", [(1, "00", "00"), (2, "00", "00")]),  # 今日の芝。これから走る
            ("08", "20251108", 1, "17", _BACK_WIN),                         # 1年前の芝（いつもの割合）
            ("08", "20201108", 1, "17", _FRONT_WIN),                        # 3年より前（数えない）
        ])
    return path


def test_先に終わった同じ芝ダのレースと_いつもの割合で傾向を出す(tmp_path: Path) -> None:
    tendency = TrackTendencies(_db(tmp_path)).of("2026110808050203", "京都")
    assert tendency is not None
    assert (tendency.venue, tendency.surface) == ("京都", "芝")
    assert tendency.today == PositionCounts(races=1, top3=3, front=1, middle=2, back=0)
    assert tendency.usual == PositionCounts(races=1, top3=3, front=0, middle=2, back=1)


def test_その日の最初のレースとDBに無いレースは出さない(tmp_path: Path) -> None:
    tendencies = TrackTendencies(_db(tmp_path))
    assert tendencies.of("2026110808050201", "京都") is None      # その日の最初のレース
    assert tendencies.of("2026110808050299", "京都") is None      # DB に無いレース


def test_先に走った同じ芝ダのレースが無ければ_このレースが最初と言う(tmp_path: Path) -> None:
    tendency = TrackTendencies(_db(tmp_path)).of("2026110808050202", "京都")      # その日の最初のダート
    assert tendency is not None
    assert tendency.text() == "馬場 京都・ダート: 今日のダートはこのレースが最初"


def _waiting_db(tmp_path: Path) -> Path:
    path = tmp_path / "jvdata.duckdb"
    with duckdb.connect(str(path)) as con:
        make_tables(con, [
            ("08", "20261108", 1, "17", _FRONT_WIN),                                  # 芝。通過順まで届いた
            ("08", "20261108", 2, "17", [(1, "01", "00"), (2, "02", "00"), (3, "03", "00")]),  # 芝。着順だけ（通過順の速報待ち）
            ("08", "20261108", 3, "10", [(1, "01", "00"), (2, "02", "00"), (3, "03", "00")]),  # 芝の直線（通過順が付かない）
            ("08", "20261108", 4, "17", [(1, "00", "00")]),                            # 芝。これから走る
            ("08", "20251108", 1, "17", _BACK_WIN),
        ])
    return path


def test_通過順の速報待ちのレースは数えずに番号を言う_直線のコースは待たない(tmp_path: Path) -> None:
    tendency = TrackTendencies(_waiting_db(tmp_path)).of("2026110808050204", "京都")
    assert tendency is not None
    assert tendency.today.races == 1 and tendency.waiting == (2,)
    assert tendency.text().endswith("。2R は通過順の速報待ちで数えていない")


def test_先に走った同じ芝ダのレースがどれも速報待ちなら_まだ出せないと言う(tmp_path: Path) -> None:
    path = tmp_path / "jvdata.duckdb"
    with duckdb.connect(str(path)) as con:
        make_tables(con, [
            ("08", "20261108", 1, "24", _FRONT_WIN),                                  # ダート
            ("08", "20261108", 2, "17", [(1, "01", "00"), (2, "02", "00")]),           # 芝。通過順の速報待ち
            ("08", "20261108", 3, "17", [(1, "00", "00")]),                            # 芝。これから走る
        ])
    tendency = TrackTendencies(path).of("2026110808050203", "京都")
    assert tendency is not None
    assert tendency.text() == "馬場 京都・芝: 2R の通過順の速報がまだ届いていないので、まだ出せない"
