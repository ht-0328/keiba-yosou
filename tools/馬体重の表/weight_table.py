"""馬体重の表: 増減の帯 × 前走からの間隔 × 馬齢ごとの「市場の見立てより来たか」の表 W を見せ、出走馬ごとの体重の割引を判定する。

    uv run python tools/馬体重の表/weight_table.py --table                                              # 表 W を見る
    uv run python tools/馬体重の表/weight_table.py --table --detail                                     # 件数と寄せる前の差も
    uv run python tools/馬体重の表/weight_table.py --date 2026-10-11 --venue 東京 --race 11             # 1レースの出走馬ごとの割引
    uv run python tools/馬体重の表/weight_table.py 2026101105050411                                     # rid で
    uv run python tools/馬体重の表/weight_table.py --date 2026-10-11 --all                              # その日の全レース
    uv run python tools/馬体重の表/weight_table.py --table --rebuild                                    # 表 W を作り直してから

表 W は、過去の全出走（2011年〜）を増減の帯（−10kg以下 / −9〜−4kg / −3〜+3kg / +4〜+9kg / +10kg以上）× 前走からの間隔（中3週以内 / 4〜9週 /
10週以上）× 馬齢（2〜3歳 / 4歳以上）に分け、マスごとに「実際の3着以内率 − 市場から見た3着以内率」を平均したもの（件数の少ないマスは同じ増減の帯の
全体の値に寄せる）。市場は発表された馬体重を見てオッズを動かすので、値は「市場が割り引き足りない分」。線（−0.02）以下を「体重の割引」と判定する
（設計書「買うレースと買い目を決める」06 の 2）。表は ``reports/馬体重の表/cache/`` にとっておく（元DB が更新されたら作り直す。1分ほど）。
レースの出走馬の増減は、速報の馬体重（当日に取り込んだもの）か、終わったレースなら確定の値。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import card, cli, db, race  # noqa: E402
from 共通.render import Table  # noqa: E402

from yosou.shared.dataset.race_records_loader import RaceRecordsLoader  # noqa: E402
from yosou.weight_table import (  # noqa: E402
    DEFAULT_CACHE_FOLDER,
    DEFAULT_LINE,
    WeightBands,
    WeightJudge,
    WeightTable,
    WeightTableStore,
    names,
)

#: 1頭ごとの表の列。
HORSE_COLUMNS: list[str] = ["馬番", "馬名", "増減", "間隔", "馬齢", "増減の帯", "間隔の帯", "体重の割引", "判定"]


def main(args) -> None:
    judge = WeightJudge(args.line)
    with db.open_db(args.db) as con:
        if args.rebuild:
            print("表 W を 2011年からの全出走から作り直しています …", file=sys.stderr, flush=True)
        table = WeightTableStore(args.cache).load(con, db.resolve_db(args.db), rebuild=args.rebuild)
        results = _table_views(table, args.detail) if args.table else _race_views(con, table, judge, args)
    cli.emit(results, args)


def _race_views(con, table: WeightTable, judge: WeightJudge, args) -> list[Table]:
    results = []
    for rid in _rids(con, args):
        header = card.race_header(con, rid)
        entries = RaceRecordsLoader(con).load(rid).entries
        bands = WeightBands().of(entries["weight_change"], entries["interval_days"], entries["age"])
        discount = table.lookup(bands)
        verdict = judge.of(discount)
        rows = []
        for i in entries.index:
            rows.append([_plain(entries.loc[i, "horse_no"]), entries.loc[i, "horse_name"], _signed(entries.loc[i, "weight_change"]),
                         _plain(entries.loc[i, "interval_days"]), _plain(entries.loc[i, "age"]), bands.loc[i, names.CHANGE_BAND],
                         bands.loc[i, names.INTERVAL_BAND], _points(discount[i]), verdict[i]])
        note = (f"表 W は {_as_of(table)} までの出走から。体重の割引は3着以内の確率のポイント（負なら、市場の見立てより来ない）。"
                f"線 {judge.line:g} 以下で「体重の割引」。増減の無い馬（初出走・馬体重の未発表）は欠損値")
        results.append(Table(HORSE_COLUMNS, rows, title=f"馬体重の表: {card.header_title(header)}", note=note))
    return results


def _table_views(table: WeightTable, detail: bool) -> list[Table]:
    """馬齢の組ごとに、増減の帯 × 間隔の帯 の表。"""
    results = []
    for age in names.AGE_BANDS:
        rows_of = table.frame[table.frame[names.AGE_BAND] == age]
        matrix = rows_of.pivot(index=names.CHANGE_BAND, columns=names.INTERVAL_BAND, values=names.GAP)
        counts = rows_of.pivot(index=names.CHANGE_BAND, columns=names.INTERVAL_BAND, values=names.COUNT)
        rows = []
        for change in names.CHANGE_BANDS:
            values = []
            for interval in names.INTERVAL_BANDS:
                value = matrix.loc[change, interval] if change in matrix.index and interval in matrix.columns else float("nan")
                text = _points(value)
                if detail and change in counts.index and interval in counts.columns and pd.notna(counts.loc[change, interval]):
                    text += f"（{int(counts.loc[change, interval]):,}）"
                values.append(text)
            rows.append([change, *values])
        note = (f"{_as_of(table)} までの出走。値は「実際の3着以内率 − 市場から見た3着以内率」の平均（ポイント）で、件数の少ないマスは"
                "同じ増減の帯の全体の値に寄せてある" + ("。括弧は件数" if detail else ""))
        results.append(Table(["増減の帯", *names.INTERVAL_BANDS], rows, title=f"表 W: {age}", note=note))
    return results


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
    raise ValueError("レースを指定します: rid か --date --venue --race、またはその日の全レースなら --date --all（表 W だけ見るなら --table）")


def _as_of(table: WeightTable) -> str:
    return "（材料なし）" if table.as_of is None else f"{table.as_of:%Y-%m-%d}"


def _points(value) -> str:
    return "" if value is None or value != value else f"{value:+.3f}"


def _signed(value) -> str:
    return "" if value is None or value != value else f"{int(value):+d}"


def _plain(value):
    return None if value is None or value != value else int(value)


def build_parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("rid", nargs="?", help="レースの rid（16桁）")
    parser.add_argument("--date", help="開催日（YYYY-MM-DD）")
    parser.add_argument("--venue", help="競馬場（東京・中山 … かコード）")
    parser.add_argument("--race", type=int, help="レース番号")
    parser.add_argument("--all", action="store_true", help="--date の日の全レース（--venue で絞れる）")
    parser.add_argument("--table", action="store_true", help="レースではなく、表 W を見る")
    parser.add_argument("--detail", action="store_true", help="--table で件数も出す")
    parser.add_argument("--line", type=float, default=DEFAULT_LINE, help=f"「体重の割引」の線（既定: {DEFAULT_LINE:g}）")
    parser.add_argument("--rebuild", action="store_true", help="表 W を作り直す（元DB が更新されたときは自動で作り直す）")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE_FOLDER, help="表 W をとっておく場所（既定: reports/馬体重の表/cache）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
