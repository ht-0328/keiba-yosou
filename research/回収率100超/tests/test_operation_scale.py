"""運用の目安の部品（参加するレース・点数の分布・買う馬の傾向・金額の上限）のテスト。架空の値だけを使う。"""

import pandas as pd
import pytest

from 回収率100超.analysis.backtest import (
    BetsPerRaceDistribution,
    BoughtHorseProfile,
    RaceParticipation,
    StakeCeiling,
)

#: 架空の2レース（r1 は 3頭、r2 は 2頭）。
EVALUATED = pd.DataFrame({
    "rid": ["r1", "r1", "r1", "r2", "r2"],
    "horse_no": [1, 2, 3, 1, 2],
    "year": [2024] * 5,
    "day": ["d1", "d1", "d1", "d2", "d2"],
    "win_odds": [2.0, 15.0, 60.0, 3.0, 8.0],
})
#: r1 の 2番と 3番を買い（2番が的中 250円）、r2 は買わない。
BOUGHT = pd.DataFrame({
    "rid": ["r1", "r1"], "horse_no": [2, 3], "year": [2024, 2024], "day": ["d1", "d1"],
    "place_payout": [250.0, 0.0],
    "複勝プールの大きさ": [100000.0, 100000.0], "想定払戻倍率": [2.0, 8.0],
})


def test_participation_counts_races_bought_out_of_races_predicted():
    table = RaceParticipation().yearly(EVALUATED, BOUGHT)
    row = table.iloc[0]
    assert (row["予測したレース"], row["買ったレース"], row["買ったレースの割合"]) == (2, 1, 0.5)
    assert row["1開催日あたりの買うレース"] == 0.5


def test_bets_per_race_distribution():
    table = BetsPerRaceDistribution().table(BOUGHT)
    assert table.to_dict("records") == [{"1レースの点数": 2, "レースの数": 1, "割合": 1.0}]


def test_profile_bands_by_popularity_and_odds():
    tables = BoughtHorseProfile().tables(EVALUATED, BOUGHT)
    popularity = tables["人気"].set_index("帯")
    assert popularity.loc["1〜3番人気", "点数"] == 2
    odds = tables["単勝オッズ"].set_index("帯")
    assert odds.loc["10〜30倍", "的中率"] == 1.0 and odds.loc["50倍以上", "回収率"] == 0.0
    assert tables["出走頭数"].set_index("帯").loc["8頭以下", "点数"] == 2


def test_stake_ceiling_shrinks_as_the_expected_price_grows():
    ceiling = StakeCeiling().per_bet(BOUGHT)
    # 売上 1,000万円 × 0.8 ÷ 3 ÷ 倍率 が、その馬に入った金額。その 5/95 が上限。
    assert ceiling.iloc[0] == pytest.approx(10_000_000 * 0.8 / 3 / 2.0 * 0.05 / 0.95)
    assert ceiling.iloc[1] < ceiling.iloc[0]
    summary = StakeCeiling().summary(BOUGHT)
    assert summary.bets == 2 and summary.lower_tenth < summary.median
