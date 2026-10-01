"""オッズを使わない勝率のモデルを作り、年ごとに市場（単勝オッズ）と当たり具合を比べる（入口②）。

    uv run python research/馬の力と展開でオッズに勝つ/experiment.py --name 基本

学習用の表は初回に作って ``cache/dataset.parquet`` に保存し、2回目からは使い回す（``--rebuild`` で作り直す）。
評価はウォークフォワード: その年の2年前までで学習し、前の年で木の本数を決め、その年を予測する。
既定の評価の年は 2019〜2021年（作り方を選ぶための年）。2022年からは最後の確かめに取っておく。
出力は ``reports/馬の力と展開でオッズに勝つ/実験/<name>.md`` と、予測の表（``<name>_予測.parquet``）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 馬の力と展開でオッズに勝つ.analysis.dataset_builder import MINING_COLUMNS, DatasetBuilder  # noqa: E402
from 馬の力と展開でオッズに勝つ.analysis.race_log_loss import RaceLogLoss  # noqa: E402
from 馬の力と展開でオッズに勝つ.analysis.rank_win_model import RankWinModel  # noqa: E402
from 馬の力と展開でオッズに勝つ.analysis.win_model import WinModel  # noqa: E402

DEFAULT_CACHE = Path("reports/馬の力と展開でオッズに勝つ/cache")
DEFAULT_FIGURES = Path("reports/能力指数/cache/figures.parquet")
DEFAULT_OUT = Path("reports/馬の力と展開でオッズに勝つ/実験")
#: 学習に使う最初の年（2011年は過去走を作るためだけに使う）。
FIRST_TRAIN_YEAR = 2012


def main() -> None:
    parser = argparse.ArgumentParser(description="オッズを使わない勝率のモデルを確かめる", allow_abbrev=False)
    parser.add_argument("--name", required=True)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--figures", type=Path, default=DEFAULT_FIGURES)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--years", type=int, nargs="+", default=[2019, 2020, 2021])
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--mining", action="store_true", help="JRA-VAN のマイニング予想も材料に入れる")
    parser.add_argument("--catboost", action="store_true", help="CatBoost も学習して平均する")
    parser.add_argument("--drop", nargs="*", default=[], help="材料から外す列の頭（前方一致）")
    parser.add_argument("--rank", action="store_true", help="順位の学習（lambdarank）で学ぶ")
    parser.add_argument("--also-placed", action="store_true", help="3着以内の確率のモデルも学習する（複勝を確かめるため）")
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--leaves", type=int, default=63)
    parser.add_argument("--min-child", type=int, default=200)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    table, features = _dataset(args)
    features = [f for f in features if not any(f.startswith(prefix) for prefix in args.drop)]
    features += list(MINING_COLUMNS) if args.mining else []
    predicted = []
    for year in args.years:
        train = table[(table["year"] >= FIRST_TRAIN_YEAR) & (table["year"] <= year - 2)]
        valid, test = table[table["year"] == year - 1], table[table["year"] == year].copy()
        settings = {"learning_rate": args.learning_rate, "num_leaves": args.leaves,
                    "min_child_samples": args.min_child}
        model = (RankWinModel() if args.rank else WinModel(use_catboost=args.catboost, **settings)).fit(
            train, valid, features)
        test["p_win"] = model.predict(test)
        if args.also_placed:
            placed_model = WinModel(target="placed", use_catboost=args.catboost).fit(train, valid, features)
            test["p_placed"] = placed_model.predict(test)
        predicted.append(test)
        print(f"  {year}: 予測しました（{test['race_id'].nunique():,} レース）", flush=True)
    result = pd.concat(predicted, ignore_index=True)
    _write(args, result, model.importance(), len(features))


def _dataset(args: argparse.Namespace) -> tuple[pd.DataFrame, list[str]]:
    path, names = args.cache / "dataset.parquet", args.cache / "dataset_features.json"
    if path.exists() and names.exists() and not args.rebuild:
        return pd.read_parquet(path), json.loads(names.read_text(encoding="utf-8"))
    print("学習用の表を作っています...", flush=True)
    table, features = DatasetBuilder().build(
        pd.read_parquet(args.cache / "facts.parquet"), pd.read_parquet(args.figures),
        pd.read_parquet(args.cache / "workouts.parquet"), pd.read_parquet(args.cache / "connections.parquet"))
    table.to_parquet(path, index=False)
    names.write_text(json.dumps(features, ensure_ascii=False), encoding="utf-8")
    return table, features


def _write(args: argparse.Namespace, result: pd.DataFrame, importance: pd.Series, feature_count: int) -> None:
    losses = RaceLogLoss().per_race(result, "p_win").merge(result[["race_id", "year"]].drop_duplicates(), on="race_id")
    by_year = losses.groupby("year")[["model", "market"]].mean().round(4)
    by_year["差（モデル − 市場）"] = (by_year["model"] - by_year["market"]).round(4)
    segments = _segments(result, losses)
    lines = [f"# 実験: {args.name}", "", f"材料の数: {feature_count}", "",
             "## 1着のログ損失（小さいほど良い）", "", by_year.to_markdown(), "",
             "## 条件ごとの差（モデル − 市場。正ならモデルが負けている）", "", segments.to_markdown(), "",
             "## 効いた材料（LightGBM の gain、最後の年のモデル、上位 30）", "",
             importance.head(30).round(0).to_frame("gain").to_markdown(), ""]
    (args.out / f"{args.name}.md").write_text("\n".join(lines), encoding="utf-8")
    kept = ["race_id", "horse_no", "year", "p_win", "market_win", "won", "placed", "places", "win_odds",
            "place_payout", "win_payout", "runners"] + (["p_placed"] if "p_placed" in result.columns else [])
    result[kept].to_parquet(args.out / f"{args.name}_予測.parquet", index=False)
    print(by_year.to_string(), flush=True)


def _segments(result: pd.DataFrame, losses: pd.DataFrame) -> pd.DataFrame:
    races = result.drop_duplicates("race_id").set_index("race_id")
    joined = losses.join(races[["class_name", "surface", "runners"]], on="race_id")
    joined["頭数"] = pd.cut(joined["runners"], [0, 10, 14, 18])
    rows = []
    for column in ("class_name", "surface", "頭数"):
        grouped = joined.groupby(column, observed=True)
        part = grouped.agg(レース数=("model", "size"), モデル=("model", "mean"), 市場=("market", "mean"))
        part["差"] = (part["モデル"] - part["市場"]).round(4)
        rows.append(part.round(4).rename(index=lambda value, c=column: f"{c}={value}"))
    return pd.concat(rows)


if __name__ == "__main__":
    main()
