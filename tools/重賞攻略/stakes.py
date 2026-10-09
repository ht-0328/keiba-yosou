"""重賞（G1・G2・G3）ごとの「攻略ポイント」を、過去の開催のずれから出す。

    uv run python tools/重賞攻略/stakes.py --list                    # 重賞の一覧（番号・名前・開催数）
    uv run python tools/重賞攻略/stakes.py --name 有馬               # 名前（部分一致）で1レースのページを出す
    uv run python tools/重賞攻略/stakes.py --no 0006                 # 特別競走番号で
    uv run python tools/重賞攻略/stakes.py --all                     # 全重賞のページと索引を reports/重賞攻略/ に書く
    uv run python tools/重賞攻略/stakes.py --name 有馬 --before 2025-12-01   # その日より前の開催だけで数える

どのレースでも成り立つ一般論（1番人気や前に行く馬が走る）ではなく、**そのレースならではのずれ**を出す。
人気の信頼度は同じグレードの重賞全体と、脚質の前・枠の内はそのコースの全クラスと、
年齢・ローテなどはそのレースのほかの出走馬と比べ、ずれの大きさ・検定の印・回収率を添える。
持続性の注意（人気・脚質・枠は年をまたいで持続しやすい、荒れ度などは入れ替わりやすい）もページに書く。

予想モデル「重賞の傾向と近走から3着以内を予想」の特徴量は、同じ数え上げ（tools/共通/stakes.py）を使う。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db  # noqa: E402
from 重賞攻略 import page  # noqa: E402
from 重賞攻略.guide import StakesGuide  # noqa: E402

#: --all の既定の出力先（Git 対象外）。
DEFAULT_OUT_DIR = Path("reports/重賞攻略")


def main(args) -> None:
    with db.open_db(args.db) as con:
        guide = StakesGuide.load(con, args.before)
    if args.list:
        cli.emit(guide.list_table(), args)
        return
    if args.all:
        _write_all(guide, args.out_dir)
        return
    if not (args.no or args.name):
        raise ValueError("--list・--all・--name・--no のどれかを指定してください")
    built = guide.page(guide.choose(args.no, args.name))
    _write_page_text(built.markdown, args.out)


def _write_all(guide: StakesGuide, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    pages: list[page.StakesPage] = []
    for stakes_no in guide.stakes_numbers():
        built = guide.page(stakes_no)
        (out_dir / built.file_name).write_text(built.markdown, encoding="utf-8", newline="\n")
        pages.append(built)
    (out_dir / "README.md").write_text(_index_markdown(pages), encoding="utf-8", newline="\n")
    print(f"{len(pages)} レースのページと索引を {out_dir} に書きました")


def _index_markdown(pages: list[page.StakesPage]) -> str:
    lines = [
        "# 重賞攻略の索引", "",
        "レースごとの攻略ポイント（過去の開催の、基準からのずれ）。作り直すときは "
        "`uv run python tools/重賞攻略/stakes.py --all`。"
        "距離の変更の列は、前走から距離を短縮した馬と延長した馬のどちらが有利か（人気の偏りを除いて比べ、"
        "検定で 5%・1% の線を超えたときだけ書く）。", "",
        "| グレード | 競走名 | 条件 | 開催数 | 攻略ポイント | 主なポイント | 距離の変更（勝つ） | 距離の変更（穴馬の好走） |",
        "|" + " :--- |" * 8,
    ]
    grade_names = {"A": "G1", "B": "G2", "C": "G3"}
    for built in pages:
        first = built.findings[0].text.split(" — ")[0] if built.findings else "（有意なずれなし）"
        condition = f"{built.venue} {built.course} {built.distance_m}m"
        lines.append(
            f"| {grade_names.get(built.grade, built.grade)} | [{built.stakes_name}]({built.file_name}) "
            f"| {condition} | {built.editions} | {len(built.findings)} | {first} "
            f"| {built.distance_win} | {built.distance_longshot} |")
    lines.append("")
    return "\n".join(lines)


def _write_page_text(markdown: str, out: Path | None) -> None:
    if out is None:
        sys.stdout.write(markdown)
        sys.stdout.flush()
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(markdown, encoding="utf-8", newline="\n")


def build_parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--list", action="store_true", help="重賞の一覧を出して終わる")
    parser.add_argument("--all", action="store_true", help=f"全重賞のページと索引を --out-dir（既定 {DEFAULT_OUT_DIR}）に書く")
    parser.add_argument("--name", help="競走名（部分一致）で1レースを選ぶ")
    parser.add_argument("--no", help="特別競走番号で1レースを選ぶ")
    parser.add_argument("--before", help="この開催日より前の開催だけで数える（YYYY-MM-DD。モデルが見る値の確かめ用）")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="--all の出力先")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
