"""開催日の予想のまとめ: 保存してある予想（reports/今週の予想/<開催日>/<rid>.json）と計画（plan.json）から、
一覧（1行1レース）・買うレース（計画の表）・レースごとの印と買い目・◎ の理由と近走の Markdown を出す。

    uv run python tools/今週の予想/summary.py --date 2026-10-31            # その日のまとめを出し、まとめ.md も書き直す
    uv run python tools/今週の予想/summary.py --date 2026-10-31 --brief    # 一覧・買うレースと、重賞・実際に買うレースの文だけ（まとめ.md は書かない）
    uv run python tools/今週の予想/summary.py --date 2026-10-31 --out 土曜.md

forecast.py は予想と計画のあとに同じまとめを reports/今週の予想/<開催日>/まとめ.md に自動で書く。この道具は出し直すためのもの。
DB は開かないので、forecast.py が予想している間でも使える。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[0])]

from 共通 import cli, render  # noqa: E402

from 今週の予想.day_summary import DaySummary  # noqa: E402
from 今週の予想.forecast_store import DEFAULT_FOLDER, ForecastStore  # noqa: E402
from 今週の予想.plan_store import PlanStore  # noqa: E402
from 今週の予想.summary_store import SummaryStore  # noqa: E402


def main(args) -> None:
    store = ForecastStore(args.out_dir)
    if not (store.folder / args.date.isoformat()).is_dir():
        days = sorted(path.name for path in store.folder.iterdir() if path.is_dir() and path.name[:1].isdigit()) if store.folder.is_dir() else []
        raise LookupError(f"{args.date} の予想がありません（{store.folder}）。あるのは: {'、'.join(days[-5:]) or 'なし'}")
    text = DaySummary(store, PlanStore(store)).markdown(args.date, brief=args.brief)
    if not args.brief:
        print(f"まとめ: {SummaryStore(store).save(args.date, text)}", file=sys.stderr, flush=True)
    render.write(text, args.out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--date", type=date.fromisoformat, default=date.today(), help="開催日 YYYY-MM-DD（既定: 今日）")
    parser.add_argument("--brief", action="store_true", help="一覧・買うレースと、平地の重賞・実際に買うレースの文だけにする（まとめ.md は書かない）")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_FOLDER, help="予想の置き場所（既定: reports/今週の予想）")
    parser.add_argument("--out", type=Path, default=None, help="このファイルに書く（省略すると標準出力）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
