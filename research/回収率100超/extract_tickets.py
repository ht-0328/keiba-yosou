"""元DB から、券種ごとの買い目のオッズと払戻を中間データ（parquet）にする（研究「回収率100超」の入口④）。

    uv run python research/回収率100超/extract_tickets.py

複勝以外の券種（単勝・ワイド・馬連・馬単・3連複・3連単）を検証する ``backtest_tickets.py`` が使う。
3連単は1年で数百万点あるので、券種 × 年ごとに1つのファイルにする。
出力は ``reports/回収率100超/cache/tickets/``（Git 対象外）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import db  # noqa: E402

from 回収率100超.analysis.repository import TicketOddsRepository, TicketPayoutRepository  # noqa: E402
from 回収率100超.analysis.tickets.ticket_kind import TICKET_KINDS  # noqa: E402

DEFAULT_OUT = Path("reports/回収率100超/cache/tickets")


def main() -> None:
    parser = argparse.ArgumentParser(description="券種ごとの買い目のオッズと払戻を読み出す", allow_abbrev=False)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="中間データの置き場")
    parser.add_argument("--from-year", type=int, default=2016)
    parser.add_argument("--to-year", type=int, default=2026)
    parser.add_argument("--db", type=Path, default=None, help="元DB の場所")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    with db.open_db(args.db) as connection:
        odds = TicketOddsRepository(connection)
        payouts = TicketPayoutRepository(connection, args.from_year)
        for kind in TICKET_KINDS:
            print(f"{kind.name} の払戻を読み出し中...", flush=True)
            _write(payouts.read(kind), args.out / f"{kind.key}_payout.parquet")
            for year in range(args.from_year, args.to_year + 1):
                _write(odds.read(kind, year), args.out / f"{kind.key}_{year}.parquet")


def _write(frame: pd.DataFrame, path: Path) -> None:
    frame.to_parquet(path, index=False)
    print(f"  {path.name}: {len(frame):,} 行", flush=True)


if __name__ == "__main__":
    main()
