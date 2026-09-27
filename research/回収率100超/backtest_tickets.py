"""複勝以外の券種を期待値で買ったときの回収率を、年ごとのウォークフォワードで確かめる（研究「回収率100超」の入口⑤）。

    uv run python research/回収率100超/backtest_tickets.py

先に ``extract.py`` と ``extract_tickets.py`` で中間データを作っておく。ここでは元DB に触らない。

1. 年ごとに「1着になるか」と「3着以内に入るか」を学習して予測する（2018〜2026年）。予測は中間データの置き場に
   保存し、2回目からは使い回す（``--retrain`` で学習し直す）。
2. 券種ごと・年ごとに、全部の買い目の確率・期待値・払戻を出す。確率は、前の年までの実績でオッズの帯ごとに直す。
3. 買い方2通り（期待値が線以上の買い目を全部／印のルールの買い目）で、線を前半（2019〜2021年）だけで決め、
   後半（2022〜2026年）で確かめる。比べる目安として、複勝も同じ手順で出す。
4. 結果を ``reports/回収率100超/券種ごとの検証.md``（Git 対象外）に書く。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 回収率100超.analysis.backtest import WalkForwardYears  # noqa: E402
from 回収率100超.analysis.cache_loader import CacheLoader  # noqa: E402
from 回収率100超.analysis.feature import LearningTable  # noqa: E402
from 回収率100超.analysis.feature.learning_table import PLACE_BASELINE  # noqa: E402
from 回収率100超.analysis.market import RaceFinishSample, SternFitter, SternProbabilities  # noqa: E402
from 回収率100超.analysis.probability import GradientBoostingPair  # noqa: E402
from 回収率100超.analysis.ticket import PlacePriceEstimator, RacePlaceProbability  # noqa: E402
from 回収率100超.analysis.tickets import (  # noqa: E402
    EARLY_YEARS,
    LATE_YEARS,
    TICKET_KINDS,
    ComboProbability,
    LineStudy,
    MarkTickets,
    OddsBandCalibrator,
    RaceMarks,
    RaceWinTable,
    StudyResult,
    TicketKind,
    YearTicketScorer,
)

DEFAULT_CACHE = Path("reports/回収率100超/cache")
DEFAULT_OUT = Path("reports/回収率100超")
PREDICTIONS_FILE = "predictions_win_place.parquet"
#: 予測を出す最初の年。2018年の予測は、2019年の確率の較正にだけ使う（評価には使わない）。
FIRST_PREDICTED_YEAR = 2018
#: Stern のべき乗を推定するのに使うレースの数（backtest.py と同じ）。
STERN_SAMPLE_RACES = 6000
#: 印の買い目がある券種。3連単・馬単には印のルールが無い。
MARK_KINDS = ("win", "wide", "quinella", "trio")
#: 「荒れそう」の決め方: 3連複が 3,000円（30倍）以上になる確率が、前の年のレースの上位 3割に入る。
UPSET_ODDS, UPSET_QUANTILE = 30.0, 0.7
#: 1点の額（円）。印のルールは、単位 × この額。
UNIT_YEN = 100.0


def main() -> None:
    parser = argparse.ArgumentParser(description="複勝以外の券種を確かめる", allow_abbrev=False)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--last-year", type=int, default=2026)
    parser.add_argument("--retrain", action="store_true", help="予測を使い回さずに学習し直す")
    args = parser.parse_args()

    runners = CacheLoader(args.cache).read()
    stern = _fit_stern(runners)
    table, features = LearningTable(stern).build(runners)
    predictions = _add_place_value(_predictions(table, features, args), table, args.last_year)
    day_of = predictions.drop_duplicates("rid").set_index("rid")["day"]
    wins = RaceWinTable(predictions["rid"], predictions["horse_no"], predictions["p_won"])
    mark_tickets = MarkTickets().build(RaceMarks().build(predictions))

    results: dict[str, dict[str, StudyResult]] = {"place": {"期待値で全部": _study_place(predictions)}}
    for kind in TICKET_KINDS:
        results[kind.key] = _study_kind(kind, args, ComboProbability(stern), wins, mark_tickets, day_of)
    _write_report(results, args.out / "券種ごとの検証.md")


def _fit_stern(runners: pd.DataFrame) -> SternProbabilities:
    """Stern のべき乗を、評価に使わない年（2019年より前）の着順から推定する（backtest.py と同じ）。"""
    early = runners[runners["year"] < EARLY_YEARS[0]]
    lam, mu = SternFitter().fit(RaceFinishSample("単勝から見た勝率").build(early, limit=STERN_SAMPLE_RACES))
    print(f"Stern のべき乗: λ={lam:.4f}（2着）, μ={mu:.4f}（3着）", flush=True)
    return SternProbabilities(lam, mu)


def _predictions(table: pd.DataFrame, features: list[str], args: argparse.Namespace) -> pd.DataFrame:
    """1頭ごとの「1着の確率」「3着以内の確率」。保存したものがあれば使い回す。"""
    path = args.cache / PREDICTIONS_FILE
    if path.exists() and not args.retrain:
        print(f"保存した予測を使います: {path}", flush=True)
        return pd.read_parquet(path)
    predicted = table[["rid", "horse_no", "year", "day", "popularity", "field", "place_places", "won",
                       "placed", "place_odds_low", "place_payout", PLACE_BASELINE]].copy()
    predicted["rid"] = predicted["rid"].astype("int64")
    predicted["p_won"] = _walk_forward(table, features, "won", args.last_year)
    predicted["p_placed"] = _walk_forward(table, features, "placed", args.last_year)
    predicted = predicted[predicted["p_won"].notna()].reset_index(drop=True)
    predicted["p_won"] = predicted["p_won"] / predicted.groupby("rid")["p_won"].transform("sum")
    predicted["p_placed"] = RacePlaceProbability().normalize(
        predicted["p_placed"], predicted["rid"], predicted["place_places"])
    predicted = predicted.rename(columns={PLACE_BASELINE: "market_placed"})
    predicted.to_parquet(path, index=False)
    return predicted


def _walk_forward(table: pd.DataFrame, features: list[str], target: str, last_year: int) -> np.ndarray:
    """年ごとに学習し直して、その年の確率を予測する（backtest.py と同じ作り）。"""
    values = table[target].to_numpy()
    predicted = np.full(len(table), np.nan)
    frame = table[features]
    for split in WalkForwardYears(table["year"].to_numpy(), FIRST_PREDICTED_YEAR, last_year):
        pair = GradientBoostingPair().fit(frame[split.fit], values[split.fit],
                                          frame[split.valid], values[split.valid])
        predicted[split.test] = pair.predict(frame[split.test])
        print(f"  {target} {split.test_year}: 予測しました（{int(split.test.sum()):,} 頭）", flush=True)
    return predicted


def _add_place_value(predictions: pd.DataFrame, table: pd.DataFrame, last_year: int) -> pd.DataFrame:
    """複勝の期待値（3着以内の確率 × 受け取る額の見込み）。見込みは評価する年より前の的中だけから作る。"""
    price = pd.Series(np.nan, index=predictions.index)
    for year in range(FIRST_PREDICTED_YEAR, last_year + 1):
        train = table[table["year"] < year]
        estimator = PlacePriceEstimator().fit(train["place_odds_low"], train["place_payout"], train["placed"])
        rows = predictions["year"] == year
        price[rows] = estimator.estimate(predictions.loc[rows, "place_odds_low"])
    return predictions.assign(place_ev=predictions["p_placed"] * price)


def _study_place(predictions: pd.DataFrame) -> StudyResult:
    """比べる目安: 複勝を、期待値が線以上なら全部買う（研究で 100% を超えた買い方と同じ）。"""
    tickets = predictions[predictions["year"] >= EARLY_YEARS[0]]
    tickets = pd.DataFrame({"rid": tickets["rid"], "year": tickets["year"], "day": tickets["day"],
                            "ev": tickets["place_ev"], "payout": tickets["place_payout"], "stake": UNIT_YEN})
    return LineStudy().run(tickets, cap=None)


def _study_kind(kind: TicketKind, args: argparse.Namespace, probability: ComboProbability,
                wins: RaceWinTable, mark_tickets: pd.DataFrame, day_of: pd.Series) -> dict[str, StudyResult]:
    """1つの券種を、年ごとに点数を付けてから、2通りの買い方で確かめる。"""
    tickets_dir = args.cache / "tickets"
    payouts = pd.read_parquet(tickets_dir / f"{kind.key}_payout.parquet")
    wide_hits = _wide_hits(tickets_dir, payouts, args.last_year) if kind.lowest_price else None
    calibrator = OddsBandCalibrator(kind.bands)
    scorer = YearTicketScorer(kind, probability, wins)
    candidates, marked, upset = [], [], []
    for year in range(FIRST_PREDICTED_YEAR, args.last_year + 1):
        odds = pd.read_parquet(tickets_dir / f"{kind.key}_{year}.parquet")
        score = scorer.score(odds, payouts, calibrator, _price(odds, wide_hits, year),
                             keep_all=kind.key in MARK_KINDS)
        calibrator.add(score.raw["odds"].to_numpy(), score.raw["raw_probability"].to_numpy(),
                       score.raw["hit"].to_numpy())
        candidates.append(score.candidates.assign(year=year))
        marked.append(_mark_rows(score.all_rows, mark_tickets, kind).assign(year=year))
        upset.append(_upset_probability(score.all_rows, kind).assign(year=year))
        print(f"  {kind.name} {year}: 期待値 1.0 以上 {len(score.candidates):,} 点", flush=True)
    everything = _for_evaluation(pd.concat(candidates, ignore_index=True), day_of).assign(stake=UNIT_YEN)
    results = {"期待値で全部": LineStudy().run(everything, cap=kind.cap)}
    if kind.key in MARK_KINDS:
        chosen = _choose_variant(pd.concat(marked, ignore_index=True), pd.concat(upset, ignore_index=True))
        marks = _for_evaluation(chosen, day_of)
        results["印のルール"] = LineStudy().run(marks.assign(stake=marks["stake_units"] * UNIT_YEN), cap=None)
    return results


def _wide_hits(tickets_dir: Path, payouts: pd.DataFrame, last_year: int) -> pd.DataFrame:
    """ワイドの当たった買い目の、年・最低オッズ・払戻（受け取る額の見込みを作るため）。"""
    frames = []
    for year in range(2016, last_year + 1):
        odds = pd.read_parquet(tickets_dir / f"wide_{year}.parquet")
        hits = odds.merge(payouts, on=["rid", "h1", "h2"], how="inner")
        frames.append(hits.assign(year=year)[["year", "odds", "payout"]])
    return pd.concat(frames, ignore_index=True)


def _price(odds: pd.DataFrame, wide_hits: pd.DataFrame | None, year: int) -> pd.Series:
    """受け取る額の見込み。ワイドは最低オッズ × 帯ごとの倍率（評価する年より前の当たりから）、ほかはオッズ。"""
    if wide_hits is None:
        return odds["odds"]
    train = wide_hits[wide_hits["year"] < year]
    estimator = PlacePriceEstimator().fit(train["odds"], train["payout"], pd.Series(1, index=train.index))
    return estimator.estimate(odds["odds"])


def _mark_rows(all_rows: pd.DataFrame, mark_tickets: pd.DataFrame, kind: TicketKind) -> pd.DataFrame:
    """印のルールの買い目に、期待値と払戻を付ける。売られなかった買い目は落とす。"""
    mine = mark_tickets[mark_tickets["kind"] == kind.key]
    return mine.merge(all_rows[["rid", "flat", "ev", "payout"]], on=["rid", "flat"], how="inner")


def _upset_probability(all_rows: pd.DataFrame, kind: TicketKind) -> pd.DataFrame:
    """3連複が 30倍以上になる確率（レースごと）。3連複以外は空。"""
    if kind.key != "trio":
        return pd.DataFrame(columns=["rid", "upset"])
    rows = all_rows[all_rows["odds"] >= UPSET_ODDS]
    return rows.groupby("rid", as_index=False)["probability"].sum().rename(columns={"probability": "upset"})


def _choose_variant(marked: pd.DataFrame, upset: pd.DataFrame) -> pd.DataFrame:
    """3連複は、荒れそうなレースで「荒れそう」の買い目、そうでなければ「通常」の買い目を使う。

    荒れそうの線は、前の年のレースの上位 3割（その年の結果は使わない）。荒れそうでも ☆ が無く
    「荒れそう」の買い目が無いレースは、「通常」の買い目を使う。
    """
    if upset.empty:
        return marked[marked["variant"] == "通常"]
    lines = upset.groupby("year")["upset"].quantile(UPSET_QUANTILE)
    upset = upset.assign(flag=upset["upset"] >= upset["year"].sub(1).map(lines))
    flagged = set(upset.loc[upset["flag"], "rid"])
    has_upset_tickets = set(marked.loc[marked["variant"] == "荒れそう", "rid"])
    use_upset = marked["rid"].isin(flagged & has_upset_tickets)
    return marked[(marked["variant"] == "荒れそう") == use_upset]


def _for_evaluation(tickets: pd.DataFrame, day_of: pd.Series) -> pd.DataFrame:
    """評価する年（2019年から）だけにして、開催日を付ける。"""
    tickets = tickets[tickets["year"] >= EARLY_YEARS[0]]
    return tickets.assign(day=tickets["rid"].map(day_of))


def _write_report(results: dict[str, dict[str, StudyResult]], path: Path) -> None:
    names = {"place": "複勝（比べる目安）", **{kind.key: kind.name for kind in TICKET_KINDS}}
    lines = ["# 券種ごとの検証", "",
             f"線は前半（{EARLY_YEARS[0]}〜{EARLY_YEARS[1]}年）だけで決め、後半（{LATE_YEARS[0]}〜"
             f"{LATE_YEARS[1]}年）で確かめた。採用の基準は、後半の回収率が 100% を超え、90% の幅の下の端も 100% を超えること。",
             "確定オッズでの検証（実際に買う締め切り前のオッズより楽観側）。JV-Data 由来の値を含むため、この文書は Git の対象外。",
             "", "## まとめ", "", _summary(results, names), ""]
    for key, studies in results.items():
        for method, study in studies.items():
            lines += [f"## {names[key]}・{method}", "", _detail(study), ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"書き出しました: {path}", flush=True)


def _summary(results: dict[str, dict[str, StudyResult]], names: dict[str, str]) -> str:
    rows = [_summary_row(names[key], method, study)
            for key, studies in results.items() for method, study in studies.items()]
    return pd.DataFrame(rows).to_markdown(index=False)


def _summary_row(name: str, method: str, study: StudyResult) -> dict[str, object]:
    chosen = study.chosen
    if chosen is None:
        return {"券種": name, "買い方": method, "選んだ線": "（前半の当たりが足りない）", "採否": "不採用"}
    late = chosen.late
    return {"券種": name, "買い方": method, "選んだ線": chosen.line, "前半の回収率": round(chosen.early.rate, 1),
            "後半の点数": late.bets, "後半の回収率": round(late.rate, 1),
            "後半の90%の幅": f"{late.low:.1f}〜{late.high:.1f}", "採否": "採用" if study.adopted else "不採用"}


def _detail(study: StudyResult) -> str:
    rows = [{"線": result.line, "前半の点数": result.early.bets, "前半の的中": result.early.hits,
             "前半の回収率": round(result.early.rate, 1), "後半の点数": result.late.bets,
             "後半の的中": result.late.hits, "後半の回収率": round(result.late.rate, 1),
             "後半の90%の幅": f"{result.late.low:.1f}〜{result.late.high:.1f}"} for result in study.lines]
    return pd.DataFrame(rows).to_markdown(index=False)


if __name__ == "__main__":
    main()
