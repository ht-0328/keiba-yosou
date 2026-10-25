"""特別登録の時点の全頭評価を、1レース 1枚の Markdown に書く。

    uv run python tools/全頭評価/review.py --date 2026-10-18 --venue 京都 --race 11
    uv run python tools/全頭評価/review.py 2026101808040711
    uv run python tools/全頭評価/review.py --date 2026-10-18 --all

登録馬の全員について、予想「特別登録馬の近走と適性から3着以内を予想」の確率と寄与、事実表の数字、重賞の傾向から、
有力馬の候補・評価順の表・馬ごとの強みと弱みを定型の文で出す。印・的中率と配当率・買い目・想定人気は出さない。
書く場所は reports/全頭評価/<開催日>/<rid>.md（--out-dir で変えられる）。同じ内容を標準出力にも出す。
予測の前に jvdata-store で特別登録（TOKU）と確定成績・調教・マスタを取り込んでおく（出走馬名表・オッズは要らない）。
モデルは予想の学習済みのもの（--models。既定は reports/特別登録馬の近走と適性から3着以内を予想/models）。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db  # noqa: E402

from yosou.shared.command import FigureCacheArgument  # noqa: E402
from yosou.special_registration_top3.repository import RegistrationListRepository, RegistrationRaceRepository  # noqa: E402
from yosou.special_registration_top3.workflow import REPORT_ROOT  # noqa: E402
from 全頭評価.field_review import FieldReview  # noqa: E402
from 全頭評価.review_writer import ReviewWriter  # noqa: E402

#: 書く場所の既定（Git の対象外の reports/）。
DEFAULT_OUT_DIR = Path(__file__).resolve().parents[2] / "reports" / "全頭評価"
DEFAULT_MODELS = REPORT_ROOT / "models"


def race_ids(args: argparse.Namespace, con: duckdb.DuckDBPyConnection) -> list[str]:
    """rid か、開催日・競馬場・レース番号か、``--all`` の日の登録のある全レース。"""
    if args.rid:
        return [args.rid]
    if args.all:
        if args.date is None:
            raise ValueError("--all には --date（開催日）を指定してください")
        races = RegistrationListRepository(con).read(args.date, args.date)
        if races.empty:
            raise LookupError(f"{args.date} に特別登録のある平地のレースがありません")
        return [str(race_id) for race_id in races["race_id"]]
    if not (args.date and args.venue and args.race):
        raise ValueError("rid か、--date --venue --race の3つ（または --date と --all）を指定してください")
    return [RegistrationRaceRepository(con).resolve(args.date.isoformat(), args.venue, args.race)]


def main(args: argparse.Namespace) -> None:
    writer = ReviewWriter()
    with db.open_db(args.db) as con:
        review = FieldReview(con, args.models, args.figure_cache)
        for race_id in race_ids(args, con):
            document = review.build(race_id)
            text = writer.markdown(document)
            folder = args.out_dir / document.race_date.isoformat()
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"{race_id}.md"
            path.write_text(text, encoding="utf-8", newline="\n")
            print(text)
            print(f"（書いた場所: {path}）\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("rid", nargs="?", help="レースの rid（16桁。特別登録から引く）")
    parser.add_argument("--date", type=date.fromisoformat, help="開催日 YYYY-MM-DD（rid を省くとき）")
    parser.add_argument("--venue", help="競馬場の名前かコード（rid を省くとき）")
    parser.add_argument("--race", type=int, help="レース番号（rid を省くとき）")
    parser.add_argument("--all", action="store_true", help="--date の日の、特別登録のある平地の全レースを出す")
    parser.add_argument("--models", type=Path, default=DEFAULT_MODELS, help=f"予想の学習済みモデルの置き場所（既定: {DEFAULT_MODELS}）")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help=f"評価を書く場所（既定: {DEFAULT_OUT_DIR}。<開催日>/<rid>.md）")
    parser.add_argument("--db", default=None, help="元DB のパス（既定: ../jvdata-store/jvdata.duckdb か環境変数 YOSOU_DB）")
    FigureCacheArgument().add_to(parser)
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
