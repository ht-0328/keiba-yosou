"""重賞の攻略ポイントの部品（CLI と検索画面が使う）を、合成DB の架空の重賞「テスト記念」で確かめる。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from 共通 import db  # noqa: E402
from 合成DB import synth  # noqa: E402
from 重賞攻略.guide import StakesGuide  # noqa: E402

from yosou.shared.tests import synthetic_season as season  # noqa: E402


@pytest.fixture(scope="module")
def season_db(tmp_path_factory) -> Path:
    """月の最初の土曜に重賞「テスト記念」（G3・特別競走番号 9001）がある、架空の1シーズン。"""
    return synth.build_db(tmp_path_factory.mktemp("guide_season") / "season.duckdb", season.SeasonBuilder().build())


def test_list_and_page_of_the_fictional_stakes(season_db):
    with db.open_db(season_db) as con:
        guide = StakesGuide.load(con)
    table = guide.list_table()
    assert [row[:3] for row in table.rows] == [["9001", "G3", "テスト記念"]]
    assert guide.choose(None, "テスト") == "9001"
    built = guide.page("9001")
    assert built.markdown.startswith("# テスト記念（G3）の攻略ポイント")
    assert built.editions == table.rows[0][6]


def test_before_counts_only_earlier_editions(season_db):
    with db.open_db(season_db) as con:
        every = StakesGuide.load(con).list_table().rows[0][6]
        earlier = StakesGuide.load(con, "2024-06-01").list_table().rows[0][6]
        with pytest.raises(ValueError):
            StakesGuide.load(con, "2000-01-01")
    assert 0 < earlier < every


def test_unknown_stakes_is_a_lookup_error(season_db):
    with db.open_db(season_db) as con:
        guide = StakesGuide.load(con)
    with pytest.raises(LookupError):
        guide.choose("0000", None)
    with pytest.raises(LookupError):
        guide.choose(None, "有馬")
