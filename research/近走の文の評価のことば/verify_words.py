"""近走の文の評価のことばと苦手の傾向の線を、過去の全走で確かめる。

    uv run python research/近走の文の評価のことば/verify_words.py                      # 全走（2011年〜）で確かめて reports/ に書く
    uv run python research/近走の文の評価のことば/verify_words.py --recent-from 2021    # 「最近」の区切りの年を変える（既定 2021）

候補のことば（負けて強し・上向き・人気薄で好走の実績・大敗続き）と苦手の傾向（重い馬場・芝ダ・距離。線の候補ごと）を、
各走の「その走までの材料」だけで付け、付いた走の3着以内率を同じ人気の馬がふつう出す率と比べる（人気から見た差）。
結果は reports/近走の文の評価のことば/評価のことばの確かめ.md（全期間と、最近の年以降の2つの表）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db  # noqa: E402

from yosou.review.repository.review_store import DEFAULT_REVIEW_DB, ReviewStore  # noqa: E402
from 近走の文の評価のことば.analysis.label_tally import LabelTally  # noqa: E402
from 近走の文の評価のことば.analysis.report_writer import ReportWriter  # noqa: E402
from 近走の文の評価のことば.analysis.run_frame_repository import RunFrameRepository  # noqa: E402
from 近走の文の評価のことば.analysis.tendency_labels import TendencyLabels  # noqa: E402
from 近走の文の評価のことば.analysis.word_labels import WORD_SIDES, WordLabels  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = _REPO_ROOT / "reports" / "近走の文の評価のことば" / "評価のことばの確かめ.md"


def main(args) -> None:
    with db.open_db(args.db) as con:
        frame = RunFrameRepository(con, ReviewStore(args.review_db)).read()
    words = WordLabels().of(frame)
    tendencies = TendencyLabels().of(frame)
    # 苦手の傾向は「次も苦手」の向きなので、悪いことばとして（差が − なら採用）数える
    sides = {**WORD_SIDES, **{name: False for name in tendencies.columns}}
    labels = words.join(tendencies)
    sections = []
    for heading, chosen in ((f"全期間（{frame['year'].min()}〜{frame['year'].max()}年）", frame.index),
                            (f"{args.recent_from}年以降", frame.index[frame["year"] >= args.recent_from])):
        rows = LabelTally(frame.loc[chosen]).rows(labels.loc[chosen], sides)
        sections.append((heading, rows))
    notes = [
        f"出走した走 {len(frame):,}（取消・除外を除く）。ことばは各走の前の走だけから付け、その走の3着以内率を数えた。",
        "人気から見た差 = 3着以内率 − 同じ人気の馬がふつう出す3着以内率（期待はその表の全走で数える）。標準誤差は差のばらつき。",
        "採用は、良いことばなら差が +（標準誤差の2倍以上）、悪いことばなら −（同じく）。苦手の傾向は「次も苦手」なので差が −なら採用。",
        f"回顧の不利は {args.review_db} の表3から。",
    ]
    text = ReportWriter().markdown("近走の文の評価のことばの確かめ", sections, notes)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8", newline="\n")
    print(text)
    print(f"（書いた場所: {args.out}）")


def build_parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--recent-from", type=int, default=2021, help="「最近」の表に入れる最初の年（既定 2021）")
    parser.add_argument("--review-db", type=Path, default=DEFAULT_REVIEW_DB, help=f"回顧の DuckDB（既定: {DEFAULT_REVIEW_DB}）")
    parser.set_defaults(out=DEFAULT_OUT)
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
