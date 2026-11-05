"""LocalForecastStore（地方の predict の JSON の置き場所）のテスト。"""

from __future__ import annotations

from pathlib import Path

from 発走前の通知.local_forecast_store import LocalForecastStore


def test_開催日のフォルダに_rid_の_json_を置き_無ければ_None(tmp_path: Path) -> None:
    store = LocalForecastStore(tmp_path)
    rid = "2026110547150401"
    assert store.path(rid) == tmp_path / "2026-11-05" / f"{rid}.json"
    assert store.saved_at(rid) is None
    assert store.load(rid) is None
    store.path(rid).parent.mkdir(parents=True)
    store.path(rid).write_text('{"title": "t", "columns": [], "rows": []}', encoding="utf-8")
    assert store.saved_at(rid) is not None
    assert store.load(rid) == {"title": "t", "columns": [], "rows": []}
