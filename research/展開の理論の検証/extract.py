"""元DB から、出走の表とレースの表（ペースの区分つき）を作って保存する（研究「展開の理論の検証」の入口①）。

    uv run python research/展開の理論の検証/extract.py

元DB を長く握ると、ほかの道具が DB を開けなくなる。ここでまとめて読み出し、以後は parquet だけを使う。
出力は ``reports/展開の理論の検証/cache/`` の ``runners.parquet``（1行 = 1頭）と ``races.parquet``（1行 = 1レース）。
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db  # noqa: E402
from 共通.render import Table  # noqa: E402

from 展開の理論の検証.analysis.cache_store import CacheStore  # noqa: E402
from 展開の理論の検証.analysis.pace import PACE, RacePaceClassifier, RaceTable  # noqa: E402
from 展開の理論の検証.analysis.repository import PaceRunnerRepository  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE = _REPO_ROOT / "reports" / "展開の理論の検証" / "cache"
#: 読む最初の日。前半タイムの基準に前の3年が要るので、DB にある最初の年（2011年）から読む。
_FIRST_DAY = date(2011, 1, 1)


def main(args) -> None:
    print("元DB から全出走を読んでいます …", file=sys.stderr, flush=True)
    with db.open_db(args.db) as con:
        runners = PaceRunnerRepository(con).read(_FIRST_DAY)
    print("レースごとのペースを決めています …", file=sys.stderr, flush=True)
    races = RacePaceClassifier().classify(RaceTable().build(runners))
    store = CacheStore(args.cache)
    store.write("runners", runners)
    store.write("races", races)
    counts = races.groupby(["year", PACE]).size().unstack(fill_value=0)
    rows = [[year, *counts.loc[year].tolist()] for year in counts.index]
    cli.emit(Table(["年", *counts.columns.tolist()], rows, title=f"年ごとのペースの区分（{len(races)}レース）",
                   note=str(args.cache)), args)


def _parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE, help="中間データの置き場")
    return parser


if __name__ == "__main__":
    cli.run(_parser(), main)
