"""オッズを使わないモデルの確率で、全券種を期待値で買って確かめる（研究「馬の力と展開でオッズに勝つ」の入口④）。

    uv run --with pyarrow --with tabulate python research/馬の力と展開でオッズに勝つ/backtest.py --predictions 全年

``experiment.py --also-placed --years 2018 … 2026`` の予測（``実験/<名前>_予測.parquet``）を使う。
オッズは、期待値の値段と精算にだけ使い、確率には入れない。組み合わせの券種の確率は、モデルの1着の確率から
Stern の補正を入れた Harville の式で作る（べき乗はモデルの確率と着順から推定し、オッズは使わない）。
確率は前の年までの実績でオッズの帯ごとに直し、線は前半（2019〜2021年）だけで決め、後半（2022〜2026年）で確かめる。
買い目のオッズ・払戻は、研究「回収率100超」の中間データ（``extract_tickets.py``）を使う。
出力は ``reports/馬の力と展開でオッズに勝つ/検証の結果.md``（Git 対象外）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 回収率100超.analysis.market import RaceFinishSample, SternFitter, SternProbabilities  # noqa: E402
from 回収率100超.analysis.ticket import PlacePriceEstimator  # noqa: E402
from 回収率100超.analysis.tickets import (  # noqa: E402
    EARLY_YEARS,
    LATE_YEARS,
    TICKET_KINDS,
    ComboProbability,
    LineStudy,
    OddsBandCalibrator,
    RaceWinTable,
    StudyResult,
    TicketKind,
    YearTicketScorer,
)

DEFAULT_OUT = Path("reports/馬の力と展開でオッズに勝つ")
DEFAULT_TICKETS = Path("reports/回収率100超/cache")
FIRST_YEAR = 2018
#: 複勝の見込みの払戻倍率の帯と、較正の帯（最低オッズ）。
PLACE_BANDS: tuple[float, ...] = (0, 1.5, 2, 3, 5, 10, 20, 1e9)


def main() -> None:
    parser = argparse.ArgumentParser(description="オッズを使わないモデルで全券種を確かめる", allow_abbrev=False)
    parser.add_argument("--predictions", required=True, help="実験の名前（実験/<名前>_予測.parquet）")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--tickets-cache", type=Path, default=DEFAULT_TICKETS)
    parser.add_argument("--last-year", type=int, default=2026)
    args = parser.parse_args()

    predictions = pd.read_parquet(args.out / "実験" / f"{args.predictions}_予測.parquet")
    finish = pd.read_parquet(args.out / "cache" / "dataset.parquet", columns=["race_id", "horse_no", "finish"])
    predictions = predictions.merge(finish, on=["race_id", "horse_no"], how="left")
    predictions["rid"] = predictions["race_id"].astype("int64")
    # rid の先頭 8桁が開催日（YYYYMMDD）。信頼区間は開催日を単位に取り直す。
    day_of = predictions.drop_duplicates("rid").set_index("rid")["race_id"].str[:8]
    stern = _fit_stern(predictions)
    wins = RaceWinTable(predictions["rid"], predictions["horse_no"], predictions["p_win"])
    results = {"place": _study_place(predictions, args.tickets_cache, day_of)}
    for kind in TICKET_KINDS:
        results[kind.key] = _study_kind(kind, args, ComboProbability(stern), wins, day_of)
    _write(results, args.out / f"検証の結果_{args.predictions}.md")


def _fit_stern(predictions: pd.DataFrame) -> SternProbabilities:
    """Stern のべき乗を、評価に使わない 2018年の、モデルの1着の確率と着順から推定する。"""
    early = predictions[predictions["year"] == FIRST_YEAR]
    lam, mu = SternFitter().fit(RaceFinishSample("p_win").build(early, limit=3000))
    print(f"Stern のべき乗（モデルから）: λ={lam:.4f}, μ={mu:.4f}", flush=True)
    return SternProbabilities(lam, mu)


def _study_place(predictions: pd.DataFrame, cache: Path, day_of: pd.Series) -> StudyResult:
    """複勝: 3着以内の確率 × 受け取る額の見込み（最低オッズ × 帯ごとの倍率）。確率は前の年までの実績で直す。"""
    runners = pd.read_parquet(cache / "runners.parquet", columns=["rid", "horse_no", "place_odds_low", "place_payout"])
    runners["rid"] = runners["rid"].astype("int64")
    table = predictions.merge(runners.rename(columns={"place_payout": "payout_hr"}), on=["rid", "horse_no"], how="inner")
    table = table[table["place_odds_low"] > 0]
    calibrator = OddsBandCalibrator(PLACE_BANDS)
    frames = []
    for year in range(FIRST_YEAR, int(table["year"].max()) + 1):
        rows = table[table["year"] == year]
        train = table[table["year"] < year]
        estimator = PlacePriceEstimator().fit(train["place_odds_low"], train["payout_hr"], train["placed"]) \
            if len(train) else None
        price = estimator.estimate(rows["place_odds_low"]) if estimator else rows["place_odds_low"] * 1.19
        probability = rows["p_placed"] * calibrator.factors(rows["place_odds_low"].to_numpy())
        frames.append(pd.DataFrame({"rid": rows["rid"], "year": year, "ev": probability * price,
                                    "payout": rows["payout_hr"], "stake": 100.0}))
        calibrator.add(rows["place_odds_low"].to_numpy(), rows["p_placed"].to_numpy(),
                       (rows["payout_hr"] > 0).to_numpy(dtype=float))
    tickets = pd.concat(frames, ignore_index=True)
    tickets = tickets[tickets["year"] >= EARLY_YEARS[0]].assign(day=lambda t: t["rid"].map(day_of))
    return LineStudy().run(tickets, cap=3)


def _study_kind(kind: TicketKind, args: argparse.Namespace, probability: ComboProbability, wins: RaceWinTable,
                day_of: pd.Series) -> StudyResult:
    tickets_dir = args.tickets_cache / "tickets"
    payouts = pd.read_parquet(tickets_dir / f"{kind.key}_payout.parquet")
    calibrator = OddsBandCalibrator(kind.bands)
    scorer = YearTicketScorer(kind, probability, wins)
    wide_hits = _wide_hits(tickets_dir, payouts, args.last_year) if kind.lowest_price else None
    frames = []
    for year in range(FIRST_YEAR, args.last_year + 1):
        odds = pd.read_parquet(tickets_dir / f"{kind.key}_{year}.parquet")
        price = odds["odds"] if wide_hits is None else _wide_price(odds, wide_hits, year)
        score = scorer.score(odds, payouts, calibrator, price, keep_all=False)
        calibrator.add(score.raw["odds"].to_numpy(), score.raw["raw_probability"].to_numpy(), score.raw["hit"].to_numpy())
        frames.append(score.candidates.assign(year=year))
        print(f"  {kind.name} {year}: 期待値 1.0 以上 {len(score.candidates):,} 点", flush=True)
    tickets = pd.concat(frames, ignore_index=True)
    tickets = tickets[tickets["year"] >= EARLY_YEARS[0]].assign(day=lambda t: t["rid"].map(day_of), stake=100.0)
    return LineStudy().run(tickets, cap=kind.cap)


def _wide_hits(tickets_dir: Path, payouts: pd.DataFrame, last_year: int) -> pd.DataFrame:
    """ワイドの当たった買い目の、年・最低オッズ・払戻（研究「回収率100超」の backtest_tickets.py と同じ見積もり方）。"""
    frames = []
    for year in range(2016, last_year + 1):
        hits = pd.read_parquet(tickets_dir / f"wide_{year}.parquet").merge(payouts, on=["rid", "h1", "h2"])
        frames.append(hits.assign(year=year)[["year", "odds", "payout"]])
    return pd.concat(frames, ignore_index=True)


def _wide_price(odds: pd.DataFrame, wide_hits: pd.DataFrame, year: int) -> pd.Series:
    """ワイドで受け取る額の見込み = 最低オッズ × 帯ごとの倍率（評価する年より前の当たりから）。"""
    train = wide_hits[wide_hits["year"] < year]
    estimator = PlacePriceEstimator().fit(train["odds"], train["payout"], pd.Series(1, index=train.index))
    return estimator.estimate(odds["odds"])


def _write(results: dict[str, StudyResult], path: Path) -> None:
    names = {"place": "複勝", **{kind.key: kind.name for kind in TICKET_KINDS}}
    rows = []
    for key, study in results.items():
        for line in study.lines:
            rows.append({"券種": names[key], "線": line.line, "前半の点数": line.early.bets,
                         "前半の回収率": round(line.early.rate, 1), "後半の点数": line.late.bets,
                         "後半の回収率": round(line.late.rate, 1),
                         "後半の90%の幅": f"{line.late.low:.1f}〜{line.late.high:.1f}",
                         "選んだ線": "◯" if study.chosen is line else "",
                         "採否": ("採用" if study.adopted else "不採用") if study.chosen is line else ""})
    text = ["# オッズを使わないモデルでの検証の結果", "",
            f"線は前半（{EARLY_YEARS[0]}〜{EARLY_YEARS[1]}年）だけで選び、後半（{LATE_YEARS[0]}〜{LATE_YEARS[1]}年）で確かめた。"
            "確定オッズで精算。JV-Data 由来の値を含むため Git の対象外。", "", pd.DataFrame(rows).to_markdown(index=False), ""]
    path.write_text("\n".join(text), encoding="utf-8")
    print(f"書き出しました: {path}", flush=True)


if __name__ == "__main__":
    main()
