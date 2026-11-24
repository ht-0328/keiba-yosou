"""材料の計算のテスト。架空の4頭のレース（``synthetic_race.py``）で、手で計算できる値と比べる。"""

from __future__ import annotations

from itertools import permutations
from math import log

import numpy as np
import pandas as pd
import pytest

from yosou.shared.betting import TicketType

from ..dataset import ComboTableBuilder, HorseMaterials, PayoutBand, RaceMaterials, TrifectaPoolWin
from ..feature import CATALOGS, ComboMembers, ComboSummaryFeatures, HarvilleProbability
from ..feature.material_names import HORSE_MATERIALS
from . import synthetic_race as race

WIDE, QUINELLA, EXACTA = TicketType.WIDE, TicketType.QUINELLA, TicketType.EXACTA
TRIO, TRIFECTA = TicketType.TRIO, TicketType.TRIFECTA
#: 材料は小さい型（float32）で持つので、比べるときの許す差。
NEAR = 1e-5


@pytest.fixture(scope="module")
def tables() -> dict[TicketType, pd.DataFrame]:
    """架空の4頭のレースの、5券種の組の表（全部の組が対象になる広い帯）。組番を index にしてある。"""
    built = ComboTableBuilder(race.WIDE_OPEN_BANDS).build(race.horses(), race.boards())
    return {ticket_type: table.set_index("combo") for ticket_type, table in built.items()}


def _q(ticket_type: TicketType, *combo: int) -> float:
    return race.market_probability(ticket_type, combo)


def _harville(shares: dict[int, float], *order: int) -> float:
    """着順どおりに入る確率（テスト側の素直な計算）。"""
    first, second = shares[order[0]], shares[order[1]]
    top_two = first * second / (1 - first)
    if len(order) == 2:
        return top_two
    return top_two * shares[order[2]] / (1 - first - second)


def _any_order(shares: dict[int, float], *numbers: int) -> float:
    """並びを問わずに上位を占める確率（全部の並びの和）。"""
    return sum(_harville(shares, *order) for order in permutations(numbers))


def _place_market() -> dict[int, float]:
    """複勝オッズから見た3着以内率。真ん中の逆数を、4頭（7頭以下）なので合計 2 にそろえる。"""
    support = {number: 2.0 / (low + high) for number, (low, high) in race.PLACE_ODDS.items()}
    return {number: value / sum(support.values()) * 2 for number, value in support.items()}


def test_材料の数は券種ごとに決まっている() -> None:
    counts = {ticket_type.label: len(catalog.names) for ticket_type, catalog in CATALOGS.items()}
    assert counts == {"ワイド": 80, "馬連": 81, "馬単": 81, "3連複": 99, "3連単": 102}
    assert all(not catalog.categorical for catalog in CATALOGS.values())


def test_組の表は全部の組を持ち_列は一覧どおり(tables) -> None:
    assert {ticket_type: len(table) for ticket_type, table in tables.items()} == {WIDE: 6, QUINELLA: 6, EXACTA: 12, TRIO: 4, TRIFECTA: 24}
    quinella = tables[QUINELLA].reset_index()
    assert list(quinella.columns) == ["combo", "race_id", "ticket_type", "h1", "h2", "odds", "baseline", *CATALOGS[QUINELLA].names]
    assert set(quinella["ticket_type"]) == {"馬連"} and quinella[list(CATALOGS[QUINELLA].names)].dtypes.eq(np.float32).all()


def test_その券種の市場の材料は_オッズの逆数をレースで合計1にそろえた確率の対数(tables) -> None:
    row = tables[QUINELLA].loc["0102"]
    q = _q(QUINELLA, 1, 2)
    assert row["odds"] == pytest.approx(12.0) and row["log_odds"] == pytest.approx(log(12.0), abs=NEAR)
    assert row["log_q"] == pytest.approx(log(q), abs=NEAR)
    assert row["baseline"] == pytest.approx(log(q / (1 - q)), abs=NEAR)
    assert np.exp(tables[QUINELLA]["log_q"]).sum() == pytest.approx(1.0, abs=NEAR)
    assert np.exp(tables[WIDE]["log_q"]).sum() == pytest.approx(3.0, abs=NEAR)   # ワイドは3組当たるので合計 3


def test_3連単の市場から足し合わせた確率は_組の馬が上位を占める3連単の組の和(tables) -> None:
    trifecta = race.combos_of(TRIFECTA)
    top_two = sum(_q(TRIFECTA, *combo) for combo in trifecta if set(combo[:2]) == {1, 2})   # 馬連 1-2: 1・2着が 1番と2番
    both_in = sum(_q(TRIFECTA, *combo) for combo in trifecta if {1, 2} <= set(combo))        # ワイド 1-2: 1番と2番が3着以内
    quinella, wide = tables[QUINELLA].loc["0102"], tables[WIDE].loc["0102"]
    assert quinella["log_t"] == pytest.approx(log(top_two), abs=NEAR)
    assert quinella["d_t"] == pytest.approx(log(top_two) - log(_q(QUINELLA, 1, 2)), abs=NEAR)
    assert wide["log_t"] == pytest.approx(log(both_in), abs=NEAR)


def test_ほかの券種の市場の材料は_同じ馬の組のほかの券種での確率(tables) -> None:
    wide = tables[WIDE].loc["0102"]
    assert wide["x_exa"] == pytest.approx(log(_q(EXACTA, 1, 2) + _q(EXACTA, 2, 1)), abs=NEAR)
    assert wide["x_quin"] == pytest.approx(log(_q(QUINELLA, 1, 2)), abs=NEAR)
    assert wide["d_quin"] == pytest.approx(log(_q(QUINELLA, 1, 2)) - log(_q(WIDE, 1, 2)), abs=NEAR)
    quinella = tables[QUINELLA].loc["0102"]
    assert quinella["x_wide"] == pytest.approx(log(_q(WIDE, 1, 2)), abs=NEAR)
    assert quinella["d_exa"] == pytest.approx(log(_q(EXACTA, 1, 2) + _q(EXACTA, 2, 1)) - log(_q(QUINELLA, 1, 2)), abs=NEAR)
    exacta = tables[EXACTA].loc["0201"]   # 2番 → 1番。馬連・ワイドは馬番の小さい順（1-2）で引く
    assert exacta["x_rev"] == pytest.approx(log(_q(EXACTA, 1, 2)), abs=NEAR)
    assert exacta["x_quin"] == pytest.approx(log(_q(QUINELLA, 1, 2)), abs=NEAR)
    assert exacta["x_wide"] == pytest.approx(log(_q(WIDE, 1, 2)), abs=NEAR)


def test_3頭の券種のほかの券種の市場の材料は_3つの2頭の組の対数の和(tables) -> None:
    pairs = ((1, 2), (1, 3), (2, 3))
    trio = tables[TRIO].loc["010203"]
    assert trio["x_wide"] == pytest.approx(sum(log(_q(WIDE, *pair)) for pair in pairs), abs=NEAR)
    assert trio["x_quin"] == pytest.approx(sum(log(_q(QUINELLA, *pair)) for pair in pairs), abs=NEAR)
    trifecta = tables[TRIFECTA].loc["030102"]   # 3番 → 1番 → 2番
    assert trifecta["x_trio"] == pytest.approx(log(_q(TRIO, 1, 2, 3)), abs=NEAR)
    assert trifecta["d_trio"] == pytest.approx(log(_q(TRIO, 1, 2, 3)) - log(_q(TRIFECTA, 3, 1, 2)), abs=NEAR)
    assert trifecta["x_exa"] == pytest.approx(log(_q(EXACTA, 3, 1)), abs=NEAR)
    assert trifecta["x_quin"] == pytest.approx(log(_q(QUINELLA, 1, 3)), abs=NEAR)
    assert trifecta["x_wide"] == pytest.approx(sum(log(_q(WIDE, *pair)) for pair in pairs), abs=NEAR)


def test_ほかの券種の板に無い組は欠損値() -> None:
    boards = race.boards()
    boards[QUINELLA] = boards[QUINELLA][boards[QUINELLA]["combo"] != "0102"]
    wide = ComboTableBuilder(race.WIDE_OPEN_BANDS).build(race.horses(), boards)[WIDE].set_index("combo")
    assert np.isnan(wide.loc["0102", "x_quin"]) and np.isnan(wide.loc["0102", "d_quin"])
    assert not np.isnan(wide.loc["0103", "x_quin"])


def test_Harvilleの式は_3頭なら手で計算した値になる() -> None:
    harville = HarvilleProbability()
    shares = np.array([[0.5, 0.3, 0.2]])
    assert harville.in_order(shares[:, :2])[0] == pytest.approx(0.3)            # 0.5 × 0.3 ÷ (1 − 0.5)
    assert harville.in_order(shares)[0] == pytest.approx(0.3)                   # さらに × 0.2 ÷ (1 − 0.5 − 0.3)
    assert harville.any_order(shares[:, :2])[0] == pytest.approx(0.3 + 0.3 * 0.5 / 0.7)
    assert harville.any_order(shares)[0] == pytest.approx(1.0)                  # 3頭のレースの3連複は必ず当たる
    pairs = harville.pairs_in_top3(np.array([0.5, 0.3, 0.2]))
    assert pairs[0, 1] == pytest.approx(1.0) and pairs[1, 2] == pytest.approx(1.0) and pairs[0, 0] == 0.0


def test_Harvilleの材料は_予想の1着の確率と市場の勝率のそれぞれから出す(tables) -> None:
    model, market = race.WIN_PROBABILITY, race.MARKET_WIN   # どちらも合計 1
    exacta = tables[EXACTA].loc["0102"]
    assert exacta["log_hv"] == pytest.approx(log(0.4 * 0.3 / 0.6), abs=NEAR)   # 1 → 2 = 0.2
    assert exacta["log_hw"] == pytest.approx(log(0.1 * 0.2 / 0.9), abs=NEAR)
    assert exacta["d_hv"] == pytest.approx(log(0.2) - log(_q(EXACTA, 1, 2)), abs=NEAR)
    quinella = tables[QUINELLA].loc["0102"]
    assert quinella["log_hv"] == pytest.approx(log(_any_order(model, 1, 2)), abs=NEAR)
    trifecta = tables[TRIFECTA].loc["010203"]
    assert trifecta["log_hv"] == pytest.approx(log(0.2 * 0.2 / 0.3), abs=NEAR)   # 1 → 2 → 3
    trio_123, trio_124 = _any_order(model, 1, 2, 3), _any_order(model, 1, 2, 4)
    assert tables[TRIO].loc["010203", "log_hv"] == pytest.approx(log(trio_123), abs=NEAR)
    assert tables[WIDE].loc["0102", "log_hv"] == pytest.approx(log(trio_123 + trio_124), abs=NEAR)   # 3頭目は 3番か4番
    wide_market = _any_order(market, 1, 2, 3) + _any_order(market, 1, 2, 4)
    assert tables[WIDE].loc["0102", "log_hw"] == pytest.approx(log(wide_market), abs=NEAR)


def test_馬ごとの材料は_予想と市場の差と比を出す() -> None:
    pool_win = TrifectaPoolWin().of(race.board(TRIFECTA))
    materials = HorseMaterials().of(race.horses(), pool_win).set_index("horse_no")
    place_market = _place_market()
    first = materials.loc[1]
    assert first["pm"] == pytest.approx(place_market[1]) and first["e3"] == pytest.approx(0.9 - place_market[1])
    assert first["r3"] == pytest.approx(log(0.9 / 0.6)) and first["rw"] == pytest.approx(log(0.4 / 0.1))
    assert first["rpm"] == pytest.approx(log(0.9 / place_market[1]))
    assert first["lwo"] == pytest.approx(log(8.0)) and first["lpo"] == pytest.approx(log(3.0))
    assert first["mk"] == 0 and materials.loc[4, "mk"] == 7                     # ◎ は 0、消 は 7
    assert first["dg"] == 0.0 and first["ds"] == 0.0                            # 危険な人気馬でなければ 0（点数の欠損も 0）
    assert materials.loc[4, "dg"] == 1.0 and materials.loc[4, "ds"] == pytest.approx(0.3)
    wins_first = sum(_q(TRIFECTA, *combo) for combo in race.combos_of(TRIFECTA) if combo[0] == 1)
    assert first["psup"] == pytest.approx(wins_first / 0.1)                     # 3連単の板から見た勝率 ÷ 単勝から見た勝率
    assert materials["pwn"].sum() == pytest.approx(1.0) and materials["mwn"].sum() == pytest.approx(1.0)


def test_1倍未満のオッズの対数は0_印の無い馬は印なしの番号() -> None:
    horses = race.horses().assign(win_odds=[0.5, 4.0, 2.7, 2.0], mark=["◎", None, "?", "消"])
    materials = HorseMaterials().of(horses, TrifectaPoolWin().of(race.board(TRIFECTA))).set_index("horse_no")
    assert materials.loc[1, "lwo"] == 0.0
    assert materials.loc[2, "mk"] == 6 and materials.loc[3, "mk"] == 6


def test_順不同の券種は人気の小さい順に_着順を区別する券種は組番の並びで馬を置く(tables) -> None:
    quinella = tables[QUINELLA].loc["0102"]   # 2番（3番人気）が位置 0、1番（4番人気）が位置 1
    assert (quinella["pop0"], quinella["pop1"]) == (3, 4)
    assert quinella["pw0"] == pytest.approx(0.3) and quinella["pw1"] == pytest.approx(0.4)
    assert (quinella["mk0"], quinella["mk1"]) == (1, 0)
    exacta = tables[EXACTA].loc["0102"]       # 着順のまま
    assert (exacta["pop0"], exacta["pop1"]) == (4, 3) and exacta["pw0"] == pytest.approx(0.4)
    trio = tables[TRIO].loc["010204"]         # 4番（1番人気）・2番（3番人気）・1番（4番人気）
    assert (trio["pop0"], trio["pop1"], trio["pop2"]) == (1, 3, 4) and trio["dg0"] == 1.0
    trifecta = tables[TRIFECTA].loc["030102"]
    assert (trifecta["pop0"], trifecta["pop1"], trifecta["pop2"]) == (2, 4, 3)


def test_組のまとめの材料は_組の馬の和と最小と最大(tables) -> None:
    place_market = _place_market()
    edge = {number: race.TOP3_PROBABILITY[number] - place_market[number] for number in (1, 2, 3, 4)}
    top3_ratio = {number: log(race.TOP3_PROBABILITY[number] / race.MARKET_TOP3[number]) for number in (1, 2, 3, 4)}
    quinella = tables[QUINELLA].loc["0102"]
    assert (quinella["s_pop"], quinella["max_pop"], quinella["min_pop"]) == (7, 4, 3)
    assert quinella["s_e3"] == pytest.approx(edge[1] + edge[2], abs=NEAR)
    assert quinella["min_e3"] == pytest.approx(min(edge[1], edge[2]), abs=NEAR) and quinella["max_e3"] == pytest.approx(max(edge[1], edge[2]), abs=NEAR)
    assert quinella["s_lp3"] == pytest.approx(log(0.9) + log(0.8), abs=NEAR)
    assert quinella["s_lpm"] == pytest.approx(log(place_market[1]) + log(place_market[2]), abs=NEAR)
    assert quinella["log_ratio"] == pytest.approx(top3_ratio[1] + top3_ratio[2], abs=NEAR)   # 順不同は r3 の和
    assert quinella["n_dg_in"] == 0 and tables[QUINELLA].loc["0104", "n_dg_in"] == 1
    exacta = tables[EXACTA].loc["0102"]                                                       # 着順を区別する券種は 1頭目の rw ＋ 2頭目の r3
    assert exacta["log_ratio"] == pytest.approx(log(0.4 / 0.1) + top3_ratio[2], abs=NEAR)


def test_組の中の予想が買っている穴馬を数える() -> None:
    values = np.zeros((2, 2, len(HORSE_MATERIALS)))
    popularity, edge = HORSE_MATERIALS.index("pop"), HORSE_MATERIALS.index("e3")
    values[0, :, popularity], values[0, :, edge] = (7, 2), (0.06, 0.20)   # 7番人気で差 0.06 → 穴馬。2番人気は人気が足りない
    values[1, :, popularity], values[1, :, edge] = (6, 9), (0.04, 0.05)   # 6番人気で差 0.04 は差が足りない。9番人気で差 0.05 → 穴馬
    summary = ComboSummaryFeatures().of(ComboMembers(values, is_ordered=True), pd.RangeIndex(2))
    assert list(summary["n_ls_in"]) == [1, 1]


def test_レースの材料は_そのレースの全部の組に同じ値(tables) -> None:
    place_market = _place_market()
    quinella = tables[QUINELLA]
    row = quinella.loc["0102"]
    entropy = -sum(share * log(share) for share in race.MARKET_WIN.values())
    assert row["field"] == 4 and row["fav_odds"] == pytest.approx(2.0, abs=NEAR) and row["ent"] == pytest.approx(entropy, abs=NEAR)
    assert row["n_dg"] == 1 and row["max_wv"] == pytest.approx(1.2, abs=NEAR) and row["s3"] == pytest.approx(0.9, abs=NEAR)
    assert row["n_ls"] == 0 and row["exp_high"] == 1                                 # ◎ の単勝の期待値が 1.2
    assert row["fav_dg"] == 1 and row["fav_e3"] == pytest.approx(0.6 - place_market[4], abs=NEAR)
    assert row["fav_rw"] == pytest.approx(log(0.1 / 0.4), abs=NEAR)
    assert quinella["field"].nunique() == 1 and quinella["ent"].nunique() == 1
    assert row["fav_out_dg"] == 1 and quinella.loc["0104", "fav_out_dg"] == 0        # 危険な1番人気（4番）を含まない組だけ 1


def test_レースごとの表は_穴馬を数え_本命や1番人気がいなければ0か欠損値() -> None:
    count = 7
    materials = pd.DataFrame({name: np.zeros(count) for name in HORSE_MATERIALS})
    materials["race_id"], materials["horse_no"] = race.RACE, np.arange(1, count + 1)
    materials["pop"] = [2, 3, 4, 5, 6, 7, 8]          # 1番人気がいない
    materials["e3"] = [0.5, 0.5, 0.5, 0.5, 0.05, 0.04, 0.10]
    materials["mw"] = [0.3, 0.25, 0.2, 0.1, 0.05, 0.05, 0.05]
    materials["mk"] = 6.0                              # ◎ がいない
    races = RaceMaterials().of(materials).loc[race.RACE]
    assert races["field"] == 7 and races["n_ls"] == 2 and races["s3"] == pytest.approx(0.75)
    assert races["exp_high"] == 0.0 and np.isnan(races["fav_dg"]) and np.isnan(races["fav_e3"])


def test_学ぶ帯の大きさは_学ぶ下限以上の組の数と確率の合計() -> None:
    # 馬連のオッズは 12・14・16・17・19・22倍。学ぶ下限 15倍・上限 20倍なら、対象は 16・17・19倍の3組、下限以上は 22倍を入れて4組
    band = {QUINELLA: PayoutBand(QUINELLA, learn_from=15.0, high_line=17.0, cap=20.0)}
    table = ComboTableBuilder(band).build(race.horses(), race.boards())[QUINELLA].set_index("combo")
    assert sorted(table.index) == ["0104", "0203", "0204"] and table["odds"].between(15.0, 20.0, inclusive="left").all()
    at_or_above = sum(_q(QUINELLA, *combo) for combo in ((1, 4), (2, 3), (2, 4), (3, 4)))
    assert (table["reg_n"] == 4).all() and table["reg_q"].iloc[0] == pytest.approx(at_or_above, abs=NEAR)
    assert table["reg_hv"].iloc[0] == pytest.approx(np.exp(table["log_hv"].astype(float)).sum(), abs=NEAR)
