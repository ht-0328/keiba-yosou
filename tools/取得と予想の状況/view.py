"""取得と予想の状況を画面で見る: 検索画面を起動して、ブラウザで「状況」のタブを開く。

    uv run python tools/取得と予想の状況/view.py                # 起動して「状況」を開く（起動済みなら開くだけ）
    uv run python tools/取得と予想の状況/view.py --port 9000

``tools/検索画面/web.py --open --tab overview`` と同じ。ダブルクリックなら、同じフォルダの run.bat。
終了するには、起動した黒い窓で Ctrl+C を押すか、窓を閉じる。同じ中身を表で出すだけなら status.py。
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[0])]

from 共通 import cli, db  # noqa: E402
from 検索画面 import server  # noqa: E402

#: 開くタブ（画面の index.html の VIEWS の名前）。
TAB = "overview"


def main(args) -> None:
    server.serve(db.resolve_db(args.db), args.port, True, idle_seconds=args.idle, tab=TAB)


def build_parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--port", type=int, default=server.DEFAULT_PORT, help=f"待ち受けるポート（既定 {server.DEFAULT_PORT}）")
    parser.add_argument("--idle", type=float, default=60.0, help="この秒数放置したら DB を手放す（既定 60）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
