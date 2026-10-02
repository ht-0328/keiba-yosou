"""元DB から、能力指数の元になる全出走を読んで保存する（研究「能力指数の作り方」の入口①）。

    uv run python research/能力指数の作り方/extract.py

出力は ``reports/能力指数の作り方/cache/runs.parquet``（1行 = 1頭。2011年からの中央・平地の全出走）。
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db  # noqa: E402
from 共通.ability import RunSource  # noqa: E402

from 展開の理論の検証.analysis.cache_store import CacheStore  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE = _REPO_ROOT / "reports" / "能力指数の作り方" / "cache"
#: 読む最初の日（DB にある最初の年）。
_FIRST_DAY = date(2011, 1, 1)


def main(args) -> None:
    print("元DB から全出走を読んでいます …", file=sys.stderr, flush=True)
    with db.open_db(args.db) as con:
        runs = RunSource(con).read(_FIRST_DAY)
    path = CacheStore(args.cache).write("runs", runs)
    print(f"{len(runs)} 行を書きました: {path}", file=sys.stderr)


def _parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE, help="中間データの置き場")
    return parser


if __name__ == "__main__":
    cli.run(_parser(), main)
