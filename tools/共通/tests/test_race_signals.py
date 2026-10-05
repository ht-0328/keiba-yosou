"""レース前の材料の有無（``共通.race_signals``）のテスト。合成DB に、出馬表・締め切り前のオッズ・馬体重・馬場状態を段階的に足して確かめる。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import db
from 共通.race_signals import RaceScope, RaceSignalReader
from 合成DB import synth

#: 合成DB の確定前の2レース（2025-04-19 東京）。1R は出走馬名表、2R は出馬表。
NAME_LIST_RID = "2025041905010101"
CARD_RID = "2025041905010102"
#: 締め切り前の単勝オッズの断面の発表月日時分（4月19日 10:00）。
ANNOUNCED = "04191000"


def _is_card_second(row: dict[str, str]) -> bool:
    """確定前の 2R（2025-04-19）の行か。確定成績の 2024 年の 2R と見分ける。"""
    return row["開催年"] == "2025" and row["レース番号"] == "02"


def with_realtime(sample: synth.Sample, *, odds: bool = False, weights: bool = False, going: bool = False) -> synth.Sample:
    """確定前の2R（出馬表）に、速報で入る材料を足す。"""
    second = next(row for row in sample.ra if _is_card_second(row))
    runners = [row for row in sample.se if _is_card_second(row)]
    if odds:
        sample.odds.append(("o1", synth.odds_header(second, "o1", stage="1", announced=ANNOUNCED)))
        sample.odds.extend(("o1__単勝オッズ", synth.odds_row(second, "o1__単勝オッズ", row["馬番"], 35 + 10 * index, seq=index + 1, announced=ANNOUNCED))
                           for index, row in enumerate(runners))
    if weights:
        for row in runners[:4]:  # 6頭のうち4頭に出る（半分以上）
            row["馬体重"] = "480"
    if going:
        second["芝馬場状態コード"] = "1"
    return sample


def build(path: Path, **realtime: bool) -> Path:
    return synth.build_db(path, with_realtime(synth.sample().extend(synth.card_sample()), **realtime))


def test_出走馬名表と出馬表の段階が分かる(tmp_path: Path) -> None:
    with db.open_db(build(tmp_path / "a.duckdb")) as con:
        found = RaceSignalReader(con).read_days("2025-04-19")
    assert [each.rid for each in found] == [NAME_LIST_RID, CARD_RID]
    first, second = found
    assert first.is_name_list and not first.is_numbered and first.entries == 6 and first.numbered == 0
    assert second.is_card and second.is_numbered and second.numbered == 6
    assert not first.has_odds and not second.has_odds and not second.is_weighed and not second.going_announced
    assert second.going == "未発表" and second.venue == "東京" and second.race_no == 2 and second.post_time == "15:00"
    assert second.post_datetime().isoformat() == "2025-04-19T15:00:00"


def test_速報が入ると_オッズ_馬体重_馬場状態が付く(tmp_path: Path) -> None:
    with db.open_db(build(tmp_path / "b.duckdb", odds=True, weights=True, going=True)) as con:
        second = RaceSignalReader(con).read_race(CARD_RID)
    assert second.has_odds and second.odds_count == 6 and second.odds_announced_at == ANNOUNCED
    assert second.odds_announced_datetime().isoformat() == "2025-04-19T10:00:00"
    assert second.is_weighed and second.weighed == 4 and second.going_announced and second.going == "良"


def test_確定成績のレースは終了と分かり_範囲は開催日と競馬場で絞れる(tmp_path: Path) -> None:
    with db.open_db(build(tmp_path / "c.duckdb")) as con:
        reader = RaceSignalReader(con)
        finished = reader.read(RaceScope.days("2024-04-06", "2024-04-06", venue_code="05"))
        nakayama = reader.read(RaceScope.days("2024-04-07", "2024-04-07", venue_code="06"))
    assert len(finished) == 3 and all(each.is_finished and each.stage_name == "成績（確定）" for each in finished)
    assert [each.venue for each in nakayama] == ["中山"]


def test_無いレースは見つからないと言う(tmp_path: Path) -> None:
    with db.open_db(build(tmp_path / "d.duckdb")) as con:
        with pytest.raises(LookupError):
            RaceSignalReader(con).read_race("2025041905010109")
    with pytest.raises(ValueError):
        RaceScope.race("123")
