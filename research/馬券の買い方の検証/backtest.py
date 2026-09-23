"""保存した予測・確定オッズ・払戻から、参加パターン × 買い方 の回収率を出す（研究「馬券の買い方の検証」の入口②）。

    uv run python research/馬券の買い方の検証/backtest.py --check-data                      # 読めた予測・オッズ・払戻の数だけ出す
    uv run python research/馬券の買い方の検証/backtest.py --settle-only                     # 精算表（レース × 買い方）を作って保存する
    uv run python research/馬券の買い方の検証/backtest.py --out reports/馬券の買い方の検証/search/2025H2.md   # 探索（検証期間）
    uv run python research/馬券の買い方の検証/backtest.py --confirm reports/馬券の買い方の検証/search/chosen.json --out reports/馬券の買い方の検証/confirm/2026.md  # 確認（テスト期間。1回だけ）

先に predict_all.py で予測の CSV を作り、--settle-only で精算表を作っておく。探索と確認の期間・しきい値の格子・採否の基準は
docs/03-protocol.md（analysis/periods.py・analysis/search/threshold_grid.py）。
元DB は事実表（探索・確認）とオッズ・払戻（--check-data・--settle-only）を読む間だけ開く。出力は reports/馬券の買い方の検証/（Git 対象外）。
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db  # noqa: E402
from 共通.render import Table  # noqa: E402

from 馬券の買い方の検証.analysis import periods  # noqa: E402
from 馬券の買い方の検証.analysis.column_names import RACE_ID  # noqa: E402
from 馬券の買い方の検証.analysis.loading import MarketBooks, MarketBooksLoader, MaterialsLoader  # noqa: E402
from 馬券の買い方の検証.analysis.participation import PATTERNS, PATTERNS_BY_KEY  # noqa: E402
from 馬券の買い方の検証.analysis.race_material import RaceMaterials  # noqa: E402
from 馬券の買い方の検証.analysis.repository import RaceDayRange  # noqa: E402
from 馬券の買い方の検証.analysis.search import (  # noqa: E402
    CHOSEN_LIMIT,
    AdoptionRule,
    ChosenStrategiesFile,
    ConfirmRunner,
    SearchRunner,
    StrategyEvaluator,
    StrategyGrid,
    StrategyResult,
)
from 馬券の買い方の検証.analysis.settlement import OddsFloorCut, PlanSettler, SettlementTable  # noqa: E402
from 馬券の買い方の検証.analysis.summary import PlanSummaryTables  # noqa: E402
from 馬券の買い方の検証.analysis.summary.strategy_tables import StrategyTables  # noqa: E402
from 馬券の買い方の検証.analysis.ticket import ALL_NARROW_PLANS, ALL_PLANS, ALL_WIDE_PLANS, TicketType  # noqa: E402

#: リポジトリ直下と、出力の置き場（Git 対象外の reports/）。
_REPO_ROOT = Path(__file__).resolve().parents[2]
_REPORTS_DIR = _REPO_ROOT / "reports" / "馬券の買い方の検証"
_DEFAULT_PREDICTIONS = _REPORTS_DIR / "predictions"
_DEFAULT_SETTLEMENT = _REPORTS_DIR / "settlement.csv"
_DEFAULT_CHOSEN = _REPORTS_DIR / "search" / "chosen.json"
_DEFAULT_ALL_RESULTS = _REPORTS_DIR / "search" / "all-results.csv"
#: 探索の途中経過を出す間隔（戦略の数）。
_PROGRESS_EVERY = 200
#: 全期間（予測のある期間）。探索・確認はこの中を切る。
_ALL_DAYS = RaceDayRange(periods.PREDICTION_FIRST_DAY, periods.PREDICTION_LAST_DAY)


def main(args) -> None:
    if args.check_data:
        cli.emit(_check_data(args), args)
        return
    if args.settle_only:
        cli.emit(_settle(args), args)
        return
    if args.confirm is not None:
        cli.emit(_confirm(args), args)
        return
    cli.emit(_search(args), args)


def _materials(args) -> RaceMaterials:
    """予測の CSV と事実表から材料表を作る（元DB は事実表を読む間だけ開く）。"""
    started = time.perf_counter()
    _say("予測と事実表を読んでいます…")
    with db.open_db(args.db) as con:
        materials = MaterialsLoader(args.predictions, con).load(_ALL_DAYS)
    _say(f"材料表 {time.perf_counter() - started:.0f} 秒（{len(materials.race_ids):,} レース）")
    return materials


def _load(args) -> tuple[RaceMaterials, MarketBooks]:
    """材料表と、オッズ・払戻の帳簿を読む（--check-data・--settle-only 用）。"""
    started = time.perf_counter()
    with db.open_db(args.db) as con:
        _say("予測と事実表を読んでいます…")
        materials = MaterialsLoader(args.predictions, con).load(_ALL_DAYS)
        books = MarketBooksLoader(con, progress=lambda name: _say(f"{name}を読んでいます…")).load(_ALL_DAYS)
    _say(f"読み込み {time.perf_counter() - started:.0f} 秒（{len(materials.race_ids):,} レース）")
    return materials, books


def _check_data(args) -> list[Table]:
    materials, books = _load(args)
    rows = [
        ["予測のあるレース", len(materials.race_ids)],
        ["払戻のあるレース", books.payout_races],
        ["返還のあったレース", books.refunded_races],
        *[[f"{ticket_type.label}のオッズのあるレース", books.odds_races[ticket_type]] for ticket_type in TicketType],
        *[[f"{ticket_type.label}が不成立・特払のレース", books.void_counts[ticket_type]] for ticket_type in TicketType],
    ]
    return [Table(["項目", "数"], rows, title="読めたデータ", note=f"期間 {_ALL_DAYS.first_day}〜{_ALL_DAYS.last_day}")]


def _settle(args) -> list[Table]:
    """全買い方 × 全レースの精算表を作って保存し、買い方ごとの要約を返す。"""
    materials, books = _load(args)
    started = time.perf_counter()
    cut = OddsFloorCut(books.odds_book)
    results = []
    for plan in ALL_PLANS:
        _say(f"{plan.name} を精算しています…")
        results += PlanSettler(plan, materials, books.payout_book, cut).settle_all()
    table = SettlementTable.from_results(results)
    table.write(args.settlement)
    _say(f"精算 {time.perf_counter() - started:.0f} 秒 → {args.settlement}")
    return PlanSummaryTables(table).tables()


def _search(args) -> list[Table]:
    """探索: 検証期間で格子の全戦略を評価し、採用候補を chosen.json に書く。"""
    materials = _materials(args)
    settlement = SettlementTable.read(args.settlement)
    races = materials.between(periods.SEARCH_FIRST_DAY, periods.SEARCH_LAST_DAY).races
    rule = AdoptionRule()
    runner = SearchRunner(StrategyEvaluator(settlement, PATTERNS_BY_KEY), StrategyGrid(PATTERNS, ALL_WIDE_PLANS, ALL_NARROW_PLANS),
                          rule, progress=_report_progress)
    started = time.perf_counter()
    results = runner.run(races)
    adopted = runner.adopted(results)
    chosen = _chosen(adopted, args)
    ChosenStrategiesFile(args.chosen).write([result.strategy for result in chosen], meta={
        "search_period": f"{periods.SEARCH_FIRST_DAY}〜{periods.SEARCH_LAST_DAY}", "adoption_rule": rule.describe(),
        "strategies_evaluated": len(results), "adopted": len(adopted), "picked": args.pick or "",
    })
    _write_all_results(results, args.all_results, rule)
    _say(f"探索 {time.perf_counter() - started:.0f} 秒: {len(results):,} 戦略、候補 {len(adopted)}、選んだ {len(chosen)} → {args.chosen}")
    tables = StrategyTables(PATTERNS_BY_KEY, rule)
    period = f"探索期間 {periods.SEARCH_FIRST_DAY}〜{periods.SEARCH_LAST_DAY}"
    return [
        tables.baseline_table(settlement, list(races[RACE_ID]), title=f"基準の買い方（{period}、全レース）"),
        tables.results_table(results, title=f"探索の結果（{period}。回収率の順）", limit=args.top),
        tables.results_table(adopted, title="採用候補（採否の基準を満たす戦略。回収率の順）"),
        tables.results_table(chosen, title="確認に回す戦略（chosen.json）"),
        tables.monthly_table(chosen, title="確認に回す戦略の月別の回収率（探索期間）"),
    ]


def _chosen(adopted: list[StrategyResult], args) -> list[StrategyResult]:
    """確認に回す戦略。``--pick`` があれば採用候補の表の番号で選び、無ければ上位 ``--chosen-limit``。"""
    if not args.pick:
        return adopted[:args.chosen_limit]
    numbers = [int(text) for text in args.pick.split(",")]
    outside = [number for number in numbers if number < 1 or number > len(adopted)]
    if outside:
        raise ValueError(f"採用候補の番号は 1〜{len(adopted)} です: {outside}")
    if len(numbers) > args.chosen_limit:
        raise ValueError(f"確認に回す戦略は {args.chosen_limit} つまでです（docs/03-protocol.md）: {len(numbers)} つ")
    return [adopted[number - 1] for number in numbers]


def _confirm(args) -> list[Table]:
    """確認: 選んだ戦略だけをテスト期間で評価する（1回だけ）。"""
    if args.out is not None and Path(args.out).exists():
        _say(f"注意: {args.out} は既にあります。確認は1回だけの約束です（docs/03-protocol.md）")
    materials = _materials(args)
    settlement = SettlementTable.read(args.settlement)
    races = materials.between(periods.CONFIRM_FIRST_DAY, periods.CONFIRM_LAST_DAY).races
    strategies = ChosenStrategiesFile(args.confirm).read()
    results = ConfirmRunner(StrategyEvaluator(settlement, PATTERNS_BY_KEY)).run(strategies, races)
    tables = StrategyTables(PATTERNS_BY_KEY, AdoptionRule())
    period = f"確認期間 {periods.CONFIRM_FIRST_DAY}〜{periods.CONFIRM_LAST_DAY}"
    return [
        tables.baseline_table(settlement, list(races[RACE_ID]), title=f"基準の買い方（{period}、全レース）"),
        tables.results_table(results, title=f"確認の結果（{period}。探索で選んだ順）"),
        tables.monthly_table(results, title="月別の回収率（確認期間）"),
    ]


def _write_all_results(results: list[StrategyResult], path: Path, rule: AdoptionRule) -> None:
    """全戦略の結果を CSV に残す（表は上位だけなので）。"""
    table = StrategyTables(PATTERNS_BY_KEY, rule).results_table(results, title="全戦略")
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(table.rows, columns=table.columns).to_csv(path, index=False, encoding="utf-8-sig")


def _report_progress(done: int, total: int) -> None:
    if done % _PROGRESS_EVERY == 0 or done == total:
        _say(f"  {done:,} / {total:,} 戦略")


def _say(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def build_parser():
    parser = cli.build_parser(__doc__, filters=False, limit=None)
    mode = parser.add_argument_group("何をするか（省略すると探索）")
    mode.add_argument("--check-data", action="store_true", help="読めた予測・オッズ・払戻の数だけ出して終わる")
    mode.add_argument("--settle-only", action="store_true", help="精算表を作って保存し、買い方ごとの要約を出して終わる")
    mode.add_argument("--confirm", type=Path, default=None, metavar="chosen.json", help="探索で選んだ戦略をテスト期間で確かめる（1回だけ）")
    search = parser.add_argument_group("探索")
    search.add_argument("--top", type=int, default=100, help="探索の結果の表に出す戦略の数（既定: 100。全部は --all-results の CSV）")
    search.add_argument("--chosen-limit", type=int, default=CHOSEN_LIMIT, help=f"確認に回す戦略の数の上限（既定: {CHOSEN_LIMIT}）")
    search.add_argument("--pick", default=None, metavar="1,7,11",
                        help="確認に回す戦略を、採用候補の表の番号で選ぶ（カンマ区切り。省略すると回収率の上位）")
    search.add_argument("--chosen", type=Path, default=_DEFAULT_CHOSEN,
                        help=f"選んだ戦略を書く JSON（既定: {_DEFAULT_CHOSEN.relative_to(_REPO_ROOT)}）")
    search.add_argument("--all-results", type=Path, default=_DEFAULT_ALL_RESULTS,
                        help=f"全戦略の結果を書く CSV（既定: {_DEFAULT_ALL_RESULTS.relative_to(_REPO_ROOT)}）")
    place = parser.add_argument_group("置き場")
    place.add_argument("--predictions", type=Path, default=_DEFAULT_PREDICTIONS,
                       help=f"predict_all.py が書いた予測のフォルダ（既定: {_DEFAULT_PREDICTIONS.relative_to(_REPO_ROOT)}）")
    place.add_argument("--settlement", type=Path, default=_DEFAULT_SETTLEMENT,
                       help=f"精算表の CSV（既定: {_DEFAULT_SETTLEMENT.relative_to(_REPO_ROOT)}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
