"""決着の型の契約: 決着の表の値、切り口の割合、人気で決める買い目の精算、ハサミ目、馬単÷馬連。合成DB だけを使う。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import db
from 共通.filters import Filters, Range
from 合成DB import synth

from 決着の型 import outcome_dimension
from 決着の型.hasami_bet import HasamiBet
from 決着の型.outcome_share import OutcomeShare
from 決着の型.pattern_bet import PatternBet
from 決着の型.pattern_settlement import PatternSettlement
from 決着の型.payout_ratio import PayoutRatio
from 決着の型.popularity_map import PopularityMap
from 決着の型.race_selection import RaceSelection
from 決着の型.race_table import OUT_OF_MONEY, RaceTable
from 決着の型.repository.combo_payout_repository import ComboPayoutRepository
from 決着の型.repository.race_runner_repository import RaceRunnerRepository
from 決着の型.ticket_kind import ticket_kind

DAY = "20240406"


def _sandwich_race(no: str) -> synth.Sample:
    """1着 馬番1・2着 馬番3・3着 馬番5 のレース。1〜3着の馬番 [1, 3, 5] に挟まれた 2 と 4 がハサミ目になる。"""
    ra = synth.race(DAY, no)
    finishes = {1: 1, 2: 4, 3: 2, 4: 5, 5: 3}
    se = [synth.runner(ra, num, num, fin) for num, fin in finishes.items()]
    return synth.Sample(ra=[ra], se=se, win=[synth.payout(ra, 1, 200)],
                        place=[synth.payout(ra, num, 150, seq=seq) for seq, num in enumerate((1, 3, 5), start=1)])


@pytest.fixture
def outcome_db(tmp_path: Path) -> Path:
    """10R = ハサミ目の元（1着 1・2着 3・3着 5）、11R = ``simple_race``（1着 4番人気の馬番4・2着 馬番2・3着 馬番3）に、組み合わせの払戻を足した DB。"""
    sample = _sandwich_race("10").extend(synth.simple_race(DAY, "11"))
    ra = sample.ra[1]
    sample.trio.append(synth.combo_payout(ra, "020304", 1500, table="hr__3連複払戻"))
    sample.quinella.append(synth.combo_payout(ra, "0204", 900, table="hr__馬連払戻"))
    sample.exacta.append(synth.combo_payout(ra, "0402", 1800, table="hr__馬単払戻"))
    sample.wide.extend(synth.combo_payout(ra, combo, yen, seq=seq, table="hr__ワイド払戻")
                       for seq, (combo, yen) in enumerate((("0204", 300), ("0304", 500), ("0203", 200)), start=1))
    return synth.build_db(tmp_path / "outcome.duckdb", sample)


def _load(path: Path):
    with db.open_db(path) as con:
        runners = RaceRunnerRepository(con).read(Filters())
        payouts = {name: ComboPayoutRepository(con).read(ticket_kind(name)) for name in ("3連複", "馬連", "馬単", "ワイド")}
    return runners, RaceTable().build(runners), payouts


def test_race_table_values(outcome_db: Path):
    """11R: 1〜3着の人気 4・2・3、1番人気は4着（馬券外）、単勝 10倍以下 3頭・30倍以下 5頭。"""
    runners, races, _ = _load(outcome_db)
    eleventh = races[races["race_no"].eq(11)].iloc[0]
    assert (eleventh["pop_1st"], eleventh["pop_2nd"], eleventh["pop_3rd"]) == (4, 2, 3)
    assert eleventh["fav1_finish"] == OUT_OF_MONEY and eleventh["fav2_finish"] == 2
    assert (eleventh["n_under10"], eleventh["n_under30"]) == (3, 5)
    assert eleventh["odds_1st"] == 15.0 and eleventh["age_min"] == eleventh["age_max"] == 4
    assert PopularityMap(runners).of(eleventh.name) == {1: [1], 2: [2], 3: [3], 4: [4], 5: [5]}


def test_share_labels_and_order(outcome_db: Path):
    _, races, _ = _load(outcome_db)
    table = OutcomeShare([outcome_dimension.dimension("top5-mix")]).table(races, "全レース")
    assert table.rows == [["上位人気3頭", 2, "100.0%"]]
    # 10R は全馬 3.5倍（10倍以下が5頭）、11R は 10倍以下が3頭。2つ目の切り口の割合は、1つ目の値が同じレースの中で数える
    crossed = OutcomeShare([outcome_dimension.dimension("fav1-finish"), outcome_dimension.dimension("odds-spread")]).count(races)
    assert crossed[["1番人気の着順", "単勝オッズの散らばり"]].values.tolist() == [
        ["1着", "それ以外"], ["4着以下", "10倍以下3頭以下かつ30倍以下5頭以下"]]
    assert crossed["share"].tolist() == [1.0, 1.0]
    by_year = OutcomeShare([outcome_dimension.dimension("year"), outcome_dimension.dimension("fav1-finish")]).count(races)
    assert by_year["share"].tolist() == [0.5, 0.5]
    assert outcome_dimension.dimension("pop-sum").values(races).tolist() == ["9〜12", "9〜12"]  # 1+3+5 と 4+2+3
    assert outcome_dimension.dimension("top3-any").values(races).tolist() == ["どれかが3着以内"] * 2
    assert outcome_dimension.dimension("fav2-out").values(races).tolist() == ["どちらかが3着以内"] * 2
    assert outcome_dimension.dimension("winner-odds").values(races).tolist() == ["10倍未満", "10〜30倍"]  # 3.5倍 と 15.0倍
    with pytest.raises(ValueError):
        OutcomeShare([])
    with pytest.raises(LookupError):
        outcome_dimension.dimension("nope")


def test_pattern_bet_parse_and_tickets():
    box = PatternBet.parse("3連複:1,2,3,5,6")
    assert box.is_box and box.columns == (frozenset({1, 2, 3, 5, 6}),)
    assert len(box.tickets({1: [1], 2: [2], 3: [3], 5: [5], 6: [6]})) == 10
    assert box.tickets({1: [1], 2: [2], 3: [3], 5: [5]}) == {(1, 2, 3), (1, 2, 5), (1, 3, 5), (2, 3, 5)}  # 6番人気がいない
    formation = PatternBet.parse("3連単:2/1/6-10")
    assert formation.tickets({1: [1], 2: [2], 6: [6], 7: [7]}) == {(2, 1, 6), (2, 1, 7)}
    assert formation.tickets({1: [1], 2: [2]}) == set()
    assert PatternBet.parse("馬連:1/2-3").tickets({1: [1], 2: [2], 3: [3]}) == {(1, 2), (1, 3)}
    assert PatternBet.parse("馬単:1,2").tickets({1: [1], 2: [2]}) == {(1, 2), (2, 1)}
    for bad in ("3連複", "3連複:", "3連複:1,2", "3連複:1/2", "3連単:3-1", "枠連:1,2", "3連複:a"):
        with pytest.raises((ValueError, LookupError)):
            PatternBet.parse(bad)


def test_pattern_settlement_hits_and_recovery(outcome_db: Path):
    """3連複 1〜4番人気ボックス: 10R は 4点外れ、11R は 4点のうち 2-3-4 が当たり 1,500円 → 回収率 1500 ÷ 800。"""
    runners, races, payouts = _load(outcome_db)
    popularity = PopularityMap(runners)
    settlement = PatternSettlement(PatternBet.parse("3連複:1,2,3,4"))
    settled = settlement.settle(races, popularity, payouts["3連複"])
    assert settled["tickets"].tolist() == [4, 4] and settled["hit"].tolist() == [False, True] and settled["yen"].sum() == 1500
    total = settlement.table(settled, "全レース").rows[-1]
    assert total == ["合計", "2", "2", "8", "800", "1", "50.0%", "1500", "187.5%"]
    wide = PatternSettlement(PatternBet.parse("ワイド:4/1-3")).settle(races, popularity, payouts["ワイド"])
    assert wide["yen"].tolist() == [0, 800]  # 4-2 と 4-3 の2点が同時に当たる
    missing = PatternSettlement(PatternBet.parse("3連単:2/1/6-10")).settle(races, popularity, payouts["3連複"])
    assert missing["tickets"].tolist() == [0, 0]
    assert PatternSettlement(PatternBet.parse("3連単:2/1/6-10")).table(missing, "全レース").rows[-1][-1] == "—"


def test_hasami_bet(outcome_db: Path):
    """10R の 1〜3着の馬番 [1, 3, 5] → 11R で 2 と 4 を買う。単勝は 4 が 1,500円、複勝は 2 が 180円・4 が 400円。"""
    runners, _, _ = _load(outcome_db)
    bet = HasamiBet(10, 11)
    settled = bet.settle(runners)
    assert settled[["numbers", "tickets", "win_hits", "win_yen", "place_hits", "place_yen"]].values.tolist() == [[2, 2, 1, 1500, 2, 580]]
    assert bet.table(settled, "全レース").rows[-1] == ["合計", "1", "1", "2", "200", "1", "1500", "750.0%", "2", "580", "290.0%"]
    assert HasamiBet(1, 2).settle(runners).empty
    with pytest.raises(ValueError):
        HasamiBet(10, 10)


def test_payout_ratio(outcome_db: Path):
    _, races, payouts = _load(outcome_db)
    ratios = PayoutRatio().ratios(races, payouts["馬単"], payouts["馬連"])
    assert ratios["ratio"].tolist() == [2.0] and ratios["favourite_won"].tolist() == [False]  # 4番人気 → 2番人気
    rows = PayoutRatio().table(ratios, "全レース").rows
    assert rows[-3][:4] == ["合計", "全部", "1", "2.00"] and rows[-2][2] == "0" and rows[-1][2] == "1"


def test_race_selection_apply_and_describe(outcome_db: Path):
    _, races, _ = _load(outcome_db)
    narrow = RaceSelection(under10=Range.parse("-3"), age_only=4)
    assert narrow.apply(races)["race_no"].tolist() == [11] and narrow.describe() == "単勝10倍以下 -3頭 4歳限定戦"
    assert RaceSelection(under30=Range.parse("5-")).apply(races)["race_no"].tolist() == [10, 11]
    assert RaceSelection(age_only=3).apply(races).empty
    assert RaceSelection().describe() == "全レース"
