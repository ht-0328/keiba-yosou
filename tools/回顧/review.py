"""回顧: 終わったレースの回顧（レースの回顧・馬の回顧ノート）を JV-Data から自動で作って保存し、買い目の記録に払戻を書き足す。

    uv run python tools/回顧/review.py                                   # 前に書いた範囲の次の日から、終わったレースの回顧を書き足す（今週の予想が自動で呼ぶ）
    uv run python tools/回顧/review.py --backfill                        # 2011年からの全レースをさかのぼって書く（初めの1回。2〜3分）
    uv run python tools/回顧/review.py --from 2026-10-01                 # その日以降を書き直す
    uv run python tools/回顧/review.py --show 2026101105040411           # 1レースの回顧と、不利のあった馬を見る
    uv run python tools/回顧/review.py --notes 2021100001                # 1頭の回顧ノート（不利のあった走）を見る
    uv run python tools/回顧/review.py --bets                            # 買い目の記録（直近）と、参加の種類ごとの投資・払戻・回収率

3つの表（設計書「買うレースと買い目を決める」08 の 3）を ``reports/回顧/review.duckdb`` に置く。人が手で書く列は無い。

- 表2「レースの回顧」: 予想のペース（予想したときに残した展開の予想③の確率）と結果のペース、終わった日のバイアスの傾き（内・前）、馬場状態。
- 表3「馬の回顧ノート」: 不利のあった馬だけ。出遅れ（最初のコーナーの位置が近5走の平均より 0.4 以上後ろ）・展開が向かなかった
  （結果の脚質とペースで引いた表 G が −0.01 以下）・バイアスと逆（結果の位置で出したバイアスの補正が −0.02 以下）。どれも 4着以下の馬だけ。
  程度（小・中・大）は線をどれだけ超えたかで、中以上なら次走の扱いは「見直す」。
- 表1「買い目の記録」: 今週の予想が買うレースを決めたときに書く行に、レースが終わったら払戻を書き足す（複勝・単勝）。

表3の判定に使う表 G と過去の傾きの表は、さかのぼって書くときはレースの年ごとに「その年より前のレース」で作る（学習データの材料と同じ決まり）。
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db  # noqa: E402
from 共通.render import Table  # noqa: E402

from yosou.review import DEFAULT_REVIEW_DB, ReviewStore, ReviewWorkflow, names  # noqa: E402

from 今週の予想.forecast_paces import ForecastPaces  # noqa: E402
from 今週の予想.forecast_store import DEFAULT_FOLDER as FORECAST_FOLDER  # noqa: E402
from 今週の予想.forecast_store import ForecastStore  # noqa: E402

#: さかのぼって書くときの最初の開催日（事実表の最初の年）。
BACKFILL_FROM = date(2011, 1, 1)


def main(args) -> None:
    store = ReviewStore(args.review_db)
    if args.show or args.notes or args.bets:
        cli.emit(_views(store, args), args)
        return
    start = BACKFILL_FROM if args.backfill else args.date_from
    with db.open_db(args.db) as con:
        written = ReviewWorkflow(store).run(con, start, ForecastPaces(ForecastStore(args.forecasts)).table())
    as_of = store.as_of()
    print(f"書き足しました: レースの回顧 {written[names.RACES_TABLE]:,} 行・馬の回顧ノート {written[names.HORSES_TABLE]:,} 行・"
          f"精算した買い目 {written[names.BETS_TABLE]:,} 点（範囲は {as_of} まで）→ {store.path}", file=sys.stderr, flush=True)


def _views(store: ReviewStore, args) -> list[Table]:
    if args.show:
        race = store.read(names.RACES_TABLE, f"{names.RACE_ID} = ?", [args.show])
        horses = store.read(names.HORSES_TABLE, f"{names.RACE_ID} = ?", [args.show])
        return [_frame_table(race, f"レースの回顧: {args.show}"), _frame_table(_notes_view(horses), f"馬の回顧ノート: {args.show}")]
    if args.notes:
        horses = store.read(names.HORSES_TABLE, f"{names.HORSE_ID} = ? ORDER BY {names.RACE_DATE}", [args.notes])
        return [_frame_table(_notes_view(horses), f"馬の回顧ノート: 馬 {args.notes}")]
    bets = store.read(names.BETS_TABLE, f"TRUE ORDER BY {names.RACE_DATE} DESC, {names.RACE_ID} LIMIT 60")
    return [_frame_table(bets, "買い目の記録（直近）"), _summary_table(store)]


def _notes_view(horses: pd.DataFrame) -> pd.DataFrame:
    if horses.empty:
        return horses
    view = horses.copy()
    view[names.DEGREE] = view[names.DEGREE].map(names.DEGREE_NAMES)
    return view[[names.RACE_ID, names.RACE_DATE, names.HORSE_ID, names.HANDICAPS, names.DEGREE, names.NEXT_RUN,
                 names.LATE_START_GAP, names.RESULT_SCORE, names.RESULT_BIAS]]


def _summary_table(store: ReviewStore) -> Table:
    bets = store.read(names.BETS_TABLE, f"{names.SETTLED} AND NOT {names.RECORD_ONLY}")
    rows = []
    for kind, group in bets.groupby(names.PARTICIPATION, sort=False):
        stake, payout = int(group[names.STAKE_YEN].sum()), int(group[names.PAYOUT_YEN].fillna(0).sum())
        rows.append([kind, len(group), f"{stake:,}", f"{payout:,}", f"{payout / stake:.1%}" if stake else ""])
    return Table(["参加の種類", "点数", "投資（円）", "払戻（円）", "回収率"], rows, title="精算した買い目の成績（財布ごと）",
                 note="記録だけの買い目は入れない。回収率 = 払戻 ÷ 投資")


def _frame_table(frame: pd.DataFrame, title: str) -> Table:
    rows = [[_plain(value) for value in row] for row in frame.itertuples(index=False)]
    return Table(list(frame.columns), rows, title=title)


def _plain(value):
    if value is None or (isinstance(value, float) and value != value):
        return None
    if isinstance(value, float):
        return round(value, 4)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def build_parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--backfill", action="store_true", help="2011年からの全レースをさかのぼって書く")
    parser.add_argument("--from", dest="date_from", type=date.fromisoformat, default=None, help="その日以降を書き直す（省略すると、前に書いた範囲の次から）")
    parser.add_argument("--show", metavar="rid", default=None, help="1レースの回顧と、不利のあった馬を見る")
    parser.add_argument("--notes", metavar="hid", default=None, help="1頭の回顧ノートを見る")
    parser.add_argument("--bets", action="store_true", help="買い目の記録と、参加の種類ごとの成績を見る")
    parser.add_argument("--review-db", type=Path, default=DEFAULT_REVIEW_DB, help="回顧の DuckDB の場所（既定: reports/回顧/review.duckdb）")
    parser.add_argument("--forecasts", type=Path, default=FORECAST_FOLDER, help="今週の予想の結果の置き場所（予想のペースを読む）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
