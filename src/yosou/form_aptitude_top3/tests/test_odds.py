"""予測のときに使う単勝オッズの決め方（設計書 06 の図2・07 の「予測のときのオッズの与え方」）。

実DB は使わない。締め切り前のオッズの SQL そのもののテストは、``AnnouncedOddsRepository`` を共通で使う
「人気馬が4着以下になるかを予想」のテストにある。
"""

from __future__ import annotations

import pandas as pd
import pytest

from yosou.shared.tests import synthetic_season as season

from ..dataset import OddsInput, OddsResolver

RACE = season.CARD_RACE_ID


class _FixedOdds:
    """``AnnouncedOddsRepository`` の代わり（渡した表をそのまま返す）。"""

    def __init__(self, odds: pd.DataFrame) -> None:
        self._odds = odds

    def read(self, race_id: str) -> pd.DataFrame:
        return self._odds


def _odds_table(rows: list[tuple[int, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["horse_no", "odds"])


def test_odds_input_reads_pairs_written_as_separate_arguments():
    assert OddsInput.of(["3:2.4", "7:5.1", "11:38"]).as_mapping() == {3: 2.4, 7: 5.1, 11: 38.0}


def test_odds_input_reads_pairs_written_with_commas():
    assert OddsInput.of(["3:2.4,7:5.1"]).as_mapping() == {3: 2.4, 7: 5.1}
    assert OddsInput.of(["3:2.4", "7:5.1,11:38"]).as_mapping() == {3: 2.4, 7: 5.1, 11: 38.0}


@pytest.mark.parametrize(("texts", "message"), [
    (["3-2.4"], "馬番:オッズ"),
    (["3:2.4:1"], "馬番:オッズ"),
    (["0:2.4"], "馬番"),
    (["a:2.4"], "馬番"),
    (["3:0.9"], "オッズ"),
    (["3:b"], "オッズ"),
    (["3:inf"], "オッズ"),
    ([], "1つ以上"),
    (["3:2.4", "3:5.1"], "同じ馬番 3"),
])
def test_odds_input_reports_what_is_wrong(texts: list[str], message: str):
    with pytest.raises(ValueError, match=message):
        OddsInput.of(texts)


def test_given_odds_come_first():
    resolver = OddsResolver(_FixedOdds(_odds_table([(1, 2.0), (2, 3.0)])))
    assert resolver.resolve(RACE, OddsInput.of(["5:1.8", "8:12"])) == {5: 1.8, 8: 12.0}


def test_announced_odds_are_used_when_nothing_is_given():
    resolver = OddsResolver(_FixedOdds(_odds_table([(1, 8.4), (2, 2.1), (3, 5.0)])))
    assert resolver.resolve(RACE, None) == {1: 8.4, 2: 2.1, 3: 5.0}


def test_no_odds_is_left_to_the_database():
    # 渡されたオッズも締め切り前のオッズも無ければ None。元DB の単勝オッズ（確定オッズ）がそのまま使われる
    resolver = OddsResolver(_FixedOdds(_odds_table([])))
    assert resolver.resolve(RACE, None) is None
