"""近走の文: 馬の過去走を1走ずつ文にして、負けた走には敗因の候補を添える。

    uv run python tools/近走の文/story.py ウマノナマエ                          # 馬名（部分一致）か hid。今日より前の近5走
    uv run python tools/近走の文/story.py 2021100001 --before 2026-10-18 --runs 8
    uv run python tools/近走の文/story.py --rid 2026101805040611              # 出馬表（出走馬名表）の全頭。基準日はそのレースの日
    uv run python tools/近走の文/story.py --rid 2026101805040611 --out reports/tmp/story.md

文は JV-Data にある事実（着順・人気・着差・コーナーの順位・上がり・ペース・馬場・騎手・馬体重）と、回顧の不利判定
（reports/回顧/review.duckdb。無ければ不利なし）から定型で作る。敗因の候補は 4着以下の走にだけ付き、材料が無ければ書かない。
馬名の候補が複数なら候補の表を出すので、hid を指定し直す。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import card, cli, db, horse, keys  # noqa: E402

from yosou.review.repository.review_store import DEFAULT_REVIEW_DB, ReviewStore  # noqa: E402
from 近走の文.card_horse_repository import CardHorseRepository  # noqa: E402
from 近走の文.past_run_reader import PastRunReader  # noqa: E402
from 近走の文.past_run_story import RUNS_SHOWN, PastRunStory  # noqa: E402
from 近走の文.story_writer import StoryWriter  # noqa: E402


def main(args: argparse.Namespace) -> None:
    if not args.rid and not args.target:
        raise ValueError("馬名か hid か、--rid を指定してください")
    with db.open_db(args.db) as con:
        reader = PastRunReader(con, ReviewStore(args.review_db))
        story = PastRunStory(args.runs)
        if args.rid:
            horses, before, title = _card(con, args.rid)
        else:
            horses, before, title = _one_horse(con, args.target, args.before, args)
            if horses is None:
                return
        history = reader.read([horse_id for horse_id, _ in horses], before)
        stories = [story.of(horse_id, name, history[horse_id]) for horse_id, name in horses]
    text = StoryWriter().markdown(stories, title)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8", newline="\n")
    print(text)


def _card(con: duckdb.DuckDBPyConnection, rid: str) -> tuple[list[tuple[str, str]], date, str]:
    """出馬表の全頭。基準日はそのレースの日。"""
    frame = CardHorseRepository(con).read(rid)
    if frame.empty:
        raise LookupError(f"出走馬が見つかりません: {rid}")
    parts = keys.split_rid(rid)
    day = date.fromisoformat(f"{parts['開催年']}-{parts['開催月日'][:2]}-{parts['開催月日'][2:]}")
    title = card.header_title(card.race_header(con, rid))
    return [(str(row.horse_id), str(row.horse_name)) for row in frame.itertuples(index=False)], day, f"{title} の近走の文"


def _one_horse(con: duckdb.DuckDBPyConnection, target: str, before: date | None,
               args: argparse.Namespace) -> tuple[list[tuple[str, str]] | None, date, str]:
    """馬名か hid の1頭。候補が複数なら候補の表を出して None。"""
    text = target.strip()
    if len(text) == keys.HID_LENGTH and text.isdigit():
        hid = text
    else:
        found = horse.find_horses(con, text)
        if len(found.rows) != 1:
            cli.emit(found, args)
            return None, before or date.today(), ""
        hid = str(found.rows[0][0])
    name = str(horse.horse_profile(con, hid)["馬名"])
    day = before or date.today()
    return [(hid, name)], day, f"{name} の近走の文（{day.isoformat()} より前）"


def build_parser() -> argparse.ArgumentParser:
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("target", nargs="?", help="馬名（部分一致）か hid（10桁）")
    parser.add_argument("--rid", help="出馬表の rid（16桁）。その全頭の近走の文を出す")
    parser.add_argument("--before", type=date.fromisoformat, help="この日より前の走だけ（既定: 今日。--rid のときはそのレースの日）")
    parser.add_argument("--runs", type=int, default=RUNS_SHOWN, help=f"文にする走の数（新しい方から。既定 {RUNS_SHOWN}。0 で全部）")
    parser.add_argument("--review-db", type=Path, default=DEFAULT_REVIEW_DB, help=f"回顧の DuckDB（既定: {DEFAULT_REVIEW_DB}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
