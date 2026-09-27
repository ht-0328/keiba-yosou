"""手順1: 券種どうしの値段の食い違いが大きかったレースを集めて見る（研究「複勝以外の回収率100超」の入口①）。

    uv run python research/複勝以外の回収率100超/cases.py

線を決める前半の年（2019〜2021年）だけを見る。確かめに使う後半の年は見ない。
先に研究「回収率100超」の ``extract.py``・``extract_tickets.py``・``backtest_tickets.py`` を回しておく
（中間データと、保存した予測を使う）。出力は ``reports/複勝以外の回収率100超/事例.md``（Git 対象外）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通.codes import VENUE_NAMES  # noqa: E402

from 回収率100超.analysis.tickets import KINDS_BY_KEY, OddsBandCalibrator, TicketKind, YearTicketScorer  # noqa: E402
from 複勝以外の回収率100超.analysis import OWN, TRIFECTA, HorseUplift, MarketComboTable, MarketSource  # noqa: E402
from 複勝以外の回収率100超.analysis.gap_cases import GapCases  # noqa: E402

DEFAULT_CACHE = Path("reports/回収率100超/cache")
DEFAULT_OUT = Path("reports/複勝以外の回収率100超")
#: 見る年（前半）。
YEARS = (2019, 2020, 2021)
#: 見る券種と、成績を分けるオッズの帯。
TARGETS: dict[str, tuple[float, ...]] = {
    "win": (0, 5, 20, 1e9), "wide": (0, 5, 20, 1e9), "quinella": (0, 10, 50, 1e9),
    "exacta": (0, 20, 100, 1e9), "trio": (0, 30, 150, 1e9),
}
CASES_PER_KIND = 15


def main() -> None:
    parser = argparse.ArgumentParser(description="券種どうしの値段の食い違いの事例を集める", allow_abbrev=False)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    predictions = pd.read_parquet(args.cache / "predictions_win_place.parquet")
    uplift = HorseUplift(predictions["rid"], predictions["horse_no"], predictions["p_placed"],
                         predictions["market_placed"], strength=0.0)
    races = _race_info(args.cache)
    lines = ["# 券種どうしの値段の食い違いの事例（2019〜2021年）", "",
             "比 = 3連単のオッズから作った組の確率 ÷ その券種自身のオッズから作った組の確率。"
             "1 より大きい組は、3連単の市場から見て、その券種では割安に売られていた。",
             "回収率は、その帯の組を1点100円ずつ全部買ったとき（確定オッズ）。JV-Data 由来の値を含むため Git の対象外。", ""]
    for key, odds_bands in TARGETS.items():
        rows = _paired_rows(KINDS_BY_KEY[key], args.cache / "tickets", uplift)
        lines += _kind_section(KINDS_BY_KEY[key], GapCases(rows), odds_bands, races, predictions)
    (args.out / "事例.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"書き出しました: {args.out / '事例.md'}", flush=True)


def _paired_rows(kind: TicketKind, tickets_dir: Path, uplift: HorseUplift) -> pd.DataFrame:
    """年ごとに、その券種自身から見た確率と、3連単から見た確率を並べる（どちらも較正しない）。"""
    payouts = pd.read_parquet(tickets_dir / f"{kind.key}_payout.parquet")
    frames = []
    for year in YEARS:
        odds = pd.read_parquet(tickets_dir / f"{kind.key}_{year}.parquet")
        tables = {OWN: MarketComboTable(kind, odds),
                  TRIFECTA: MarketComboTable(KINDS_BY_KEY["trifecta"],
                                             pd.read_parquet(tickets_dir / f"trifecta_{year}.parquet"))}
        own = _score(kind, MarketSource(OWN, tables, uplift), odds, payouts)
        derived = _score(kind, MarketSource(TRIFECTA, tables, uplift), odds, payouts)
        frames.append(own.rename(columns={"probability": "own"}).merge(
            derived[["rid", "flat", "probability"]].rename(columns={"probability": "derived"}),
            on=["rid", "flat"]))
        print(f"  {kind.name} {year}: {len(frames[-1]):,} 点", flush=True)
    return pd.concat(frames, ignore_index=True)


def _score(kind: TicketKind, source: MarketSource, odds: pd.DataFrame, payouts: pd.DataFrame) -> pd.DataFrame:
    score = YearTicketScorer(kind, source).score(odds, payouts, OddsBandCalibrator(kind.bands), odds["odds"])
    return score.all_rows[["rid", "flat", "odds", "probability", "payout"]]


def _race_info(cache: Path) -> pd.DataFrame:
    runners = pd.read_parquet(cache / "runners.parquet")
    runners["rid"] = runners["rid"].astype("int64")
    races = runners.drop_duplicates("rid").set_index("rid")
    # トラックコード（コード表 2009）は 10〜22 が芝、23〜29 がダート。
    surface = np.where(pd.to_numeric(races["track_code"], errors="coerce") <= 22, "芝", "ダ")
    return pd.DataFrame({"日付": races["race_date"].dt.date, "競馬場": races["venue_code"].map(VENUE_NAMES),
                         "コース": pd.Series(surface, index=races.index) + races["distance_m"].astype(str),
                         "グレード": races["grade_code"].fillna("").str.strip()}, index=races.index)


def _kind_section(kind: TicketKind, gaps: GapCases, odds_bands: tuple[float, ...], races: pd.DataFrame,
                  predictions: pd.DataFrame) -> list[str]:
    cases = gaps.top_cases(CASES_PER_KIND)
    return [f"## {kind.name}", "", "### 比の帯ごとの成績", "", gaps.by_band().to_markdown(index=False), "",
            "### 比の帯 × オッズの帯", "", gaps.by_band_and_odds(odds_bands).to_markdown(index=False), "",
            f"### 比が大きかったレース（3連単から見た確率 {0.02} 以上の組、上位 {CASES_PER_KIND}）", "",
            _case_table(kind, cases, races, predictions).to_markdown(index=False), ""]


def _case_table(kind: TicketKind, cases: pd.DataFrame, races: pd.DataFrame,
                predictions: pd.DataFrame) -> pd.DataFrame:
    horses = _horses(kind, cases["flat"].to_numpy())
    info = races.reindex(cases["rid"]).reset_index(drop=True)
    popularity = predictions.set_index(["rid", "horse_no"])["popularity"]
    finish = predictions.set_index(["rid", "horse_no"])["placed"]
    labels = [_label(rid, combo, popularity) for rid, combo in zip(cases["rid"], horses, strict=True)]
    results = [_result(rid, combo, finish) for rid, combo in zip(cases["rid"], horses, strict=True)]
    return info.assign(買い目=labels, オッズ=cases["odds"].round(1), その券種から=cases["own"].round(3),
                       三連単から=cases["derived"].round(3), 比=cases["ratio"].round(2), 結果=results,
                       払戻=cases["payout"].astype(int))


def _horses(kind: TicketKind, flat: np.ndarray) -> list[tuple[int, ...]]:
    digits = [(flat // 18 ** power) % 18 + 1 for power in range(kind.horses - 1, -1, -1)]
    return list(zip(*[column.astype(int) for column in digits], strict=True))


def _label(rid: int, combo: tuple[int, ...], popularity: pd.Series) -> str:
    return "-".join(f"{horse}({int(popularity.get((rid, horse), 0))}人気)" for horse in combo)


def _result(rid: int, combo: tuple[int, ...], placed: pd.Series) -> str:
    inside = sum(int(placed.get((rid, horse), 0)) for horse in combo)
    return f"{inside}/{len(combo)}頭が3着以内"


if __name__ == "__main__":
    main()
