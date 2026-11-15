"""地方の印の買い目に、裏（1着が ○▲☆ で ◎ が2着か3着）を足すかを、裏の当たる確率のモデルで決められるかを確かめる（中央の研究「裏目を買うかの予想」の地方版）。

    uv run python research/地方の印の買い目/reverse.py --build-marked          # 印の全頭の表を作る（元DB を読む。数分）
    uv run python research/地方の印の買い目/reverse.py                         # 年を入れ替えて学び、今のままと比べる（数分）
    uv run python research/地方の印の買い目/reverse.py --protocol 前の年       # 前の年だけで学ぶ（2025・2026年）

印の全頭の表は、印の組の表（``mark_tickets.py --build``）の元になった道具「印の成績」と同じ引数で付ける。比べは印の組の表（``印の組[-前の年].pkl``）の
馬単の裏の行を使う。出るもの（Git 対象外）: reports/地方の印の買い目/marked.pkl・裏を買うかの成績[-前の年].md。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
_REPO_ROOT = _RESEARCH.parent
sys.path[:0] = [str(_RESEARCH), str(_REPO_ROOT / "tools")]

import pandas as pd  # noqa: E402

from 共通 import cli  # noqa: E402
from 地方の印の買い目.analysis.mark_table_builder import LEAVE_ONE_OUT, PROTOCOLS  # noqa: E402
from 地方の印の買い目.analysis.mark_table_store import MarkTableStore  # noqa: E402
from 地方の印の買い目.analysis.marked_table import MarkedTable, MarkedTableSettings  # noqa: E402
from 地方の印の買い目.analysis.reverse_study import ReverseStudy  # noqa: E402

DEFAULT_OUT = _REPO_ROOT / "reports" / "地方の印の買い目"
_FORM = _REPO_ROOT / "reports" / "地方競馬の近走と適性から3着以内を予想"
MARKED_NAME = "marked.pkl"


def main(args: argparse.Namespace) -> None:
    marked_path = args.out_dir / MARKED_NAME
    if args.build_marked:
        settings = MarkedTableSettings(form=_FORM / "predictions-2024検証" / "race_day.pkl", win=_FORM / "predictions-2024検証" / "race_day-1着.pkl",
                                       models=_FORM / "models-2024検証", db_path=args.db)
        table = MarkedTable(settings).build()
        args.out_dir.mkdir(parents=True, exist_ok=True)
        table.to_pickle(marked_path)
        print(f"{table['race_id'].nunique():,} レースの印の表を書きました: {marked_path}")
        return
    suffix = "" if args.protocol == LEAVE_ONE_OUT else f"-{args.protocol}"
    marked = pd.read_pickle(marked_path)
    path = ReverseStudy(MarkTableStore(args.out_dir, suffix).load(), marked, args.protocol).write(args.out_dir)
    print(f"書きました: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--build-marked", action="store_true", help="印の全頭の表を作る（元DB を読む）")
    parser.add_argument("--db", default=None, help="元DB のパス（既定: 地方の元DB。写しを渡せる）")
    parser.add_argument("--protocol", choices=PROTOCOLS, default=LEAVE_ONE_OUT, help="当てはめ方（既定: 入れ替え）")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help=f"書く場所（既定: {DEFAULT_OUT}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
