"""取得と予想の状況: 中央（jvdata-store）と地方（nvdata-store）のデータがどこまで入っているか（出馬表・オッズ・馬体重・
馬場状態・確定成績・同期の記録）と、今週の予想（中央）がそれに追いついているか（レースごとに 最新 / 時点が進んだ /
作り方が古い / オッズが新しい / 未予想）を、表で出す。

    uv run python tools/取得と予想の状況/status.py                       # 今日（今日にレースが無ければ次の開催日）のレースごとの表も
    uv run python tools/取得と予想の状況/status.py --date 2026-10-11     # その日のレースごとの表
    uv run python tools/取得と予想の状況/status.py --format json
    uv run python tools/取得と予想の状況/status.py --store-url http://127.0.0.1:9000/   # jvdata-store の画面のポートを変えているとき
    uv run python tools/取得と予想の状況/status.py --local-db D:/keiba/nvdata.duckdb   # 地方の DB が別の場所にあるとき

同じ表を、検索画面の「状況」タブ（同じフォルダの run.bat で開く）が見せる。
jvdata-store・nvdata-store の画面が動いているか・何を取得中かも聞く（アドレスは既定で http://127.0.0.1:8766/ と 8768/）。
DB は読むだけで、短く開いてすぐ手放す（取得中なら「読めない」と出し、ほかの項目は出す）。事実表は作らない。
"""

from __future__ import annotations

import functools
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[0])]

from 共通 import cli, db  # noqa: E402
from 取得と予想の状況.overview_reader import OverviewReader  # noqa: E402
from 取得と予想の状況.overview_tables import OverviewTables  # noqa: E402
from 取得と予想の状況.local_store_reader import DEFAULT_LOCAL_DB, LocalStoreReader  # noqa: E402
from 取得と予想の状況.store_screen_probe import JRA_STORE_URL, LOCAL_STORE_APP, LOCAL_STORE_URL, StoreScreenProbe  # noqa: E402
from 今週の予想.forecast_store import DEFAULT_FOLDER, ForecastStore  # noqa: E402

#: DB のロックを待つ上限（秒）。取得中なら待たずに「読めない」と出す。
DEFAULT_LOCK_WAIT_SECONDS = 3.0


def main(args) -> None:
    path = db.resolve_db(args.db)
    local = LocalStoreReader(args.local_db, StoreScreenProbe(args.local_store_url, LOCAL_STORE_APP), lock_timeout=args.wait)
    reader = OverviewReader(connect=functools.partial(db.open_db, path, lock_timeout=args.wait), db_path=path,
                            forecasts=ForecastStore(args.forecasts), probe=StoreScreenProbe(args.store_url), local=local)
    cli.emit(OverviewTables().tables(reader.read(args.date)), args)


def build_parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--date", help="レースごとの表に出す開催日 YYYY-MM-DD（省略すると今日。今日にレースが無ければ次の開催日）")
    parser.add_argument("--store-url", default=JRA_STORE_URL, help=f"jvdata-store の画面のアドレス（既定 {JRA_STORE_URL}）")
    parser.add_argument("--local-db", type=Path, default=DEFAULT_LOCAL_DB, help=f"地方競馬DATA の DB（既定 {DEFAULT_LOCAL_DB}）")
    parser.add_argument("--local-store-url", default=LOCAL_STORE_URL, help=f"nvdata-store の画面のアドレス（既定 {LOCAL_STORE_URL}）")
    parser.add_argument("--wait", type=float, default=DEFAULT_LOCK_WAIT_SECONDS,
                        help=f"DB が使用中のとき待つ秒数（既定 {DEFAULT_LOCK_WAIT_SECONDS:g}。過ぎたら読めないまま出す）")
    parser.add_argument("--forecasts", type=Path, default=DEFAULT_FOLDER, help="今週の予想の結果の置き場所（既定: reports/今週の予想）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
