"""傾向スコアの検証の契約: 終わったレースを順に採点し、点数の順位別・人気の順位別の成績を数える。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 傾向スコア import backtest
from 共通 import db, trend, trend_backtest
from 共通.filters import Filters

LOOSE = trend.Options(min_runs=3, min_z=0.0)


def test_counts_results_by_score_rank_and_popularity_rank(trend_db: Path):
    """いつも馬番4（4番人気）が勝つ6レース。傾向が付く4レース目からは、点数1位が勝ち馬になる。"""
    with db.open_db(trend_db) as con:
        rids = trend_backtest.race_ids(con, Filters.from_mapping({"from": "2024-04-06", "to": "2024-05-11"}))
        seen: list[tuple[int, int]] = []
        result = trend_backtest.run(con, rids, LOOSE, progress=lambda done, total, _: seen.append((done, total)))
    assert len(rids) == 6 and result.races == 6 and result.skipped == 0 and seen[-1] == (6, 6)
    assert (result.first_date, result.last_date) == ("2024-04-06", "2024-05-11")
    summary, by_score, by_popularity, by_band, crossed = result.tables()
    top = next(row for row in by_score.rows if row[0] == "1位")
    assert top[1] == "6" and int(top[2].split("-")[0]) >= 3            # 点数1位は6頭、うち3勝以上
    favourite = next(row for row in by_popularity.rows if row[0] == "1位")
    assert favourite[1:3] == ["6", "0-0-0-6"]                          # 1番人気はいつも4着
    assert sum(int(row[1]) for row in by_band.rows) == 30 and {row[1] for row in crossed.rows} <= {"1〜3番人気", "4〜6番人気"}


def test_sample_thins_races_and_market_items_can_be_dropped(trend_db: Path):
    with db.open_db(trend_db) as con:
        assert len(trend_backtest.race_ids(con, Filters(), sample=3)) == 3
        assert trend_backtest.race_ids(con, Filters.from_mapping({"venue": "中山"})) == []
    kept = trend_backtest.without_market()
    assert {factor.group for factor in kept} == {1, 2, 3, 4, 5, 6, 7}


def test_cli_writes_tables_and_requires_a_start_date(trend_db: Path, tmp_path: Path):
    out = tmp_path / "backtest.md"
    parser = backtest.build_parser()
    backtest.main(parser.parse_args(["--db", str(trend_db), "--from", "2024-04-27", "--min-runs", "3", "--min-z", "0", "--out", str(out)]))
    text = out.read_text(encoding="utf-8")
    assert "### 点数の順位別の成績" in text and "| 採点したレース | 3（2024-04-27〜2024-05-11） |" in text and "2024-04-27〜" in text
    with pytest.raises(ValueError):
        backtest.main(parser.parse_args(["--db", str(trend_db)]))
    with pytest.raises(LookupError):
        backtest.main(parser.parse_args(["--db", str(trend_db), "--from", "2030-01-01"]))
