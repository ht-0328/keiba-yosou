"""締め切り前のオッズで買っていたら回収率はどうなったかを、過去のレースで確かめる（研究「回収率100超」の入口⑥）。

    uv run python research/回収率100超/check_pre_deadline.py

先に ``extract.py`` で中間データを作り、``backtest.py`` を回しておく（全部の材料のモデルの予測を使う）。
元DB には、jvdata-store の ``jvstore timeseries`` と ``jvstore merge-odds`` で、期間の時系列オッズ
（単複枠と馬連の締め切り前の断面）を入れておく。

同じレース（期間のうち、締め切り前の断面がそろうレース）で、次の4通りの買い方を、採用した線で比べる。

- A: 全部の材料・確定オッズ（``backtest.py`` の検証と同じ。上限の見積もり）
- B: 締め切り前に手に入る材料だけ・確定オッズ
- C: 締め切り前に手に入る材料だけ・締め切り前のオッズ（実際に買うときにいちばん近い）
- D: 全部の材料の確率 × 締め切り前の複勝オッズ（複勝オッズが締め切りまでに動くぶんだけの影響）

B と C の差が「確定オッズで検証したことによる水増し」、A と B の差が「3連単などの材料が無いことによる差」になる。
出力は ``reports/回収率100超/締め切り前のオッズでの確認（N分前）.md``（Git 対象外。N は ``--minutes``）。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import db  # noqa: E402

from 回収率100超.analysis.backtest import Payback, PaybackInterval, WalkForwardYears  # noqa: E402
from 回収率100超.analysis.bet_rule import PLACE_RULE  # noqa: E402
from 回収率100超.analysis.cache_loader import CacheLoader  # noqa: E402
from 回収率100超.analysis.feature import LearningTable, PreDeadlineTable  # noqa: E402
from 回収率100超.analysis.market import RaceFinishSample, SternFitter, SternProbabilities  # noqa: E402
from 回収率100超.analysis.probability import GradientBoostingPair  # noqa: E402
from 回収率100超.analysis.repository import (  # noqa: E402
    PreDeadlineQuinellaRepository,
    PreDeadlineWinPlaceRepository,
)
from 回収率100超.analysis.ticket import PlacePriceEstimator, RacePlaceProbability  # noqa: E402

DEFAULT_CACHE = Path("reports/回収率100超/cache")
DEFAULT_OUT = Path("reports/回収率100超")
#: ``backtest.py`` が残す、全部の材料のモデルの予測。
FULL_PREDICTIONS = "place_predictions.parquet"
#: Stern のべき乗を推定する年とレースの数（backtest.py と同じ）。
FIRST_TEST_YEAR, STERN_SAMPLE_RACES = 2019, 6000
#: 確かめる線（採用した線のほかに、線を動かしたときの向きを見る）。
LINES: tuple[float, ...] = (1.00, 1.10, 1.20, 1.25, 1.30)
VARIANTS = {
    "A": "全部の材料・確定オッズ",
    "B": "締め切り前に手に入る材料だけ・確定オッズ",
    "C": "締め切り前に手に入る材料だけ・締め切り前のオッズ",
    "D": "全部の材料の確率 × 締め切り前の複勝オッズ",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="締め切り前のオッズで確かめる", allow_abbrev=False)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--db", type=Path, default=None, help="元DB の場所")
    parser.add_argument("--from", dest="first_day", type=date.fromisoformat, default=date(2025, 9, 1))
    parser.add_argument("--to", dest="last_day", type=date.fromisoformat, default=date(2026, 9, 27))
    parser.add_argument("--minutes", type=int, default=10, help="発走の何分前までに発表された断面を使うか")
    args = parser.parse_args()

    runners = CacheLoader(args.cache).read()
    learning = LearningTable(_fit_stern(runners))
    table, features = learning.build(runners)
    pre_table = PreDeadlineTable(learning)
    reduced = pre_table.features(features)
    print(f"締め切り前に手に入る材料: {len(reduced)} 列（全部の材料は {len(features)} 列）", flush=True)

    with db.open_db(args.db) as connection:
        win_place = PreDeadlineWinPlaceRepository(connection, args.first_day, args.last_day, args.minutes).read()
        quinella = PreDeadlineQuinellaRepository(connection, args.first_day, args.last_day, args.minutes).read()
    window = table[(table["day"] >= args.first_day) & (table["day"] <= args.last_day)]
    pre_rows = pre_table.rebuild(window, win_place, quinella)
    same = window[window["rid"].isin(set(pre_rows["rid"]))].reset_index(drop=True)
    print(f"期間のレース {window['rid'].nunique():,} のうち、締め切り前の断面がそろうレース {same['rid'].nunique():,}",
          flush=True)

    final_prob, pre_prob = _walk_forward(table, same, pre_rows, reduced)
    variants = _variants(table, same, pre_rows, final_prob, pre_prob, args.cache / FULL_PREDICTIONS)
    _write_report(variants, window, same, pre_rows, args)


def _fit_stern(runners: pd.DataFrame) -> SternProbabilities:
    """Stern のべき乗を、評価に使わない年の着順から推定する（backtest.py と同じ）。"""
    early = runners[runners["year"] < FIRST_TEST_YEAR]
    lam, mu = SternFitter().fit(RaceFinishSample("単勝から見た勝率").build(early, limit=STERN_SAMPLE_RACES))
    return SternProbabilities(lam, mu)


def _walk_forward(table: pd.DataFrame, same: pd.DataFrame, pre_rows: pd.DataFrame,
                  features: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """締め切り前に手に入る材料だけのモデルを年ごとに学習し、確定オッズの材料と締め切り前の材料の両方で予測する。"""
    final_prob, pre_prob = np.full(len(same), np.nan), np.full(len(pre_rows), np.nan)
    target = table["placed"].to_numpy()
    years = sorted(same["year"].unique())
    for split in WalkForwardYears(table["year"].to_numpy(), int(years[0]), int(years[-1])):
        pair = GradientBoostingPair().fit(table.loc[split.fit, features], target[split.fit],
                                          table.loc[split.valid, features], target[split.valid])
        final_rows, pre_year = (same["year"] == split.test_year).to_numpy(), (pre_rows["year"] == split.test_year).to_numpy()
        final_prob[final_rows] = pair.predict(same.loc[final_rows, features])
        pre_prob[pre_year] = pair.predict(pre_rows.loc[pre_year, features])
        print(f"  {split.test_year}: 予測しました（{int(final_rows.sum()):,} 頭）", flush=True)
    return final_prob, pre_prob


def _variants(table: pd.DataFrame, same: pd.DataFrame, pre_rows: pd.DataFrame, final_prob: np.ndarray,
              pre_prob: np.ndarray, full_path: Path) -> dict[str, pd.DataFrame]:
    """4通りの買い方の、1頭ごとの期待値と払戻（``rid``・``year``・``day``・``ev``・``payout``・``place_odds_low``）。"""
    normalize = RacePlaceProbability().normalize
    price = _PlacePrice(table)
    pre_low = same[["rid", "horse_no"]].merge(pre_rows[["rid", "horse_no", "place_odds_low"]],
                                             on=["rid", "horse_no"], how="left")["place_odds_low"]
    variants = {
        "B": _frame(same, normalize(pd.Series(final_prob), same["rid"], same["place_places"])
                    * price.of(same, same["place_odds_low"]), same["place_odds_low"]),
        "C": _frame(pre_rows, normalize(pd.Series(pre_prob), pre_rows["rid"], pre_rows["place_places"])
                    * price.of(pre_rows, pre_rows["place_odds_low"]), pre_rows["place_odds_low"]),
    }
    if not full_path.exists():
        print(f"注意: {full_path} が無いので A・D を出しません（先に backtest.py を回す）", flush=True)
        return variants
    full = same[["rid", "horse_no"]].merge(pd.read_parquet(full_path)[["rid", "horse_no", "3着以内の確率", "複勝の期待値"]],
                                          on=["rid", "horse_no"], how="left")
    variants["A"] = _frame(same, full["複勝の期待値"], same["place_odds_low"])
    variants["D"] = _frame(same, full["3着以内の確率"] * price.of(same, pre_low), pre_low)
    return dict(sorted(variants.items()))


def _frame(rows: pd.DataFrame, ev: pd.Series, place_odds_low: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({"rid": rows["rid"].to_numpy(), "year": rows["year"].to_numpy(), "day": rows["day"].to_numpy(),
                         "ev": np.asarray(ev, dtype=float), "payout": rows["place_payout"].to_numpy(),
                         "place_odds_low": np.asarray(place_odds_low, dtype=float)})


class _PlacePrice:
    """複勝の想定払戻倍率。評価する年より前の確定の的中だけから作る（backtest.py と同じ）。"""

    def __init__(self, table: pd.DataFrame) -> None:
        self._table = table
        self._estimators: dict[int, PlacePriceEstimator] = {}

    def of(self, rows: pd.DataFrame, place_odds_low: pd.Series) -> np.ndarray:
        price = np.full(len(rows), np.nan)
        low = np.asarray(place_odds_low, dtype=float)
        for year in rows["year"].unique():
            mask = (rows["year"] == year).to_numpy()
            price[mask] = self._estimator(int(year)).estimate(pd.Series(low[mask])).to_numpy()
        return price

    def _estimator(self, year: int) -> PlacePriceEstimator:
        if year not in self._estimators:
            train = self._table[self._table["year"] < year]
            self._estimators[year] = PlacePriceEstimator().fit(train["place_odds_low"], train["place_payout"],
                                                               train["placed"])
        return self._estimators[year]


def _write_report(variants: dict[str, pd.DataFrame], window: pd.DataFrame, same: pd.DataFrame,
                  pre_rows: pd.DataFrame, args: argparse.Namespace) -> None:
    interval = PaybackInterval()
    rows = [_summary(key, frame[frame["ev"] >= PLACE_RULE.lower], interval) for key, frame in variants.items()]
    sweep = [{"買い方": key, **{f"線 {line:.2f}": _rate(frame[frame["ev"] >= line]) for line in LINES}}
             for key, frame in variants.items()]
    lines = [
        "# 回収率100超 — 締め切り前のオッズでの確認", "",
        f"期間 {args.first_day}〜{args.last_day}。締め切り前のオッズは、発走の {args.minutes} 分前までに発表された、"
        "いちばん新しい断面（時系列オッズ）。JV-Data 由来の値を含むため、この文書は Git の対象外。", "",
        f"- 期間のレース: {window['rid'].nunique():,}　うち締め切り前の断面がそろうレース: {same['rid'].nunique():,}"
        "（以下はすべて、このそろうレースだけで比べる）",
        *[f"- {key}: {name}" for key, name in VARIANTS.items() if key in variants], "",
        f"## 1. 採用した線（{PLACE_RULE.describe()}）で買ったとき", "",
        pd.DataFrame(rows).to_markdown(index=False), "",
        "## 2. 線を動かしたときの回収率", "",
        pd.DataFrame(sweep).to_markdown(index=False), "",
        "## 3. 複勝オッズは締め切りまでにどれだけ動くか", "",
        *_drift(same, pre_rows), "",
    ]
    path = args.out / f"締め切り前のオッズでの確認（{args.minutes}分前）.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"書き出しました: {path}", flush=True)


def _summary(key: str, bought: pd.DataFrame, interval: PaybackInterval) -> dict[str, object]:
    payback = Payback(bought["payout"])
    low, high = interval.of(bought["day"], bought["payout"]) if len(bought) else (np.nan, np.nan)
    return {"買い方": f"{key}: {VARIANTS[key]}", "買い目": payback.bet_count, "的中率": round(payback.hit_rate, 3),
            "回収率": round(payback.rate, 1), "90%の下限": round(low, 1), "90%の上限": round(high, 1)}


def _rate(bought: pd.DataFrame) -> str:
    return f"{Payback(bought['payout']).rate:.1f}%（{len(bought):,}点）"


def _drift(same: pd.DataFrame, pre_rows: pd.DataFrame) -> list[str]:
    """締め切り前の複勝の最低オッズ ÷ 確定の複勝の最低オッズ。"""
    joined = same[["rid", "horse_no", "place_odds_low"]].merge(
        pre_rows[["rid", "horse_no", "place_odds_low"]], on=["rid", "horse_no"], suffixes=("_final", "_pre"))
    ratio = joined["place_odds_low_pre"] / joined["place_odds_low_final"]
    return [f"- 締め切り前 ÷ 確定 の中央値: {ratio.median():.3f}",
            f"- 締め切り前のほうが高かった割合: {(ratio > 1).mean():.3f}　低かった割合: {(ratio < 1).mean():.3f}",
            f"- 10% 以上動いた割合: {((ratio - 1).abs() >= 0.10).mean():.3f}"]


if __name__ == "__main__":
    main()
