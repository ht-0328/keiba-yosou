"""地方の印の買い目: 印で組む買い目（◎ の単勝・◎−○▲☆ の馬連・馬単とその裏・3連複・3連単・◎−☆注 のワイド）を、
地方の組の確率（研究「地方の万馬券」段5 の 1着・2着・3着の条件つきロジット）で期待値を付けて買うかを決め、2024〜2026年の年ごとに確かめる。

    uv run python research/地方の印の買い目/mark_tickets.py --build    # 印の組の表を作る（各年を残りの年で当てはめる。30〜40分）
    uv run python research/地方の印の買い目/mark_tickets.py            # 買い方の候補の年ごとの成績を書く（20分ほど）
    uv run python research/地方の印の買い目/mark_tickets.py --build --protocol 前の年   # 前の年だけで当てはめた表（2025・2026年）
    uv run python research/地方の印の買い目/mark_tickets.py --protocol 前の年           # その表で成績を書く

印の組は、道具「印の成績」を地方の全頭の予想（2023年前半までで学んだ当日の予測）で動かしたときの買い目の表から読む
（reports/印の成績/地方/2024検証/買い目/predictions-2024検証_race_day.csv）。
出るもの（Git 対象外）: reports/地方の印の買い目/印の組[-前の年].pkl・印の買い目の成績[-前の年].md。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
_REPO_ROOT = _RESEARCH.parent
sys.path[:0] = [str(_RESEARCH), str(_REPO_ROOT / "tools")]

from 共通 import cli, db  # noqa: E402
from 地方の印の買い目.analysis.mark_combos import MarkCombos  # noqa: E402
from 地方の印の買い目.analysis.mark_study import MarkStudy  # noqa: E402
from 地方の印の買い目.analysis.mark_table_builder import LEAVE_ONE_OUT, PROTOCOLS, MarkTableBuilder, MarkTableSettings  # noqa: E402
from 地方の印の買い目.analysis.mark_table_store import MarkTableStore  # noqa: E402

DEFAULT_OUT = _REPO_ROOT / "reports" / "地方の印の買い目"
DEFAULT_PREDICTIONS = _REPO_ROOT / "reports" / "地方競馬の近走と適性から3着以内を予想" / "predictions-2024検証"
DEFAULT_MARKS = _REPO_ROOT / "reports" / "印の成績" / "地方" / "2024検証" / "買い目" / "predictions-2024検証_race_day.csv"


def main(args: argparse.Namespace) -> None:
    suffix = "" if args.protocol == LEAVE_ONE_OUT else f"-{args.protocol}"
    store = MarkTableStore(args.out_dir, suffix)
    if args.build:
        print("印の組を読みます", flush=True)
        marks = MarkCombos(args.marks).load()
        settings = MarkTableSettings(date_from=args.date_from, predictions=args.predictions, protocol=args.protocol)
        with db.open_db(args.db, default=db.LOCAL) as con:
            table = MarkTableBuilder(con, settings).build(marks)
        store.save(table)
        print(f"書きました: {store.path}")
        return
    path = MarkStudy(store.load(), protocol=args.protocol).write(args.out_dir)
    print(f"書きました: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--build", action="store_true", help="印の組の表を作る（元DB を読む）")
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス（既定: ../nvdata-store/nvdata.duckdb か環境変数 YOSOU_LOCAL_DB）")
    parser.add_argument("--date-from", type=date.fromisoformat, default=date(2024, 1, 1), help="対象の最初の開催日（既定: 2024-01-01）")
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS, help="全頭の予想の当日の予測の表の置き場所")
    parser.add_argument("--protocol", choices=PROTOCOLS, default=LEAVE_ONE_OUT, help="当てはめ方（既定: 入れ替え。各年を残りの年で当てはめる）")
    parser.add_argument("--marks", type=Path, default=DEFAULT_MARKS, help="印の成績の買い目の表（地方・当日）")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help=f"書く場所（既定: {DEFAULT_OUT}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
