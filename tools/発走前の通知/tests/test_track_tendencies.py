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


def test_先に終わった同じ芝ダのレースが無ければ出さない(tmp_path: Path) -> None:
    tendencies = TrackTendencies(_db(tmp_path))
    assert tendencies.of("2026110808050201", "京都") is None      # その日の最初の芝
    assert tendencies.of("2026110808050202", "京都") is None      # その日の最初のダート
    assert tendencies.of("2026110808050299", "京都") is None      # DB に無いレース
