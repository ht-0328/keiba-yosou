"""市場の組の確率を作る部品のテスト。架空の値だけを使う。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from 回収率100超.analysis.market import SternProbabilities
from 回収率100超.analysis.tickets import KINDS_BY_KEY, OddsBandCalibrator
from 複勝以外の回収率100超.analysis import (
    OWN,
    TRIFECTA,
    TRIO,
    HorseUplift,
    MarketComboTable,
    MarketSource,
    PoolDerivation,
)
from 複勝以外の回収率100超.analysis.variant import variants_for

HARVILLE = SternProbabilities(1.0, 1.0)
WINS = np.r_[0.4, 0.3, 0.2, 0.1, np.zeros(14)]


def _index(kind: str, *horses: int) -> int:
    return int(KINDS_BY_KEY[kind].flat_index(np.array([horses]))[0])


def _no_uplift(rid: int = 1) -> HorseUplift:
    return HorseUplift(pd.Series([rid]), pd.Series([1]), pd.Series([0.5]), pd.Series([0.5]), strength=0.0)


def test_市場の組の確率はオッズの逆数をレースで合計1にそろえた値() -> None:
    odds = pd.DataFrame({"rid": [1, 1], "h1": [1, 1], "h2": [2, 3], "odds": [2.0, 4.0]})
    table = MarketComboTable(KINDS_BY_KEY["quinella"], odds).get(1)
    assert table[_index("quinella", 1, 2)] == pytest.approx(2 / 3)
    assert table[_index("quinella", 2, 1)] == pytest.approx(2 / 3)
    assert table[_index("quinella", 1, 3)] == pytest.approx(1 / 3)


def test_オッズの無いレースは表が無い() -> None:
    odds = pd.DataFrame({"rid": [1], "h1": [1], "odds": [2.0]})
    assert MarketComboTable(KINDS_BY_KEY["win"], odds).get(2) is None


def test_3連単から作ったワイドと馬連はHarvilleの式と一致する() -> None:
    trifecta = HARVILLE.ordered_triple(WINS).ravel()
    derivation = PoolDerivation()
    wide = derivation.from_trifecta(KINDS_BY_KEY["wide"], trifecta)
    quinella = derivation.from_trifecta(KINDS_BY_KEY["quinella"], trifecta)
    assert wide == pytest.approx(HARVILLE.wide(WINS).ravel())
    assert quinella == pytest.approx(HARVILLE.quinella(WINS).ravel())


def test_3連単から作った単勝は1着の確率に戻る() -> None:
    trifecta = HARVILLE.ordered_triple(WINS).ravel()
    assert PoolDerivation().from_trifecta(KINDS_BY_KEY["win"], trifecta) == pytest.approx(WINS)


def test_3連複から作ったワイドは2頭とも3着以内の確率() -> None:
    trio = HARVILLE.trio(WINS).ravel()
    wide = PoolDerivation().from_trio(KINDS_BY_KEY["wide"], trio)
    assert wide == pytest.approx(HARVILLE.wide(WINS).ravel())


def test_上げ下げの強さが0なら表は変わらない() -> None:
    table = HARVILLE.quinella(WINS).ravel()
    uplift = HorseUplift(pd.Series([1, 1]), pd.Series([1, 2]), pd.Series([0.9, 0.1]),
                         pd.Series([0.5, 0.5]), strength=0.0)
    assert uplift.apply(KINDS_BY_KEY["quinella"], 1, table) == pytest.approx(table)


def test_上げ下げは市場より来ると見た馬の組を上げ_合計は変えない() -> None:
    table = HARVILLE.quinella(WINS).ravel()
    uplift = HorseUplift(pd.Series([1, 1]), pd.Series([1, 4]), pd.Series([0.5, 0.4]),
                         pd.Series([0.5, 0.2]), strength=1.0)
    adjusted = uplift.apply(KINDS_BY_KEY["quinella"], 1, table)
    assert adjusted.sum() == pytest.approx(table.sum())
    assert adjusted[_index("quinella", 1, 4)] > table[_index("quinella", 1, 4)]
    assert uplift.apply(KINDS_BY_KEY["quinella"], 2, table) is None


def test_ワイドの市場の確率は当たりの組の数の3にそろえる() -> None:
    odds = pd.DataFrame({"rid": [1, 1, 1], "h1": [1, 1, 2], "h2": [2, 3, 3], "odds": [1.5, 1.5, 1.5]})
    table = MarketComboTable(KINDS_BY_KEY["wide"], odds).get(1)
    assert table[_index("wide", 1, 2)] == pytest.approx(1.0)


def test_帯ごとの直しは人気薄の組を下げて合計は変えない() -> None:
    odds = pd.DataFrame({"rid": [1, 1], "h1": [1, 1], "h2": [2, 3], "odds": [2.0, 50.0]})
    correction = OddsBandCalibrator((0, 10, 1e9), shrink=0.0)
    correction.add(np.array([2.0, 50.0]), np.array([10.0, 10.0]), np.array([10.0, 5.0]))
    plain = MarketComboTable(KINDS_BY_KEY["quinella"], odds).get(1)
    fixed = MarketComboTable(KINDS_BY_KEY["quinella"], odds, correction).get(1)
    assert fixed[_index("quinella", 1, 3)] < plain[_index("quinella", 1, 3)]
    assert fixed[_index("quinella", 1, 2)] + fixed[_index("quinella", 1, 3)] == pytest.approx(1.0)


def test_3連単はその券種自身からだけ作り_ワイドは3連複からも作る() -> None:
    assert {variant.origin for variant in variants_for(KINDS_BY_KEY["trifecta"])} == {OWN}
    assert {variant.origin for variant in variants_for(KINDS_BY_KEY["wide"])} == {OWN, TRIFECTA, TRIO}
    assert len(variants_for(KINDS_BY_KEY["quinella"])) == 9


def test_出どころは元の券種を選べる() -> None:
    trifecta_odds = pd.DataFrame({"rid": [1, 1], "h1": [1, 2], "h2": [2, 1], "h3": [3, 3],
                                  "odds": [2.0, 2.0]})
    quinella_odds = pd.DataFrame({"rid": [1, 1], "h1": [1, 1], "h2": [2, 3], "odds": [1.5, 3.0]})
    tables = {TRIFECTA: MarketComboTable(KINDS_BY_KEY["trifecta"], trifecta_odds),
              OWN: MarketComboTable(KINDS_BY_KEY["quinella"], quinella_odds)}
    kind = KINDS_BY_KEY["quinella"]
    from_trifecta = MarketSource(TRIFECTA, tables, _no_uplift()).table(kind, 1)
    from_own = MarketSource(OWN, tables, _no_uplift()).table(kind, 1)
    # 3連単は 1→2→3 と 2→1→3 だけ売れていて、どちらも 1・2 が1・2着なので、馬連 1-2 は 1。
    assert from_trifecta[_index("quinella", 1, 2)] == pytest.approx(1.0)
    assert from_own[_index("quinella", 1, 2)] == pytest.approx(2 / 3)
