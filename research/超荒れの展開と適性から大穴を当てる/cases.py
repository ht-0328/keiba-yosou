"""超荒れの展開と適性から大穴を当てる: 事例を集めて数える（研究「超荒れの展開と適性から大穴を当てる」の入口。段1・段2）。

    uv run python research/超荒れの展開と適性から大穴を当てる/cases.py              # 元DB から出走の表を作り、表と事例を書く（数分）
    uv run python research/超荒れの展開と適性から大穴を当てる/cases.py --cached     # 前に作った出走の表（出走の表.pkl.gz）から書き直す

出るもの（Git 対象外）: ``reports/超荒れの展開と適性から大穴を当てる/事例.md``（事例の数・展開・バイアス・大穴2頭以上・ハンデと斤量・
適性・前半と後半の年・どの大穴が来たか・1レースずつ見た事例）、``事例の一覧.csv``、``コースの単位ごとの数.csv``、``出走の表.pkl.gz``（gzip で縮めた pickle）。
元DB は jvdata-store の jvdata.duckdb（``--db`` か環境変数 YOSOU_DB）。読むだけ。ほかに回顧の DB（reports/回顧/review.duckdb）と、
予想「展開から着順を予想」の年ごとの予測（reports/展開から着順を予想/out_of_sample/）を読む。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

_RESEARCH = Path(__file__).resolve().parents[1]
_REPO_ROOT = _RESEARCH.parent
sys.path[:0] = [str(_RESEARCH), str(_REPO_ROOT / "tools"), str(_REPO_ROOT / "src")]

from 共通 import cli, db  # noqa: E402
from 超荒れの展開と適性から大穴を当てる.analysis.case_study import RUNNERS_CACHE, CaseStudy, CaseStudySettings  # noqa: E402
from 超荒れの展開と適性から大穴を当てる.analysis.repository import DEFAULT_PACE_FORECASTS, DEFAULT_REVIEW_DB  # noqa: E402

DEFAULT_OUT = _REPO_ROOT / "reports" / "超荒れの展開と適性から大穴を当てる"


def main(args: argparse.Namespace) -> None:
    settings = CaseStudySettings(date_from=args.date_from, review_db=args.review_db, pace_forecasts=args.pace_forecasts)
    study = CaseStudy(settings)
    cache = args.out_dir / RUNNERS_CACHE
    if args.cached and cache.exists():
        runners = pd.read_pickle(cache)
    else:
        with db.open_db(args.db, default=db.JRA) as con:
            runners = study.load(con)
        args.out_dir.mkdir(parents=True, exist_ok=True)
        runners.to_pickle(cache, compression="gzip")
    print(f"書きました: {study.write(runners, args.out_dir)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス（既定: ../jvdata-store/jvdata.duckdb か環境変数 YOSOU_DB）")
    parser.add_argument("--from", dest="date_from", type=date.fromisoformat, default=date(2015, 1, 1), help="事例の最初の開催日（既定: 2015-01-01）")
    parser.add_argument("--review-db", type=Path, default=DEFAULT_REVIEW_DB, help="回顧の DB（結果のペース・その日の傾き・不利）")
    parser.add_argument("--pace-forecasts", type=Path, default=DEFAULT_PACE_FORECASTS, help="展開の予想の年ごとの予測の置き場所（前日の時点）")
    parser.add_argument("--cached", action="store_true", help="前に作った出走の表（出走の表.pkl.gz）があれば、元DB を読まずに使う")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help=f"書く場所（既定: {DEFAULT_OUT}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
