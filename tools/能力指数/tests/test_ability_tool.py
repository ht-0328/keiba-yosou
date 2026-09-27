"""能力指数の CLI の契約: 1レースのランキングを出す、過去の走の指数をとっておいて使い回す、レースの指定を確かめる。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from 能力指数 import ability

#: 合成DB の確定前のレース（2025-04-19 東京 2R 出馬表）と、確定成績のレース。
UPCOMING = "2025041905010102"


def _run(card_db: Path, cache: Path, *extra: str) -> str:
    out = cache.parent / "out.md"
    parser = ability.build_parser()
    ability.main(parser.parse_args(["--db", str(card_db), "--cache", str(cache), "--out", str(out), *extra]))
    return out.read_text(encoding="utf-8")


def test_これから走るレースのランキングを出し_過去の走の指数をとっておく(card_db: Path, tmp_path: Path):
    cache = tmp_path / "cache"
    text = _run(card_db, cache, UPCOMING, "--detail")
    assert "### 能力指数" in text and "| 順位 | 馬番 | 馬名 | 能力指数 |" in text
    assert "この走の指数" not in text                        # 確定前のレースには、その走の指数は無い
    assert "### 各馬の近5走のスピード指数" in text
    stamp = json.loads((cache / "stamp.json").read_text(encoding="utf-8"))
    assert stamp["db"].endswith("card.duckdb") and (cache / "figures.parquet").exists()
    assert _run(card_db, cache, UPCOMING) .startswith("### 能力指数")   # 2回目はとっておいたものを読む


def test_レースの指定が無ければ断る(card_db: Path, tmp_path: Path):
    with pytest.raises(ValueError):
        _run(card_db, tmp_path / "cache")
