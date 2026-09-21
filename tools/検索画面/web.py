"""検索画面（ブラウザ）を起動する。DB・テーブル・出馬表・レース・馬・出走・事象・成績・回収率探索・SQL のタブがある（一覧は tools/README.md）。

    uv run python tools/検索画面/web.py --open              # 起動してブラウザで開く
    uv run python tools/検索画面/web.py --port 9000 --idle 300
    uv run python tools/検索画面/web.py --db reports/synth.duckdb --open    # 合成DB で試す

画面の絞り込みの項目名は CLI のフラグ名と同じで、各結果の下に「同じ条件の CLI」が出る。
DB は使っている間だけロックし、--idle 秒（既定 60）放置すると手放す（jvdata-store の取得を塞がないため）。
ダブルクリックで起動するには、同じフォルダの run.bat を使う。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db  # noqa: E402
from 検索画面 import server  # noqa: E402


def main(args) -> None:
    server.serve(db.resolve_db(args.db), args.port, args.open, idle_seconds=args.idle)


def build_parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--port", type=int, default=server.DEFAULT_PORT, help=f"待ち受けるポート（既定 {server.DEFAULT_PORT}）")
    parser.add_argument("--open", action="store_true", help="起動後にブラウザで開く")
    parser.add_argument("--idle", type=float, default=60.0, help="この秒数放置したら DB を手放す（既定 60）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
