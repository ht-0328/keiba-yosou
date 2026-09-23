"""学習と検証をまとめて回し、結果を reports/回収率100超/ に書く（研究「回収率100超」の入口②）。

    uv run python research/回収率100超/backtest.py

先に ``extract.py`` で中間データを作っておく。ここでは元DB に触らない。
学習はウォークフォワード（その年より前で学習 → その年で予測）で、1年ずつ進む。
出力は ``reports/回収率100超/``（Git 対象外）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 回収率100超.analysis.backtest import Payback, PaybackInterval, WalkForwardYears  # noqa: E402
from 回収率100超.analysis.bet_rule import PLACE_RULE  # noqa: E402
from 回収率100超.analysis.cache_loader import CacheLoader  # noqa: E402
from 回収率100超.analysis.feature import LearningTable  # noqa: E402
from 回収率100超.analysis.market import (  # noqa: E402
    RaceFinishSample,
    SternFitter,
    SternProbabilities,
)
from 回収率100超.analysis.probability import GradientBoostingPair  # noqa: E402
from 回収率100超.analysis.ticket import PlacePriceEstimator, RacePlaceProbability  # noqa: E402

DEFAULT_CACHE = Path("reports/回収率100超/cache")
DEFAULT_OUT = Path("reports/回収率100超")
#: Stern のべき乗を推定するのに使うレースの数。2つの値を決めるだけなので、これで足りる。
STERN_SAMPLE_RACES = 6000


def main() -> None:
    parser = argparse.ArgumentParser(description="学習と検証を回す", allow_abbrev=False)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--first-test-year", type=int, default=2019)
    parser.add_argument("--last-test-year", type=int, default=2026)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    runners = CacheLoader(args.cache).read()
    stern = _fit_stern(runners, args.first_test_year)
    table, features = LearningTable(stern).build(runners)
    table["3着以内の確率"] = _walk_forward(table, features, "placed", args)
    table["3着以内の確率"] = RacePlaceProbability().normalize(
        table["3着以内の確率"], table["rid"], table["place_places"])
    table["想定払戻倍率"] = _place_price(table, args)
    table["複勝の期待値"] = table["3着以内の確率"] * table["想定払戻倍率"]

    evaluated = table[table["3着以内の確率"].notna() & table["複勝の期待値"].notna()]
    _write_report(evaluated[PLACE_RULE.selects(evaluated["複勝の期待値"])], args.out / "検証の結果.md")


def _fit_stern(runners: pd.DataFrame, first_test_year: int) -> SternProbabilities:
    """Stern のべき乗を、評価に使わない年（最初の評価年より前）の着順から推定する。"""
    early = runners[runners["year"] < first_test_year]
    races = RaceFinishSample("単勝から見た勝率").build(early, limit=STERN_SAMPLE_RACES)
    lam, mu = SternFitter().fit(races)
    print(f"Stern のべき乗: λ={lam:.4f}（2着）, μ={mu:.4f}（3着）", flush=True)
    return SternProbabilities(lam, mu)


def _walk_forward(table: pd.DataFrame, features: list[str], target_column: str,
                  args: argparse.Namespace) -> np.ndarray:
    """年ごとに学習し直して、その年の確率を予測する。"""
    target = table[target_column].to_numpy()
    predicted = np.full(len(table), np.nan)
    frame = table[features]
    for split in WalkForwardYears(table["year"].to_numpy(), args.first_test_year,
                                  args.last_test_year):
        pair = GradientBoostingPair().fit(frame[split.fit], target[split.fit],
                                          frame[split.valid], target[split.valid])
        predicted[split.test] = pair.predict(frame[split.test])
        print(f"  {split.test_year}: 予測しました（{int(split.test.sum()):,} 頭）", flush=True)
    return predicted


def _place_price(table: pd.DataFrame, args: argparse.Namespace) -> pd.Series:
    """複勝の想定払戻倍率。評価する年より前の的中だけから作る。"""
    price = pd.Series(np.nan, index=table.index)
    for test_year in range(args.first_test_year, args.last_test_year + 1):
        train = table[table["year"] < test_year]
        if train.empty:
            continue
        estimator = PlacePriceEstimator().fit(train["place_odds_low"], train["place_payout"],
                                              train["placed"])
        rows = table["year"] == test_year
        price[rows] = estimator.estimate(table.loc[rows, "place_odds_low"])
    return price


def _write_report(bought: pd.DataFrame, path: Path) -> None:
    """買った馬券の成績を書き出す。"""
    interval = PaybackInterval()
    rows = []
    for year, group in bought.groupby("year"):
        rows.append(_row(int(year), group, interval))
    rows.append(_row("合計", bought, interval))
    lines = [f"# 回収率100超 — 複勝・{PLACE_RULE.describe()}", "",
             "ウォークフォワード（その年より前で学習 → その年で予測）。",
             "JV-Data 由来の値を含むため、この文書は Git の対象外。", "",
             pd.DataFrame(rows).to_markdown(index=False), ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"書き出しました: {path}")


def _row(label: object, group: pd.DataFrame, interval: PaybackInterval) -> dict[str, object]:
    payback = Payback(group["place_payout"])
    low, high = interval.of(group["day"], group["place_payout"])
    return {"年": label, "買い目": payback.bet_count, "的中率": round(payback.hit_rate, 3),
            "回収率": round(payback.rate, 1), "90%の下限": round(low, 1),
            "90%の上限": round(high, 1)}


if __name__ == "__main__":
    main()
