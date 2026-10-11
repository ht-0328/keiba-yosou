"""展開スコアの CLI の契約: 表 G を見る、表 G をとっておく、レースの指定を確かめる。合成DB だけを使う（展開のモデルは要らない）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 展開スコア import development_score


def _run(card_db: Path, cache: Path, *extra: str) -> str:
    out = cache.parent / "out.md"
    parser = development_score.build_parser()
    development_score.main(parser.parse_args(["--db", str(card_db), "--cache", str(cache), "--out", str(out), *extra]))
    return out.read_text(encoding="utf-8")


def test_表Gを競馬場と芝ダごとに出し_とっておいたものを使い回す(card_db: Path, tmp_path: Path):
    cache = tmp_path / "cache"
    text = _run(card_db, cache, "--table", "--venue", "東京", "--surface", "芝", "--detail")
    assert "### 表 G: 東京・芝" in text and "| 脚質 | スロー | 平均 | ハイ |" in text
    assert text.count("| 逃げ |") == 1 and "（" in text                       # 件数の括弧
    assert (cache / "表G.pkl").exists() and (cache / "stamp.json").exists()
    everything = _run(card_db, cache, "--table")                               # 2回目はとっておいたものを読む
    assert everything.count("### 表 G:") >= 1


def test_レースの指定が無ければ断る(card_db: Path, tmp_path: Path):
    with pytest.raises(ValueError):
        _run(card_db, tmp_path / "cache")
    with pytest.raises(ValueError):
        _run(card_db, tmp_path / "cache", "--all")
