"""研究「指数の順位で組む買い目」の入口: 予想サイトの「指数 n位」の買い目の形を、今のモデルのレースの中の順位に当てて、過去のレースで全券種の的中率と回収率を出す。

    uv run python research/指数の順位で組む買い目/rank_tickets.py run --timing 当日      # 当日の予測で形を組んで精算する（元DB を読む。10分ほど）
    uv run python research/指数の順位で組む買い目/rank_tickets.py run --timing 前日      # 前日の予測
    uv run python research/指数の順位で組む買い目/rank_tickets.py baseline --timing 当日 # 比べる相手（今の印の買い目）を道具「印の成績」の買い目の CSV からまとめる（数分）
    uv run python research/指数の順位で組む買い目/rank_tickets.py report                # 置いてある精算と比べる相手から、成績の表を書く

順位は、走った馬を 3着以内の確率の高い順（主）と 1着の確率の高い順（比べる）に並べたもの。形は analysis/formation_catalog.py。
予測は研究「複勝以外の回収率100超」の半年ごとに学び直した区切りの予測（当日は 2015年〜、前日は 2019年〜）のテスト期間の行。
払戻は道具「印の成績」の精算と同じ部品（PayoutRepository）で確定の払戻を読む。1点 100円。
出るものは全部 Git 対象外の reports/指数の順位で組む買い目/（精算/<時点>-<順位>.parquet・比べる相手/<時点>.parquet・成績.md・docs向けの表.md）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 指数の順位で組む買い目.analysis.repo_paths import RepoPaths  # noqa: E402

PATHS = RepoPaths().add_to_sys_path()

import pandas as pd  # noqa: E402

from 共通 import db  # noqa: E402

from yosou.shared.repository import RaceDayRange  # noqa: E402

from 印の成績.prediction_file import TEST, PredictionFile  # noqa: E402
from 印の成績.race_results import RaceResults  # noqa: E402
from 指数の順位で組む買い目.analysis.baseline_summary import BaselineSummary  # noqa: E402
from 指数の順位で組む買い目.analysis.formation_catalog import FormationCatalog  # noqa: E402
from 指数の順位で組む買い目.analysis.payout_table import PayoutTable  # noqa: E402
from 指数の順位で組む買い目.analysis.rank_table import RANKINGS, RankTable  # noqa: E402
from 指数の順位で組む買い目.analysis.report_writer import ReportWriter  # noqa: E402
from 指数の順位で組む買い目.analysis.result_store import COLUMNS as SETTLED_COLUMNS, ResultStore  # noqa: E402
from 指数の順位で組む買い目.analysis.ticket_builder import TicketBuilder  # noqa: E402
from 指数の順位で組む買い目.analysis.ticket_settlement import TicketSettlement  # noqa: E402
from 指数の順位で組む買い目.analysis.timing_source import TIMINGS  # noqa: E402

#: 出力の置き場所（Git 対象外）。
OUT = PATHS.reports / "指数の順位で組む買い目"


def main() -> None:
    args = _parser().parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    store = ResultStore(Path(args.out_dir) if args.out_dir else OUT)
    {"run": _run, "baseline": _baseline, "report": _report}[args.command](args, store)


def _run(args: argparse.Namespace, store: ResultStore) -> None:
    source = TIMINGS[args.timing]
    top3 = _test_rows(PredictionFile(str(source.top3_path(PATHS.reports))).load())
    win = _test_rows(PredictionFile(str(source.win_path(PATHS.reports))).load())
    race_ids = top3["race_id"].drop_duplicates()
    print(f"{source.label}: テスト期間 {len(race_ids):,} レースの結果と払戻を読みます", file=sys.stderr, flush=True)
    with db.open_db(args.db) as con:
        results = RaceResults().read(con, race_ids)
        ranked = RankTable().build(top3, win, results)
        dates = pd.to_datetime(ranked["race_date"])
        days = RaceDayRange(dates.min().date(), dates.max().date())
        payouts = {ticket: PayoutTable(con).read(ticket, days, set(ranked["race_id"])) for ticket in FormationCatalog.tickets()}
    race_dates = ranked.drop_duplicates("race_id").set_index("race_id")["race_date"]
    builder, settlement = TicketBuilder(), TicketSettlement()
    for ranking, rank_column in RANKINGS.items():
        parts = []
        for formation in FormationCatalog.all():
            tickets = builder.build(ranked, rank_column, formation)
            per_race = settlement.settle(tickets, payouts[formation.ticket])
            per_race = per_race.assign(timing=source.label, ranking=ranking, group=formation.group, formation=formation.label,
                                       ticket=formation.ticket.label, race_date=per_race["race_id"].map(race_dates))
            parts.append(per_race[list(SETTLED_COLUMNS)])
            print(f"  {ranking} {formation.label}: {len(per_race):,} レース {int(per_race['points'].sum()):,} 点", file=sys.stderr, flush=True)
        path = store.save_settled(pd.concat(parts, ignore_index=True), source.label, ranking)
        print(f"保存先: {path}", file=sys.stderr, flush=True)


def _test_rows(predictions: pd.DataFrame) -> pd.DataFrame:
    tested = predictions[predictions["period"] == TEST]
    if tested.empty:
        raise LookupError("テスト期間の行がありません")
    return tested.reset_index(drop=True)


def _baseline(args: argparse.Namespace, store: ResultStore) -> None:
    source = TIMINGS[args.timing]
    csv_path = Path(args.csv) if args.csv else source.baseline_path(PATHS.reports)
    print(f"{csv_path} を読みます", file=sys.stderr, flush=True)
    table = BaselineSummary().summarize(csv_path)
    path = store.save_baseline(table, source.label)
    print(f"保存先: {path}（{table['race_id'].nunique():,} レース）", file=sys.stderr, flush=True)


def _report(args: argparse.Namespace, store: ResultStore) -> None:
    settled = store.load_settled()
    if settled.empty:
        raise LookupError(f"精算の表がありません: {store.folder}（先に run を実行してください）")
    full, docs = ReportWriter().write(settled, store.load_baselines(), store.folder)
    print(f"保存先: {full}\n{docs}", file=sys.stderr, flush=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--out-dir", default=None, help=f"出力の置き場所（既定: {OUT}）")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="予測で形を組んで精算する")
    run.add_argument("--timing", choices=tuple(TIMINGS), default="当日", help="予測の時点（既定: 当日）")
    run.add_argument("--db", default=None, help="元DB のパス（既定: ../jvdata-store/jvdata.duckdb か環境変数 YOSOU_DB）")
    baseline = commands.add_parser("baseline", help="比べる相手（今の印の買い目）をまとめる")
    baseline.add_argument("--timing", choices=tuple(TIMINGS), default="当日", help="時点（既定: 当日）")
    baseline.add_argument("--csv", default=None, help="道具「印の成績」の買い目の CSV（既定: 時点ごとの置き場所）")
    commands.add_parser("report", help="成績の表を書く")
    return parser


if __name__ == "__main__":
    main()
