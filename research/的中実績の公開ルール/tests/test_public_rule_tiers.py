"""研究「的中実績の公開ルール」の 02 の部品（断面の表・年ごとの学習・公開ルールの払戻・成績の表）のテスト。値は架空。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from yosou.shared.win_correction import FACT_COLUMNS

from 的中実績の公開ルール.analysis.public_bets import PublicBets
from 的中実績の公開ルール.analysis.snapshot_table import SnapshotTable
from 的中実績の公開ルール.analysis.tier_report import TierReport
from 的中実績の公開ルール.analysis.walk_forward_model import WalkForwardModel


def _table(races: int, year: int, seed: int = 0) -> pd.DataFrame:
    """学習の表と同じ形の表（1レース 4頭）。"""
    rng = np.random.default_rng(seed)
    rows = []
    for race in range(races):
        p = rng.dirichlet(np.ones(4))
        winner = int(rng.choice(4, p=p))
        for number in range(4):
            rows.append({"race_id": f"{year}{race:04d}", "race_date": f"{year}-10-0{1 + race % 2}", "year": year, "horse_no": number + 1,
                         "win_probability": p[number], "probability": min(0.95, 2 * p[number]), "win_odds": 0.8 / p[number],
                         "place_odds_low": max(1.0, 0.3 / p[number]), "place_odds_high": max(1.1, 0.4 / p[number]), "quinella_top2": 2 * p[number],
                         "won": int(number == winner), **{column: 1.0 for column in FACT_COLUMNS}})
    return pd.DataFrame(rows)


def test_断面の表は全頭の板がそろうレースだけで_オッズと確率を断面の値にする() -> None:
    final = _table(2, 2025)
    first, second = final["race_id"].unique()
    win = final.assign(combo=final["horse_no"].map("{:02d}".format), odds=final["win_odds"] * 1.1)
    win = win[~((win["race_id"] == second) & (win["horse_no"] == 4))][["race_id", "combo", "odds"]]
    place = final.assign(combo=final["horse_no"].map("{:02d}".format), odds=2.0)[["race_id", "combo", "odds"]]
    quinella = pd.DataFrame({"race_id": [first] * 2, "combo": ["0102", "0304"], "odds": [3.0, 6.0]})
    shot = SnapshotTable(final, {"単勝": win, "複勝最低": place, "複勝最高": place, "馬連": quinella}).build()
    # 2つ目のレースは 4番の単勝が無いので外す。オッズを一様に 1.1倍にしても、オッズから見た勝率は変わらないので確率もそのまま
    assert set(shot["race_id"]) == {first}
    assert list(shot["win_odds"]) == pytest.approx(list(final.loc[final["race_id"] == first, "win_odds"] * 1.1))
    assert list(shot["win_probability"]) == pytest.approx(list(final.loc[final["race_id"] == first, "win_probability"]))
    assert list(shot["place_odds_low"]) == [2.0] * 4


def test_年ごとの学習は最初の2年を除き_その年より前だけで学んだ確率を付ける() -> None:
    final = pd.concat([_table(60, year, seed=year) for year in (2020, 2021, 2022)], ignore_index=True)
    (corrected,) = WalkForwardModel(final).predict([final])
    assert set(corrected["year"]) == {2022}
    assert np.allclose(corrected.groupby("race_id")["corrected"].sum(), 1.0)


def test_公開ルールの払戻は本番と同じ決め方の本命と相手で付け_成績の表は段ごとに数える() -> None:
    horses = pd.DataFrame({"race_id": ["r1"] * 4 + ["r2"] * 4, "race_date": ["2025-10-04"] * 8, "year": 2025, "horse_no": [1, 2, 3, 4] * 2,
                           "win_odds": [2.0, 5.0, 8.0, 40.0] * 2, "corrected": [0.5, 0.3, 0.15, 0.05, 0.4, 0.2, 0.1, 0.3]})
    win = pd.DataFrame({"race_id": ["r1", "r2"], "combo": ["02", "01"], "yen": [500, 200]})
    exacta = pd.DataFrame({"race_id": ["r1"], "combo": ["0201"], "yen": [900]})
    races = PublicBets(horses, win, exacta).races()
    # r1: 期待値は 1番 1.0・2番 1.5・3番 1.2 → ◎ 2番（勝負）。相手は 1・3・4。r2: 1番 0.8・2番 1.0・3番 0.8（4番は 40倍で候補外）→ ◎ 2番
    assert list(races["value"]) == pytest.approx([1.5, 1.0])
    assert list(races["win_back"]) == [500, 0] and list(races["exacta_back"]) == [900, 0]
    report = TierReport(races.assign(year=2023), races, 1.25)
    rows = {(row[0], row[1]): row[3:] for row in report.periods().rows}
    assert rows[("確定・2023〜2023年", "全レース")][:5] == [2, "2.0", 1, "50.0%", "250.0%"]   # 2レースとも同じ開催日
    assert rows[("確定・2023〜2023年", "勝負")][:5] == [1, "1.0", 1, "100.0%", "350.0%"]
