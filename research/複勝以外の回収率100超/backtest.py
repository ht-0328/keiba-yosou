"""手順2・3: 市場の組の確率から作る作り方で、複勝以外の券種を確かめる（研究「複勝以外の回収率100超」の入口②）。

    uv run python research/複勝以外の回収率100超/backtest.py

先に研究「回収率100超」の ``extract.py``・``extract_tickets.py``・``backtest_tickets.py`` を回しておく
（中間データと、保存した予測を使う。ここでは学習しない）。

券種ごとに、次の作り方をすべて試す（``analysis/variant.py``）。
- 組の確率の出どころ: その券種自身のオッズ ／ 3連単のオッズ ／ 3連単を先に直したもの ／ 3連複のオッズ（ワイドだけ）
- 馬ごとの上げ下げの強さ: 0 ／ 0.5 ／ 1
確率は前の年までの実績でオッズの帯ごとに直し、期待値が線以上の買い目を買う（1レースの点数に上限あり）。
線は前半（2019〜2021年）だけで決め、後半（2022〜2026年）で確かめる。作り方も前半だけで1つ選ぶ。
出力は ``reports/複勝以外の回収率100超/検証の結果.md``（Git 対象外）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 回収率100超.analysis.tickets import (  # noqa: E402
    EARLY_YEARS,
    KINDS_BY_KEY,
    LATE_YEARS,
    TICKET_KINDS,
    LineStudy,
    OddsBandCalibrator,
    StudyResult,
    TicketKind,
    WidePriceBook,
    YearTicketScorer,
)
from 複勝以外の回収率100超.analysis import OWN, TRIFECTA, TRIO, HorseUplift, MarketComboTable, MarketSource  # noqa: E402
from 複勝以外の回収率100超.analysis.trifecta_corrections import TrifectaCorrections  # noqa: E402
from 複勝以外の回収率100超.analysis.variant import STRENGTHS, Variant, variants_for  # noqa: E402

DEFAULT_CACHE = Path("reports/回収率100超/cache")
DEFAULT_OUT = Path("reports/複勝以外の回収率100超")
#: 中間データの最初の年と、予測がある最初の年（2018年は較正にだけ使う）。
FIRST_DATA_YEAR, FIRST_PREDICTED_YEAR = 2016, 2018
UNIT_YEN = 100.0


def main() -> None:
    parser = argparse.ArgumentParser(description="市場の組の確率から作る作り方で確かめる", allow_abbrev=False)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--last-year", type=int, default=2026)
    parser.add_argument("--kinds", nargs="*", default=[kind.key for kind in TICKET_KINDS])
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    tickets_dir = args.cache / "tickets"
    predictions = pd.read_parquet(args.cache / "predictions_win_place.parquet")
    day_of = predictions.drop_duplicates("rid").set_index("rid")["day"]
    uplifts = {strength: HorseUplift(predictions["rid"], predictions["horse_no"], predictions["p_placed"],
                                     predictions["market_placed"], strength) for strength in STRENGTHS}
    print("3連単の直しの倍率を作っています...", flush=True)
    corrections = TrifectaCorrections(tickets_dir, FIRST_DATA_YEAR, args.last_year)
    results = {key: _study_kind(KINDS_BY_KEY[key], tickets_dir, uplifts, corrections, day_of, args.last_year)
               for key in args.kinds}
    _write_report(results, args.out / "検証の結果.md")


def _study_kind(kind: TicketKind, tickets_dir: Path, uplifts: dict[float, HorseUplift],
                corrections: TrifectaCorrections, day_of: pd.Series, last_year: int) -> dict[Variant, StudyResult]:
    """1つの券種の、すべての作り方の成績。"""
    variants = variants_for(kind)
    payouts = pd.read_parquet(tickets_dir / f"{kind.key}_payout.parquet")
    wide_prices = WidePriceBook(tickets_dir, payouts, FIRST_DATA_YEAR, last_year) if kind.lowest_price else None
    calibrators = {variant: OddsBandCalibrator(kind.bands) for variant in variants}
    candidates: dict[Variant, list[pd.DataFrame]] = {variant: [] for variant in variants}
    for year in range(FIRST_PREDICTED_YEAR, last_year + 1):
        odds = pd.read_parquet(tickets_dir / f"{kind.key}_{year}.parquet")
        price = odds["odds"] if wide_prices is None else wide_prices.price(odds, year)
        tables = _tables(kind, tickets_dir, year, odds, corrections)
        _score_year(kind, variants, tables, uplifts, odds, payouts, price, calibrators, candidates, year)
        print(f"  {kind.name} {year}: 作り方 {len(variants)} 通りを点数付けしました", flush=True)
    return {variant: _study(pd.concat(found, ignore_index=True), day_of, kind.cap)
            for variant, found in candidates.items()}


def _tables(kind: TicketKind, tickets_dir: Path, year: int, odds: pd.DataFrame,
            corrections: TrifectaCorrections) -> dict[bool, dict[str, MarketComboTable]]:
    """組の確率の元になる表。キーは「3連単を先に直すか」。"""
    own = {OWN: MarketComboTable(kind, odds)}
    if kind.key == "trifecta":
        return {False: own}
    trifecta_kind = KINDS_BY_KEY["trifecta"]
    trifecta_odds = pd.read_parquet(tickets_dir / f"trifecta_{year}.parquet")
    extra = {}
    if kind.key == "wide":
        extra[TRIO] = MarketComboTable(KINDS_BY_KEY["trio"], pd.read_parquet(tickets_dir / f"trio_{year}.parquet"))
    return {False: {**own, **extra, TRIFECTA: MarketComboTable(trifecta_kind, trifecta_odds)},
            True: {**own, **extra, TRIFECTA: MarketComboTable(trifecta_kind, trifecta_odds,
                                                              corrections.for_year(year))}}


def _score_year(kind: TicketKind, variants: list[Variant], tables: dict[bool, dict[str, MarketComboTable]],
                uplifts: dict[float, HorseUplift], odds: pd.DataFrame, payouts: pd.DataFrame, price: pd.Series,
                calibrators: dict[Variant, OddsBandCalibrator], candidates: dict[Variant, list[pd.DataFrame]],
                year: int) -> None:
    """1年ぶんを、作り方ごとに点数付けする。較正は、その年を点数付けしてから足す（次の年から効く）。"""
    for variant in variants:
        source = MarketSource(variant.origin, tables[variant.corrected], uplifts[variant.strength])
        score = YearTicketScorer(kind, source).score(odds, payouts, calibrators[variant], price, keep_all=False)
        calibrators[variant].add(score.raw["odds"].to_numpy(), score.raw["raw_probability"].to_numpy(),
                                 score.raw["hit"].to_numpy())
        candidates[variant].append(score.candidates.assign(year=year))


def _study(candidates: pd.DataFrame, day_of: pd.Series, cap: int) -> StudyResult:
    tickets = candidates[candidates["year"] >= EARLY_YEARS[0]]
    tickets = tickets.assign(day=tickets["rid"].map(day_of), stake=UNIT_YEN)
    return LineStudy().run(tickets, cap=cap)


def _best(results: dict[Variant, StudyResult]) -> tuple[Variant, StudyResult] | None:
    """前半の回収率がいちばん高い作り方（線を選べたものの中から）。後半の結果は使わない。"""
    usable = [(variant, study) for variant, study in results.items() if study.chosen is not None]
    return max(usable, key=lambda pair: pair[1].chosen.early.rate, default=None)


def _write_report(results: dict[str, dict[Variant, StudyResult]], path: Path) -> None:
    lines = ["# 複勝以外の回収率100超: 検証の結果", "",
             f"作り方と線は前半（{EARLY_YEARS[0]}〜{EARLY_YEARS[1]}年）だけで選び、後半（{LATE_YEARS[0]}〜"
             f"{LATE_YEARS[1]}年）で確かめた。採用の基準は、後半の回収率が 100% を超え、90% の幅の下の端も 100% を超えること。",
             "確定オッズでの検証。JV-Data 由来の値を含むため、この文書は Git の対象外。", "",
             "## まとめ（券種ごとに、前半で選んだ作り方）", "", _summary(results), ""]
    for key, by_variant in results.items():
        lines += [f"## {KINDS_BY_KEY[key].name}（作り方ごと。線は作り方ごとに前半で選んだもの）", "",
                  _variant_table(by_variant), ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"書き出しました: {path}", flush=True)


def _summary(results: dict[str, dict[Variant, StudyResult]]) -> str:
    rows = []
    for key, by_variant in results.items():
        best = _best(by_variant)
        rows.append(_row(KINDS_BY_KEY[key].name, best))
    return pd.DataFrame(rows).to_markdown(index=False)


def _row(name: str, best: tuple[Variant, StudyResult] | None) -> dict[str, object]:
    if best is None:
        return {"券種": name, "作り方": "（前半の当たりが足りない）", "採否": "不採用"}
    variant, study = best
    return {"券種": name, "作り方": variant.name, **_numbers(study),
            "採否": "採用" if study.adopted else "不採用"}


def _variant_table(by_variant: dict[Variant, StudyResult]) -> str:
    rows = [{"作り方": variant.name, **_numbers(study)} for variant, study in by_variant.items()]
    return pd.DataFrame(rows).to_markdown(index=False)


def _numbers(study: StudyResult) -> dict[str, object]:
    chosen = study.chosen
    if chosen is None:
        return {"線": "−"}
    return {"線": chosen.line, "前半の点数": chosen.early.bets, "前半の回収率": round(chosen.early.rate, 1),
            "後半の点数": chosen.late.bets, "後半の回収率": round(chosen.late.rate, 1),
            "後半の90%の幅": f"{chosen.late.low:.1f}〜{chosen.late.high:.1f}"}


if __name__ == "__main__":
    main()
