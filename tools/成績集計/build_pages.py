"""基準のページ（reports/成績集計/）を、元DB の確定成績から作り直す。答え合わせ（perf.py --check）の基準になる。

    uv run python tools/成績集計/build_pages.py                            # 2011年1月から DB の最後まで（数分）
    uv run python tools/成績集計/build_pages.py --from 2016-01-01 --to 2026-09-27
    uv run python tools/成績集計/build_pages.py --out-dir reports/tmp/成績集計  # 別の場所に作る

答え合わせの意味は「別々に数えた値が一致すること」にある。そのため、perf.py が使う事実表（共通/facts.py）と
集計（共通/perf.py）は使わず、元DB の se・ra・払戻・血統・対戦型予想の表を直接読んで（repository/）、pandas で数える。
作り直したら、最後に出る期間を check.py の CHECK_DATE_FROM・CHECK_DATE_TO に書き、perf.py --check で一致を確かめる。
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db  # noqa: E402

from 成績集計.reference_index_writer import ReferenceIndexWriter  # noqa: E402
from 成績集計.reference_labels import ReferenceLabels  # noqa: E402
from 成績集計.reference_page_writer import ReferencePageWriter  # noqa: E402
from 成績集計.reference_runs import ReferenceRuns  # noqa: E402
from 成績集計.reference_tally import ReferenceTally  # noqa: E402
from 成績集計.repository import (  # noqa: E402
    FinalRunnerRepository, MiningScoreRepository, PayoutRepository, PedigreeRepository,
)

DEFAULT_OUT_DIR = Path(__file__).resolve().parents[2] / "reports" / "成績集計"
#: 既定の最初の開催日。DB の中央の確定成績は 2011年1月から続けて入っていて、それより前は散らばった数レースしか無い。
DEFAULT_DATE_FROM = "2011-01-01"


def main(args) -> None:
    with db.open_db(args.db) as con:
        runners, payouts = FinalRunnerRepository(con).read(), PayoutRepository(con).read()
        pedigrees, scores = PedigreeRepository(con).read(), MiningScoreRepository(con).read()
    runs = ReferenceRuns().build(runners, payouts, pedigrees, scores, args.date_from, args.date_to)
    if runs.empty:
        raise ValueError("その期間に確定成績がありません")
    runs = ReferenceLabels().add(runs)
    made_on = date.today().isoformat()
    pages = ReferencePageWriter(ReferenceTally(), made_on).write(runs, args.out_dir)
    index = ReferenceIndexWriter(made_on).write(runs, args.out_dir)
    print(f"{len(pages)} ページと目次を書きました: {index}")
    print(f"期間: {runs['race_date'].min()} 〜 {runs['race_date'].max()}（check.py の CHECK_DATE_FROM・CHECK_DATE_TO に書く）")


def build_parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--from", dest="date_from", default=DEFAULT_DATE_FROM,
                        help=f"最初の開催日 YYYY-MM-DD（既定: {DEFAULT_DATE_FROM}）")
    parser.add_argument("--to", dest="date_to", help="最後の開催日 YYYY-MM-DD（省略すると DB の最後まで）")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help=f"書く場所（既定: {DEFAULT_OUT_DIR}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
