"""作り方ごとに7つの区切りで学習し、予測を保存する（研究「一番人気を疑う」の入口②）。

    uv run --with pyarrow python research/一番人気を疑う/run_experiments.py                       # 全部（済んだものは飛ばす）
    uv run --with pyarrow python research/一番人気を疑う/run_experiments.py --names 21_木曜_研究の材料  # 1つだけ

先に、研究「既存モデルの改善」の ``build_tables.py``（今の予想の材料の表）と、研究「馬の力と展開でオッズに勝つ」の
``extract.py``・``extract_extra.py``・``experiment.py --rebuild``（197個の材料の表）と、この研究の ``extract_sales.py`` を回しておく。
出力は ``reports/一番人気を疑う/予測/<作り方>.parquet``（Git 対象外）。元DB は開かない。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 一番人気を疑う.analysis.experiment_runner import ExperimentRunner  # noqa: E402
from 一番人気を疑う.analysis.experiments import EXPERIMENTS, experiment_named  # noqa: E402

DEFAULT_TABLES = Path("reports/既存モデルの改善/tables")
DEFAULT_ABILITY = Path("reports/馬の力と展開でオッズに勝つ/cache")
DEFAULT_SALES = Path("reports/一番人気を疑う/cache/sales.parquet")
DEFAULT_OUT = Path("reports/一番人気を疑う/予測")


def main() -> None:
    parser = argparse.ArgumentParser(description="作り方ごとに7つの区切りで学習して予測を保存する", allow_abbrev=False)
    parser.add_argument("--names", nargs="*", default=None, metavar="作り方", help="回す作り方（省略すると全部）")
    parser.add_argument("--rerun", action="store_true", help="予測がすでにあっても回し直す")
    parser.add_argument("--tables", type=Path, default=DEFAULT_TABLES)
    parser.add_argument("--ability", type=Path, default=DEFAULT_ABILITY)
    parser.add_argument("--sales", type=Path, default=DEFAULT_SALES)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    experiments = [experiment_named(name) for name in args.names] if args.names else list(EXPERIMENTS)
    runner = ExperimentRunner(args.tables, args.ability, args.sales)
    args.out.mkdir(parents=True, exist_ok=True)
    for experiment in experiments:
        path = args.out / f"{experiment.key}.parquet"
        if path.exists() and not args.rerun:
            print(f"済み: {experiment.key}", flush=True)
            continue
        started = time.time()
        predictions, trees = runner.run(experiment)
        predictions.to_parquet(path)
        log = {"作り方": experiment.key, "説明": experiment.label, "木の数": trees, "秒": int(time.time() - started)}
        (args.out / f"{experiment.key}.json").write_text(json.dumps(log, ensure_ascii=False), encoding="utf-8")
        print(f"書き出しました: {path}（{log['秒']} 秒）", flush=True)


if __name__ == "__main__":
    main()
