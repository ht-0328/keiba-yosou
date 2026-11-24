"""組の表づくりの流れのテスト。元DB の代わりに、架空の1レースを入れた合成DB を使う。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from 共通 import keys
from 合成DB import synth

from yosou.shared.betting import TicketType

from ..command import CommandLine
from ..repository import ComboTableRepository
from ..workflow import TableWorkflow
from . import synthetic_race as race

QUINELLA, TRIFECTA, WIDE = TicketType.QUINELLA, TicketType.TRIFECTA, TicketType.WIDE
#: 合成DB に入れる当たりの組（券種 → 組番と 100円あたりの払戻）。
WINNERS: dict[TicketType, list[tuple[str, int]]] = {
    TicketType.QUINELLA: [("0204", 1_900)], TicketType.EXACTA: [("0402", 3_800)], TicketType.TRIO: [("020304", 2_100)],
    TicketType.TRIFECTA: [("040203", 16_000)], TicketType.WIDE: [("0204", 600), ("0304", 700), ("0203", 400)],
}
PAYOUT_ROWS = {TicketType.QUINELLA: "quinella", TicketType.EXACTA: "exacta", TicketType.TRIO: "trio",
               TicketType.TRIFECTA: "trifecta", TicketType.WIDE: "wide"}


def _odds_rows(race_row: dict[str, str], ticket_type: TicketType) -> list[tuple[str, dict[str, str]]]:
    """1つの券種の確定オッズの親と子の行（架空の4頭の全部の組）。ワイドは最低と最高。"""
    table = ticket_type.spec.odds_table
    combos = race.combos_of(ticket_type)
    tenths = [round(race.odds_of(ticket_type, combo) * 10) for combo in combos]
    children = [_odds_row(race_row, ticket_type, race.combo_text(combo), value, seq)
                for seq, (combo, value) in enumerate(zip(combos, tenths), start=1)]
    return [(ticket_type.spec.odds_parent, synth.odds_header(race_row, ticket_type.spec.odds_parent)), *((table, row) for row in children)]


def _odds_row(race_row: dict[str, str], ticket_type: TicketType, combo: str, tenths: int, seq: int) -> dict[str, str]:
    """オッズの子の1行。ワイドは最低オッズ ``tenths`` と、それより 2倍高い最高オッズ。"""
    if ticket_type is WIDE:
        return synth.range_odds_row(race_row, ticket_type.spec.odds_table, combo, tenths, tenths + 20, seq=seq)
    return synth.odds_row(race_row, ticket_type.spec.odds_table, combo, tenths, seq=seq)


def _payout_rows(race_row: dict[str, str], ticket_type: TicketType) -> list[dict[str, str]]:
    return [synth.combo_payout(race_row, combo, yen, seq=seq, table=ticket_type.spec.payout_table)
            for seq, (combo, yen) in enumerate(WINNERS[ticket_type], start=1)]


@pytest.fixture(scope="module")
def market_db(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, pd.DataFrame]:
    """架空の1レース（2024-04-06）の確定オッズの板と払戻を入れた合成DB と、そのレースの馬ごとの表。"""
    sample = synth.simple_race()
    race_row = sample.ra[0]
    for ticket_type in race.ALL_TICKET_TYPES:
        sample.odds.extend(_odds_rows(race_row, ticket_type))
        getattr(sample, PAYOUT_ROWS[ticket_type]).extend(_payout_rows(race_row, ticket_type))
    path = synth.build_db(tmp_path_factory.mktemp("high_payout_db") / "market.duckdb", sample)
    race_id = "".join(race_row[column] for column in keys.RACE_KEY)
    return path, race.horses(race_id).assign(race_date=pd.Timestamp("2024-04-06"))


def _workflow(market_db: tuple[Path, pd.DataFrame], folder: Path, **options: bool) -> TableWorkflow:
    path, horses = market_db
    return TableWorkflow(path, horses, ComboTableRepository(folder), race.ALL_TICKET_TYPES, bands=race.WIDE_OPEN_BANDS, **options)


def test_確定オッズの板と払戻から_券種ごとの年の表を作る(market_db: tuple[Path, pd.DataFrame], tmp_path: Path) -> None:
    results = _workflow(market_db, tmp_path).run(date(2024, 1, 1), date(2024, 12, 31))
    counts = {result.ticket_type.label: (result.year, result.row_count, result.hit_count) for result in results}
    assert counts == {"ワイド": (2024, 6, 3), "馬連": (2024, 6, 1), "馬単": (2024, 12, 1), "3連複": (2024, 4, 1), "3連単": (2024, 24, 1)}
    trifecta = ComboTableRepository(tmp_path).load(TRIFECTA, 2024).set_index("combo")
    assert trifecta.loc["040203", "payout"] == 16_000 and trifecta.loc["040203", "hit"] == 1 and trifecta["hit"].sum() == 1
    assert trifecta.loc["040203", "odds"] == pytest.approx(race.odds_of(TRIFECTA, (4, 2, 3)))
    assert (trifecta["race_date"] == pd.Timestamp("2024-04-06")).all()
    wide = ComboTableRepository(tmp_path).load(WIDE, 2024).set_index("combo")
    assert wide.loc["0204", "odds"] == pytest.approx(race.odds_of(WIDE, (2, 4)))   # ワイドは最低オッズ


def test_済んでいる年は飛ばし_作り直しを頼めば作り直す(market_db: tuple[Path, pd.DataFrame], tmp_path: Path) -> None:
    _workflow(market_db, tmp_path).run(date(2024, 1, 1), date(2024, 12, 31))
    again = _workflow(market_db, tmp_path).run(date(2024, 1, 1), date(2024, 12, 31))
    assert all(result.was_skipped for result in again)
    forced = _workflow(market_db, tmp_path, overwrite=True).run(date(2024, 1, 1), date(2024, 12, 31))
    assert not any(result.was_skipped for result in forced) and sum(result.row_count for result in forced) == 52


def test_期間の外のレースは作らない(market_db: tuple[Path, pd.DataFrame], tmp_path: Path) -> None:
    assert _workflow(market_db, tmp_path).run(date(2025, 1, 1), date(2025, 12, 31)) == []
    assert ComboTableRepository(tmp_path).years(QUINELLA) == []


def test_tablesコマンドは_馬ごとの表と合成DBから表を作って結果を出す(market_db: tuple[Path, pd.DataFrame], tmp_path: Path,
                                             capsys: pytest.CaptureFixture[str]) -> None:
    path, horses = market_db
    (tmp_path / "horses").mkdir()
    horses.to_parquet(tmp_path / "horses" / "2024.parquet")
    arguments = ["tables", "--from", "2024-01-01", "--db", str(path), "--horses", str(tmp_path / "horses"),
                 "--tables", str(tmp_path / "tables"), "--ticket", "馬連", "trifecta"]
    with pytest.raises(SystemExit) as exit_info:
        CommandLine().run(arguments)
    assert exit_info.value.code == 0
    assert ComboTableRepository(tmp_path / "tables").years(QUINELLA) == [2024]
    assert ComboTableRepository(tmp_path / "tables").years(WIDE) == []   # --ticket で絞った券種だけ
    assert "馬連" in capsys.readouterr().out


def test_扱わない券種を頼むと誤り(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        CommandLine().run(["tables", "--horses", str(tmp_path), "--ticket", "単勝"])
    assert exit_info.value.code == 1 and "馬ごとの表がありません" in capsys.readouterr().err
