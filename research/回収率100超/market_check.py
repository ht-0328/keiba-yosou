"""市場（単勝オッズ）そのものの歪みを測る（研究「回収率100超」の入口③・診断用）。

    uv run python research/回収率100超/market_check.py

「人気薄が買われすぎる偏り」を、べき乗ではなく log の折れ線で直したときに、勝率の当たり具合が
どれだけ良くなるかを年ごとに出す。この研究の土台（02-市場の測り方.md の 2）が成り立っているかの確認で、
買い方を決めるものではない。出力は標準出力だけ。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 回収率100超.analysis.cache_loader import CacheLoader  # noqa: E402
from 回収率100超.analysis.market import (  # noqa: E402
    ConditionalLogit,
    LogProbabilityBasis,
    RaceSoftmax,
)

DEFAULT_CACHE = Path("reports/回収率100超/cache")


def main() -> None:
    parser = argparse.ArgumentParser(description="市場の歪みを測る", allow_abbrev=False)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--first-test-year", type=int, default=2019)
    args = parser.parse_args()

    table = CacheLoader(args.cache).read().sort_values(["rid", "horse_no"]).reset_index(drop=True)
    features = LogProbabilityBasis().build(table["単勝から見た勝率"].to_numpy())
    won = table["won"].to_numpy()
    year = table["year"].to_numpy()

    print("その年より前で学習して、その年で測る。値はレース1つあたりの負のログ尤度（小さいほど良い）。")
    print(f"{'年':>6} {'レース':>8} {'オッズそのまま':>14} {'折れ線で直す':>14} {'差':>10}")
    for test_year in range(args.first_test_year, int(year.max()) + 1):
        train, test = year < test_year, year == test_year
        if not test.any():
            continue
        fitted = ConditionalLogit().fit(features[train], pd.factorize(table.loc[train, "rid"])[0],
                                        won[train])
        test_races = pd.factorize(table.loc[test, "rid"])[0]
        corrected = fitted.predict(features[test], test_races)
        market = RaceSoftmax(test_races).to_probability(
            np.log(np.clip(table.loc[test, "単勝から見た勝率"].to_numpy(), 1e-9, None)))
        before, after = _loss(market, won[test]), _loss(corrected, won[test])
        print(f"{test_year:>6} {test_races.max() + 1:>8,} {before:>14.5f} {after:>14.5f} "
              f"{before - after:>+10.5f}")


def _loss(probability: np.ndarray, won: np.ndarray) -> float:
    """1着の馬に付けた確率の log の、レース1つあたりの平均（符号を反転）。"""
    return float(-np.log(np.clip(probability[won == 1], 1e-12, None)).mean())


if __name__ == "__main__":
    main()
