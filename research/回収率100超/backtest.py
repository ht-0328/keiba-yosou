"""学習と検証をまとめて回し、結果を reports/回収率100超/ に書く（研究「回収率100超」の入口②）。

    uv run python research/回収率100超/backtest.py

先に ``extract.py`` で中間データを作っておく。ここでは元DB に触らない。
学習はウォークフォワード（その年より前で学習 → その年で予測）で、1年ずつ進む。
出力は ``reports/回収率100超/検証の結果.md``（Git 対象外）。1回の実行で、次の4つを書く。

1. 採用した線（``analysis/bet_rule.py`` の ``PLACE_RULE``）で買ったときの年ごとの成績
2. 線の選び方（線ごとの前半・後半の成績と、決まりで選んだ線。``PLACE_RULE`` と食い違えば知らせる）
3. 同じ線で、大穴（単勝オッズ 50倍以上）に絞ったとき
4. 運用の目安（参加するレースの数と割合、1レースの点数の分布、年ごとの金額、最大の連敗と落ち込み、
   結果として買う馬の傾向（頭数・人気・単勝オッズ）、金額を上げるときの上限）

1頭ごとの確率・期待値は ``reports/回収率100超/cache/place_predictions.parquet`` にも残す。
``--reuse`` を付けると、学習し直さずにその予測から表だけを書き直す（採用する線を変えたときなど）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 回収率100超.analysis.backtest import (  # noqa: E402
    EARLY_YEARS,
    LATE_YEARS,
    MIN_YEARLY_BETS,
    BetsPerRaceDistribution,
    BoughtHorseProfile,
    LineStudyTable,
    OperationSummary,
    PlaceLineChoice,
    PlaceLineStudy,
    RaceParticipation,
    StakeCeiling,
    WalkForwardYears,
    YearlyPaybackTable,
)
from 回収率100超.analysis.backtest.stake_ceiling import ALLOWED_DROP  # noqa: E402
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
#: 大穴とみなす単勝オッズ（倍）。
LONGSHOT_ODDS = 50.0
PREDICTIONS_FILE = "place_predictions.parquet"
#: レースごとの券種の売上（extract.py が作る）。金額の上限の見積もりに使う。
POOL_SIZE_FILE = "pool_size.parquet"
PREDICTION_COLUMNS = ["rid", "horse_no", "year", "day", "win_odds", "placed", "place_payout",
                      "3着以内の確率", "想定払戻倍率", "複勝の期待値"]


def main() -> None:
    parser = argparse.ArgumentParser(description="学習と検証を回す", allow_abbrev=False)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--first-test-year", type=int, default=2019)
    parser.add_argument("--last-test-year", type=int, default=2026)
    parser.add_argument("--reuse", action="store_true", help="学習し直さずに、残した予測から表だけを書き直す")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    evaluated = pd.read_parquet(args.cache / PREDICTIONS_FILE) if args.reuse else _predict(args)
    tickets = pd.DataFrame({"rid": evaluated["rid"], "year": evaluated["year"], "day": evaluated["day"],
                            "ev": evaluated["複勝の期待値"], "payout": evaluated["place_payout"]})
    study = PlaceLineChoice().run(tickets)
    bought = evaluated[PLACE_RULE.selects(evaluated["複勝の期待値"])]
    pools = pd.read_parquet(args.cache / POOL_SIZE_FILE)[["rid", "複勝プールの大きさ"]]
    _write_report(evaluated, bought.merge(pools, on="rid", how="left"), study, args.out / "検証の結果.md")


def _predict(args: argparse.Namespace) -> pd.DataFrame:
    """学習と予測をして、1頭ごとの確率・期待値を残す。"""
    runners = CacheLoader(args.cache).read()
    stern = _fit_stern(runners, args.first_test_year)
    table, features = LearningTable(stern).build(runners)
    table["3着以内の確率"] = _walk_forward(table, features, "placed", args)
    table["3着以内の確率"] = RacePlaceProbability().normalize(
        table["3着以内の確率"], table["rid"], table["place_places"])
    table["想定払戻倍率"] = _place_price(table, args)
    table["複勝の期待値"] = table["3着以内の確率"] * table["想定払戻倍率"]

    evaluated = table[table["3着以内の確率"].notna() & table["複勝の期待値"].notna()][PREDICTION_COLUMNS]
    evaluated.to_parquet(args.cache / PREDICTIONS_FILE, index=False)
    return evaluated


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


def _write_report(evaluated: pd.DataFrame, bought: pd.DataFrame, study: PlaceLineStudy, path: Path) -> None:
    """買った馬券の成績・線の選び方・大穴に絞ったとき・運用の目安を書き出す。"""
    lines = [f"# 回収率100超 — 複勝・{PLACE_RULE.describe()}", "",
             "ウォークフォワード（その年より前で学習 → その年で予測）。確定オッズでの検証。",
             "JV-Data 由来の値を含むため、この文書は Git の対象外。", "",
             "## 1. 採用した線で買ったときの年ごとの成績", "",
             _yearly_table(bought), "",
             *_line_section(study),
             f"## 3. 同じ線で、大穴（単勝オッズ {LONGSHOT_ODDS:.0f}倍以上）に絞ったとき", "",
             _yearly_table(bought[bought["win_odds"] >= LONGSHOT_ODDS]), "",
             *_operation_section(evaluated, bought)]
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"書き出しました: {path}")
    if study.chosen is None or study.chosen.line != PLACE_RULE.lower:
        print("注意: 決まりで選んだ線が PLACE_RULE と食い違っています（検証の結果.md の 2.）", flush=True)


def _yearly_table(bought: pd.DataFrame) -> str:
    return YearlyPaybackTable().build(bought).to_markdown(index=False)


def _line_section(study: PlaceLineStudy) -> list[str]:
    """線ごとの前半・後半の成績と、決まりで選んだ線。"""
    chosen = "なし" if study.chosen is None else f"{study.chosen.line:.2f}"
    agreement = "一致している" if study.chosen and study.chosen.line == PLACE_RULE.lower else "食い違っている"
    return [f"## 2. 線の選び方（前半 {EARLY_YEARS[0]}〜{EARLY_YEARS[1]}年で選び、後半 {LATE_YEARS[0]}〜{LATE_YEARS[1]}年で確かめる）",
            "",
            f"決まり: 前半で回収率が 100% を超え、前半の1年あたりの買い目が {MIN_YEARLY_BETS} 点以上残る線のうち、"
            "前半の回収率がいちばん高い線。後半の結果は選ぶのに使わない。", "",
            LineStudyTable().build(study).to_markdown(index=False), "",
            f"決まりで選んだ線: **{chosen}**（採用している線 {PLACE_RULE.lower:.2f} と{agreement}）", ""]


def _operation_section(evaluated: pd.DataFrame, bought: pd.DataFrame) -> list[str]:
    """この買い方に従うと、実際に何をどれだけ買うことになるか（1点 100円）。"""
    operation = OperationSummary()
    frame = pd.DataFrame({"year": bought["year"], "day": bought["day"], "rid": bought["rid"],
                          "payout": bought["place_payout"]})
    totals = operation.totals(frame)
    ceiling = StakeCeiling().summary(bought)
    profile = BoughtHorseProfile().tables(evaluated, bought)
    lines = ["## 4. 運用の目安（1点 100円）", "",
             "### 4-1. 参加するレースの数と割合", "",
             RaceParticipation().yearly(evaluated, bought).to_markdown(index=False), "",
             "### 4-2. 1レースの点数の分布", "",
             BetsPerRaceDistribution().table(bought).to_markdown(index=False), "",
             "### 4-3. 年ごとの金額と損益", "",
             operation.yearly(frame).to_markdown(index=False), "",
             f"- 最大の連敗: {totals.longest_losing_streak} 回",
             f"- 最大の落ち込み（それまでの最高の損益からの下がり幅）: {totals.max_drawdown:,.0f} 円",
             f"- 1レースで買う最大の点数: {totals.max_bets_per_race} 点", "",
             "### 4-4. 結果として買う馬の傾向", ""]
    for title, table in profile.items():
        lines += [f"**{title}**", "", table.to_markdown(index=False), ""]
    lines += ["### 4-5. 金額を上げるときの上限（目安）", "",
              f"自分の投票で見込みの払戻倍率が {ALLOWED_DROP:.0%} 以上下がらない、1点あたりの金額の見積もり"
              "（複勝の売上と見込みの払戻倍率から逆算した近似）。",
              f"- 見積もった買い目: {ceiling.bets} 点",
              f"- 1点あたりの上限の中央値: {ceiling.median:,.0f} 円",
              f"- 下から 1割の買い目の上限: {ceiling.lower_tenth:,.0f} 円（これより多く張ると、1割の買い目で倍率が目安以上に下がる）", ""]
    return lines

if __name__ == "__main__":
    main()
