"""超荒れの展開と適性から大穴を当てる: 段3 の予測を確かめる（段3 の入口②）。

    uv run python research/超荒れの展開と適性から大穴を当てる/evaluate.py danger --timing 当日     # 印の成績に渡す「4着以下の確率」の表を書く
    uv run python research/超荒れの展開と適性から大穴を当てる/evaluate.py report --timing 当日 --marks <印の成績の買い目の csv>

report は、中穴・大穴の並べ方と荒れる前提の確率、人気帯ごとの確率の当たり具合、人気馬が4着以下になる確率、中穴・大穴2頭の組の確率、
抑えの買い目（``--marks`` を渡したときだけ。元DB から 3連複の払戻を読む）、消の決め方を替えたときの全券種の印の成績（``--compare``）を、``reports/超荒れの展開と適性から大穴を当てる/段3の結果-<時点>.md`` に書く。
危険な人気馬の採否に使う全券種の回収率は、danger で書いた表を道具「印の成績」の ``--danger`` に渡して出す（docs/04 に手順）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
_REPO_ROOT = _RESEARCH.parent
sys.path[:0] = [str(_RESEARCH), str(_REPO_ROOT / "tools"), str(_REPO_ROOT / "src")]

from 共通 import db  # noqa: E402

from yosou.shared.feature import PredictionTiming  # noqa: E402

from 超荒れの展開と適性から大穴を当てる.analysis.scenario_evaluation.scenario_evaluation import ScenarioEvaluation  # noqa: E402

DEFAULT_ROOT = _REPO_ROOT / "reports" / "超荒れの展開と適性から大穴を当てる"
_TIMINGS = {"当日": PredictionTiming.RACE_DAY, "前日": PredictionTiming.DAY_BEFORE}


def main() -> None:
    args = _parser().parse_args()
    compared = dict(item.split("=", 1) for item in args.compare)
    evaluation = ScenarioEvaluation(args.root, _TIMINGS[args.timing], args.marks, {name: Path(path) for name, path in compared.items()})
    if args.step == "danger":
        print(f"書きました: {evaluation.write_danger_file()}", flush=True)
        return
    frame = evaluation.frame()
    if args.marks is not None:
        with db.open_db(args.db, default=db.JRA) as con:
            sections = evaluation.sections(frame, con)
    else:
        sections = evaluation.sections(frame, None)
    print(f"書きました: {evaluation.write(sections)}", flush=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("step", choices=("danger", "report"), help="danger（印の成績に渡す表）・report（確かめの表）")
    parser.add_argument("--timing", default="当日", choices=tuple(_TIMINGS), help="時点（既定: 当日）")
    parser.add_argument("--marks", type=Path, default=None, help="道具「印の成績」の買い目の csv（抑えの買い目を確かめるとき）")
    parser.add_argument("--compare", nargs="*", default=[], metavar="名前=csv",
                        help="消の決め方ごとの印の成績の買い目の csv（2つ以上で、券種ごとの的中率と回収率を並べる）")
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス（抑えの払戻を読む）")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="出力の置き場所")
    return parser


if __name__ == "__main__":
    main()
