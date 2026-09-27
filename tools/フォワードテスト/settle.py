"""フォワードテスト: 記録した買い目のうち、結果が出たものを精算して、成績の文書を書き直す。

    uv run python tools/フォワードテスト/settle.py

ふだんは follow.py が開催日の終わりに精算するので、呼ばなくてよい。月曜の成績の取り込みのあとや、
follow.py が途中で止まったときに使う。成績は reports/フォワードテスト/成績.md。
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[0]), str(HERE.parents[1] / "src")]

from 共通 import cli, db  # noqa: E402

from フォワードテスト.follow import LEDGER  # noqa: E402
from フォワードテスト.forward_summary import ForwardSummary  # noqa: E402
from フォワードテスト.ledger import Ledger  # noqa: E402
from フォワードテスト.settlement import Settlement  # noqa: E402


def main(args) -> None:
    ledger = Ledger(LEDGER)
    with db.open_db(args.db) as con:
        settled = Settlement(ledger).settle(con, datetime.now())
    path = ForwardSummary(ledger).write(datetime.now())
    print(f"{settled} 点を精算しました。成績: {path}")


if __name__ == "__main__":
    cli.run(cli.build_parser(__doc__, limit=None), main)
