"""LocalUpsetFile（券種ごとの中荒れ以上の確率のファイル）と SavedUpsetProbabilities（推奨買目へ渡す）のテスト。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 発走前の通知.local_forecast_store import LocalForecastStore
from 発走前の通知.local_upset_file import LocalUpsetFile
from 発走前の通知.saved_upset_probabilities import SavedUpsetProbabilities

RID = "2026110754100109"


def test_書いた確率を_要る券種だけ読む(tmp_path: Path) -> None:
    path = tmp_path / "日" / f"{RID}.荒れ具合.json"
    file = LocalUpsetFile()
    file.write(path, {"単勝": 0.4, "3連複": 0.61})
    assert file.read(path, ["3連複"]) == {"3連複": 0.61}


def test_理由が書いてあれば_ValueError_に理由を入れる(tmp_path: Path) -> None:
    path = tmp_path / f"{RID}.荒れ具合.json"
    file = LocalUpsetFile()
    file.write_reason(path, "1番人気の馬体重がまだ DB にありません。速報を取り込んでください")
    with pytest.raises(ValueError, match="馬体重"):
        file.read(path, ["3連複"])


def test_無いファイルと_無い券種と_消したあと(tmp_path: Path) -> None:
    path = tmp_path / f"{RID}.荒れ具合.json"
    file = LocalUpsetFile()
    with pytest.raises(FileNotFoundError):
        file.read(path, ["3連複"])
    file.write(path, {"単勝": 0.4})
    with pytest.raises(LookupError, match="3連複"):
        file.read(path, ["3連複"])
    file.clear(path)
    file.clear(path)  # 無くても失敗しない
    assert not path.exists()


def test_推奨買目には_レースの置き場所のファイルを読んで渡す(tmp_path: Path) -> None:
    store = LocalForecastStore(tmp_path)
    LocalUpsetFile().write(store.upset_path(RID), {"3連複": 0.72})
    assert SavedUpsetProbabilities(store).of(None, RID, ["3連複"]) == {"3連複": 0.72}
