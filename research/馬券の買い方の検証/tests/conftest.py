"""研究「馬券の買い方の検証」のテストの共通の準備。合成DB（架空の値）だけを使い、実DB と学習済みモデルには触らない。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 合成DB import synth


@pytest.fixture
def betting_db(tmp_path: Path) -> Path:
    """確定オッズ・7券種の払戻・払戻のフラグまで入った、2レースの合成DB。

    1R（2025-07-06 東京 1R）: 馬番4（4番人気・15.0倍）が1着、2番・3番が 2・3着。確定オッズ（データ区分 5）のほかに、
    締め切り前の断面（データ区分 1。4番の単勝が 9.9倍）も入れ、確定のほうが選ばれることを確かめられるようにする。
    単勝は返還あり。2R は 3連単が不成立。
    """
    rows = synth.simple_race("20250706", "01")
    ra = rows.ra[0]
    rows.odds += [("o1", synth.odds_header(ra, "o1")), ("o1", synth.odds_header(ra, "o1", stage="1", announced="07061200"))]
    rows.odds += [
        ("o1__単勝オッズ", synth.odds_row(ra, "o1__単勝オッズ", f"{num:02d}", tenths, pop=num))
        for num, tenths in ((1, 20), (2, 45), (3, 80), (4, 150))
    ]
    rows.odds.append(("o1__単勝オッズ", synth.odds_row(ra, "o1__単勝オッズ", "04", 99, pop=4, announced="07061200")))
    rows.odds.append(("o1__単勝オッズ", synth.odds_row(ra, "o1__単勝オッズ", "06", 0, pop=0)))
    rows.odds.append(("o1__複勝オッズ", synth.range_odds_row(ra, "o1__複勝オッズ", "04", 30, 45, pop=4)))
    rows.odds += [("o3", synth.odds_header(ra, "o3")), ("o3__ワイドオッズ", synth.range_odds_row(ra, "o3__ワイドオッズ", "0204", 503, 538, pop=33))]
    rows.odds += [("o5", synth.odds_header(ra, "o5")), ("o5__3連複オッズ", synth.odds_row(ra, "o5__3連複オッズ", "020304", 1785, pop=14))]
    rows.odds += [("o6", synth.odds_header(ra, "o6")), ("o6__3連単オッズ", synth.odds_row(ra, "o6__3連単オッズ", "040203", 123456, pop=250))]
    rows.quinella.append(synth.combo_payout(ra, "0204", 2340, table="hr__馬連払戻"))
    rows.wide += [
        synth.combo_payout(ra, combo, yen, seq=seq, table="hr__ワイド払戻")
        for seq, (combo, yen) in enumerate((("0204", 900), ("0304", 1500), ("0203", 400)), start=1)
    ]
    rows.exacta.append(synth.combo_payout(ra, "0402", 5600, table="hr__馬単払戻"))
    rows.trio.append(synth.combo_payout(ra, "020304", 17850, table="hr__3連複払戻"))
    rows.trifecta.append(synth.combo_payout(ra, "040203", 123450, table="hr__3連単払戻"))
    rows.headers.append(synth.payout_header(ra, refund=("単勝",)))
    second = synth.simple_race("20250706", "02")
    second.headers.append(synth.payout_header(second.ra[0], void=("3連単",)))
    rows.extend(second)
    return synth.build_db(tmp_path / "betting.duckdb", rows)
