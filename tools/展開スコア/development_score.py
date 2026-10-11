"""展開スコア: 脚質 × ペースの有利・不利を市場の見立てとの差で数え、出走馬ごとに展開有利・展開不利を判定する。

    uv run python tools/展開スコア/development_score.py --date 2026-10-11 --venue 東京 --race 11            # 1レース
    uv run python tools/展開スコア/development_score.py 2026101105050411                                    # rid で
    uv run python tools/展開スコア/development_score.py --date 2026-10-11 --all                             # その日の全レース
    uv run python tools/展開スコア/development_score.py --date 2026-10-11 --venue 東京 --race 11 --detail   # 脚質ごとの内訳も出す
    uv run python tools/展開スコア/development_score.py --table --venue 東京 --surface 芝                   # 表 G（東京・芝）を見る
    uv run python tools/展開スコア/development_score.py --table                                             # 表 G を全部見る
    uv run python tools/展開スコア/development_score.py --date 2026-10-11 --all --rebuild                   # 表 G を作り直してから

予想「展開から着順を予想」の保存したモデルで、各馬が逃げ・先行・差し・追込の位置を取る確率とレースのペース（ハイ・平均・スロー）の確率を出し、
過去のレースから数えた表 G（脚質 × ペース × 競馬場と芝ダ ごとの「実際の3着以内率 − 市場から見た3着以内率」）と掛け合わせて、
馬ごとの展開スコア（3着以内の確率のポイント。+0.02 なら市場の見立てより 2ポイント来やすい）を出す。線（±0.01）で展開有利・展開不利を判定する
（設計書「買うレースと買い目を決める」05）。時点（木曜・前日・当日）は DB の情報から自動で選ぶ（今週の予想と同じ決め方）。
表 G は 2011年からの全出走から作り、``reports/展開スコア/cache/`` にとっておく（元DB が更新されたら作り直す。1分ほど）。
先に ``uv run python -m yosou.race_development train`` で展開のモデルを作っておく。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import card, cli, codes, db, race  # noqa: E402
from 共通.render import Table  # noqa: E402

from 今週の予想.timing_chooser import TimingChooser  # noqa: E402

from yosou.development_score import (  # noqa: E402
    DEFAULT_CACHE_FOLDER,
    DEFAULT_LINE,
    AdvantageJudge,
    AdvantageTable,
    AdvantageTableStore,
    RaceScore,
    RaceScoreWorkflow,
    names,
)
from yosou.development_score.entry_name_repository import HORSE_NAME, HORSE_NO  # noqa: E402
from yosou.form_aptitude_top3.command.development_root_argument import DEFAULT_DEVELOPMENT_ROOT  # noqa: E402
from yosou.shared.feature import PredictionTiming  # noqa: E402

#: 1頭ごとの表の列（``--detail`` で内訳の4列を足す）。
HORSE_COLUMNS: list[str] = ["馬番", "馬名", *names.STYLES, "展開スコア", "判定"]


def main(args) -> None:
    judge = AdvantageJudge(args.line)
    with db.open_db(args.db) as con:
        if args.rebuild:
            print("表 G を 2011年からの全出走から作り直しています …", file=sys.stderr, flush=True)
        table = AdvantageTableStore(args.cache).load(con, db.resolve_db(args.db), rebuild=args.rebuild)
        if args.table:
            results = _table_views(table, args)
        else:
            results = _race_views(con, table, judge, args)
    cli.emit(results, args)


def _race_views(con, table: AdvantageTable, judge: AdvantageJudge, args) -> list[Table]:
    workflow = RaceScoreWorkflow(args.development_root / "models", table, judge)
    chooser = TimingChooser()
    results = []
    for rid in _rids(con, args):
        header = card.race_header(con, rid)
        if header["コース"].startswith("障害"):
            print(f"飛ばします（障害）: {card.header_title(header)}", file=sys.stderr, flush=True)
            continue
        if args.timing:
            timing, reason = PredictionTiming.parse(args.timing), "指定"
        else:
            choice = chooser.choose(con, rid)
            timing, reason = choice.timing, choice.reason
        score = workflow.run(con, rid, timing)
        results.append(_race_table(score, card.header_title(header), reason, table, judge, args.detail))
    return results


def _race_table(score: RaceScore, title: str, reason: str, table: AdvantageTable, judge: AdvantageJudge, detail: bool) -> Table:
    columns = HORSE_COLUMNS + (list(names.CONTRIBUTIONS) if detail else [])
    rows = []
    for _, horse in score.horses.iterrows():
        row: dict[str, Any] = {"馬番": _plain(horse[HORSE_NO]), "馬名": horse[HORSE_NAME],
                               **{style: _percent(horse[style]) for style in names.STYLES},
                               "展開スコア": _points(horse[names.SCORE]), "判定": horse[names.VERDICT]}
        row.update({name: _points(horse[name]) for name in names.CONTRIBUTIONS})
        rows.append([row[column] for column in columns])
    paces = "・".join(f"{pace} {_percent(score.paces[pace])}" for pace in (names.HIGH, names.EVEN, names.SLOW))
    note = (f"時点: {score.timing.label}（{reason}）。ペースの確率: {paces}。"
            f"逃げ〜追込は各馬がその位置を取る確率。展開スコアは3着以内の確率のポイント（市場の見立てとの差）。"
            f"線 ±{judge.line:g} で展開有利・展開不利。表 G は {_as_of(table)} までの {codes.venue_name(score.venue_code)}・{score.surface} のレースから")
    return Table(columns, rows, title=f"展開スコア: {title}", note=note)


def _table_views(table: AdvantageTable, args) -> list[Table]:
    """競馬場と芝ダごとの表 G。材料に無い競馬場（や材料が無いとき）は全競馬場の値を1つの表で出す。"""
    if args.venue and args.surface:
        return [_matrix_table(table, codes.venue_code(args.venue), args.surface, args.detail)]
    courses = table.frame[[names.VENUE_CODE, names.SURFACE]].drop_duplicates().sort_values([names.VENUE_CODE, names.SURFACE])
    if args.venue:
        courses = courses[courses[names.VENUE_CODE] == codes.venue_code(args.venue)]
    if args.surface:
        courses = courses[courses[names.SURFACE] == args.surface]
    if courses.empty:
        return [_matrix_table(table, None, None, args.detail)]
    return [_matrix_table(table, venue, surface, args.detail) for venue, surface in courses.itertuples(index=False)]


def _matrix_table(table: AdvantageTable, venue: str | None, surface: str | None, detail: bool) -> Table:
    """1つの競馬場と芝ダの 4 × 3 の表。``venue`` が None か材料に無ければ、全競馬場の値（競馬場で分けない表）。"""
    rows_of = table.frame[(table.frame[names.VENUE_CODE] == venue) & (table.frame[names.SURFACE] == surface)] if venue else table.frame.iloc[:0]
    pooled = rows_of.empty
    source = table.pool if pooled else rows_of
    counts = source.pivot(index=names.STYLE, columns=names.PACE, values=names.COUNT)
    matrix = source.pivot(index=names.STYLE, columns=names.PACE, values=names.GAP)
    rows = []
    for style in names.STYLES:
        values = [_points(matrix.loc[style, pace]) + (f"（{int(counts.loc[style, pace]):,}）" if detail else "") for pace in names.PACES]
        rows.append([style, *values])
    where = "全競馬場" if venue is None else f"{codes.venue_name(venue)}・{surface}"
    note = (f"{_as_of(table)} までのレース。値は「実際の3着以内率 − 市場から見た3着以内率」の平均（ポイント）で、"
            "件数の少ないマスは同じ脚質 × ペースの全競馬場の値に寄せてある" + ("。括弧は件数" if detail else "")
            + ("。この競馬場・芝ダは材料に無いので、全競馬場の値" if pooled and venue else ""))
    return Table(["脚質", *names.PACES], rows, title=f"表 G: {where}", note=note)


def _rids(con, args) -> list[str]:
    if args.all:
        if not args.date or args.rid or args.race:
            raise ValueError("--all は --date（と --venue）と合わせて使います")
        cards = card.list_cards(con, date_from=args.date, date_to=args.date, venue=args.venue)
        if not cards.rows:
            raise LookupError(f"{args.date} のレースが DB にありません")
        rid_at = cards.columns.index("rid")
        return [row[rid_at] for row in cards.rows]
    if args.rid:
        return [args.rid]
    if args.date and args.venue and args.race:
        return [race.resolve_rid(con, args.date, args.venue, args.race)]
    raise ValueError("レースを指定します: rid か --date --venue --race、またはその日の全レースなら --date --all（表 G だけ見るなら --table）")


def _as_of(table: AdvantageTable) -> str:
    return "（材料なし）" if table.as_of is None else f"{table.as_of:%Y-%m-%d}"


def _percent(value) -> str:
    return "" if value is None or value != value else f"{value:.0%}"


def _points(value) -> str:
    return "" if value is None or value != value else f"{value:+.3f}"


def _plain(value):
    return None if value is None or value != value else int(value)


def build_parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("rid", nargs="?", help="レースの rid（16桁）")
    parser.add_argument("--date", help="開催日（YYYY-MM-DD）")
    parser.add_argument("--venue", help="競馬場（東京・中山 … かコード）。--table では表 G を絞る")
    parser.add_argument("--race", type=int, help="レース番号")
    parser.add_argument("--all", action="store_true", help="--date の日の全レース（--venue で絞れる）")
    parser.add_argument("--timing", choices=[timing.label for timing in PredictionTiming], default=None,
                        help="時点を指定する（省略すると DB の情報から自動で選ぶ）")
    parser.add_argument("--detail", action="store_true", help="脚質ごとの内訳（--table では件数）も出す")
    parser.add_argument("--table", action="store_true", help="レースではなく、表 G を見る（--venue・--surface で絞る）")
    parser.add_argument("--surface", choices=["芝", "ダート"], default=None, help="--table で見る芝ダ")
    parser.add_argument("--line", type=float, default=DEFAULT_LINE, help=f"展開有利・展開不利の線（既定: {DEFAULT_LINE:g}）")
    parser.add_argument("--rebuild", action="store_true", help="表 G を作り直す（元DB が更新されたときは自動で作り直す）")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE_FOLDER, help="表 G をとっておく場所（既定: reports/展開スコア/cache）")
    parser.add_argument("--development-root", type=Path, default=DEFAULT_DEVELOPMENT_ROOT,
                        help="予想「展開から着順を予想」の置き場所（既定: reports/展開から着順を予想。その models/ を読む）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
