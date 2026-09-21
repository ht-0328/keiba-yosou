"""傾向スコア: 当日のレースと条件が同じ過去レースの傾向を出し、出走馬を項目ごとに +1 / −1 で採点して順位を付ける。

    uv run python tools/傾向スコア/trend_score.py --date 2026-09-19 --venue 中山 --race 11 --html          # グラフ付きのページを reports/trend-score/ に書く
    uv run python tools/傾向スコア/trend_score.py --date 2026-09-19 --venue 中山 --race 11 --condition 良 --pops "3:1,7:2,1:3" --html --open
    uv run python tools/傾向スコア/trend_score.py --date 2026-09-19 --all --open                            # その日の全レースのページと、一覧のページを書く
    uv run python tools/傾向スコア/trend_score.py 2026091906040511                                          # 表だけを標準出力へ（rid で）
    uv run python tools/傾向スコア/trend_score.py --items                                                   # 点数化項目の一覧

母集団は、開催日より前の「同レース → 4つ一致（競馬場・コース・距離・馬場状態）→ 3つ以上一致 → 2つ以上一致」。
値ごとの成績を基準値と比べ、出走数が足りるいちばん狭い段で「頭向き・相手向き（+1）」「悪い（−1）」を判定する。
発走前の DB に無い材料は手で与える: 馬場状態 ``--condition``、人気 ``--pops``、馬体重 ``--weights``。無ければその項目は 0 点。
終わったレースにも使える（着順が並ぶので、点数と結果を見比べられる）。項目の説明は ``tools/傾向スコア/score-items.md``。
"""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import card, cli, db, race, trend, trend_html  # noqa: E402

#: グラフ付きのページの既定の置き場（Git 対象外）。
REPORT_DIR = Path(__file__).resolve().parents[2] / "reports" / "trend-score"
_AUTO = "auto"


def main(args) -> None:
    if args.items:
        cli.emit(trend.catalog_table(), args)
        return
    inputs = trend.ManualInputs.parse(condition=args.condition, popularity=args.pops, weights=args.weights)
    options = trend.Options(scope=args.scope, min_runs=args.min_runs, good=args.good, bad=args.bad, min_z=args.min_z)
    if args.all:
        _write_all(args, inputs, options)
        return
    if not args.rid and not (args.date and args.venue and args.race):
        raise ValueError("レースを rid か、--date --venue --race の3つで指定してください（その日の全部なら --date --all）")
    with db.open_db(args.db) as con:
        rid = args.rid or race.resolve_rid(con, args.date, args.venue, args.race)
        report = trend.score_race(con, rid, inputs, options)
    if args.html:
        path = _write_html(report, args.html)
        print(f"グラフ付きのページを書きました: {path}", file=sys.stderr)
        if args.open:
            webbrowser.open(path.resolve().as_uri())
    if args.out or not args.html:
        tables = report.tables() if args.detail else report.tables()[:2]
        cli.emit(tables, args)


def _write_all(args, inputs: trend.ManualInputs, options: trend.Options) -> None:
    """その日（と競馬場）の全レースのページと、一覧のページを書く。"""
    if not args.date or args.rid or args.race:
        raise ValueError("--all は --date（と --venue）と合わせて使います")
    if inputs.popularity or inputs.weights:
        raise ValueError("--all では --pops・--weights は使えません（馬番ごとの値はレースごとに違うため）")
    folder = REPORT_DIR if args.html in (None, _AUTO) else Path(args.html)
    races = []
    with db.open_db(args.db) as con:
        cards = card.list_cards(con, date_from=args.date, date_to=args.date, venue=args.venue)
        if not cards.rows:
            raise LookupError(f"{args.date} のレースが DB にありません")
        rid_at = cards.columns.index("rid")
        for index, row in enumerate(cards.rows, start=1):
            report = trend.score_race(con, row[rid_at], inputs, options)
            path = folder / default_name(report)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(trend_html.standalone(report.to_dict()), encoding="utf-8", newline="\n")
            races.append(_index_entry(report, path.name))
            print(f"  {index} / {len(cards.rows)}: {path.name}", file=sys.stderr, flush=True)
    index_path = folder / f"{args.date}{'-' + args.venue if args.venue else ''}-index.html"
    note = "レースを押すと、傾向のグラフと採点の内訳が開きます。ここには上位5頭と合計点だけを並べています。"
    title = f"傾向スコア: {args.date} {args.venue or ''}".strip()
    index_path.write_text(trend_html.index_page(title, note, races), encoding="utf-8", newline="\n")
    print(f"一覧のページを書きました: {index_path}", file=sys.stderr)
    if args.open:
        webbrowser.open(index_path.resolve().as_uri())


def _index_entry(report: trend.TrendReport, file_name: str) -> dict:
    """一覧のページの1レースぶん。"""
    header = report.header
    missing = f"・未入力: {'、'.join(report.missing)}" if report.missing else ""
    return {
        "venue": header["競馬場"], "file": file_name, "label": f"{header['R']}R {header['レース名'] or header['クラス']}",
        "sub": f"{header['発走']} {header['コース']} {header['距離']}m {header['頭数']}頭 {header['状態']}{missing}",
        "top": [(horse.entry["horse_no"] or "", horse.entry["horse_name"], horse.score) for horse in report.horses[:trend_html.INDEX_TOP]],
    }


def _write_html(report: trend.TrendReport, target: str) -> Path:
    path = REPORT_DIR / default_name(report) if target == _AUTO else Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(trend_html.standalone(report.to_dict()), encoding="utf-8", newline="\n")
    return path


def default_name(report: trend.TrendReport) -> str:
    """``2026-09-19-中山-11R.html``。"""
    header = report.header
    return f"{header['日付']}-{header['競馬場']}-{int(header['R']):02d}R.html"


def build_parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("rid", nargs="?", help="レースの rid（16桁）")
    parser.add_argument("--date", help="開催日 YYYY-MM-DD")
    parser.add_argument("--venue", help="競馬場の名前かコード")
    parser.add_argument("--race", type=int, help="レース番号")
    manual = parser.add_argument_group("発走前の DB に無い材料（手で与える。無ければその項目は 0 点）")
    manual.add_argument("--condition", help="当日の馬場状態（良 / 稍重 / 重 / 不良）。無ければ馬場状態を問わない段で採点する")
    manual.add_argument("--pops", metavar="馬番:人気,...", help='単勝人気。例 "3:1,7:2,1:3"（分かる馬だけでよい）')
    manual.add_argument("--weights", metavar="馬番:馬体重:増減,...", help='馬体重と増減。例 "3:480:+2,7:502:-4"')
    rule = parser.add_argument_group("判定の線引き")
    rule.add_argument("--scope", choices=list(trend.LEVEL_BY_KEY), help="この段だけで判定する（既定: 出走数が足りるいちばん狭い段）")
    rule.add_argument("--min-runs", type=int, default=trend.MIN_RUNS, help=f"判定に要る出走数（既定: {trend.MIN_RUNS}）")
    rule.add_argument("--good", type=float, default=trend.GOOD_RATIO, help=f"基準値の何倍以上で良いとするか（既定: {trend.GOOD_RATIO}）")
    rule.add_argument("--bad", type=float, default=trend.BAD_RATIO, help=f"基準値の何倍以下で悪いとするか（既定: {trend.BAD_RATIO}）")
    rule.add_argument("--min-z", type=float, default=trend.MIN_Z,
                      help=f"差が偶然では起きにくいことを求める強さ。0 で求めない（既定: {trend.MIN_Z}）")
    output = parser.add_argument_group("出力")
    output.add_argument("--html", nargs="?", const=_AUTO, metavar="PATH",
                        help="グラフ付きのページ（HTML 1ファイル）を書く。PATH を省くと reports/trend-score/<日付>-<競馬場>-<R>.html")
    output.add_argument("--all", action="store_true",
                        help="--date（と --venue）の全レースのページと、一覧のページを書く。--html にフォルダを渡すと置き場を変えられる（既定は reports/trend-score/）")
    output.add_argument("--open", action="store_true", help="書いたページをブラウザで開く")
    output.add_argument("--detail", action="store_true", help="表の出力に、傾向・馬ごとの内訳・同レースの過去も入れる（既定は見出しとランキングだけ）")
    output.add_argument("--items", action="store_true", help="点数化項目の一覧を出して終わる")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
