"""券種オッズ入りの設定を、年ごとのウォークフォワードで確かめる（研究「特徴量の組み合わせ探索」の入口⑤）。

    uv run python research/特徴量の組み合わせ探索/walk_forward.py [--only 名前 ...]

2019年から1年ずつ、その年より前で学習し直し（直前の1年は早期終了と線の選択だけに使う）、その年を予測する。
年ごとと年を合わせた、複勝の点数・回収率・開催日単位の90%の幅の下限を出し、採用の基準に当てる。
入力は入口①の表だけで、元DB に触らない。モデルは保存しない（tools/ が使う保存済みのモデルには触らない）。
出力は ``reports/特徴量の組み合わせ探索/walk_forward/``（Git 対象外）。済んだ年は飛ばすので、止まっても続きから動かせる。
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "research"), str(ROOT / "tools"), str(ROOT / "src")]

from yosou.custom_binary.feature.default_registry import DefaultRegistry  # noqa: E402

from 特徴量の組み合わせ探索.analysis.feature_table import FeatureTable  # noqa: E402
from 特徴量の組み合わせ探索.analysis.model_config import ModelConfig  # noqa: E402
from 特徴量の組み合わせ探索.analysis.model_configs import pool_configs  # noqa: E402
from 特徴量の組み合わせ探索.analysis.walk_forward_trial import WalkForwardTrial  # noqa: E402
from 特徴量の組み合わせ探索.analysis.walk_forward_verdict import WalkForwardVerdict  # noqa: E402
from 特徴量の組み合わせ探索.analysis.walk_forward_years import WalkForwardYears  # noqa: E402
from 特徴量の組み合わせ探索.analysis.yearly_payback import YearlyPayback  # noqa: E402
from 特徴量の組み合わせ探索.summarize import markdown  # noqa: E402

REPORTS = ROOT / "reports" / "特徴量の組み合わせ探索"
#: 既定で確かめる設定。pool_main_all は当日の予想の「馬体重あり」と同じ設定、pool_ref_form_all は券種オッズなしの比べる相手。
DEFAULT_CONFIGS = ("pool_main_all", "pool_ref_form_all")
#: 当日の予想（tools/当日の予想 の DEFAULT_LINE）が買いにしている期待値の線。参考に、この線で固定した結果も出す。
TODAY_LINE = 1.2


def main() -> None:
    parser = argparse.ArgumentParser(description="年ごとのウォークフォワードで確かめる", allow_abbrev=False)
    parser.add_argument("--cache", type=Path, default=REPORTS / "cache")
    parser.add_argument("--out", type=Path, default=REPORTS / "walk_forward")
    parser.add_argument("--only", nargs="+", default=list(DEFAULT_CONFIGS), help="この名前の設定だけ動かす")
    args = parser.parse_args()
    table = FeatureTable.load(args.cache)
    last_year = int(table.rows["race_date"].max().year)
    configs = [config for config in pool_configs() if config.name in args.only]
    trial = WalkForwardTrial(table, DefaultRegistry().build())
    for config in configs:
        run_years(trial, config, args.out / config.name, last_year)
    summary = {config.name: summarize(args.out / config.name) for config in configs}
    (args.out / "結果.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    lines = ["# 年ごとのウォークフォワードの結果", "", VERDICT_NOTE, ""]
    for name, result in summary.items():
        lines += section(name, result)
    (args.out / "結果.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.out / "結果.md")


def run_years(trial: WalkForwardTrial, config: ModelConfig, folder: Path, last_year: int) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for split in WalkForwardYears(last_year):
        path = folder / f"{split.year}.pkl"
        if path.exists():
            continue
        result = trial.run(config, split)
        pd.to_pickle(result, path)
        print(f"{config.name} {split.year}: 線 {result['line']}（候補 {len(result['tickets'])}点）", flush=True)


def summarize(folder: Path) -> dict:
    results = [pd.read_pickle(path) for path in sorted(folder.glob("*.pkl"))]
    tickets = {result["year"]: result["tickets"] for result in results}
    chosen = YearlyPayback().table(tickets, {result["year"]: result["line"] for result in results})
    fixed = YearlyPayback().table(tickets, {result["year"]: TODAY_LINE for result in results})
    return {"選んだ線": chosen.to_dict("records"), "選んだ線の判定": WalkForwardVerdict().judge(chosen),
            "固定の線": fixed.to_dict("records"), "固定の線の判定": WalkForwardVerdict().judge(fixed)}


def section(name: str, result: dict) -> list[str]:
    return [
        f"## {name}", "",
        f"### 直前の1年で選んだ線（判定: {verdict_text(result['選んだ線の判定'])}）", "",
        markdown(pd.DataFrame(result["選んだ線"])), "",
        f"### 線を {TODAY_LINE:g} に固定（当日の予想と同じ線。参考。判定: {verdict_text(result['固定の線の判定'])}）", "",
        markdown(pd.DataFrame(result["固定の線"])), "",
    ]


def verdict_text(verdict: dict) -> str:
    failed = [name for name, ok in verdict["基準ごと"].items() if not ok]
    return "採用" if verdict["採用"] else f"不採用（満たさない基準: {'・'.join(failed)}）"


VERDICT_NOTE = (
    "採用: 年を合わせて点数300以上・複勝の回収率100%以上・開催日単位の90%の幅の下限100%以上、"
    "かつ回収率100%以上の年が買った年の半分を超える（analysis/walk_forward_verdict.py）。"
)


if __name__ == "__main__":
    main()
