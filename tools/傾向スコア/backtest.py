"""傾向スコアの検証: 終わったレースに同じ採点を当てて、点数の高い馬が本当に来ているかを成績7つで出す。

    uv run python tools/傾向スコア/backtest.py --from 2026-08-01 --to 2026-08-31 --out reports/trend-score/backtest-2026-08.md
    uv run python tools/傾向スコア/backtest.py --from 2026-01-01 --sample 300                 # 期間から 300 レースを等間隔に選ぶ
    uv run python tools/傾向スコア/backtest.py --from 2026-08-01 --venue 中山 --surface 芝 --no-market --min-z 0

出るもの: 点数の順位別の成績、比べる相手（同じレースの人気の順位別）、点数の帯別、点数の順位×人気の帯。
採点は ``trend_score.py`` と同じで、母集団も累積も「そのレースの開催日より前」だけを使う。1レースに数秒かかるので、
期間を区切るか ``--sample`` で間引く。馬名は出ないが成績の表なので、保存するなら ``reports/`` に置く。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db, trend, trend_backtest  # noqa: E402
from 共通.filters import FILTER_FIELDS  # noqa: E402
from 共通.trend_items import FACTORS  # noqa: E402

#: 途中経過を出す間隔（レース数）。
_PROGRESS_EVERY = 20
#: 絞り込みのうち、レースを選ぶのに使うもの。馬の条件（人気・枠 …）で選ぶと、レースの一部の馬だけを見ることになるので使わない。
_RACE_FILTERS: tuple[str, ...] = ("venue", "surface", "course", "distance", "condition", "class", "field", "from", "to", "month")


def main(args) -> None:
    options = trend.Options(scope=args.scope, min_runs=args.min_runs, good=args.good, bad=args.bad, min_z=args.min_z)
    used = [name for name in _RACE_FILTERS if cli.filter_value(args, name)]
    if "from" not in used:
        raise ValueError("--from で始まりの日を指定してください（全期間は時間がかかりすぎます。1レースに数秒）")
    filters = cli.filters_from(args, exclude=[field.name for field in FILTER_FIELDS if field.name not in _RACE_FILTERS])
    factors = trend_backtest.without_market() if args.no_market else FACTORS
    with db.open_db(args.db) as con:
        rids = trend_backtest.race_ids(con, filters, sample=args.sample)
        if not rids:
            raise LookupError(f"条件に合う確定レースがありません: {filters.describe()}")
        print(f"{len(rids):,} レースを採点します（{filters.describe()}）", file=sys.stderr)
        result = trend_backtest.run(con, rids, options, factors=factors, progress=_report_progress)
    tables = result.tables()
    tables[0].rows.insert(1, ["レースの条件", filters.describe() + ("・人気を使う項目を外す" if args.no_market else "")])
    cli.emit(tables, args)


def _report_progress(done: int, total: int, seconds: float) -> None:
    if done % _PROGRESS_EVERY == 0 or done == total:
        remaining = seconds / done * (total - done)
        print(f"  {done:,} / {total:,} レース（あと約 {remaining / 60:.0f} 分）", file=sys.stderr, flush=True)


def build_parser():
    parser = cli.build_parser(__doc__, filters=True, limit=None, filter_help={
        "pop": "（検証では使わない）", "odds": "（検証では使わない）", "frame": "（検証では使わない）", "finish": "（検証では使わない）",
        "sex": "（検証では使わない）", "age": "（検証では使わない）", "jockey": "（検証では使わない）", "trainer": "（検証では使わない）",
    })
    parser.add_argument("--sample", type=int, help="条件に合うレースから、この数だけ等間隔に選ぶ（時間を抑える）")
    parser.add_argument("--no-market", action="store_true", help="人気を使う項目（穴馬の型・人気馬の型）を外して採点する")
    rule = parser.add_argument_group("判定の線引き（trend_score.py と同じ）")
    rule.add_argument("--scope", choices=list(trend.LEVEL_BY_KEY), help="この段だけで判定する")
    rule.add_argument("--min-runs", type=int, default=trend.MIN_RUNS, help=f"判定に要る出走数（既定: {trend.MIN_RUNS}）")
    rule.add_argument("--good", type=float, default=trend.GOOD_RATIO, help=f"基準値の何倍以上で良いとするか（既定: {trend.GOOD_RATIO}）")
    rule.add_argument("--bad", type=float, default=trend.BAD_RATIO, help=f"基準値の何倍以下で悪いとするか（既定: {trend.BAD_RATIO}）")
    rule.add_argument("--min-z", type=float, default=trend.MIN_Z, help=f"差が偶然では起きにくいことを求める強さ（既定: {trend.MIN_Z}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
