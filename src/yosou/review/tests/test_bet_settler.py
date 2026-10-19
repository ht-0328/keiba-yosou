"""買い目の精算（``BetSettler``）のテスト。値は架空。DB は合成DB だけを使う。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from yosou.review import ReviewStore, names
from yosou.review.bet_settler import BetSettler
from yosou.review.repository import ReviewRunRepository


def _db(tmp_path: Path, exacta: bool) -> tuple[duckdb.DuckDBPyConnection, str]:
    """1着 4番・2着 2番・3着 3番、6番は出走取消の1レース。``exacta`` なら馬単 4→2 の払戻（100円あたり 5,000円）を入れる。"""
    from 共通 import keys
    from 合成DB import synth

    sample = synth.simple_race()
    ra = sample.ra[0]
    if exacta:
        sample.headers.append(synth.payout_header(ra))
        sample.exacta.append(synth.combo_payout(ra, "0402", 5000, table="hr__馬単払戻"))
    con = duckdb.connect(str(synth.build_db(tmp_path / "settle.duckdb", sample)), read_only=True)
    return con, "".join(ra[column] for column in keys.RACE_KEY)


def _bets(rid: str) -> pd.DataFrame:
    rows = [("単勝", "04", 300), ("馬単", "0402", 200), ("馬単", "0401", 100), ("馬単", "0406", 100)]
    return pd.DataFrame([{names.RACE_ID: rid, names.TICKET_TYPE: kind, names.COMBO: combo, names.RACE_DATE: date(2024, 4, 6),
                          names.PARTICIPATION: names.MATCH_WIN, names.RECORD_ONLY: False, names.STAKE_YEN: yen, names.PAYOUT_YEN: None,
                          names.SETTLED: False} for kind, combo, yen in rows])


def test_馬単は払戻の明細から精算し_外れは0_取消の馬を含む組は返還する(tmp_path: Path) -> None:
    con, rid = _db(tmp_path, exacta=True)
    store = ReviewStore(tmp_path / "review.duckdb")
    store.write(names.BETS_TABLE, _bets(rid))
    assert BetSettler(store).settle(ReviewRunRepository(con).read(), con) == 4
    settled = store.read(names.BETS_TABLE).set_index(names.COMBO)
    assert settled[names.SETTLED].all()
    assert settled.loc["04", names.PAYOUT_YEN] == 4_500    # 単勝 4番 1,500円 × 3
    assert settled.loc["0402", names.PAYOUT_YEN] == 10_000  # 馬単 4→2 5,000円 × 2
    assert settled.loc["0401", names.PAYOUT_YEN] == 0       # 外れ
    assert settled.loc["0406", names.PAYOUT_YEN] == 100     # 6番は出走取消なので返還


def test_馬単の払戻がまだ取り込まれていなければ精算せず_DBを渡さなければ組の券種は精算しない(tmp_path: Path) -> None:
    con, rid = _db(tmp_path, exacta=False)
    store = ReviewStore(tmp_path / "review.duckdb")
    store.write(names.BETS_TABLE, _bets(rid))
    runs = ReviewRunRepository(con).read()
    assert BetSettler(store).settle(runs) == 1                 # 単勝だけ
    assert BetSettler(store).settle(runs, con) == 1            # 取消を含む組の返還だけ（払戻の明細が無い組は待つ）
    pending = store.read(names.BETS_TABLE, f"NOT {names.SETTLED}")
    assert sorted(pending[names.COMBO]) == ["0401", "0402"]


def test_枠連は払戻の明細から精算し_枠の馬が全部取消なら返還する(tmp_path: Path) -> None:
    """合成DB の簡単なレースは馬番がそのまま枠番。1着 4番・2着 2番で、6番（6枠）は出走取消。枠連 2-4 の払戻は 100円あたり 1,200円。"""
    from 共通 import keys
    from 合成DB import synth

    sample = synth.simple_race()
    ra = sample.ra[0]
    sample.headers.append(synth.payout_header(ra))
    sample.bracket.append(synth.combo_payout(ra, "24", 1200, table="hr__枠連払戻"))
    con = duckdb.connect(str(synth.build_db(tmp_path / "bracket.duckdb", sample)), read_only=True)
    rid = "".join(ra[column] for column in keys.RACE_KEY)
    rows = [("24", 200), ("14", 100), ("46", 100)]
    store = ReviewStore(tmp_path / "review.duckdb")
    store.write(names.BETS_TABLE, pd.DataFrame([
        {names.RACE_ID: rid, names.TICKET_TYPE: "枠連", names.COMBO: combo, names.RACE_DATE: date(2024, 4, 6),
         names.PARTICIPATION: names.MATCH_COMBO, names.RECORD_ONLY: False, names.STAKE_YEN: yen, names.PAYOUT_YEN: None,
         names.SETTLED: False} for combo, yen in rows]))
    assert BetSettler(store).settle(ReviewRunRepository(con).read(), con) == 3
    settled = store.read(names.BETS_TABLE).set_index(names.COMBO)
    assert settled.loc["24", names.PAYOUT_YEN] == 2_400   # 1,200円 × 2
    assert settled.loc["14", names.PAYOUT_YEN] == 0       # 外れ
    assert settled.loc["46", names.PAYOUT_YEN] == 100     # 6枠の馬は全部取消なので返還
