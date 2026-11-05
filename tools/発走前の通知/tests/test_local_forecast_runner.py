"""LocalForecastRunner（地方の predict を動かす）のテスト。predict は動かさず、呼ばれた引数を覚える偽のプロセスを使う。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 発走前の通知.local_forecast_runner import LocalForecastRunner
from 発走前の通知.local_forecast_store import LocalForecastStore

RID = "2026110547150401"
WEIGHT_MISSING = "エラー: 馬体重がまだ DB にありません。馬体重の発表のあとに realtime で速報を取り込んでください。"


class _Process:
    def __init__(self, fail_first: str | None = None) -> None:
        self.calls: list[list[str]] = []
        self._fail_first = fail_first

    def run(self, arguments: list[str], label: str, day: str) -> None:
        self.calls.append(list(arguments))
        if self._fail_first and len(self.calls) == 1:
            raise RuntimeError(f"{label}に失敗しました:\n{self._fail_first}")

    def log_path(self, day: str) -> Path:
        return Path(f"logs/地方-{day}.log")


def test_当日の時点で予想し_結果は開催日のフォルダの_json(tmp_path: Path) -> None:
    process = _Process()
    runner = LocalForecastRunner(store=LocalForecastStore(tmp_path), process=process, log=lambda _: None)
    runner.run_race(RID, "2026-11-05")
    assert process.calls == [[RID, "--timing", "当日", "--format", "json", "--out", str(tmp_path / "2026-11-05" / f"{RID}.json")]]
    assert (tmp_path / "2026-11-05").is_dir()
    assert runner.log_path("2026-11-05") == Path("logs/地方-2026-11-05.log")


def test_馬体重がまだ無ければ前日の時点で予想し直す(tmp_path: Path) -> None:
    process = _Process(fail_first=WEIGHT_MISSING)
    logs: list[str] = []
    LocalForecastRunner(store=LocalForecastStore(tmp_path), process=process, log=logs.append).run_race(RID, "2026-11-05")
    assert [call[2] for call in process.calls] == ["当日", "前日"]
    assert any("前日の時点" in line for line in logs)


def test_馬体重以外の失敗はそのまま伝える(tmp_path: Path) -> None:
    process = _Process(fail_first="ValueError: モデルがありません")
    with pytest.raises(RuntimeError, match="モデルがありません"):
        LocalForecastRunner(store=LocalForecastStore(tmp_path), process=process, log=lambda _: None).run_race(RID, "2026-11-05")
    assert len(process.calls) == 1


def test_朝の全レースの予想は何もしない(tmp_path: Path) -> None:
    process = _Process()
    logs: list[str] = []
    LocalForecastRunner(store=LocalForecastStore(tmp_path), process=process, log=logs.append).run_day("2026-11-05")
    assert process.calls == []
    assert logs and "地方" in logs[0]
