"""オッズを使わないモデルの勝率と、市場の勝率を組み合わせる（研究「馬の力と展開でオッズに勝つ」の入口⑤）。

    uv run python research/馬の力と展開でオッズに勝つ/combine.py --predictions 全年

**これはオッズを使う作り方で、オッズを使わないモデルとは別に扱う。** Benter の方法にならい、
勝率 ∝ exp(a × log モデルの勝率 + b × log 市場の勝率) の a・b を、レース単位の条件付きロジットで学ぶ。
a・b は、その年より前の年（予測のある 2018年から）だけで学び、その年に当てる（2018年は自分の年で学ぶので評価に使わない）。
3着以内の確率は、組み合わせた勝率から Stern の補正を入れた Harville の式で出す（べき乗は 2018年の着順から推定）。
出力は ``実験/<元の名前>_結合_予測.parquet`` と、年ごとのログ損失。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 回収率100超.analysis.market import ConditionalLogit, RaceFinishSample, SternFitter, SternProbabilities  # noqa: E402
from 馬の力と展開でオッズに勝つ.analysis.race_log_loss import RaceLogLoss  # noqa: E402

DEFAULT_OUT = Path("reports/馬の力と展開でオッズに勝つ")
FIRST_YEAR = 2018


def main() -> None:
    parser = argparse.ArgumentParser(description="モデルと市場の勝率を組み合わせる", allow_abbrev=False)
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    table = pd.read_parquet(args.out / "実験" / f"{args.predictions}_予測.parquet")
    finish = pd.read_parquet(args.out / "cache" / "dataset.parquet", columns=["race_id", "horse_no", "finish"])
    table = table.merge(finish, on=["race_id", "horse_no"], how="left")
    table = table[table["market_win"].notna() & table["p_win"].notna()].sort_values(["race_id", "horse_no"])
    table = table.reset_index(drop=True)
    table["p_model"] = table["p_win"]
    combined = np.full(len(table), np.nan)
    for year in range(FIRST_YEAR, int(table["year"].max()) + 1):
        train = table[(table["year"] < year) | ((table["year"] == FIRST_YEAR) & (year == FIRST_YEAR))]
        rows = table["year"] == year
        logit = ConditionalLogit().fit(_features(train), _race_index(train), train["won"].to_numpy())
        combined[rows.to_numpy()] = logit.predict(_features(table[rows]), _race_index(table[rows]))
        print(f"  {year}: a（モデル）= {logit.coefficients[0]:.3f}, b（市場）= {logit.coefficients[1]:.3f}", flush=True)
    table["p_win"] = combined
    table["p_placed"] = _placed(table)
    losses = RaceLogLoss().per_race(table, "p_win").merge(table[["race_id", "year"]].drop_duplicates(), on="race_id")
    model_only = RaceLogLoss().per_race(table.assign(p_win=table["p_model"]), "p_win")
    by_year = losses.groupby("year")[["model", "market"]].mean()
    by_year["モデルだけ"] = model_only.merge(table[["race_id", "year"]].drop_duplicates(), on="race_id") \
        .groupby("year")["model"].mean()
    print(by_year.round(4).rename(columns={"model": "組み合わせ", "market": "市場"}).to_string(), flush=True)
    table.drop(columns=["finish"]).to_parquet(args.out / "実験" / f"{args.predictions}_結合_予測.parquet", index=False)


def _features(table: pd.DataFrame) -> np.ndarray:
    return np.column_stack([np.log(table["p_model"].clip(1e-6)), np.log(table["market_win"].clip(1e-6))])


def _race_index(table: pd.DataFrame) -> np.ndarray:
    return pd.factorize(table["race_id"], sort=False)[0]


def _placed(table: pd.DataFrame) -> np.ndarray:
    """組み合わせた勝率から、3着以内（7頭以下は2着以内）の確率を出す。"""
    sample = table[table["year"] == FIRST_YEAR].assign(rid=lambda t: t["race_id"])
    lam, mu = SternFitter().fit(RaceFinishSample("p_win").build(sample, limit=3000))
    stern = SternProbabilities(lam, mu)
    result = np.empty(len(table))
    starts = np.flatnonzero(np.r_[True, table["race_id"].to_numpy()[1:] != table["race_id"].to_numpy()[:-1]])
    ends = np.r_[starts[1:], len(table)]
    probability, places = table["p_win"].to_numpy(), table["places"].to_numpy()
    for begin, end in zip(starts, ends, strict=True):
        p = probability[begin:end] / probability[begin:end].sum()
        result[begin:end] = stern.top_three(p) if places[begin] == 3 else stern.quinella(p).sum(axis=1)
    return np.clip(result, 1e-9, 1.0)


if __name__ == "__main__":
    main()
