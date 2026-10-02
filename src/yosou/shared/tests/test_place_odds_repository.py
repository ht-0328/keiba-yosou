"""複勝オッズ（最低・最高）を読むリポジトリ（既存モデルの修正計画の 2「3着以内と複勝的中」）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import db, keys
from 合成DB import synth

from ..repository import PlaceOddsRepository, TargetScope

#: 複勝オッズの子の表。
_PLACE = "o1__複勝オッズ"


def _race_id(race_row: dict[str, str]) -> str:
    return "".join(race_row[name] for name in keys.RACE_KEY)


@pytest.fixture(scope="module")
def odds_db(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    """1レースに、締め切り前の断面（データ区分 1）と確定の断面（データ区分 5）の複勝オッズを入れた合成DB。"""
    sample = synth.simple_race()
    race_row = sample.ra[0]
    early = "04061200"
    sample.odds += [
        ("o1", synth.odds_header(race_row, "o1", stage="1", announced=early)),
        ("o1", synth.odds_header(race_row, "o1", stage="5")),
        (_PLACE, synth.range_odds_row(race_row, _PLACE, "01", 11, 13, announced=early)),
        (_PLACE, synth.range_odds_row(race_row, _PLACE, "01", 12, 15, seq=1)),
        (_PLACE, synth.range_odds_row(race_row, _PLACE, "04", 30, 45, seq=2)),
        (_PLACE, synth.range_odds_row(race_row, _PLACE, "06", 0, 0, seq=3)),
    ]
    path = synth.build_db(tmp_path_factory.mktemp("place-odds") / "odds.duckdb", sample)
    return path, _race_id(race_row)


def test_reads_the_final_place_odds_when_the_race_is_over(odds_db: tuple[Path, str]):
    path, race_id = odds_db
    with db.open_db(path) as con:
        odds = PlaceOddsRepository(con).read(TargetScope(f"(SELECT '{race_id}' AS race_id)"))
    by_horse = odds.set_index("horse_no")
    # 確定の断面（1.2〜1.5倍）を使い、締め切り前の断面（1.1〜1.3倍）は使わない。無投票（0）は欠損値
    assert by_horse.loc[1, "place_odds_low"] == pytest.approx(1.2)
    assert by_horse.loc[1, "place_odds_high"] == pytest.approx(1.5)
    assert by_horse.loc[4, "place_odds_low"] == pytest.approx(3.0)
    assert by_horse.loc[6, ["place_odds_low", "place_odds_high"]].isna().all()


def test_reads_nothing_when_the_db_has_no_odds_tables(tmp_path: Path):
    path = synth.build_db(tmp_path / "no-odds.duckdb", synth.simple_race())
    with db.open_db(path) as con:
        odds = PlaceOddsRepository(con).read(TargetScope("(SELECT 'x' AS race_id)"))
    assert odds.empty and list(odds.columns) == ["race_id", "horse_no", "place_odds_low", "place_odds_high"]
