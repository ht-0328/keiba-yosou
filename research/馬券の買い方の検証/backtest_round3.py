"""保存した7つの区切りの予測から、期待値の高い穴馬の複勝の買い方を 枠A「馬を選ぶ」→ 枠B「レースを選ぶ」で評価する
（研究「馬券の買い方の検証」の入口③。3回目。決まりは docs/05-round3-protocol.md）。

    uv run python research/馬券の買い方の検証/backtest_round3.py --build-materials   # 材料表を作る（元DB は重賞かを読む間だけ開く）
    uv run python research/馬券の買い方の検証/backtest_round3.py --check-data        # 材料表の行数・レース数を区切りごとに出す（回収率は出さない）
    uv run python research/馬券の買い方の検証/backtest_round3.py --stage search      # 探索（2023〜2024年の4区切り。既定）
    uv run python research/馬券の買い方の検証/backtest_round3.py --stage confirm     # 確認（2025年の2区切り。1回だけ。明示したときだけ動く）
    uv run python research/馬券の買い方の検証/backtest_round3.py --stage final       # 最後の1回（2026年。1回だけ。明示したときだけ動く）

材料は 4つの予想の区切りごとの予測（出どころは reports/馬券の買い方の検証/round3/materials/README.md）。探索・確認・最後の1回は
元DB を開かない。出力は reports/馬券の買い方の検証/round3/<段階>/（Git 対象外）。確認と最後の1回は、出力が既にあれば動かない
（--allow-rerun で動かせるが、1回だけの約束を破ることになる）。
"""

from __future__ import annotations

import sys
import time
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db, render  # noqa: E402
from 共通.render import Table  # noqa: E402

from yosou.upset_level.dataset import BetType  # noqa: E402

from 馬券の買い方の検証.analysis.value_betting import (  # noqa: E402
    STRATEGIES,
    BaselineBets,
    ConfirmAdoptionRule,
    FinalRule,
    MaterialsBuilder,
    MaterialsStore,
    OperationalSummary,
    ResultTables,
    Round3Materials,
    SearchAdoptionRule,
    Stage,
    StrategyEvaluator,
    StrategyListFile,
    StrategyResult,
    UpsetBreakdown,
    WindowPreparer,
    default_sources,
)
from 馬券の買い方の検証.analysis.value_betting import columns as c  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REPORTS = _REPO_ROOT / "reports"
_ROUND3 = _REPORTS / "馬券の買い方の検証" / "round3"
#: 段階の間で渡すファイルの名前と、結果の表の名前。
_CHOSEN, _ADOPTED, _RESULT_MD, _TICKETS_CSV, _RESULTS_CSV = "chosen.json", "adopted.json", "結果.md", "買い目.csv", "全戦略.csv"
#: 元DB のロックを待つ上限（秒）。ほかの道具が読んでいる間は待つ。
_LOCK_WAIT_SECONDS = 1800.0
#: 買い目の CSV に書く列。
_TICKET_COLUMNS: tuple[str, ...] = (
    c.WINDOW, c.RACE_ID, c.RACE_DATE, c.HORSE_NO, c.POPULARITY, c.LONGSHOT_ZONE, c.LONGSHOT_PROB, c.PLACE_ODDS, c.PLACE_PRICE,
    c.PLACE_VALUE, c.MARK, c.LINE, c.STAKE_YEN, c.PAYOUT_YEN, c.FINISH,
)


def main(args) -> None:
    if args.build_materials:
        cli.emit(_build_materials(args), args)
        return
    if args.check_data:
        cli.emit(_check_data(MaterialsStore(args.materials).read()), args)
        return
    stage = Stage(args.stage)
    runner = {Stage.SEARCH: _search, Stage.CONFIRM: _confirm, Stage.FINAL: _final}[stage]
    cli.emit(runner(args, stage), args)


def _build_materials(args) -> Table:
    """4つの予測と学習データの表と元DB（重賞か）から材料表を作って保存する。"""
    sources = default_sources(args.reports)
    started = time.perf_counter()
    _say("予測と学習データの表を読み、元DB からレースの属性を読んでいます…")
    with db.open_db(args.db, lock_timeout=_LOCK_WAIT_SECONDS) as con:
        materials = MaterialsBuilder(sources, con).build()
    folder = MaterialsStore(args.materials).write(materials, {"sources": sources.describe()})
    _say(f"材料表 {time.perf_counter() - started:.0f} 秒 → {folder}")
    return _check_data(materials)


def _check_data(materials: Round3Materials) -> Table:
    """区切り × 期間 ごとの行数（回収率は出さない）。"""
    rows = []
    for window in materials.window_names:
        for part in (c.PART_VALID, c.PART_TEST):
            runners, races = materials.runners_of(window, part), materials.races_of(window, part)
            rows.append([
                window, part, len(runners), int(runners[c.RACE_ID].nunique()), int(runners[c.LONGSHOT_ZONE].notna().sum()),
                int(runners[c.DANGER_PROB].notna().sum()), int(races[c.upset_column(BetType.TRIO)].notna().sum()),
                int(races[c.IS_GRADED].fillna(False).astype(bool).sum()),
            ])
    columns = ["区切り", "期間", "1頭ごとの行", "レース数", "穴馬の行", "人気馬の行", "荒れ具合のあるレース", "平地の重賞"]
    return Table(columns, rows, title="材料表の数", note=f"払戻の履歴 {len(materials.price_history):,} 行（見込みの倍率を学ぶのに使う）")


def _search(args, stage: Stage) -> list[Table]:
    """探索: 12 の戦略を4区切りで評価し、採否の基準で候補を絞って chosen.json に書く。"""
    materials, evaluator, out = _prepare(args, stage)
    rule = SearchAdoptionRule()
    started = time.perf_counter()
    results = [evaluator.evaluate(strategy, stage.window_names) for strategy in STRATEGIES]
    ordered = sorted(results, key=lambda result: _conservative(result), reverse=True)
    chosen = rule.chosen(results)
    StrategyListFile(out / _CHOSEN).write([result.strategy for result in chosen], meta={
        "stage": stage.value, "windows": list(stage.window_names), "rule": rule.describe(),
        "evaluated": len(results), "candidates": sum(rule.is_candidate(result) for result in results),
    })
    _say(f"探索 {time.perf_counter() - started:.0f} 秒: {len(results)} 戦略、候補 {len(chosen)} → {out / _CHOSEN}")
    tables = ResultTables()
    period = f"探索 {'・'.join(stage.window_names)}"
    produced = [
        tables.baseline_table(BaselineBets(materials).summaries(stage.window_names), title=f"比べる目安（{period}）"),
        tables.results_table(ordered, [rule.verdict(result) for result in ordered], title=f"探索の結果（{period}。控えめな見積もりの順）"),
        tables.lines_table(ordered, title="区切りごとに使った線"),
        tables.results_table(chosen, ["確認へ"] * len(chosen), title=f"確認に回す戦略（{_CHOSEN}。{rule.describe()}）"),
        *_breakdowns(chosen, materials, stage),
    ]
    _write_all(produced, ordered, out)
    return produced


def _confirm(args, stage: Stage) -> list[Table]:
    """確認: 探索で選んだ戦略だけを 2025年の2区切りで評価し、採用を adopted.json に書く（1回だけ）。"""
    strategies = StrategyListFile(args.out_dir / Stage.SEARCH.folder / _CHOSEN).read()
    _guard_once(args, stage, _ADOPTED)
    if not strategies:
        return _nothing_to_confirm(args, stage)
    materials, evaluator, out = _prepare(args, stage)
    rule = ConfirmAdoptionRule()
    results = [evaluator.evaluate(strategy, stage.window_names) for strategy in strategies]
    final = rule.for_final(results)
    StrategyListFile(out / _ADOPTED).write([final.strategy] if final else [], meta={
        "stage": stage.value, "windows": list(stage.window_names), "rule": rule.describe(),
        "verdicts": {result.strategy.key: rule.verdict(result) for result in results},
    })
    _say(f"確認: {len(results)} 戦略、採用 {sum(rule.is_adopted(result) for result in results)} → {out / _ADOPTED}")
    tables = ResultTables()
    period = f"確認 {'・'.join(stage.window_names)}"
    produced = [
        tables.baseline_table(BaselineBets(materials).summaries(stage.window_names), title=f"比べる目安（{period}）"),
        tables.results_table(results, [rule.verdict(result) for result in results], title=f"確認の結果（{period}。探索の順位の順。{rule.describe()}）"),
        tables.lines_table(results, title="区切りごとに使った線"),
        *[tables.window_table(result, title=f"区切りごとの成績: {result.strategy.name}") for result in results],
        *_breakdowns(results, materials, stage),
    ]
    _write_all(produced, results, out)
    return produced


def _nothing_to_confirm(args, stage: Stage) -> list[Table]:
    """探索で候補が無かったとき: 確認期間の数値は見ずに、採用なしの adopted.json と、その旨の表だけを書く。"""
    out = args.out_dir / stage.folder
    out.mkdir(parents=True, exist_ok=True)
    rule = ConfirmAdoptionRule()
    StrategyListFile(out / _ADOPTED).write([], meta={"stage": stage.value, "windows": list(stage.window_names), "rule": rule.describe(),
                                                      "verdicts": {}, "note": "探索で候補が無かったので、確認する戦略が無い"})
    table = Table(["結果"], [["探索で採否の基準を満たす戦略が無かったので、確認する戦略が無い。確認期間の数値は見ていない（docs/05-round3-protocol.md）"]],
                  title="確認")
    (out / _RESULT_MD).write_text(render.render([table], "markdown"), encoding="utf-8")
    _say(f"確認: 探索の候補が無いので評価しない → {out / _ADOPTED}")
    return [table]


def _final(args, stage: Stage) -> list[Table]:
    """最後の1回: 確認で採用した1つだけを 2026年で評価し、提案に書く運用の数値を出す（1回だけ）。"""
    strategies = StrategyListFile(args.out_dir / Stage.CONFIRM.folder / _ADOPTED).read()
    if not strategies:
        return [Table(["結果"], [["確認で採用した戦略が無いので、最後の1回は行わない（docs/05-round3-protocol.md）"]], title="最後の1回")]
    _guard_once(args, stage, _RESULT_MD)
    materials, evaluator, out = _prepare(args, stage)
    rule = FinalRule()
    results = [evaluator.evaluate(strategy, stage.window_names) for strategy in strategies[:1]]
    tables = ResultTables()
    period = f"最後の1回 {'・'.join(stage.window_names)}"
    races = pd.concat([materials.races_of(window, c.PART_TEST) for window in stage.window_names], ignore_index=True)
    produced = [
        tables.baseline_table(BaselineBets(materials).summaries(stage.window_names), title=f"比べる目安（{period}）"),
        tables.results_table(results, [rule.verdict(result) for result in results], title=f"最後の1回の結果（{period}。{rule.describe()}）"),
        tables.window_table(results[0], title=f"区切りごとの成績: {results[0].strategy.name}"),
        tables.operational_table(OperationalSummary.of(results[0].tickets, races), title="提案に書く運用の数値（2026年に買ったとおり）"),
        *_breakdowns(results, materials, stage),
    ]
    _write_all(produced, results, out)
    return produced


def _prepare(args, stage: Stage) -> tuple[Round3Materials, StrategyEvaluator, Path]:
    materials = MaterialsStore(args.materials).read()
    missing = [name for name in stage.window_names if name not in materials.window_names]
    if missing:
        raise ValueError(f"材料表に区切りがありません: {'・'.join(missing)}（--build-materials で作り直してください）")
    out = args.out_dir / stage.folder
    out.mkdir(parents=True, exist_ok=True)
    return materials, StrategyEvaluator(WindowPreparer(materials)), out


def _guard_once(args, stage: Stage, marker: str) -> None:
    """確認・最後の1回は1回だけ。出力が既にあれば、--allow-rerun が無いかぎり動かさない。"""
    existing = args.out_dir / stage.folder / marker
    if existing.exists() and not args.allow_rerun:
        raise ValueError(f"{stage.label}は1回だけの約束です（docs/05-round3-protocol.md）。{existing} が既にあります。"
                         "やり直すなら --allow-rerun を付け、やり直したことを結果に書き添えてください")
    if existing.exists():
        _say(f"注意: {existing} を上書きします。{stage.label}を2回行ったことを結果に書き添えてください")


def _breakdowns(results: Sequence[StrategyResult], materials: Round3Materials, stage: Stage) -> list[Table]:
    races = pd.concat([materials.races_of(window, c.PART_TEST) for window in stage.window_names], ignore_index=True)
    return [UpsetBreakdown().table(result.tickets, races, title=f"荒れ具合の切り口: {result.strategy.name}") for result in results]


def _write_all(tables: Sequence[Table], results: Sequence[StrategyResult], out: Path) -> None:
    (out / _RESULT_MD).write_text(render.render(list(tables), "markdown"), encoding="utf-8")
    frames = [result.tickets.assign(戦略=result.strategy.key) for result in results if not result.tickets.empty]
    tickets = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["戦略", *_TICKET_COLUMNS])
    tickets[["戦略", *[column for column in _TICKET_COLUMNS if column in tickets.columns]]].to_csv(
        out / _TICKETS_CSV, index=False, encoding="utf-8-sig")
    pd.DataFrame([_result_record(result) for result in results]).to_csv(out / _RESULTS_CSV, index=False, encoding="utf-8-sig")


def _result_record(result: StrategyResult) -> dict[str, object]:
    total = result.total
    record: dict[str, object] = {
        "戦略": result.strategy.key, "名前": result.strategy.name, "点数": total.points, "レース数": total.races, "開催日数": total.days,
        "賭け金": total.stake_yen, "払戻": total.payout_yen, "回収率": total.rate, "90%の下限": total.lower, "90%の上限": total.upper,
        "控えめな見積もり": total.conservative,
    }
    record.update({f"{name} の回収率": summary.rate for name, summary in result.by_window.items()})
    record.update({f"{name} の線": line for name, line in result.lines.items()})
    return record


def _conservative(result: StrategyResult) -> float:
    value = result.total.conservative
    return float("-inf") if value != value else float(value)


def _say(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def build_parser():
    parser = cli.build_parser(__doc__, filters=False, limit=None)
    mode = parser.add_argument_group("何をするか（省略すると --stage search）")
    mode.add_argument("--build-materials", action="store_true", help="4つの予測と学習データの表から材料表を作って保存する（元DB を開く）")
    mode.add_argument("--check-data", action="store_true", help="材料表の行数・レース数を区切りごとに出して終わる（回収率は出さない）")
    mode.add_argument("--stage", choices=[stage.value for stage in Stage], default=Stage.SEARCH.value,
                      help="段階（search 探索 / confirm 確認 / final 最後の1回。confirm と final は1回だけ）")
    mode.add_argument("--allow-rerun", action="store_true", help="確認・最後の1回の出力が既にあっても動かす（1回だけの約束を破る。結果に書き添える）")
    place = parser.add_argument_group("置き場")
    place.add_argument("--reports", type=Path, default=_REPORTS, help="予測の出どころの親（既定: reports/）")
    place.add_argument("--materials", type=Path, default=_ROUND3 / "materials",
                       help=f"材料表のフォルダ（既定: {(_ROUND3 / 'materials').relative_to(_REPO_ROOT)}）")
    place.add_argument("--out-dir", type=Path, default=_ROUND3, help=f"結果を書く親フォルダ（既定: {_ROUND3.relative_to(_REPO_ROOT)}）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
